# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: candidate_ranker.py
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

"""Ordenacao de candidatos do motor de argilominerais interestratificados.

Este modulo nao cria diagnosticos novos. Ele apenas organiza a lista de
candidatos ja explicados por outros componentes do painel, preservando
evidencias e fontes.
"""


def rank_candidates(candidates: list[dict]) -> list[dict]:
    """Ordena candidatos pelo campo numerico `confidence`.

    Args:
        candidates: Lista de candidatos produzidos pelo `diagnostic_engine`.

    Returns:
        Lista ordenada do maior para o menor grau de confianca. A funcao e
        deliberadamente simples para nao alterar a interpretacao cientifica.
    """
    return sorted(candidates or [], key=lambda c: c.get("confidence", 0.0), reverse=True)
