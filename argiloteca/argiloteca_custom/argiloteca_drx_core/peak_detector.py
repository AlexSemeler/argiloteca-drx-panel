"""Detector mínimo de picos para difratogramas DRX/XRD.

O módulo lê espectros tabulares medidos em 2θ, remove baseline, suaviza o
sinal, detecta máximos com SciPy e retorna um contrato JSON serializável com
proveniência e métricas básicas de explainability.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pybaselines import Baseline
from scipy.signal import find_peaks, peak_widths, savgol_filter


DEFAULT_PARAMS: dict[str, Any] = {
    "baseline": {"method": "asls", "lam": 1e5, "p": 0.01, "niter": 10},
    "smooth": {"window_length": 11, "polyorder": 3},
    "find_peaks": {"prominence_sigma": 4.0, "height_sigma": 3.0, "distance_deg": 0.10},
}

PEAK_ATTRIBUTION_METHOD = "scipy_find_peaks+gaussian_fwhm"
PEAK_KEYS = [
    "peak_id",
    "position_two_theta_deg",
    "fwhm_deg",
    "integrated_intensity",
    "position_uncertainty_deg",
    "snr",
    "attribution_method",
]


def _deep_merge(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    """Combina parâmetros aninhados sem modificar os dicionários originais."""
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _checksum_sha256(filepath: str | Path) -> str:
    """Calcula SHA-256 do arquivo bruto lido pelo detector."""
    digest = hashlib.sha256()
    with Path(filepath).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_spectrum(filepath: str) -> tuple[np.ndarray, np.ndarray]:
    """Lê CSV/TSV com colunas de 2θ e intensidade.

    O separador é inferido pelo pandas e os nomes de coluna são normalizados de
    forma case-insensitive para aceitar variações como `2theta` e `twoTheta`.
    """
    frame = pd.read_csv(filepath, sep=None, engine="python")
    normalized = {_normalize_column_name(column): column for column in frame.columns}
    theta_column = next((normalized[key] for key in ("twotheta", "2theta", "two_theta") if key in normalized), None)
    intensity_column = next((normalized[key] for key in ("intensity", "counts", "i") if key in normalized), None)
    if theta_column is None or intensity_column is None:
        raise ValueError("Arquivo deve conter colunas two_theta/2theta e intensity.")

    data = frame[[theta_column, intensity_column]].apply(pd.to_numeric, errors="coerce").dropna()
    if data.empty:
        raise ValueError("Arquivo não contém pontos numéricos válidos.")
    data = data.sort_values(theta_column)
    return data[theta_column].to_numpy(float), data[intensity_column].to_numpy(float)


def _normalize_column_name(value: Any) -> str:
    """Normaliza nomes de colunas para comparação tolerante."""
    return str(value).strip().lower().replace(" ", "").replace("-", "").replace("_", "")


def _baseline(intensity: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    """Estima baseline por pybaselines usando ASLS/ALS."""
    cfg = params.get("baseline", {})
    method = str(cfg.get("method", "asls")).lower()
    lam = float(cfg.get("lam", 1e5))
    p = float(cfg.get("p", 0.01))
    max_iter = int(cfg.get("max_iter", cfg.get("niter", 10)))
    baseline = Baseline()
    if method == "asls":
        y_base, _ = baseline.asls(intensity, lam=lam, p=p, max_iter=max_iter)
    elif method == "airpls":
        y_base, _ = baseline.airpls(intensity, lam=lam, max_iter=max_iter)
    elif method == "iasls":
        y_base, _ = baseline.iasls(intensity, lam=lam, p=p, max_iter=max_iter)
    else:
        raise ValueError(f"Método de baseline não suportado: {method}")
    return np.asarray(y_base, dtype=float)


def _smooth(y: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    """Suaviza o sinal com Savitzky-Golay preservando picos estreitos."""
    cfg = params.get("smooth", {})
    window = int(cfg.get("window_length", 11))
    polyorder = int(cfg.get("polyorder", 3))
    if window % 2 == 0:
        window += 1
    window = max(polyorder + 2 + ((polyorder + 2) % 2 == 0), window)
    if window >= len(y):
        window = len(y) - 1 if len(y) % 2 == 0 else len(y)
    if window < 3 or window <= polyorder:
        return y.astype(float, copy=True)
    return savgol_filter(y, window_length=window, polyorder=polyorder)


def _estimate_noise(y: np.ndarray) -> float:
    """Estima ruído robusto por MAD escalado para sigma gaussiano."""
    residual = np.diff(y) / np.sqrt(2.0) if len(y) > 2 else y
    median = np.median(residual)
    mad = np.median(np.abs(residual - median))
    sigma = 1.4826 * mad
    if not np.isfinite(sigma) or sigma <= 0:
        sigma = float(np.std(residual))
    return max(float(sigma), 1e-12)


def _mean_step(two_theta: np.ndarray) -> float:
    """Calcula passo médio absoluto do eixo 2θ."""
    diffs = np.diff(two_theta)
    finite = diffs[np.isfinite(diffs) & (np.abs(diffs) > 0)]
    if finite.size == 0:
        raise ValueError("Eixo two_theta precisa ter ao menos dois pontos distintos.")
    return float(np.median(np.abs(finite)))


def _peak_candidates(y: np.ndarray, params: dict[str, Any], step_deg: float | None = None) -> np.ndarray:
    """Seleciona candidatos com `scipy.signal.find_peaks`."""
    cfg = params.get("find_peaks", {})
    noise = _estimate_noise(y)
    distance_deg = float(cfg.get("distance_deg", 0.10))
    distance_pts = max(1, int(round(distance_deg / step_deg))) if step_deg else 1
    peaks, _ = find_peaks(
        y,
        prominence=float(cfg.get("prominence_sigma", 4.0)) * noise,
        height=float(cfg.get("height_sigma", 3.0)) * noise,
        distance=distance_pts,
    )
    return peaks.astype(int)


def _peak_widths_fwhm(y: np.ndarray, peaks: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    """Mede FWHM em pontos pelo algoritmo de largura relativa de SciPy."""
    if len(peaks) == 0:
        return np.array([], dtype=float)
    widths, _height, _left, _right = peak_widths(y, peaks, rel_height=0.5)
    return np.asarray(widths, dtype=float)


def _integrated_intensity(two_theta: np.ndarray, y: np.ndarray, peak_idx: int, width_pts: float) -> float:
    """Integra área local do pico por regra trapezoidal."""
    half_width = max(2, int(np.ceil(width_pts)))
    start = max(0, int(peak_idx) - half_width)
    end = min(len(y), int(peak_idx) + half_width + 1)
    if end - start < 2:
        return 0.0
    local_y = np.clip(y[start:end], 0.0, None)
    return float(np.trapz(local_y, two_theta[start:end]))


def _refine_position_parabolic(two_theta: np.ndarray, y: np.ndarray, peak_idx: int) -> float:
    """Refina a posição do máximo por interpolação parabólica local."""
    if peak_idx <= 0 or peak_idx >= len(y) - 1:
        return float(two_theta[peak_idx])
    y0, y1, y2 = float(y[peak_idx - 1]), float(y[peak_idx]), float(y[peak_idx + 1])
    denominator = y0 - 2.0 * y1 + y2
    if abs(denominator) < 1e-12:
        return float(two_theta[peak_idx])
    offset_pts = 0.5 * (y0 - y2) / denominator
    offset_pts = float(np.clip(offset_pts, -1.0, 1.0))
    return float(two_theta[peak_idx] + offset_pts * _mean_step(two_theta))


def detect_peaks(filepath: str, params: dict) -> dict[str, Any]:
    """Detecta picos em espectro DRX e retorna contrato JSON serializável."""
    params_used = _deep_merge(DEFAULT_PARAMS, params or {})
    two_theta, intensity = _read_spectrum(filepath)
    step_deg = _mean_step(two_theta)
    y_baseline = _baseline(intensity, params_used)
    corrected = np.clip(intensity - y_baseline, 0.0, None)
    smoothed = _smooth(corrected, params_used)
    noise = _estimate_noise(corrected - smoothed)
    peak_indices = _peak_candidates(smoothed, params_used, step_deg=step_deg)
    width_pts = _peak_widths_fwhm(smoothed, peak_indices, params_used)

    peaks: list[dict[str, Any]] = []
    for peak_idx, width in zip(peak_indices, width_pts):
        height = float(max(smoothed[int(peak_idx)], corrected[int(peak_idx)]))
        snr = height / noise
        if snr < 5.0:
            continue
        fwhm_deg = float(width * step_deg)
        peak = {
            "peak_id": len(peaks) + 1,
            "position_two_theta_deg": round(_refine_position_parabolic(two_theta, smoothed, int(peak_idx)), 6),
            "fwhm_deg": round(fwhm_deg, 6),
            "integrated_intensity": round(_integrated_intensity(two_theta, corrected, int(peak_idx), float(width)), 6),
            "position_uncertainty_deg": round(step_deg / 2.0, 6),
            "snr": round(float(snr), 6),
            "attribution_method": PEAK_ATTRIBUTION_METHOD,
        }
        peaks.append(peak)

    baseline_rmse = float(np.sqrt(np.mean(np.square(intensity - y_baseline))))
    return {
        "version": "argiloteca.drx.peaks.v1",
        "metadata": {
            "arg": {"peaks": peaks},
            "provenance": {
                "instrument": params_used.get("instrument"),
                "radiation": params_used.get("radiation"),
                "params_used": params_used,
                "checksum_sha256": _checksum_sha256(filepath),
                "baseline_rmse": round(baseline_rmse, 6),
            },
        },
        "data": {
            "n_points": int(len(two_theta)),
            "two_theta_min": float(np.min(two_theta)),
            "two_theta_max": float(np.max(two_theta)),
        },
    }


def export_explainability(spectrum_meta: dict, peaks: list[dict]) -> dict[str, Any]:
    """Gera explainability serializável para picos detectados."""
    provenance = (spectrum_meta or {}).get("provenance", {})
    params_used = provenance.get("params_used", {})
    snrs = [float(peak["snr"]) for peak in peaks if "snr" in peak]
    fwhms = [float(peak["fwhm_deg"]) for peak in peaks if "fwhm_deg" in peak]
    return {
        "method": "xrd_peak_pipeline_v1",
        "global_metrics": {
            "baseline_rmse": float(provenance.get("baseline_rmse", 0.0) or 0.0),
            "snr_median": float(np.median(snrs)) if snrs else 0.0,
            "fwhm_median_deg": float(np.median(fwhms)) if fwhms else 0.0,
            "n_peaks": int(len(peaks)),
        },
        "feature_attributions": [
            {
                "peak_id": int(peak["peak_id"]),
                "influence_window_deg": [
                    float(peak["position_two_theta_deg"] - 2.0 * peak["fwhm_deg"]),
                    float(peak["position_two_theta_deg"] + 2.0 * peak["fwhm_deg"]),
                ],
                "snr": float(peak["snr"]),
                "fwhm_deg": float(peak["fwhm_deg"]),
                "integrated_intensity": float(peak["integrated_intensity"]),
            }
            for peak in peaks
        ],
        "params_used": params_used,
    }

