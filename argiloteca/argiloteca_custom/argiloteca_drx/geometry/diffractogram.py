# =============================================================================
# Projeto...........: Argiloteca - Painel de DRX
# Modulo............: diffractogram.py
#
# Descricao.........:
# Disponibiliza a classe canonica de difratograma para visualizacao e auditoria.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Ultima atualizacao:
# 2026-06-30
#
# =============================================================================

"""Representacao canonica de uma curva 1D de DRX.

`Diffractogram` preserva o eixo 2theta e a intensidade lidos do arquivo,
calcula dominios de visualizacao, normalizacao para exibicao e d-spacing
quando ha comprimento de onda valido. A classe nao classifica minerais.
"""

from argiloteca_drx_core.diffractogram import Diffractogram  # noqa: F401

__all__ = ["Diffractogram"]
