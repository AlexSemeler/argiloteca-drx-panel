# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: rule_executor.py
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

"""Carregamento e filtragem do catalogo de regras do Capitulo 8."""

from .provenance_tracker import load_json


def chapter8_rules():
    """Retorna todas as regras curadas do Capitulo 8."""
    return load_json("chapter8_rules_catalog.json")


def rules_for_target(target: str):
    """Filtra regras por alvo mineral ou sistema mineral.

    Esta funcao e usada por rotinas de painel que precisam explicar quais
    regras sustentam um candidato especifico.
    """
    return [r for r in chapter8_rules() if target in {r.get("target"), r.get("mineral_system")} or target in str(r.get("target", ""))]
