# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: chapter7_rule_executor.py
#
# Descrição.........:
# Implementa regras, evidências e estruturas de interpretação mineralógica por DRX N/G/C.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Última atualização:
# 2026-06-25
#
# =============================================================================

"""Executable Chapter 7 rules for clay-mineral N/G/C classification.

This module turns the curated Chapter 7 knowledge base into direct diagnostic
candidate rows. It is intentionally conservative: a basal peak match alone is
not enough; rules combine treatment behavior, companion peaks and warnings for
known overlaps.
"""

from __future__ import annotations

from .chapter7_knowledge import SOURCE_ID, chapter7_rule_index


def _as_float(value):
    """Convert numeric peak fields without raising."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _peak_d(peak):
    """Return d-spacing from heterogeneous peak dictionaries."""
    if not isinstance(peak, dict):
        return None
    return _as_float(peak.get("d") or peak.get("d_spacing") or peak.get("d_angstrom"))


def _peak_i(peak):
    """Return absolute or relative intensity for qualitative comparisons."""
    if not isinstance(peak, dict):
        return 0.0
    return _as_float(
        peak.get("intensity")
        or peak.get("i_abs")
        or peak.get("relative_intensity")
        or peak.get("i_norm")
        or peak.get("height")
    ) or 0.0


def _find_peak(peaks, d_min, d_max):
    """Find the strongest peak in a d-spacing window."""
    matches = []
    for peak in peaks or []:
        d_value = _peak_d(peak)
        if d_value is None or d_value < d_min or d_value > d_max:
            continue
        matches.append((peak, _peak_i(peak)))
    if not matches:
        return None
    matches.sort(key=lambda row: row[1], reverse=True)
    return matches[0][0]


def _peak_around(peaks, center, tolerance):
    """Find a peak by center/tolerance."""
    return _find_peak(peaks, center - tolerance, center + tolerance)


def _has_peak(peaks, center, tolerance):
    """Return True when a peak exists in center/tolerance."""
    return _peak_around(peaks, center, tolerance) is not None


def _relation_peak(label, peak):
    """Format one peak as readable evidence relation."""
    d_value = _peak_d(peak)
    theta = _as_float(peak.get("two_theta") if isinstance(peak, dict) else None)
    intensity = _peak_i(peak)
    return {
        "label": label,
        "d": d_value,
        "two_theta": theta,
        "intensity": intensity,
    }


def _candidate(rule_id, label, family, score, confidence, evidences, explanation, competitors=None, warnings=None):
    """Create a standard Chapter 7 candidate row."""
    rule = chapter7_rule_index().get(rule_id, {})
    return {
        "label": label,
        "family": family,
        "score": round(float(score), 3),
        "confidence": confidence,
        "source": "chapter7_rule_executor",
        "source_id": SOURCE_ID,
        "rule_id": rule_id,
        "source_rule": rule,
        "evidences": evidences,
        "relations": [],
        "explain": explanation or rule.get("explanation") or "",
        "competitors": competitors or [],
        "warnings": warnings or [],
    }


def _intensity_ratio_after_heating(n_peak, c_peak):
    """Return C/N intensity ratio when measurable."""
    n_i = _peak_i(n_peak)
    c_i = _peak_i(c_peak)
    if n_i <= 0:
        return None
    return c_i / n_i


def execute_chapter7_rules(peaks, behavior=None, metadata=None):
    """Evaluate Chapter 7 diagnostic rules against N/G/C peak sets.

    Args:
        peaks: dict with N, G and C peak lists.
        behavior: optional treatment_interpreter output, used for detected
            behaviors such as expansion, collapse and thermal persistence.
        metadata: optional d060, chemistry, morphology and context.

    Returns:
        dict with candidates, applied_rules and warnings.
    """
    peaks = peaks or {}
    behavior = behavior or {}
    metadata = metadata or {}
    n = peaks.get("N") or peaks.get("natural") or []
    g = peaks.get("G") or peaks.get("glycolated") or peaks.get("glicolado") or []
    c = peaks.get("C") or peaks.get("calcined") or peaks.get("calcinado") or []
    behaviors = set(behavior.get("behaviors") or [])
    candidates = []
    warnings = []

    n14 = _peak_around(n, 14.2, 0.55)
    g14 = _peak_around(g, 14.2, 0.55)
    c14 = _peak_around(c, 14.2, 0.65)
    p7_any = _peak_around(n, 7.1, 0.25) or _peak_around(g, 7.1, 0.25) or _peak_around(c, 7.1, 0.25)
    p472_any = _peak_around(n, 4.74, 0.14) or _peak_around(g, 4.74, 0.14) or _peak_around(c, 4.74, 0.14)
    p353_any = _peak_around(n, 3.55, 0.08) or _peak_around(g, 3.55, 0.08) or _peak_around(c, 3.55, 0.08)
    chlorite_support = [row for row in [n14, g14, c14, p7_any, p472_any, p353_any] if row]
    if n14 and g14 and c14 and len(chlorite_support) >= 4 and "expands_with_glycol" not in behaviors:
        ratio = _intensity_ratio_after_heating(n14, c14)
        score = 0.82 + min(0.12, 0.03 * (len(chlorite_support) - 4))
        if ratio is not None and ratio >= 0.75:
            score += 0.04
        candidates.append(_candidate(
            "chapter7_chlorite_ool",
            "chlorite",
            "chlorite_group",
            min(score, 0.98),
            "confirmed_by_rules",
            [_relation_peak("N 14A", n14), _relation_peak("G 14A", g14), _relation_peak("C 14A", c14)],
            "Chapter 7 chlorite rule: persistent 14/7/4.74/3.55 A basal set without glycol expansion.",
            competitors=[
                {"competitor": "kaolin_group", "reason": "7 A overlap must be resolved by 14 A and heating response."},
                {"competitor": "vermiculite", "reason": "14 A phases require heating/glycerol/K behavior."},
            ],
        ))

    n7 = _peak_around(n, 7.15, 0.25)
    g7 = _peak_around(g, 7.15, 0.25)
    c7 = _peak_around(c, 7.15, 0.25)
    p357_any = _peak_around(n, 3.57, 0.06) or _peak_around(g, 3.57, 0.06)
    loss_ratio = _intensity_ratio_after_heating(n7, c7) if n7 else None
    kaolin_heat_loss = (n7 and g7 and not c7) or (loss_ratio is not None and loss_ratio <= 0.25) or "strongly_reduced_after_heating" in behaviors
    if n7 and g7 and kaolin_heat_loss and not n14:
        score = 0.84 + (0.08 if p357_any else 0.0)
        candidates.append(_candidate(
            "chapter7_kaolinite_chlorite_resolution",
            "kaolin_group",
            "kaolin_group",
            min(score, 0.96),
            "confirmed_by_rules",
            [_relation_peak("N 7A", n7), _relation_peak("G 7A", g7), _relation_peak("3.57A companion", p357_any) if p357_any else {"label": "C 7A loss", "d": None}],
            "Chapter 7 kaolin/chlorite resolution: 7 A remains after glycolation and is lost/reduced after heating.",
            competitors=[
                {"competitor": "chlorite", "reason": "chlorite should retain 14 A and companion 4.74/3.55 A reflections."},
                {"competitor": "serpentine", "reason": "serpentine can occupy 7 A and needs morphology/hkl."},
            ],
        ))
    elif n7 and g7 and kaolin_heat_loss and n14:
        warnings.append("Chapter 7: 7 A thermal loss conflicts with 14 A chlorite evidence; keep kaolin/chlorite ambiguity.")

    n_sm = _find_peak(n, 12.0, 15.6)
    g_sm = _find_peak(g, 16.1, 17.8)
    c_sm = _find_peak(c, 9.6, 10.4)
    if n_sm and g_sm and c_sm:
        candidates.append(_candidate(
            "chapter7_smectite_ngc",
            "smectite_group",
            "smectite_group",
            0.95,
            "confirmed_by_rules",
            [_relation_peak("N 12-15A", n_sm), _relation_peak("G ~17A", g_sm), _relation_peak("C ~10A", c_sm)],
            "Chapter 7 smectite rule: expansion after glycolation and collapse toward 10 A after heating.",
            competitors=[
                {"competitor": "chlorite_smectite", "reason": "mixed layers can combine persistent and expandable components."},
                {"competitor": "vermiculite", "reason": "vermiculite needs K/glycerol/heating behavior."},
            ],
        ))

    n10 = _peak_around(n, 10.0, 0.35)
    g10 = _peak_around(g, 10.0, 0.35)
    c10 = _peak_around(c, 10.0, 0.40)
    p5_any = _peak_around(n, 5.0, 0.12) or _peak_around(g, 5.0, 0.12) or _peak_around(c, 5.0, 0.12)
    p333_any = _peak_around(n, 3.33, 0.06) or _peak_around(g, 3.33, 0.06) or _peak_around(c, 3.33, 0.06)
    if n10 and g10 and c10:
        score = 0.76 + (0.08 if p5_any else 0.0) + (0.04 if p333_any else 0.0)
        candidates.append(_candidate(
            "chapter7_illite_glauconite_mica",
            "illite_mica",
            "illite_mica",
            min(score, 0.92),
            "confirmed_by_rules" if p5_any else "probable_by_rules",
            [_relation_peak("N 10A", n10), _relation_peak("G 10A", g10), _relation_peak("C 10A", c10)],
            "Chapter 7 illite/mica rule: 10 A reflection unchanged by glycolation and heating.",
            competitors=[
                {"competitor": "quartz", "reason": "3.33-3.34 A alone can be quartz; require 10 A and preferably 5 A."},
                {"competitor": "palygorskite", "reason": "10.3-10.5 A fibrous clay can overlap."},
            ],
        ))

    n_verm = _peak_around(n, 14.5, 0.8)
    g_verm = _peak_around(g, 14.5, 0.8)
    c_verm = _find_peak(c, 10.0, 12.2)
    if n_verm and g_verm and c_verm and not g_sm and not c14:
        candidates.append(_candidate(
            "chapter7_vermiculite_operational",
            "vermiculite",
            "vermiculite_group",
            0.78,
            "probable_by_rules",
            [_relation_peak("N ~14.5A", n_verm), _relation_peak("G ~14.5A", g_verm), _relation_peak("C 10-12A", c_verm)],
            "Chapter 7 vermiculite rule: operational 14 A phase that does not glycol-expand and collapses toward 10-12 A.",
            competitors=[
                {"competitor": "chlorite", "reason": "chlorite persists near 14 A after heating."},
                {"competitor": "smectite", "reason": "smectite glycol-expands near 17 A."},
            ],
        ))

    n_sep = _find_peak(n, 12.0, 12.6)
    g_sep = _find_peak(g, 12.0, 12.6)
    if n_sep and g_sep and not g_sm:
        candidates.append(_candidate(
            "chapter7_fibrous_channel_minerals",
            "sepiolite",
            "fibrous_channel",
            0.68,
            "possible_by_rules",
            [_relation_peak("N 12-12.5A", n_sep), _relation_peak("G 12-12.5A", g_sep)],
            "Chapter 7 fibrous/channel rule: sepiolite-like low-angle peak unchanged by glycolation; morphology/hkl required.",
        ))

    n_pal = _find_peak(n, 10.3, 10.6)
    g_pal = _find_peak(g, 10.3, 10.6)
    if n_pal and g_pal and not (n10 and g10 and c10):
        candidates.append(_candidate(
            "chapter7_fibrous_channel_minerals",
            "palygorskite",
            "fibrous_channel",
            0.66,
            "possible_by_rules",
            [_relation_peak("N 10.3-10.5A", n_pal), _relation_peak("G 10.3-10.5A", g_pal)],
            "Chapter 7 fibrous/channel rule: palygorskite-like 10.3-10.5 A peak unchanged by glycolation; morphology/hkl required.",
        ))

    q101 = _peak_around(n, 3.34, 0.06) or _peak_around(g, 3.34, 0.06) or _peak_around(c, 3.34, 0.06)
    q100 = _peak_around(n, 4.26, 0.10) or _peak_around(g, 4.26, 0.10) or _peak_around(c, 4.26, 0.10)
    if q101 and q100:
        warnings.append("Chapter 7 quartz rule: quartz pattern present; do not use 3.33-3.34 A alone as illite/mica evidence.")

    applied_rules = sorted({row["rule_id"] for row in candidates})
    return {
        "source_id": SOURCE_ID,
        "candidates": sorted(candidates, key=lambda row: row["score"], reverse=True),
        "applied_rules": applied_rules,
        "warnings": warnings,
    }
