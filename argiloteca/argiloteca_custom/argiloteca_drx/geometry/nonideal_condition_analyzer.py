# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: nonideal_condition_analyzer.py
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


def analyze_nonideal_conditions(metadata: dict | None = None) -> dict:
    """
    Executa a etapa `analyze_nonideal_conditions` do módulo.

        Args:
            metadata:
                Parâmetro utilizado pela etapa `analyze_nonideal_conditions`.
        Returns:
            Resultado documentado pelo contrato do chamador.

        Notes:
            Em fluxos DRX, valores de 2θ, d-spacing, FWHM e intensidade
            relativa devem ser interpretados em conjunto com preparação
            natural, glicolada e calcinada. Nenhum pico isolado deve ser
            tratado como confirmação mineralógica completa.
    """
    md = metadata or {}
    warnings = []
    for key in ("beam_divergence", "finite_spectral_width", "finite_crystallite_size", "strain", "dislocations"):
        if md.get(key):
            warnings.append(f"{key} can broaden or shift the ideal geometric peak shape")
    return {"warnings": warnings, "geometric_status_modifier": "nonideal" if warnings else "ideal_assumed"}
