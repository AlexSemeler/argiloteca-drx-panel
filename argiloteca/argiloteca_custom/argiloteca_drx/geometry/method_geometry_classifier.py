# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: method_geometry_classifier.py
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


def classify_method(lambda_behavior: str, theta_behavior: str, sample_type: str = "") -> str:
    """
    Executa a etapa `classify_method` do módulo.

        Args:
            lambda_behavior:
                Parâmetro utilizado pela etapa `classify_method`.
            theta_behavior:
                Parâmetro utilizado pela etapa `classify_method`.
            sample_type:
                Parâmetro utilizado pela etapa `classify_method`.
        Returns:
            Resultado documentado pelo contrato do chamador.

        Notes:
            Em fluxos DRX, valores de 2θ, d-spacing, FWHM e intensidade
            relativa devem ser interpretados em conjunto com preparação
            natural, glicolada e calcinada. Nenhum pico isolado deve ser
            tratado como confirmação mineralógica completa.
    """
    lb = (lambda_behavior or "").lower()
    tb = (theta_behavior or "").lower()
    sample = (sample_type or "").lower()
    if "variable" in lb and "fixed" in tb:
        return "laue_method"
    if "fixed" in lb and "variable" in tb and "powder" in sample:
        return "powder_method"
    if "fixed" in lb and "variable" in tb and "single" in sample:
        return "rotating_crystal_method"
    return "unknown"
