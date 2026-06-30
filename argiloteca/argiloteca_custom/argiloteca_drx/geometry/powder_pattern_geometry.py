# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: powder_pattern_geometry.py
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

from .hkl_indexer import generate_hkl
from .diffraction_direction_predictor import cubic_two_theta, tetragonal_two_theta


def powder_lines(lambda_A: float, crystal_system: str, unit_cell: dict, max_index: int = 5):
    """
    Executa a etapa `powder_lines` do módulo.

        Args:
            lambda_A:
                Parâmetro utilizado pela etapa `powder_lines`.
            crystal_system:
                Parâmetro utilizado pela etapa `powder_lines`.
            unit_cell:
                Parâmetro utilizado pela etapa `powder_lines`.
            max_index:
                Parâmetro utilizado pela etapa `powder_lines`.
        Returns:
            Resultado documentado pelo contrato do chamador.

        Notes:
            Em fluxos DRX, valores de 2θ, d-spacing, FWHM e intensidade
            relativa devem ser interpretados em conjunto com preparação
            natural, glicolada e calcinada. Nenhum pico isolado deve ser
            tratado como confirmação mineralógica completa.
    """
    rows = []
    for h, k, l in generate_hkl(max_index):
        if crystal_system == "cubic":
            two_theta = cubic_two_theta(lambda_A, unit_cell["a"], h, k, l)
        elif crystal_system == "tetragonal":
            two_theta = tetragonal_two_theta(lambda_A, unit_cell["a"], unit_cell["c"], h, k, l)
        else:
            two_theta = None
        if two_theta is not None:
            rows.append({"h": h, "k": k, "l": l, "two_theta_deg": two_theta})
    return sorted(rows, key=lambda r: r["two_theta_deg"])
