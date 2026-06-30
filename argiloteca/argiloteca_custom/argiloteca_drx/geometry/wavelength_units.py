# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: wavelength_units.py
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

KX_TO_ANGSTROM_STAR = 1.002056


def normalize_wavelength(value: float, unit: str = "angstrom") -> dict:
    """
    Executa a etapa `normalize_wavelength` do módulo.

        Args:
            value:
                Parâmetro utilizado pela etapa `normalize_wavelength`.
            unit:
                Parâmetro utilizado pela etapa `normalize_wavelength`.
        Returns:
            Resultado documentado pelo contrato do chamador.

        Notes:
            Em fluxos DRX, valores de 2θ, d-spacing, FWHM e intensidade
            relativa devem ser interpretados em conjunto com preparação
            natural, glicolada e calcinada. Nenhum pico isolado deve ser
            tratado como confirmação mineralógica completa.
    """
    unit_l = (unit or "angstrom").lower().replace("å", "a")
    if unit_l in {"angstrom", "a", "ang"}:
        return {"lambda_A": float(value), "unit": "angstrom", "warnings": []}
    if unit_l in {"angstrom_star", "a*", "å*"}:
        return {"lambda_A": float(value), "unit": "angstrom_star", "warnings": ["Angstrom-star is a legacy precision unit."]}
    if unit_l == "kx":
        return {"lambda_A": float(value) * KX_TO_ANGSTROM_STAR, "unit": "kX", "warnings": ["kX is a historical relative wavelength unit converted using Chapter 3 Eq. 3-16."]}
    raise ValueError(f"unsupported wavelength unit: {unit}")
