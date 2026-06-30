# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: geometry_engine.py
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

from .angle_conventions import theta_from_two_theta
from .bragg import bragg_d_spacing, bragg_observable
from .hkl_indexer import candidate_hkl_for_peak
from .nonideal_condition_analyzer import analyze_nonideal_conditions
from .wavelength_units import normalize_wavelength
from .geometry_explanation_engine import explain_geometry


def interpret_peak_geometry(two_theta_deg: float, wavelength: float, wavelength_unit: str = "angstrom", method: str = "", crystal_system: str = "", unit_cell: dict | None = None, metadata: dict | None = None) -> dict:
    """
    Executa a etapa `interpret_peak_geometry` do módulo.

        Args:
            two_theta_deg:
                Parâmetro utilizado pela etapa `interpret_peak_geometry`.
            wavelength:
                Parâmetro utilizado pela etapa `interpret_peak_geometry`.
            wavelength_unit:
                Parâmetro utilizado pela etapa `interpret_peak_geometry`.
            method:
                Parâmetro utilizado pela etapa `interpret_peak_geometry`.
            crystal_system:
                Parâmetro utilizado pela etapa `interpret_peak_geometry`.
            unit_cell:
                Parâmetro utilizado pela etapa `interpret_peak_geometry`.
            metadata:
                Parâmetro utilizado pela etapa `interpret_peak_geometry`.
        Returns:
            Resultado documentado pelo contrato do chamador.

        Notes:
            Em fluxos DRX, valores de 2θ, d-spacing, FWHM e intensidade
            relativa devem ser interpretados em conjunto com preparação
            natural, glicolada e calcinada. Nenhum pico isolado deve ser
            tratado como confirmação mineralógica completa.
    """
    wl = normalize_wavelength(wavelength, wavelength_unit)
    lambda_A = wl["lambda_A"]
    theta = theta_from_two_theta(two_theta_deg)
    d_A = bragg_d_spacing(lambda_A, two_theta_deg)
    nonideal = analyze_nonideal_conditions(metadata)
    hkl = []
    if crystal_system and unit_cell:
        hkl = candidate_hkl_for_peak(two_theta_deg, lambda_A, crystal_system, unit_cell)
    status = "valid" if bragg_observable(lambda_A, d_A) else "invalid"
    calc = {
        "calculation_id": "bragg_peak_geometry",
        "input": {"two_theta_deg": two_theta_deg, "lambda_A": lambda_A, "method": method, "crystal_system": crystal_system, "unit_cell": unit_cell or {}},
        "outputs": {"theta_deg": theta, "d_A": d_A, "candidate_hkl": hkl, "geometric_status": status},
        "evidence_for": [{"evidence": "2theta was converted to theta before applying Bragg law", "rule_id": "theta_two_theta_convention"}, {"evidence": "d-spacing computed from lambda = 2d sin theta", "rule_id": "bragg_first_order"}],
        "evidence_against": [],
        "warnings": wl["warnings"] + nonideal["warnings"] + ["Geometric possibility does not imply nonzero intensity."],
        "uncertainty_sources": nonideal["warnings"],
        "source_equations": ["eq_3_5"],
        "source_figures": ["fig_3_2"],
    }
    return explain_geometry(calc)
