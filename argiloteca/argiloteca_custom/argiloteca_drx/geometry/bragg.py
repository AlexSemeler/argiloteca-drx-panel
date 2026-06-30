# =============================================================================
# Projeto...........: Argiloteca - Painel de DRX
# Modulo............: bragg.py
#
# Descricao.........:
# Reexporta os calculos geometricos de Bragg usados pelo painel DRX.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Ultima atualizacao:
# 2026-06-30
#
# =============================================================================

"""Calculos geometricos de difracao por Lei de Bragg.

O eixo experimental de um difratograma de po normalmente e medido em 2theta.
A Lei de Bragg usa theta, portanto qualquer conversao para d-spacing deve
documentar a divisao theta = 2theta / 2 e o comprimento de onda aplicado.

Este modulo e uma fachada: a implementacao fica em `argiloteca_drx_core`, para
evitar duas fontes de verdade dentro do projeto.
"""

from argiloteca_drx_core.geometry import (  # noqa: F401
    BraggCalculation,
    bragg_from_two_theta,
    geometry_explanation,
    two_theta_from_d_spacing,
)

__all__ = [
    "BraggCalculation",
    "bragg_from_two_theta",
    "geometry_explanation",
    "two_theta_from_d_spacing",
]
