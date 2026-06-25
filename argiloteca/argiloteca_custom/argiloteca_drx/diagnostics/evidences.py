"""Shared evidence helpers for the DRX V3 engine.

Fundamentacao cientifica revisada:
    Este arquivo integra o Painel DRX da Argiloteca, projeto fundamentado nas
    referencias cientificas revisadas para interpretacao auxiliar de DRX de
    argilominerais: Brindley & Brown (1980), Bailey (1980/1988),
    Moore & Reynolds (1989/1997), Drits & Tchoubar (1990),
    Lanson & Bouchet (1995), Meunier, Clays (2005), fluxograma USGS para
    identificacao de argilominerais por DRX e referencias empiricas Pre-Sal
    UFRGS/Petrobras.

Autoria cientifica e curadoria:
    Alexandre Ribas Semeler
    E-mail: alexandre.semler@ufrgs.br

Politica de interpretacao:
    Resultados mineralogicos sao auxiliares e nao confirmatorios. O codigo
    combina comportamento N/G/C, picos companheiros, d060, ambiguidades,
    contexto e proveniencia; nao confirma mineral por pico isolado.
"""

from __future__ import annotations

import math

PREP_ALIASES = {
    "n": "N",
    "nat": "N",
    "natural": "N",
    "air_dried": "N",
    "air-dried": "N",
    "ad": "N",
    "g": "G",
    "eg": "G",
    "glycolated": "G",
    "glicolado": "G",
    "glicolada": "G",
    "c": "C",
    "h": "C",
    "heated": "C",
    "calcined": "C",
    "calcinado": "C",
    "calcinada": "C",
    "400c": "C",
    "550c": "C",
}


def prep_key(value):
    return PREP_ALIASES.get(str(value or "").strip().lower().replace(" ", "_"), str(value or "").strip().upper())


def number(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def normalize_peaks(peaks_by_preparation):
    out = {"N": [], "G": [], "C": []}
    for prep, rows in (peaks_by_preparation or {}).items():
        key = prep_key(prep)
        if key not in out:
            continue
        for row in rows or []:
            if isinstance(row, (list, tuple)):
                d_value = number(row[0] if row else None)
                intensity = number(row[1] if len(row) > 1 else 1.0) or 1.0
                payload = {"d": d_value, "intensity": intensity}
            elif isinstance(row, dict):
                d_value = number(row.get("d_spacing") or row.get("d") or row.get("d_A") or row.get("d_angstrom") or row.get("center_d_angstrom"))
                intensity = number(row.get("intensity") or row.get("intensity_abs") or row.get("relative_intensity") or row.get("i_norm") or row.get("height") or 1.0) or 1.0
                payload = {**row, "d": d_value, "intensity": intensity}
            else:
                continue
            if d_value and d_value > 0:
                out[key].append(payload)
        out[key].sort(key=lambda item: item.get("d") or 0.0, reverse=True)
    return out


def find_peak(peaks, d_min, d_max):
    candidates = [peak for peak in peaks or [] if d_min <= (peak.get("d") or 0.0) <= d_max]
    if not candidates:
        return None
    return max(candidates, key=lambda peak: peak.get("intensity") or 0.0)


def has_peak(peaks, d_min, d_max):
    return find_peak(peaks, d_min, d_max) is not None


def evidence(rule_id, kind, message, weight=0.0, peak=None):
    payload = {"rule_id": rule_id, "kind": kind, "message": message, "weight": weight}
    if peak:
        payload["peak"] = {"d": peak.get("d"), "intensity": peak.get("intensity"), "preparation": peak.get("preparation")}
    return payload


def relation(source, target, relation_type, explanation, confidence_weight=0.0, delta_d=None, intensity_change=None, rule_id=None):
    return {
        "source": source,
        "target": target,
        "type": relation_type,
        "delta_d": delta_d,
        "intensity_change": intensity_change,
        "rule_id": rule_id,
        "confidence_weight": confidence_weight,
        "explanation": explanation,
    }
