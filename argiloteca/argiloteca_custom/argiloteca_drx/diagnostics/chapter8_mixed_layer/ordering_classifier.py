# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: ordering_classifier.py
#
# Descrição.........:
# Implementa regras explicáveis para argilominerais interestratificados e padrões 00l multi-tratamento.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Última atualização:
# 2026-06-25
#
# =============================================================================

"""
Implementa regras explicáveis para argilominerais interestratificados e padrões 00l multi-tratamento.

Responsabilidades:
    - preservar contratos públicos e estruturas JSON consumidas pelo painel;
    - registrar proveniência científica e técnica das operações realizadas;
    - manter separadas etapas de leitura, processamento, diagnóstico e exportação;
    - documentar limites de interpretação mineralógica quando houver regras DRX.

Notas científicas:
    Em módulos DRX, 2θ representa o eixo angular medido no difratograma e
    d-spacing representa o espaçamento interplanar calculado pela Lei de Bragg
    (nλ = 2d sen θ). Preparações natural, glicolada e calcinada são usadas para
    observar expansão, colapso, persistência ou destruição de picos basais.
"""

from __future__ import annotations

"""Classificacao conservadora de ordenamento R0/R1/R3."""


def classify_ordering(features: dict, superstructures: list[dict]) -> dict:
    """Classifica Reichweite quando a evidencia e suficiente.

    A funcao favorece `R1` quando ha componente de superestrutura detectavel e
    retorna `unknown` quando o padrao nao permite separar R0/R1/R3. Isso evita
    forcar ordenamento a partir de um pico isolado ou de uma preparacao unica.
    """
    features = features or {}
    series = features.get("00l_series") or features.get("ool_series") or []
    treatments = features.get("treatments") or features.get("treatment_protocol_ids") or []
    cv = features.get("coefficient_of_variation_percent")
    model_fit = features.get("model_fit") or features.get("model_fit_quality")
    missing = []
    if len(series) < 3:
        missing.append("at_least_three_00l_reflections")
    if len(set(treatments)) < 2:
        missing.append("coherent_multi_treatment_series")
    if cv is None and not model_fit:
        missing.append("coefficient_of_variation_or_model_fit")
    if missing:
        return {
            "ordering": "unknown",
            "ordering_state": "unknown",
            "confidence": 0.0,
            "reason": "ordering evidence insufficient",
            "missing_requirements": missing,
        }

    names = {s.get("label", "") for s in superstructures or []}
    flags = set(features.get("features", []))
    if any("corrensite" in name or "mica_vermiculite" in name for name in names) and "rational_00l_series" in flags:
        return {"ordering": "R1", "ordering_state": "R1", "confidence": 0.75, "reason": "rational multi-treatment 00l series with superstructure support", "coefficient_of_variation_percent": cv}
    if "irrational_00l_series" in flags:
        return {"ordering": "R0", "ordering_state": "R0", "confidence": 0.65, "reason": "irrational multi-treatment 00l series", "coefficient_of_variation_percent": cv}
    return {"ordering": "unknown", "ordering_state": "unknown", "confidence": 0.2, "reason": "complete observations do not discriminate ordering", "missing_requirements": []}
