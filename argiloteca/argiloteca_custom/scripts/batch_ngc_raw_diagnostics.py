#!/usr/bin/env python3
"""
Projeto: Painel DRX Argiloteca

Descrição:
Batch N/G/C RAW diagnostics for Argiloteca DRX. This script adapts a local laboratory workflow into a reusable panel-side tool. It groups Natural/Glycolated/Calcined curves, applies optional quartz-axis calibration, removes background with ALS, detects peaks, emits structured JSON/CSV reports and can optionally route RAW files into mineral folders. All diagnoses are auxiliary and non-confirmatory.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br


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

import argparse
import csv
import json
import os
import re
import shutil
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/argiloteca_mplconfig")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from scipy import sparse
from scipy.signal import find_peaks, peak_widths, savgol_filter
from scipy.sparse.linalg import spsolve


SCRIPT_DIR = Path(__file__).resolve().parent
APP_DIR = SCRIPT_DIR.parents[1]
CUSTOM_DIR = SCRIPT_DIR.parents[0]
for import_path in (str(APP_DIR), str(CUSTOM_DIR)):
    if import_path not in sys.path:
        sys.path.insert(0, import_path)

from argiloteca_drx_core.curves import CurveParseError, calculate_d_spacing, calculate_two_theta, parse_curve_bytes


warnings.filterwarnings("ignore", message=".*prominence of 0.*")
warnings.filterwarnings("ignore", message=".*width of 0.*")


DEFAULT_WINDOW_LENGTH = 25
DEFAULT_POLYORDER = 2
DEFAULT_ALS_LAMBDA = 1e6
DEFAULT_ALS_P = 0.01
DEFAULT_START_X_SEARCH = 4.0
DEFAULT_PEAK_PROMINENCE = 0.01
DEFAULT_MAX_PEAKS = 15
DEFAULT_WAVELENGTH_CU = 1.5406
DEFAULT_K_SCHERRER = 0.9
DEFAULT_PEAK_BOUNDARY_THRESHOLD = 0.01
DEFAULT_QUARTZ_SEARCH_D = (3.27, 3.42)
DEFAULT_TARGET_QUARTZ_D = 3.34
DEFAULT_MIN_QUARTZ_INTENSITY_PERCENT = 2.0

RANGES = {
    "illite_10a": (9.73, 10.38),
    "illite_10a_n": (9.84, 10.36),
    "illite_10a_g": (9.82, 10.30),
    "illite_10a_c": (9.73, 10.38),
    "kaolinite_7a": (6.96, 7.42),
    "kaolinite_7a_n": (6.97, 7.42),
    "kaolinite_7a_g": (6.96, 7.42),
    "kaolinite_7a_c_check": (6.96, 7.42),
    "smectite_n": (13.46, 16.86),
    "smectite_g": (16.06, 18.31),
    "smectite_c": (9.65, 10.37),
    "chlorite_14a": (13.58, 14.87),
    "chlorite_14a_n": (13.74, 14.74),
    "chlorite_14a_g": (13.83, 14.72),
    "chlorite_14a_c": (13.58, 14.87),
    "quartz_101": (3.27, 3.42),
    "quartz_101_n": (3.28, 3.41),
    "quartz_101_g": (3.28, 3.42),
    "quartz_101_c": (3.27, 3.42),
    "quartz_100": (4.23, 4.35),
}

TARGETED_BASAL_RANGES = {
    "smectite_n_13_16a": {"mineral": "Esmectita", "label": "Esmectita N 13.46-16.86 A", "d_min": 13.46, "d_max": 16.86},
    "smectite_g_17a": {"mineral": "Esmectita", "label": "Esmectita G 16.06-18.31 A", "d_min": 16.06, "d_max": 18.31},
    "smectite_c_10a": {"mineral": "Esmectita", "label": "Esmectita C 9.65-10.37 A", "d_min": 9.65, "d_max": 10.37},
    "illite_10a": {"mineral": "Ilita", "label": "Ilita/Mica 9.73-10.38 A", "d_min": 9.73, "d_max": 10.38},
    "illite_5a": {"mineral": "Ilita", "label": "Ilita/Mica 5 A", "d_min": 4.85, "d_max": 5.15},
    "illite_3_33a": {"mineral": "Ilita", "label": "Ilita/Mica 3.33 A", "d_min": 3.26, "d_max": 3.40},
    "kaolinite_7a": {"mineral": "Caulinita", "label": "Caulinita 6.96-7.42 A", "d_min": 6.96, "d_max": 7.42},
    "kaolinite_3_57a": {"mineral": "Caulinita", "label": "Caulinita 3.57 A", "d_min": 3.52, "d_max": 3.62},
    "chlorite_14a": {"mineral": "Clorita", "label": "Clorita 13.58-14.87 A", "d_min": 13.58, "d_max": 14.87},
    "chlorite_7a": {"mineral": "Clorita", "label": "Clorita 7 A", "d_min": 6.9, "d_max": 7.4},
    "chlorite_4_72a": {"mineral": "Clorita", "label": "Clorita 4.72 A", "d_min": 4.60, "d_max": 4.85},
    "chlorite_3_53a": {"mineral": "Clorita", "label": "Clorita 3.53 A", "d_min": 3.45, "d_max": 3.65},
    "quartz_101": {"mineral": "Quartzo", "label": "Quartzo 101", "d_min": 3.27, "d_max": 3.42},
    "quartz_100": {"mineral": "Quartzo", "label": "Quartzo 100", "d_min": 4.23, "d_max": 4.35},
}


def read_curve(path: Path):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    parsed = parse_curve_bytes(path.read_bytes(), filename=path.name)
    return np.asarray(parsed.two_theta, dtype=float), np.asarray(parsed.intensity, dtype=float), parsed.metadata


def baseline_als(y, lam, p, niter=10):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        y: Valor de entrada consumido por esta etapa do fluxo.
        lam: Valor de entrada consumido por esta etapa do fluxo.
        p: Valor de entrada consumido por esta etapa do fluxo.
        niter: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    length = len(y)
    if length < 3:
        return np.zeros_like(y)
    diagonals = [np.ones(length), -2.0 * np.ones(length), np.ones(length)]
    d_matrix = sparse.diags(diagonals, [0, 1, 2], shape=(length - 2, length), format="csc")
    weights = np.ones(length)
    for _ in range(niter):
        w_matrix = sparse.spdiags(weights, 0, length, length)
        z_matrix = w_matrix + lam * d_matrix.T.dot(d_matrix)
        baseline = spsolve(z_matrix, weights * y)
        weights = p * (y > baseline) + (1.0 - p) * (y < baseline)
    return baseline


def safe_savgol(y, window_length, polyorder):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        y: Valor de entrada consumido por esta etapa do fluxo.
        window_length: Valor de entrada consumido por esta etapa do fluxo.
        polyorder: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if len(y) < 5:
        return y.astype(float)
    window = min(int(window_length), len(y) - 1 if len(y) % 2 == 0 else len(y))
    if window % 2 == 0:
        window -= 1
    window = max(window, int(polyorder) + 3)
    if window % 2 == 0:
        window += 1
    if window >= len(y):
        window = len(y) - 1 if len(y) % 2 == 0 else len(y)
    if window <= int(polyorder):
        return y.astype(float)
    return savgol_filter(y, window_length=window, polyorder=int(polyorder))


def calculate_quartz_offset(x, y, config):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        x: Valor de entrada consumido por esta etapa do fluxo.
        y: Valor de entrada consumido por esta etapa do fluxo.
        config: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    y_filtered = safe_savgol(y, config.window_length, config.polyorder)
    max_y = float(np.max(y_filtered)) if len(y_filtered) else 0.0
    if max_y <= 0:
        return None
    threshold_y = (config.min_quartz_intensity_percent / 100.0) * max_y
    d_min, d_max = config.quartz_search_d
    min_two_theta = calculate_two_theta(d_max, wavelength=config.wavelength)
    max_two_theta = calculate_two_theta(d_min, wavelength=config.wavelength)
    if min_two_theta is None or max_two_theta is None:
        return None
    in_range = (x >= min_two_theta) & (x <= max_two_theta)
    x_quartz = x[in_range]
    y_quartz = y_filtered[in_range]
    if not len(x_quartz):
        return None
    peaks, _ = find_peaks(y_quartz, height=threshold_y, prominence=0.01 * max(float(np.max(y_quartz)), 1.0))
    if not len(peaks):
        return None
    peak_index = peaks[int(np.argmax(y_quartz[peaks]))]
    observed_two_theta = float(x_quartz[peak_index])
    target_two_theta = calculate_two_theta(config.target_quartz_d, wavelength=config.wavelength)
    if target_two_theta is None:
        return None
    return float(target_two_theta - observed_two_theta)


def intensity_in_range(peaks, d_min, d_max):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        peaks: Valor de entrada consumido por esta etapa do fluxo.
        d_min: Valor de entrada consumido por esta etapa do fluxo.
        d_max: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    values = [float(peak["i_abs"]) for peak in peaks if d_min <= float(peak["d"]) <= d_max]
    return max(values) if values else 0.0


def targeted_quality(relative_height, local_contrast, local_maximum):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        relative_height: Valor de entrada consumido por esta etapa do fluxo.
        local_contrast: Valor de entrada consumido por esta etapa do fluxo.
        local_maximum: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if local_contrast < 0.003:
        return "not_found"
    if not local_maximum and (relative_height >= 0.008 or local_contrast >= 0.008):
        return "shoulder"
    if relative_height >= 0.05 and local_contrast >= 0.02 and local_maximum:
        return "strong"
    if local_contrast >= 0.006 or (relative_height >= 0.006 and local_maximum):
        return "weak"
    return "not_found"


def targeted_basal_peak_scan(x, y_final, config):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        x: Valor de entrada consumido por esta etapa do fluxo.
        y_final: Valor de entrada consumido por esta etapa do fluxo.
        config: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    maximum = float(np.max(y_final)) if len(y_final) and float(np.max(y_final)) > 0 else 1.0
    rows = []
    for range_id, window in TARGETED_BASAL_RANGES.items():
        d_min = float(window["d_min"])
        d_max = float(window["d_max"])
        theta_min = calculate_two_theta(d_max, wavelength=config.wavelength)
        theta_max = calculate_two_theta(d_min, wavelength=config.wavelength)
        base = {
            "range_id": range_id,
            "mineral": window["mineral"],
            "label": window["label"],
            "expected_d_min": d_min,
            "expected_d_max": d_max,
            "source": "targeted_basal_peak_scan",
            "interpretation_policy": "pico basal direcionado auxiliar; nao confirma fase mineralogica",
        }
        if theta_min is None or theta_max is None:
            rows.append({**base, "status": "not_found", "observed_peak": None})
            continue
        indices = np.where((x >= theta_min) & (x <= theta_max))[0]
        if not len(indices):
            rows.append({**base, "status": "not_found", "observed_peak": None})
            continue
        peak_index = int(indices[np.argmax(y_final[indices])])
        window_values = y_final[indices]
        peak_value = float(y_final[peak_index])
        local_contrast = float((np.max(window_values) - np.min(window_values)) / maximum) if len(window_values) else 0.0
        relative_height = peak_value / maximum if maximum else 0.0
        local_maximum = 0 < peak_index < len(y_final) - 1 and y_final[peak_index] >= y_final[peak_index - 1] and y_final[peak_index] >= y_final[peak_index + 1]
        status = targeted_quality(relative_height, local_contrast, local_maximum)
        observed = None
        observed_d = calculate_d_spacing(float(x[peak_index]), wavelength=config.wavelength)
        if status != "not_found" and observed_d:
            observed = {
                "peak_index": "targeted:%s" % range_id,
                "source_index": peak_index,
                "two_theta": round(float(x[peak_index]), 6),
                "d": round(float(observed_d), 6),
                "i_abs": round(peak_value, 6),
                "i_norm": round(float(relative_height * 100.0), 6),
                "relative_intensity": round(float(relative_height * 100.0), 6),
                "source": "targeted_basal_peak_scan",
                "targeted_range_id": range_id,
                "targeted_status": status,
            }
        rows.append(
            {
                **base,
                "status": status,
                "observed_d_angstrom": observed.get("d") if observed else None,
                "observed_two_theta": observed.get("two_theta") if observed else None,
                "intensity": observed.get("i_abs") if observed else None,
                "relative_intensity": observed.get("relative_intensity") if observed else None,
                "local_contrast": round(local_contrast, 8),
                "observed_peak": observed,
            }
        )
    return rows


def merge_targeted_peaks(peak_details, targeted_rows):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        peak_details: Valor de entrada consumido por esta etapa do fluxo.
        targeted_rows: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    merged = list(peak_details or [])
    for row in targeted_rows or []:
        observed = row.get("observed_peak") if isinstance(row, dict) else None
        if not observed:
            continue
        observed_d = observed.get("d")
        if observed_d is None:
            continue
        if any(abs(float(peak.get("d") or 0) - float(observed_d)) <= 0.04 for peak in merged):
            continue
        merged.append(
            {
                "idx": observed.get("source_index"),
                "two_theta": observed.get("two_theta"),
                "d": observed.get("d"),
                "i_abs": observed.get("i_abs"),
                "i_norm": observed.get("i_norm"),
                "fwhm": None,
                "area": None,
                "tau_nm": None,
                "source": "targeted_basal_peak_scan",
                "targeted_range_id": row.get("range_id"),
                "targeted_status": row.get("status"),
            }
        )
    return sorted(merged, key=lambda peak: float(peak.get("two_theta") or 999.0))


def diagnose_clays(peaks_n, peaks_g, peaks_c):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        peaks_n: Valor de entrada consumido por esta etapa do fluxo.
        peaks_g: Valor de entrada consumido por esta etapa do fluxo.
        peaks_c: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    diagnoses = []
    minerals = []

    int_n_10 = intensity_in_range(peaks_n, *RANGES["illite_10a_n"])
    int_g_10 = intensity_in_range(peaks_g, *RANGES["illite_10a_g"])
    int_c_10 = intensity_in_range(peaks_c, *RANGES["illite_10a_c"])
    if int_n_10 > 0 and int_g_10 > 0 and int_c_10 > 0:
        diagnoses.append({
            "mineral": "Ilita",
            "message": "Pico estavel entre %.1f-%.1f A nos tratamentos N/G/C." % RANGES["illite_10a"],
            "evidence": {"intensity_n": int_n_10, "intensity_g": int_g_10, "intensity_c": int_c_10},
        })
        minerals.append("Ilita")

    int_n_es = intensity_in_range(peaks_n, *RANGES["smectite_n"])
    int_g_es = intensity_in_range(peaks_g, *RANGES["smectite_g"])
    int_c_es = intensity_in_range(peaks_c, *RANGES["smectite_c"])
    if int_n_es > 0 and int_g_es > 0 and int_c_es > 0:
        diagnoses.append({
            "mineral": "Esmectita",
            "message": "Expansao no glicol e colapso na calcinada compativeis com esmectita.",
            "evidence": {"intensity_n": int_n_es, "intensity_g": int_g_es, "intensity_c": int_c_es},
        })
        minerals.append("Esmectita")

    int_n_7 = intensity_in_range(peaks_n, *RANGES["kaolinite_7a_n"])
    int_g_7 = intensity_in_range(peaks_g, *RANGES["kaolinite_7a_g"])
    int_c_7 = intensity_in_range(peaks_c, *RANGES["kaolinite_7a_c_check"])
    if int_n_7 > 0 and int_g_7 > 0 and int_c_7 < (0.1 * int_n_7):
        diagnoses.append({
            "mineral": "Caulinita",
            "message": "Pico 7 A destruido ou fortemente reduzido na calcinacao.",
            "evidence": {"intensity_n": int_n_7, "intensity_g": int_g_7, "intensity_c": int_c_7},
        })
        minerals.append("Caulinita")

    int_n_cl = intensity_in_range(peaks_n, *RANGES["chlorite_14a_n"])
    int_c_cl = intensity_in_range(peaks_c, *RANGES["chlorite_14a_c"])
    if int_n_cl > 0 and int_c_cl > 0:
        status = "intensificado" if int_c_cl > int_n_cl else "preservado"
        diagnoses.append({
            "mineral": "Clorita",
            "message": "Pico ~14.2 A %s na calcinada." % status,
            "evidence": {"intensity_n": int_n_cl, "intensity_c": int_c_cl},
        })
        minerals.append("Clorita")

    int_n_qz_101 = intensity_in_range(peaks_n, *RANGES["quartz_101_n"])
    int_g_qz_101 = intensity_in_range(peaks_g, *RANGES["quartz_101_g"])
    int_c_qz_101 = intensity_in_range(peaks_c, *RANGES["quartz_101_c"])
    int_n_qz_100 = intensity_in_range(peaks_n, *RANGES["quartz_100"])
    if int_n_qz_101 > 0 and int_g_qz_101 > 0 and int_c_qz_101 > 0:
        message = "Pico principal 101 do quartzo imutavel nos tres tratamentos."
        if int_n_qz_100 > 0:
            message += " Pico secundario 100 tambem observado."
        diagnoses.append({
            "mineral": "Quartzo",
            "message": message,
            "evidence": {"intensity_n": int_n_qz_101, "intensity_g": int_g_qz_101, "intensity_c": int_c_qz_101, "secondary_100_n": int_n_qz_100},
        })
        minerals.append("Quartzo")

    if not diagnoses:
        diagnoses.append({
            "mineral": None,
            "message": "Inconclusivo para os minerais primarios avaliados ou picos sobrepostos/ausentes.",
            "evidence": {},
        })
    return sorted(set(minerals)), diagnoses


def process_spectrum(path: Path, offset_two_theta, config):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
        offset_two_theta: Valor de entrada consumido por esta etapa do fluxo.
        config: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    x_raw, y_raw, metadata = read_curve(path)
    x = x_raw + float(offset_two_theta or 0.0)
    y_filtered = np.clip(safe_savgol(y_raw, config.window_length, config.polyorder), 0, None)
    y_final = np.clip(y_filtered - baseline_als(y_filtered, lam=config.als_lambda, p=config.als_p), 0, None)

    y_search = np.copy(y_final)
    y_search[x < config.start_x_search] = 0.0
    max_amp = float(np.max(y_search)) if len(y_search) and float(np.max(y_search)) > 0 else 1.0
    y_norm = y_search / max_amp

    peak_indices, _ = find_peaks(y_norm, prominence=config.peak_prominence)
    top_peaks = sorted(peak_indices, key=lambda index: y_norm[index], reverse=True)[: config.max_peaks]
    top_peaks.sort()
    widths = peak_widths(y_final, top_peaks, rel_height=0.5)[0] if top_peaks else []
    step_x = abs(float(x[1] - x[0])) if len(x) > 1 else 1.0

    peak_details = []
    for order, peak_index in enumerate(top_peaks):
        two_theta = float(x[peak_index])
        d_spacing = calculate_d_spacing(two_theta, wavelength=config.wavelength)
        theta_rad = np.radians(two_theta / 2.0)
        peak_value = float(y_final[peak_index])
        threshold = peak_value * config.peak_boundary_threshold
        left_index = int(peak_index)
        right_index = int(peak_index)
        while left_index > 0 and y_final[left_index] > threshold:
            left_index -= 1
        while right_index < len(y_final) - 1 and y_final[right_index] > threshold:
            right_index += 1
        area = float(np.trapezoid(y_final[left_index : right_index + 1], x[left_index : right_index + 1]))
        fwhm = float(widths[order] * step_x) if len(widths) else 0.0
        fwhm_rad = np.radians(fwhm)
        tau = (
            (config.scherrer_k * (config.wavelength / 10.0)) / (fwhm_rad * np.cos(theta_rad))
            if fwhm_rad > 0 and np.cos(theta_rad) != 0
            else 0.0
        )
        peak_details.append({
            "idx": int(peak_index),
            "two_theta": round(two_theta, 6),
            "d": round(float(d_spacing), 6) if d_spacing else None,
            "i_abs": round(peak_value, 6),
            "i_norm": round(float(y_norm[peak_index] * 100.0), 6),
            "fwhm": round(fwhm, 6),
            "area": round(area, 6),
            "tau_nm": round(float(tau), 6),
        })

    targeted_basal_peaks = targeted_basal_peak_scan(x, y_final, config)
    diagnostic_peaks = merge_targeted_peaks(peak_details, targeted_basal_peaks)

    return {
        "path": str(path),
        "metadata": metadata,
        "offset_two_theta": round(float(offset_two_theta or 0.0), 6),
        "x": x,
        "y_final": y_final,
        "top_peaks": [int(index) for index in top_peaks],
        "peak_details": peak_details,
        "targeted_basal_peaks": targeted_basal_peaks,
        "diagnostic_peaks": diagnostic_peaks,
    }


def infer_treatment(filename):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        filename: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    stem = Path(filename).stem.strip()
    patterns = [
        r"^(?P<base>.*?)\s*\((?P<trat>[NGC])\)$",
        r"^(?P<base>.*?)[\s_-]+(?P<trat>[NGC])$",
        r"^(?P<base>.*?)(?P<trat>[NGC])$",
    ]
    for pattern in patterns:
        match = re.search(pattern, stem, re.IGNORECASE)
        if not match:
            continue
        base = (match.group("base") or "").strip(" _-()")
        treatment = match.group("trat").upper()
        if base:
            return base, treatment
    return None, None


def discover_samples(input_dir: Path, extensions, recursive=True, group_by_basename=False):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        input_dir: Valor de entrada consumido por esta etapa do fluxo.
        extensions: Valor de entrada consumido por esta etapa do fluxo.
        recursive: Valor de entrada consumido por esta etapa do fluxo.
        group_by_basename: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    samples = {}
    iterator = input_dir.rglob("*") if recursive else input_dir.iterdir()
    for path in sorted(iterator):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        base, treatment = infer_treatment(path.name)
        if not base or treatment not in {"N", "G", "C"}:
            continue
        sample_id = base
        if recursive and not group_by_basename:
            try:
                parent = path.parent.relative_to(input_dir)
                sample_id = str(parent / base) if str(parent) != "." else base
            except ValueError:
                sample_id = str(path.parent / base)
        samples.setdefault(sample_id, {})[treatment] = path
    return samples


def plot_sample(sample_id, processed, minerals, output_dir: Path, config):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        sample_id: Valor de entrada consumido por esta etapa do fluxo.
        processed: Valor de entrada consumido por esta etapa do fluxo.
        minerals: Valor de entrada consumido por esta etapa do fluxo.
        output_dir: Valor de entrada consumido por esta etapa do fluxo.
        config: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    figure, axis = plt.subplots(figsize=(12, 8))
    max_y = max([float(np.max(data["y_final"])) for data in processed.values()] or [100.0])
    y_offset = max_y * 0.5
    colors = {"C": "red", "G": "green", "N": "blue"}
    order = ["C", "G", "N"]
    for index, treatment in enumerate(order):
        if treatment not in processed:
            continue
        data = processed[treatment]
        x_values = data["x"]
        y_plot = data["y_final"] + (len(order) - 1 - index) * y_offset
        axis.plot(x_values, y_plot, label="%s sem background" % treatment, color=colors[treatment], linewidth=1.5)
        top_peaks = data["top_peaks"]
        if top_peaks:
            axis.plot(x_values[top_peaks], y_plot[top_peaks], "x", color="black", markersize=6)
        for peak in data["peak_details"]:
            if peak.get("d") is None:
                continue
            axis.annotate(
                "%.2f" % peak["d"],
                (peak["two_theta"], y_plot[peak["idx"]]),
                textcoords="offset points",
                xytext=(0, 5),
                ha="center",
                fontsize=8,
            )
    axis.axvline(x=config.start_x_search, color="gray", linestyle=":", label="Corte baixo angulo")
    axis.set_title("Difratograma comparativo N/G/C: %s" % sample_id)
    axis.set_xlabel("2theta (graus)")
    axis.set_ylabel("Intensidade absoluta (cps), curvas deslocadas")
    axis.legend(loc="upper right")
    axis.grid(True, linestyle="--", alpha=0.6)
    figure.tight_layout()
    target_names = minerals or ["Inconclusivos"]
    saved = []
    for name in target_names:
        target = output_dir / safe_dir_name(name)
        target.mkdir(parents=True, exist_ok=True)
        plot_path = target / ("Grafico_Espectro_%s.png" % safe_dir_name(sample_id))
        figure.savefig(plot_path, dpi=150, bbox_inches="tight")
        saved.append(str(plot_path))
    plt.close(figure)
    return saved


def safe_dir_name(value):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip())
    return text.strip("_") or "sem_nome"


def route_raw_files(sample_paths, minerals, output_dir: Path):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        sample_paths: Valor de entrada consumido por esta etapa do fluxo.
        minerals: Valor de entrada consumido por esta etapa do fluxo.
        output_dir: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    target_names = minerals or ["Inconclusivos"]
    copied = []
    for name in target_names:
        target = output_dir / safe_dir_name(name)
        target.mkdir(parents=True, exist_ok=True)
        for path in sample_paths.values():
            destination = target / path.name
            shutil.copy2(path, destination)
            copied.append(str(destination))
    return copied


def process_sample(sample_id, paths, output_dir: Path, config):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        sample_id: Valor de entrada consumido por esta etapa do fluxo.
        paths: Valor de entrada consumido por esta etapa do fluxo.
        output_dir: Valor de entrada consumido por esta etapa do fluxo.
        config: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    raw_starts = {}
    warnings_out = []
    for treatment, path in paths.items():
        try:
            x_temp, _, _ = read_curve(path)
            raw_starts[treatment] = float(x_temp[0])
        except Exception as exc:
            warnings_out.append("Erro ao ler inicio de %s (%s): %s" % (sample_id, treatment, exc))

    anchor_treatment = "N"
    absolute_offset_n = 0.0
    if "N" in paths:
        try:
            x_n, y_n, _ = read_curve(paths["N"])
            quartz_offset = calculate_quartz_offset(x_n, y_n, config)
            if quartz_offset is not None:
                absolute_offset_n = float(quartz_offset)
            else:
                warnings_out.append("Quartzo nao detectado em N; eixo bruto usado como mestre.")
        except Exception as exc:
            warnings_out.append("Erro ao calibrar N por quartzo: %s" % exc)
    else:
        anchor_treatment = sorted(raw_starts.keys())[0] if raw_starts else None
        warnings_out.append("Amostra sem tratamento N; usando %s como ancora." % (anchor_treatment or "nenhuma"))

    processed = {}
    for treatment in ["N", "G", "C"]:
        if treatment not in paths:
            continue
        path = paths[treatment]
        filename = path.name
        offset = 0.0
        if filename in config.manual_offsets:
            offset = float(config.manual_offsets[filename])
            warnings_out.append("Correcao manual %.6f aplicada em %s." % (offset, filename))
        elif treatment == anchor_treatment and anchor_treatment == "N":
            offset = absolute_offset_n
        elif anchor_treatment and treatment in raw_starts and anchor_treatment in raw_starts:
            anchor_corrected = raw_starts[anchor_treatment] + (absolute_offset_n if anchor_treatment == "N" else 0.0)
            offset = anchor_corrected - raw_starts[treatment]
        try:
            processed[treatment] = process_spectrum(path, offset, config)
        except (CurveParseError, OSError, ValueError) as exc:
            warnings_out.append("Erro ao processar %s (%s): %s" % (sample_id, treatment, exc))

    minerals = []
    diagnoses = [{
        "mineral": None,
        "message": "Tratamentos insuficientes. Necessario N, G e C para diagnostico comparativo.",
        "evidence": {},
    }]
    if all(treatment in processed for treatment in ("N", "G", "C")):
        minerals, diagnoses = diagnose_clays(
            processed["N"]["diagnostic_peaks"],
            processed["G"]["diagnostic_peaks"],
            processed["C"]["diagnostic_peaks"],
        )

    plots = plot_sample(sample_id, processed, minerals, output_dir, config) if config.write_plots and processed else []
    copied = route_raw_files(paths, minerals, output_dir) if config.copy_raw else []
    return {
        "sample_id": sample_id,
        "input_files": {treatment: str(path) for treatment, path in sorted(paths.items())},
        "anchor_treatment": anchor_treatment,
        "absolute_offset_n": round(float(absolute_offset_n), 6),
        "detected_minerals": minerals,
        "diagnoses": diagnoses,
        "treatments": {
            treatment: {
                "file": data["path"],
                "metadata": data["metadata"],
                "offset_two_theta": data["offset_two_theta"],
                "peaks": data["peak_details"],
                "diagnostic_peaks": data["diagnostic_peaks"],
                "targeted_basal_peaks": data["targeted_basal_peaks"],
            }
            for treatment, data in sorted(processed.items())
        },
        "plots": plots,
        "copied_files": copied,
        "warnings": warnings_out,
        "policy": "Diagnostico N/G/C auxiliar e nao confirmatorio; requer revisao mineralogica.",
    }


def diagnostic_score_for_mineral(sample, mineral):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        sample: Valor de entrada consumido por esta etapa do fluxo.
        mineral: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    diagnoses = [row for row in sample.get("diagnoses") or [] if row.get("mineral") == mineral]
    if not diagnoses:
        return 0.0
    if mineral == "Clorita":
        return 0.9
    if mineral == "Esmectita":
        return 0.88
    if mineral == "Ilita":
        return 0.82
    if mineral == "Caulinita":
        return 0.82
    if mineral == "Quartzo":
        return 0.65
    return 0.5


def group_classification_candidates(sample):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        sample: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    rows = []
    for mineral in sample.get("detected_minerals") or []:
        if not mineral:
            continue
        score = diagnostic_score_for_mineral(sample, mineral)
        role = "accessory"
        if mineral in {"Clorita", "Esmectita", "Ilita", "Caulinita"}:
            role = "probable" if score >= 0.8 else "possible"
        rows.append(
            {
                "mineral": mineral,
                "role": role,
                "status": "probable" if role == "probable" else "possible",
                "ngc_group_score": round(score, 4),
                "basal_diagnostic_score": round(score, 4),
                "raw_candidate_score": None,
                "similarity_score": None,
                "reference_match_score": None,
                "auxiliary_neural_score": None,
                "interpretation_policy": "classificacao N/G/C auxiliar; nao confirma fase mineralogica",
            }
        )
    return sorted(rows, key=lambda row: (row["role"] != "probable", -(row["ngc_group_score"] or 0), row["mineral"]))


def best_treatment_summary(sample):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        sample: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    rows = []
    for treatment, data in (sample.get("treatments") or {}).items():
        basal_hits = [
            row for row in data.get("targeted_basal_peaks") or []
            if row.get("status") in {"strong", "weak", "shoulder"}
            and row.get("mineral") in {"Clorita", "Esmectita", "Ilita", "Caulinita"}
        ]
        rows.append(
            {
                "treatment": treatment,
                "filename": Path(data.get("file") or "").name,
                "basal_hit_count": len(basal_hits),
                "strong_hit_count": len([row for row in basal_hits if row.get("status") == "strong"]),
            }
        )
    rows.sort(key=lambda row: (row["strong_hit_count"], row["basal_hit_count"]), reverse=True)
    return rows[0] if rows else {}


def build_ngc_group_classification_payload(batch_payload):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        batch_payload: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    results = batch_payload.get("results") or []
    groups = []
    for sample in results:
        candidates = group_classification_candidates(sample)
        probable = [row for row in candidates if row.get("role") == "probable"]
        possible = [row for row in candidates if row.get("role") == "possible"]
        accessory = [row for row in candidates if row.get("role") == "accessory"]
        groups.append(
            {
                "sample_id": sample.get("sample_id"),
                "status": "trio completo" if all(key in (sample.get("treatments") or {}) for key in ("N", "G", "C")) else "trio incompleto",
                "available_treatments": sorted((sample.get("treatments") or {}).keys()),
                "probable_minerals": probable,
                "possible_minerals": possible,
                "accessory_minerals": accessory,
                "candidates": candidates,
                "diagnoses": sample.get("diagnoses") or [],
                "warnings": sample.get("warnings") or [],
                "best_treatment": best_treatment_summary(sample),
                "supporting_peaks": {
                    treatment: (data.get("diagnostic_peaks") or [])[:30]
                    for treatment, data in (sample.get("treatments") or {}).items()
                },
                "targeted_basal_peaks": {
                    treatment: data.get("targeted_basal_peaks") or []
                    for treatment, data in (sample.get("treatments") or {}).items()
                },
                "policy": "triagem mineralogica orientada por N/G/C; nao usar como confirmacao automatica",
            }
        )
    return {
        "schema_version": "argiloteca.drx.ngc_group_classification.v1",
        "generated_at": batch_payload.get("generated_at"),
        "input_dir": batch_payload.get("input_dir"),
        "samples_total": batch_payload.get("samples_total"),
        "samples_processed": batch_payload.get("samples_processed"),
        "score_contract": {
            "raw_candidate_score": "score do classificador por RAW isolado; secundario quando houver trio N/G/C",
            "ngc_group_score": "score auxiliar do comportamento N/G/C do grupo",
            "basal_diagnostic_score": "score dos picos basais e companheiros",
            "similarity_score": "reservado para similaridade com RAWs da Argiloteca",
            "reference_match_score": "reservado para padroes de referencia curados/RRUFF/COD",
            "auxiliary_neural_score": "reservado para evidencia neural auxiliar",
        },
        "groups": groups,
        "interpretation_policy": "classificacao auxiliar para priorizar curadoria; nao confirma mineralogia",
    }


def write_ngc_group_csv(payload, path: Path):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        payload: Valor de entrada consumido por esta etapa do fluxo.
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    rows = []
    for group in payload.get("groups") or []:
        for candidate in group.get("candidates") or []:
            rows.append(
                {
                    "sample_id": group.get("sample_id"),
                    "status": group.get("status"),
                    "available_treatments": ";".join(group.get("available_treatments") or []),
                    "mineral": candidate.get("mineral"),
                    "role": candidate.get("role"),
                    "candidate_status": candidate.get("status"),
                    "ngc_group_score": candidate.get("ngc_group_score"),
                    "basal_diagnostic_score": candidate.get("basal_diagnostic_score"),
                    "best_treatment": (group.get("best_treatment") or {}).get("treatment"),
                    "policy": group.get("policy"),
                }
            )
    fieldnames = [
        "sample_id",
        "status",
        "available_treatments",
        "mineral",
        "role",
        "candidate_status",
        "ngc_group_score",
        "basal_diagnostic_score",
        "best_treatment",
        "policy",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_csv(results, path: Path):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        results: Valor de entrada consumido por esta etapa do fluxo.
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    rows = []
    for sample in results:
        for treatment, data in sample.get("treatments", {}).items():
            for peak in data.get("peaks", []):
                rows.append({
                    "sample_id": sample["sample_id"],
                    "treatment": treatment,
                    "file": data.get("file"),
                    "detected_minerals": ";".join(sample.get("detected_minerals") or []),
                    "two_theta": peak.get("two_theta"),
                    "d": peak.get("d"),
                    "i_abs": peak.get("i_abs"),
                    "i_norm": peak.get("i_norm"),
                    "fwhm": peak.get("fwhm"),
                    "area": peak.get("area"),
                    "tau_nm": peak.get("tau_nm"),
                })
    fieldnames = ["sample_id", "treatment", "file", "detected_minerals", "two_theta", "d", "i_abs", "i_norm", "fwhm", "area", "tau_nm"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_manual_offsets(path):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not path:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Arquivo de offsets manuais precisa ser um objeto JSON {filename: offset}.")
    return {str(key): float(value) for key, value in payload.items()}


def parse_args(argv=None):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        argv: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    parser = argparse.ArgumentParser(description="Processa lote N/G/C de difratogramas RAW/TXT/XY/DAT.")
    parser.add_argument("--input-dir", default="input_files", help="Pasta com arquivos N/G/C.")
    parser.add_argument("--output-dir", default="output_files", help="Pasta de saida para relatorios, plots e roteamento opcional.")
    parser.add_argument("--extensions", default=".raw,.txt,.xy,.dat,.csv", help="Extensoes aceitas, separadas por virgula.")
    parser.add_argument("--window-length", type=int, default=DEFAULT_WINDOW_LENGTH)
    parser.add_argument("--polyorder", type=int, default=DEFAULT_POLYORDER)
    parser.add_argument("--als-lambda", type=float, default=DEFAULT_ALS_LAMBDA)
    parser.add_argument("--als-p", type=float, default=DEFAULT_ALS_P)
    parser.add_argument("--start-x-search", type=float, default=DEFAULT_START_X_SEARCH)
    parser.add_argument("--peak-prominence", type=float, default=DEFAULT_PEAK_PROMINENCE)
    parser.add_argument("--max-peaks", type=int, default=DEFAULT_MAX_PEAKS)
    parser.add_argument("--wavelength", type=float, default=DEFAULT_WAVELENGTH_CU)
    parser.add_argument("--scherrer-k", type=float, default=DEFAULT_K_SCHERRER)
    parser.add_argument("--peak-boundary-threshold", type=float, default=DEFAULT_PEAK_BOUNDARY_THRESHOLD)
    parser.add_argument("--quartz-search-d", default="3.27,3.42")
    parser.add_argument("--target-quartz-d", type=float, default=DEFAULT_TARGET_QUARTZ_D)
    parser.add_argument("--min-quartz-intensity-percent", type=float, default=DEFAULT_MIN_QUARTZ_INTENSITY_PERCENT)
    parser.add_argument("--manual-offsets-json", default=None, help="JSON opcional {filename: offset_2theta}.")
    parser.add_argument("--copy-raw", action="store_true", help="Copia arquivos para subpastas por mineral detectado.")
    parser.add_argument("--no-plots", action="store_true", help="Nao gera PNG empilhado.")
    parser.add_argument("--no-recursive", action="store_true", help="Nao varre subpastas da pasta de entrada.")
    parser.add_argument("--group-by-basename", action="store_true", help="Agrupa por nome base sem incluir subpasta no identificador.")
    parser.add_argument("--limit", type=int, default=0, help="Limita quantidade de amostras processadas.")
    return parser.parse_args(argv)


def main(argv=None):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        argv: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    args = parse_args(argv)
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    if not input_dir.exists():
        input_dir.mkdir(parents=True, exist_ok=True)
        print("Pasta de entrada criada. Adicione arquivos e execute novamente: %s" % input_dir)
        return 0
    quartz_parts = [float(part.strip()) for part in args.quartz_search_d.split(",") if part.strip()]
    if len(quartz_parts) != 2:
        raise SystemExit("--quartz-search-d deve ter formato d_min,d_max")
    args.quartz_search_d = tuple(quartz_parts)
    args.manual_offsets = load_manual_offsets(args.manual_offsets_json)
    args.write_plots = not args.no_plots
    args.copy_raw = bool(args.copy_raw)

    extensions = {item.strip().lower() for item in args.extensions.split(",") if item.strip()}
    samples = discover_samples(
        input_dir,
        extensions,
        recursive=not args.no_recursive,
        group_by_basename=args.group_by_basename,
    )
    items = sorted(samples.items())
    if args.limit:
        items = items[: args.limit]
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for sample_id, paths in items:
        print("Processando amostra: %s (%s)" % (sample_id, ", ".join(sorted(paths))))
        results.append(process_sample(sample_id, paths, output_dir, args))

    payload = {
        "schema_version": "argiloteca.drx.batch_ngc_raw_diagnostics.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "samples_total": len(samples),
        "samples_processed": len(results),
        "parameters": {
            "window_length": args.window_length,
            "polyorder": args.polyorder,
            "als_lambda": args.als_lambda,
            "als_p": args.als_p,
            "start_x_search": args.start_x_search,
            "peak_prominence": args.peak_prominence,
            "max_peaks": args.max_peaks,
            "wavelength": args.wavelength,
            "quartz_search_d": args.quartz_search_d,
            "target_quartz_d": args.target_quartz_d,
        },
        "results": results,
    }
    json_path = output_dir / "batch_ngc_raw_diagnostics.json"
    csv_path = output_dir / "batch_ngc_peaks.csv"
    ngc_json_path = output_dir / "classificacao_mineralogica_ngc_groups.json"
    ngc_csv_path = output_dir / "classificacao_mineralogica_ngc_groups.csv"
    ngc_payload = build_ngc_group_classification_payload(payload)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(results, csv_path)
    ngc_json_path.write_text(json.dumps(ngc_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_ngc_group_csv(ngc_payload, ngc_csv_path)
    print(
        json.dumps(
            {
                "success": True,
                "samples_processed": len(results),
                "json": str(json_path),
                "csv": str(csv_path),
                "ngc_groups_json": str(ngc_json_path),
                "ngc_groups_csv": str(ngc_csv_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
