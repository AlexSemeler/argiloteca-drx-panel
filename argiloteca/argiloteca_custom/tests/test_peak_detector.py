"""Testes de contrato e tolerância para o detector de picos DRX."""

from __future__ import annotations

import re

import numpy as np

from argiloteca_drx_core.peak_detector import (
    DEFAULT_PARAMS,
    calcular_largura_zona_morta,
    detect_peaks,
    dynamic_detection_metadata,
    export_explainability,
    obter_multiplicador_ruido,
)


def _detected_peaks(synthetic_csv):
    result = detect_peaks(str(synthetic_csv), DEFAULT_PARAMS)
    return result, result["metadata"]["arg"]["peaks"]


def test_basic_detection(synthetic_csv):
    """O detector deve encontrar ao menos um pico aceito."""
    _result, peaks = _detected_peaks(synthetic_csv)
    assert len(peaks) >= 1


def test_position_error_within_tolerance(synthetic_csv, ground_truth_peaks):
    """Cada pico verdadeiro principal deve ter correspondente em ±0,1° 2θ."""
    _result, peaks = _detected_peaks(synthetic_csv)
    positions = np.array([peak["position_two_theta_deg"] for peak in peaks])
    for truth in ground_truth_peaks:
        delta = np.min(np.abs(positions - truth["position_two_theta_deg"]))
        assert delta <= 0.1


def test_minimum_snr_for_accepted_peaks(synthetic_csv):
    """Todos os picos aceitos devem respeitar SNR mínimo."""
    _result, peaks = _detected_peaks(synthetic_csv)
    assert peaks
    assert all(peak["snr"] >= 5.0 for peak in peaks)


def test_median_fwhm_limit(synthetic_csv):
    """A mediana do FWHM deve ficar abaixo do limite de aceitação."""
    _result, peaks = _detected_peaks(synthetic_csv)
    assert np.median([peak["fwhm_deg"] for peak in peaks]) <= 0.6


def test_json_contract(synthetic_csv):
    """Valida contrato JSON mínimo do detector."""
    result, peaks = _detected_peaks(synthetic_csv)
    assert result["version"] == "argiloteca.drx.peaks.v1"
    assert isinstance(result["metadata"]["arg"]["peaks"], list)
    checksum = result["metadata"]["provenance"]["checksum_sha256"]
    assert isinstance(checksum, str)
    assert re.fullmatch(r"[0-9a-f]{64}", checksum)
    assert result["data"]["n_points"] > 0
    assert result["data"]["two_theta_min"] == 5.0
    assert result["data"]["two_theta_max"] >= 64.99

    required = {
        "peak_id",
        "position_two_theta_deg",
        "fwhm_deg",
        "integrated_intensity",
        "position_uncertainty_deg",
        "snr",
        "attribution_method",
    }
    for peak in peaks:
        assert required.issubset(set(peak))
        assert isinstance(peak["peak_id"], int)
        assert isinstance(peak["position_two_theta_deg"], float)
        assert isinstance(peak["fwhm_deg"], float)
        assert isinstance(peak["integrated_intensity"], float)
        assert isinstance(peak["position_uncertainty_deg"], float)
        assert isinstance(peak["snr"], float)
        assert peak["attribution_method"] == "scipy_find_peaks+gaussian_fwhm"
        assert "dynamic_detection" in peak


def test_explainability_schema(synthetic_csv):
    """Explainability deve refletir picos e parâmetros efetivamente usados."""
    result, peaks = _detected_peaks(synthetic_csv)
    explanation = export_explainability(result["metadata"], peaks)
    assert explanation["method"] == "xrd_peak_pipeline_v1"
    assert set(explanation["global_metrics"]) == {
        "baseline_rmse",
        "snr_median",
        "fwhm_median_deg",
        "n_peaks",
    }
    assert explanation["global_metrics"]["n_peaks"] == len(peaks)
    assert explanation["params_used"] == result["metadata"]["provenance"]["params_used"]
    assert len(explanation["feature_attributions"]) == len(peaks)
    for attribution in explanation["feature_attributions"]:
        assert set(attribution) == {
            "peak_id",
            "influence_window_deg",
            "snr",
            "fwhm_deg",
            "integrated_intensity",
        }
        start, end = attribution["influence_window_deg"]
        assert start < end


def test_dynamic_detection_parameter_functions():
    """Valida valores-chave da parametrização dinâmica em Å."""
    assert calcular_largura_zona_morta(10.0) == 0.8
    assert calcular_largura_zona_morta(7.15) == 0.4
    assert calcular_largura_zona_morta(3.34) == 0.1
    assert obter_multiplicador_ruido(17.0) == 2.0
    assert obter_multiplicador_ruido(10.0) == 2.0
    assert obter_multiplicador_ruido(12.0) == 4.0


def test_dynamic_detection_metadata_applied_with_d_spacing():
    """Pico com d-spacing confiável recebe metadados explicáveis."""
    metadata = dynamic_detection_metadata(10.0)
    assert metadata["applied"] is True
    assert metadata["dead_zone_A"] == 0.8
    assert metadata["noise_multiplier"] == 2.0
    assert "ilita" in metadata["context"]


def test_dynamic_detection_metadata_unavailable_without_d_spacing():
    """Sem d-spacing/λ explícito, a parametrização fica marcada como indisponível."""
    metadata = dynamic_detection_metadata(None)
    assert metadata["applied"] is False
    assert metadata["reason"] == "d_spacing unavailable or wavelength not explicit"


def test_detect_peaks_marks_dynamic_detection_unavailable_without_wavelength(synthetic_csv):
    """O detector não calcula d-spacing silenciosamente sem λ explícito."""
    _result, peaks = _detected_peaks(synthetic_csv)
    assert peaks
    assert all(peak["dynamic_detection"]["applied"] is False for peak in peaks)


def test_detect_peaks_applies_dynamic_detection_with_explicit_wavelength(synthetic_csv):
    """Quando λ é explícito, os picos recebem parametrização dinâmica explicável."""
    result = detect_peaks(str(synthetic_csv), {**DEFAULT_PARAMS, "wavelength_angstrom": 1.5406})
    peaks = result["metadata"]["arg"]["peaks"]
    assert peaks
    assert all(peak["dynamic_detection"]["applied"] is True for peak in peaks)
