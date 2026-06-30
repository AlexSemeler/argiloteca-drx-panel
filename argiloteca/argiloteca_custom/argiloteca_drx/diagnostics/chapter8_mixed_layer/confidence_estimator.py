# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: confidence_estimator.py
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

"""Conversao de escore numerico para status operacional do painel."""


def status_from_confidence(score: float) -> str:
    """Mapeia confianca para a linguagem usada na interface DRX.

    O Capitulo 8 exige cautela interpretativa. Por isso, mesmo escores altos
    sao reportados como `probable` nesta camada, a menos que outro componente
    curatorial do painel eleve a decisao.
    """
    if score >= 0.8:
        return "probable"
    if score >= 0.6:
        return "possible"
    if score > 0:
        return "ambiguous"
    return "rejected"
