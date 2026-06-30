# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: d_spacing.py
#
# Descrição.........:
# Implementa geometria de DRX, Lei de Bragg, conversão 2θ/d-spacing e validação físico-cristalográfica.
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
Implementa geometria de DRX, Lei de Bragg, conversão 2θ/d-spacing e validação físico-cristalográfica.

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

import math


def cubic_d_spacing(a_A: float, h: int, k: int, l: int) -> float | None:
    """
    Executa a etapa `cubic_d_spacing` do módulo.

        Args:
            a_A:
                Parâmetro utilizado pela etapa `cubic_d_spacing`.
            h:
                Parâmetro utilizado pela etapa `cubic_d_spacing`.
            k:
                Parâmetro utilizado pela etapa `cubic_d_spacing`.
            l:
                Parâmetro utilizado pela etapa `cubic_d_spacing`.
        Returns:
            Resultado documentado pelo contrato do chamador.

        Notes:
            Em fluxos DRX, valores de 2θ, d-spacing, FWHM e intensidade
            relativa devem ser interpretados em conjunto com preparação
            natural, glicolada e calcinada. Nenhum pico isolado deve ser
            tratado como confirmação mineralógica completa.
    """
    denom = h*h + k*k + l*l
    return None if denom <= 0 else float(a_A) / math.sqrt(denom)


def tetragonal_d_spacing(a_A: float, c_A: float, h: int, k: int, l: int) -> float | None:
    """
    Executa a etapa `tetragonal_d_spacing` do módulo.

        Args:
            a_A:
                Parâmetro utilizado pela etapa `tetragonal_d_spacing`.
            c_A:
                Parâmetro utilizado pela etapa `tetragonal_d_spacing`.
            h:
                Parâmetro utilizado pela etapa `tetragonal_d_spacing`.
            k:
                Parâmetro utilizado pela etapa `tetragonal_d_spacing`.
            l:
                Parâmetro utilizado pela etapa `tetragonal_d_spacing`.
        Returns:
            Resultado documentado pelo contrato do chamador.

        Notes:
            Em fluxos DRX, valores de 2θ, d-spacing, FWHM e intensidade
            relativa devem ser interpretados em conjunto com preparação
            natural, glicolada e calcinada. Nenhum pico isolado deve ser
            tratado como confirmação mineralógica completa.
    """
    inv = (h*h + k*k) / (float(a_A) ** 2) + (l*l) / (float(c_A) ** 2)
    return None if inv <= 0 else 1.0 / math.sqrt(inv)
