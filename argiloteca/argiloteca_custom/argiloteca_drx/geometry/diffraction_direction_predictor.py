# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: diffraction_direction_predictor.py
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

from .bragg import bragg_two_theta
from .d_spacing import cubic_d_spacing, tetragonal_d_spacing


def cubic_two_theta(lambda_A: float, a_A: float, h: int, k: int, l: int) -> float | None:
    """
    Executa a etapa `cubic_two_theta` do módulo.

        Args:
            lambda_A:
                Parâmetro utilizado pela etapa `cubic_two_theta`.
            a_A:
                Parâmetro utilizado pela etapa `cubic_two_theta`.
            h:
                Parâmetro utilizado pela etapa `cubic_two_theta`.
            k:
                Parâmetro utilizado pela etapa `cubic_two_theta`.
            l:
                Parâmetro utilizado pela etapa `cubic_two_theta`.
        Returns:
            Resultado documentado pelo contrato do chamador.

        Notes:
            Em fluxos DRX, valores de 2θ, d-spacing, FWHM e intensidade
            relativa devem ser interpretados em conjunto com preparação
            natural, glicolada e calcinada. Nenhum pico isolado deve ser
            tratado como confirmação mineralógica completa.
    """
    d = cubic_d_spacing(a_A, h, k, l)
    return None if d is None else bragg_two_theta(lambda_A, d)


def tetragonal_two_theta(lambda_A: float, a_A: float, c_A: float, h: int, k: int, l: int) -> float | None:
    """
    Executa a etapa `tetragonal_two_theta` do módulo.

        Args:
            lambda_A:
                Parâmetro utilizado pela etapa `tetragonal_two_theta`.
            a_A:
                Parâmetro utilizado pela etapa `tetragonal_two_theta`.
            c_A:
                Parâmetro utilizado pela etapa `tetragonal_two_theta`.
            h:
                Parâmetro utilizado pela etapa `tetragonal_two_theta`.
            k:
                Parâmetro utilizado pela etapa `tetragonal_two_theta`.
            l:
                Parâmetro utilizado pela etapa `tetragonal_two_theta`.
        Returns:
            Resultado documentado pelo contrato do chamador.

        Notes:
            Em fluxos DRX, valores de 2θ, d-spacing, FWHM e intensidade
            relativa devem ser interpretados em conjunto com preparação
            natural, glicolada e calcinada. Nenhum pico isolado deve ser
            tratado como confirmação mineralógica completa.
    """
    d = tetragonal_d_spacing(a_A, c_A, h, k, l)
    return None if d is None else bragg_two_theta(lambda_A, d)
