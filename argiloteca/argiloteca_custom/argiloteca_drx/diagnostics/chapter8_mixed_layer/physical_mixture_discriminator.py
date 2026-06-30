# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: physical_mixture_discriminator.py
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

"""Diagnostico diferencial entre mistura fisica e interestratificacao."""


def discriminate(features: dict, superstructures: list[dict]) -> dict:
    """Avalia se as evidencias favorecem interestratificacao real.

    Args:
        features: Marcadores extraidos da comparacao entre tratamentos.
        superstructures: Reflexoes longas ou de superestrutura detectadas.

    Returns:
        Status `supports_interstratification`, `supports_physical_mixture` ou
        `ambiguous`. A saida ambigua e intencional quando faltam dados.
    """
    fs = set((features or {}).get("features", []))
    if superstructures and ("expands_with_eg_to_17A" in fs or "collapses_or_returns_to_10A_after_heating" in fs):
        return {"status": "supports_interstratification", "reason": "superstructure plus treatment behavior"}
    if "fixed_discrete_peaks" in fs:
        return {"status": "supports_physical_mixture", "reason": "independent fixed peaks"}
    return {"status": "ambiguous", "reason": "requires complete 00l and multi-treatment comparison"}
