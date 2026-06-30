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
    names = {s.get("label", "") for s in superstructures or []}
    if names:
        if any("corrensite" in n or "mica_vermiculite" in n for n in names):
            return {"ordering": "R1", "confidence": 0.75, "reason": "superstructure reflection detected"}
    if "irrational_00l_series" in set((features or {}).get("features", [])):
        return {"ordering": "R0", "confidence": 0.65, "reason": "irrational 00l series"}
    return {"ordering": "unknown", "confidence": 0.3, "reason": "ordering evidence insufficient"}
