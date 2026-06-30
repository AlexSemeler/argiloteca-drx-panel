# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: geometry_explanation_engine.py
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


def explain_geometry(calculation: dict) -> dict:
    """
    Executa a etapa `explain_geometry` do módulo.

        Args:
            calculation:
                Parâmetro utilizado pela etapa `explain_geometry`.
        Returns:
            Resultado documentado pelo contrato do chamador.

        Notes:
            Em fluxos DRX, valores de 2θ, d-spacing, FWHM e intensidade
            relativa devem ser interpretados em conjunto com preparação
            natural, glicolada e calcinada. Nenhum pico isolado deve ser
            tratado como confirmação mineralógica completa.
    """
    return {
        "calculation_id": calculation.get("calculation_id"),
        "input": calculation.get("input", {}),
        "outputs": calculation.get("outputs", {}),
        "evidence_for": calculation.get("evidence_for", []),
        "evidence_against": calculation.get("evidence_against", []),
        "warnings": calculation.get("warnings", []),
        "uncertainty_sources": calculation.get("uncertainty_sources", []),
        "source_equations": calculation.get("source_equations", []),
        "source_figures": calculation.get("source_figures", []),
    }
