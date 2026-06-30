"""Normalizacao de picos DRX para regras N/G/C e mixed-layer.

As funcoes deste modulo transformam picos vindos de parsers, ALS, lmfit,
scripts de lote ou JSONs do painel em um contrato minimo comum. O contrato
mantem `d`, `two_theta`, intensidade, FWHM e marcadores de largura/ombro para
que as regras dos Capitulos 7 e 8 possam operar sem depender da origem do pico.
"""

from __future__ import annotations

import math

from .geometry import bragg_from_two_theta


def _first_present(row, keys):
    """Retorna o primeiro valor preenchido em uma lista de chaves."""
    for key in keys:
        if isinstance(row, dict) and row.get(key) not in (None, ""):
            return row.get(key)
    return None


def _float_or_none(value):
    """Converte valor numerico heterogeneo para float finito ou None."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def normalize_peak(row, *, wavelength_angstrom=1.5406, source="argiloteca_drx_core"):
    """Normaliza um pico para o contrato cientifico minimo.

    Args:
        row: Dicionario com campos de pico vindos de qualquer origem conhecida.
        wavelength_angstrom: Comprimento de onda usado para calcular `d` quando
            apenas `two_theta` estiver disponivel.
        source: Rotulo de proveniencia do normalizador.

    Returns:
        dict: Pico normalizado com `d`, `two_theta`, intensidade, FWHM,
        marcadores de pico largo/assimetrico e regra geometrica aplicada.
    """
    row = row or {}
    observed = row.get("observed_peak") if isinstance(row.get("observed_peak"), dict) else {}
    merged = {**observed, **row}
    two_theta = _float_or_none(_first_present(merged, ["two_theta", "twoTheta", "center_2theta", "observed_two_theta", "measured_two_theta"]))
    d_spacing = _float_or_none(_first_present(merged, ["d", "d_spacing", "d_angstrom", "center_d_angstrom", "observed_d_angstrom"]))
    bragg = None
    if d_spacing is None and two_theta is not None:
        bragg = bragg_from_two_theta(two_theta, wavelength_angstrom=wavelength_angstrom)
        d_spacing = bragg.d_spacing_angstrom
    intensity = _float_or_none(_first_present(merged, ["relative_intensity", "intensity_relative", "i_norm", "intensity", "height", "i_abs"]))
    fwhm = _float_or_none(_first_present(merged, ["fwhm", "beta", "peak_width"]))
    broad = bool(merged.get("broad") or merged.get("asymmetric") or (fwhm is not None and fwhm > 0.5))
    return {
        "peak_index": _first_present(merged, ["peak_index", "index", "peak_id"]),
        "two_theta": two_theta,
        "d": d_spacing,
        "d_angstrom": d_spacing,
        "intensity": intensity,
        "relative_intensity": intensity,
        "fwhm": fwhm,
        "broad": broad,
        "asymmetric": bool(merged.get("asymmetric")),
        "source": merged.get("source") or source,
        "geometry_rule_id": (bragg.rule_id if bragg else "chapter3_two_theta_to_d_spacing" if two_theta is not None else None),
    }


def normalize_peaks(rows, *, wavelength_angstrom=1.5406, source="argiloteca_drx_core"):
    """Normaliza uma lista de picos e remove entradas sem `d` e sem `2θ`."""
    normalized = [
        normalize_peak(row, wavelength_angstrom=wavelength_angstrom, source=source)
        for row in (rows or [])
        if isinstance(row, dict)
    ]
    return [peak for peak in normalized if peak.get("d") is not None or peak.get("two_theta") is not None]


def group_peaks_for_ngc(items, *, wavelength_angstrom=1.5406):
    """Agrupa picos por preparo no formato esperado pela engine N/G/C.

    Args:
        items: Lista de itens com `preparation`/`treatment` e `peaks`.
        wavelength_angstrom: Comprimento de onda usado quando for necessario
            calcular d-spacing a partir de 2θ.

    Returns:
        dict: Chaves `N`, `G` e `C` com picos normalizados.
    """
    groups = {"N": [], "G": [], "C": []}
    aliases = {
        "natural": "N",
        "air_dried": "N",
        "n": "N",
        "glicolado": "G",
        "glycolated": "G",
        "ethylene_glycol_solvated": "G",
        "g": "G",
        "calcinado": "C",
        "calcined": "C",
        "heated": "C",
        "c": "C",
    }
    for item in items or []:
        prep = str(item.get("preparation") or item.get("treatment") or "").strip().lower()
        key = aliases.get(prep)
        if not key:
            continue
        rows = item.get("peaks") or item.get("advanced_peaks") or item.get("detected_peaks") or []
        groups[key].extend(normalize_peaks(rows, wavelength_angstrom=wavelength_angstrom, source="ngc_grouping"))
    return groups
