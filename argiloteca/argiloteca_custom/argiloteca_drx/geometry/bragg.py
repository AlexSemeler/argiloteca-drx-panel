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

def bragg_d_spacing(lambda_A, two_theta_deg):
    """Calcula d-spacing por `d = lambda / (2 sen(theta))`."""
    return bragg_from_two_theta(two_theta_deg, wavelength_angstrom=lambda_A).d_spacing_angstrom


def bragg_two_theta(lambda_A, d_A):
    """Calcula a posicao 2theta esperada para um d-spacing."""
    return two_theta_from_d_spacing(d_A, wavelength_angstrom=lambda_A).get("two_theta_deg")


def bragg_observable(lambda_A, d_A):
    """Verifica a condicao geometrica de observabilidade `lambda < 2d`."""
    try:
        wavelength = float(lambda_A)
        spacing = float(d_A)
    except (TypeError, ValueError):
        return False
    return wavelength > 0 and spacing > 0 and wavelength < (2.0 * spacing)


__all__ = [
    "BraggCalculation",
    "bragg_d_spacing",
    "bragg_from_two_theta",
    "bragg_observable",
    "bragg_two_theta",
    "geometry_explanation",
    "two_theta_from_d_spacing",
]
