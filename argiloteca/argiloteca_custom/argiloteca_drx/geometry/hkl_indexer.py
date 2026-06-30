# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: hkl_indexer.py
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

from .diffraction_direction_predictor import cubic_two_theta, tetragonal_two_theta


def generate_hkl(max_index: int = 5):
    """
    Executa a etapa `generate_hkl` do módulo.

        Args:
            max_index:
                Parâmetro utilizado pela etapa `generate_hkl`.
        Returns:
            Resultado documentado pelo contrato do chamador.

        Notes:
            Em fluxos DRX, valores de 2θ, d-spacing, FWHM e intensidade
            relativa devem ser interpretados em conjunto com preparação
            natural, glicolada e calcinada. Nenhum pico isolado deve ser
            tratado como confirmação mineralógica completa.
    """
    for h in range(0, max_index + 1):
        for k in range(0, max_index + 1):
            for l in range(0, max_index + 1):
                if h or k or l:
                    yield h, k, l


def candidate_hkl_for_peak(two_theta_deg: float, lambda_A: float, crystal_system: str, unit_cell: dict, tolerance_deg: float = 0.2, max_index: int = 6):
    """
    Executa a etapa `candidate_hkl_for_peak` do módulo.

        Args:
            two_theta_deg:
                Parâmetro utilizado pela etapa `candidate_hkl_for_peak`.
            lambda_A:
                Parâmetro utilizado pela etapa `candidate_hkl_for_peak`.
            crystal_system:
                Parâmetro utilizado pela etapa `candidate_hkl_for_peak`.
            unit_cell:
                Parâmetro utilizado pela etapa `candidate_hkl_for_peak`.
            tolerance_deg:
                Parâmetro utilizado pela etapa `candidate_hkl_for_peak`.
            max_index:
                Parâmetro utilizado pela etapa `candidate_hkl_for_peak`.
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
            pred = cubic_two_theta(lambda_A, unit_cell["a"], h, k, l)
        elif crystal_system == "tetragonal":
            pred = tetragonal_two_theta(lambda_A, unit_cell["a"], unit_cell["c"], h, k, l)
        else:
            pred = None
        if pred is None:
            continue
        delta = abs(pred - float(two_theta_deg))
        if delta <= tolerance_deg:
            rows.append({"h": h, "k": k, "l": l, "two_theta_deg": pred, "delta_deg": delta})
    return sorted(rows, key=lambda r: (r["delta_deg"], r["two_theta_deg"]))
