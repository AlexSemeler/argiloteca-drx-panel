"""
Projeto: Painel DRX Argiloteca

Descrição:
Versioned DRX analysis contracts shared by API routes and reports.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br

Colaboradores:
- Lucas Jantsch
- Arthur Oliveira

Instituição:
Universidade Federal do Rio Grande do Sul (UFRGS)

Projeto:
Argiloteca / CPAA

Licença:
Preservar licença existente no repositório.

Última revisão:
2026-06-21

Observação:
Este arquivo integra o sistema de análise, comparação e interpretação de difratogramas de raios X para argilominerais.
"""

from __future__ import annotations

import hashlib
import json
import math

from .drx import (
    ADVANCED_ALS_SCHEMA,
    ADVANCED_ALS_WAVELENGTH_CU,
    advanced_als_summary,
    compact_advanced_als_curve,
    process_advanced_als_curve,
    utc_now_iso,
)
from argiloteca.drx_core.contracts import (
    DRX_ANALYSIS_RUN_SCHEMA,
    DRX_CORE_VERSION,
    DRX_DIAGNOSTIC_RULES_SCHEMA,
    auxiliary_policy,
)


DIAGNOSTIC_D_RANGES = (
    {
        "rule_id": "kaolinite_7a",
        "mineral": "caulinita",
        "label": "Caulinita 001",
        "d_min": 7.05,
        "d_max": 7.30,
        "required_preparation": "any",
        "warning": "sobreposicao possivel com clorita proximo de 7 A",
    },
    {
        "rule_id": "illite_10a",
        "mineral": "ilita/mica",
        "label": "Ilita/Mica 001",
        "d_min": 9.80,
        "d_max": 10.25,
        "required_preparation": "any",
        "warning": "pico 10 A isolado requer contexto mineralogico e reflexoes confirmatorias",
    },
    {
        "rule_id": "chlorite_14a",
        "mineral": "clorita/vermiculita",
        "label": "Clorita/Vermiculita basal",
        "d_min": 13.70,
        "d_max": 14.80,
        "required_preparation": "any",
        "warning": "diferenciar com comportamento N/G/C e harmonicos",
    },
    {
        "rule_id": "smectite_eg_17a",
        "mineral": "esmectita expansiva",
        "label": "Esmectita glicolada",
        "d_min": 16.60,
        "d_max": 18.60,
        "required_preparation": "glicolado",
        "warning": "evidencia forte apenas quando comparada com natural e calcinada",
    },
)


def _config_hash(payload):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        payload: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = json.dumps(payload or {}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _finite_float(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _diagnostic_peak_matches(peaks, preparation=None):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        peaks: Valor de entrada consumido por esta etapa do fluxo.
        preparation: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    rows = []
    preparation = str(preparation or "").strip().lower()
    for peak in peaks or []:
        d_value = _finite_float(
            peak.get("d_angstrom")
            or peak.get("d")
            or peak.get("d_spacing")
            or peak.get("center_d_angstrom")
        )
        if d_value is None:
            continue
        for rule in DIAGNOSTIC_D_RANGES:
            required = rule["required_preparation"]
            if required != "any" and preparation and preparation != required:
                continue
            if rule["d_min"] <= d_value <= rule["d_max"]:
                center = (rule["d_min"] + rule["d_max"]) / 2.0
                delta = abs(d_value - center)
                rows.append(
                    {
                        "rule_id": rule["rule_id"],
                        "schema_version": DRX_DIAGNOSTIC_RULES_SCHEMA,
                        "mineral_candidate": rule["mineral"],
                        "label": rule["label"],
                        "status": "candidate",
                        "observed_d_angstrom": round(d_value, 5),
                        "observed_two_theta": peak.get("two_theta") or peak.get("center_2theta"),
                        "expected_d_min": rule["d_min"],
                        "expected_d_max": rule["d_max"],
                        "delta_d_from_range_center": round(delta, 5),
                        "source_peak": peak,
                        "warning": rule["warning"],
                        "interpretation_policy": "diagnostico assistido; requer curadoria e padrao completo",
                    }
                )
    return rows


def build_drx_analysis_run(
    *,
    filename,
    sample_code,
    source_sha256,
    parsed,
    identification=None,
    preparation=None,
    max_points=3000,
    stored=False,
    wavelength_angstrom=ADVANCED_ALS_WAVELENGTH_CU,
):
    """Run reusable DRX processing and return a versioned analysis contract."""
    identification = identification or {}
    advanced_processing = process_advanced_als_curve(
        parsed.two_theta,
        parsed.intensity,
        sample_id=sample_code,
        filename=filename,
        metadata={**(parsed.metadata or {}), "source_sha256": source_sha256},
        wavelength_angstrom=wavelength_angstrom,
    )
    advanced_summary = advanced_als_summary(advanced_processing)
    advanced_curve = compact_advanced_als_curve(advanced_processing, max_points=max_points)
    diagnostic_evidence = _diagnostic_peak_matches(
        advanced_processing.get("peaks") or identification.get("peaks") or [],
        preparation=preparation,
    )
    targeted_basal_peaks = advanced_processing.get("targeted_basal_peaks") or []
    targeted_basal_peaks_found = [
        row for row in targeted_basal_peaks
        if isinstance(row, dict) and row.get("status") in {"strong", "weak", "shoulder"}
    ]
    methods = {
        "advanced_schema": ADVANCED_ALS_SCHEMA,
        "preprocessing": advanced_processing.get("peak_processing") or {},
        "xrd_method": advanced_processing.get("xrd_method") or {
            "radiation": "Cu Kalpha",
            "wavelength_angstrom": ADVANCED_ALS_WAVELENGTH_CU,
        },
        "advanced_summary": advanced_summary,
        "diagnostic_rules_schema": DRX_DIAGNOSTIC_RULES_SCHEMA,
        "diagnostic_rule_count": len(DIAGNOSTIC_D_RANGES),
        "mineral_classification_source": identification.get("reference_source"),
        "mineral_classification_error": identification.get("classification_error"),
    }
    input_payload = {
        "filename": filename,
        "sample_code": sample_code,
        "source_sha256": source_sha256,
        "stored": bool(stored),
        "parser_format": (parsed.metadata or {}).get("parser_format"),
        "detected_format": (parsed.metadata or {}).get("detected_format"),
        "points": (parsed.metadata or {}).get("points"),
        "two_theta_start": (parsed.metadata or {}).get("two_theta_start"),
        "two_theta_end": (parsed.metadata or {}).get("two_theta_end"),
        "wavelength_angstrom": wavelength_angstrom,
    }
    analysis_run = {
        "schema_version": DRX_ANALYSIS_RUN_SCHEMA,
        "generated_at": utc_now_iso(),
        "input": input_payload,
        "methods": methods,
        "engine": {
            "name": "argiloteca_drx_core",
            "version": DRX_CORE_VERSION,
        },
        "artifacts": {
            "advanced_curve_available": bool(advanced_curve.get("available")),
            "advanced_curve_points": advanced_curve.get("points"),
            "baseline_points": len(((advanced_processing.get("curve") or {}).get("baseline") or [])),
            "peak_count": len(advanced_processing.get("peaks") or []),
            "fit_count": len(advanced_processing.get("fit_results") or []),
            "targeted_basal_peak_count": len(targeted_basal_peaks),
            "targeted_basal_peak_found_count": len(targeted_basal_peaks_found),
            "diagnostic_evidence_count": len(diagnostic_evidence),
        },
        "reproducibility": {
            "methods_hash": _config_hash(methods),
            "input_hash": _config_hash(input_payload),
        },
        "interpretation_policy": auxiliary_policy("drx"),
    }
    return {
        "analysis_run": analysis_run,
        "advanced_processing": advanced_processing,
        "advanced_summary": advanced_summary,
        "advanced_curve": advanced_curve,
        "diagnostic_evidence": diagnostic_evidence,
    }
