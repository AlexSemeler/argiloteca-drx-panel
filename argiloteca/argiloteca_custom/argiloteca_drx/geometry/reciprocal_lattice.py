# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: reciprocal_lattice.py
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


def reciprocal_cubic_point(a_A: float, h: int, k: int, l: int) -> dict:
    """
    Executa a etapa `reciprocal_cubic_point` do módulo.

        Args:
            a_A:
                Parâmetro utilizado pela etapa `reciprocal_cubic_point`.
            h:
                Parâmetro utilizado pela etapa `reciprocal_cubic_point`.
            k:
                Parâmetro utilizado pela etapa `reciprocal_cubic_point`.
            l:
                Parâmetro utilizado pela etapa `reciprocal_cubic_point`.
        Returns:
            Resultado documentado pelo contrato do chamador.

        Notes:
            Em fluxos DRX, valores de 2θ, d-spacing, FWHM e intensidade
            relativa devem ser interpretados em conjunto com preparação
            natural, glicolada e calcinada. Nenhum pico isolado deve ser
            tratado como confirmação mineralógica completa.
    """
    b = 1.0 / float(a_A)
    return {"x": h*b, "y": k*b, "z": l*b, "unit": "angstrom^-1"}
