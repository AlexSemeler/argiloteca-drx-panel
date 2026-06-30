# =============================================================================
# Projeto...........: Argiloteca - Painel de DRX
# Modulo............: argiloteca_drx.geometry
#
# Descricao.........:
# Fachada publica para geometria de difracao, Lei de Bragg, picos e
# difratogramas usados pelo painel DRX.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Ultima atualizacao:
# 2026-06-30
#
# =============================================================================

"""Subpacote de geometria de DRX da Argiloteca.

Este pacote organiza a logica geometrica baseada no Capitulo 3
("Diffraction I: Geometry") sem duplicar implementacoes. As funcoes aqui
expostas delegam para `argiloteca_drx_core`, que contem as funcoes puras ja
usadas pelo painel.

Responsabilidades:
    * converter 2theta em d-spacing pela Lei de Bragg;
    * converter d-spacing em posicao 2theta esperada;
    * explicar a convencao theta = 2theta / 2;
    * normalizar picos para regras N/G/C e mixed-layer;
    * disponibilizar a classe `Diffractogram` para visualizacao auditavel.

Este pacote nao executa interpretacao mineralogica final.
"""

from .bragg import BraggCalculation, bragg_from_two_theta, geometry_explanation, two_theta_from_d_spacing
from .diffractogram import Diffractogram
from .peaks import group_peaks_for_ngc, normalize_peak, normalize_peaks

__all__ = [
    "BraggCalculation",
    "Diffractogram",
    "bragg_from_two_theta",
    "geometry_explanation",
    "group_peaks_for_ngc",
    "normalize_peak",
    "normalize_peaks",
    "two_theta_from_d_spacing",
]
