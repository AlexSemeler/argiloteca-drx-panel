"""Confidence scoring for Argiloteca rule-based clay-mineral candidates.

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
    O resultado pode ser confirmado pelas regras da Argiloteca quando N/G/C,
    picos companheiros e bloqueios de ambiguidade sustentam o candidato. Essa
    confirmacao e restrita ao escopo das regras implementadas.
"""

from __future__ import annotations

from .diagnostic_behavior_rules import CONFIRMED_BY_RULES, POSSIBLE_BY_RULES, PROBABLE_BY_RULES


def confidence_label(score):
    if score <= 40:
        return POSSIBLE_BY_RULES
    if score <= 70:
        return PROBABLE_BY_RULES
    return CONFIRMED_BY_RULES


def score_candidate(candidate, completeness, ambiguities=None, contradictions=None):
    behavior = min(float(candidate.get("behavior_score", 0.0)), 1.0) * 40
    peak_set = min(float(candidate.get("peak_set_score", 0.0)), 1.0) * 25
    d060 = min(float(candidate.get("d060_score", 0.0)), 1.0) * 15
    thermal = min(float(candidate.get("thermal_score", 0.0)), 1.0) * 10
    proximity = min(float(candidate.get("proximity_score", 0.0)), 1.0) * 5
    ambiguity_bonus = 5 if not ambiguities else 0
    raw_score = behavior + peak_set + d060 + thermal + proximity + ambiguity_bonus
    warnings = list(candidate.get("warnings") or [])
    if completeness.get("treatment_count", 0) < 2:
        raw_score = min(raw_score, 40)
        warnings.append("Confirmed-by-rules blocked: fewer than two treatments.")
    if not completeness.get("has_N") or not completeness.get("has_G"):
        raw_score = min(raw_score, 70)
        warnings.append("Confirmed-by-rules blocked: missing N or G treatment.")
    if completeness.get("peak_count", 0) <= 1:
        raw_score = min(raw_score, 40)
        warnings.append("Confirmed-by-rules blocked: only one peak.")
    if ambiguities and candidate.get("requires_companions") and candidate.get("peak_set_score", 0.0) < 0.5:
        raw_score = min(raw_score, 70)
        warnings.append("Confirmed-by-rules blocked: severe ambiguity without companion peaks.")
    if contradictions:
        raw_score = min(raw_score, 70)
        warnings.append("Confirmed-by-rules blocked: d060 or behavior contradiction.")
    score = round(max(0.0, min(raw_score, 100.0)), 2)
    return {"score": score, "confidence": confidence_label(score), "warnings": warnings}
