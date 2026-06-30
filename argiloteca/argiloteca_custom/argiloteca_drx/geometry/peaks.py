# =============================================================================
# Projeto...........: Argiloteca - Painel de DRX
# Modulo............: peaks.py
#
# Descricao.........:
# Fachada para normalizacao de picos e agrupamento N/G/C.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Ultima atualizacao:
# 2026-06-30
#
# =============================================================================

"""Normalizacao de picos para diagnostico DRX.

As funcoes expostas aqui convertem picos vindos de parsers, ALS, arquivos RAW
ou JSONs do painel para um contrato comum com 2theta, d-spacing, intensidade,
FWHM e proveniencia. O objetivo e alimentar as regras dos Capitulos 7 e 8 sem
depender do formato original do pico.
"""

from argiloteca_drx_core.peaks import group_peaks_for_ngc, normalize_peak, normalize_peaks  # noqa: F401

__all__ = ["group_peaks_for_ngc", "normalize_peak", "normalize_peaks"]
