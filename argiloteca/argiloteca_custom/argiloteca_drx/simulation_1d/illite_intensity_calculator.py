# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: illite_intensity_calculator.py
#
# Descrição.........:
# Implementa simulação 1D de padrões 00l, cálculo de intensidades e comparação observado × calculado.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Última atualização:
# 2026-06-25
#
# =============================================================================

"""Cálculo do exemplo de intensidade 001 da ilita."""
from __future__ import annotations
from .interference_function import finite_stack_phi
from .lorentz_polarization import lorentz_polarization

TABLE_3_1_TERMS = [
    {"atoms": "1.6 K", "contribution": -28.6},
    {"atoms": "6 O", "contribution": -43.8},
    {"atoms": "3.4 Si; 0.6 Al", "contribution": -11.8},
    {"atoms": "4 O; 2 OH", "contribution": 71.4},
    {"atoms": "3.6 Al; 0.4 Mg", "contribution": 48.1},
]

def calculate_illite_001(theta_deg=4.4, wavelength_A=1.54, d001_A=10.0, N=20, include_lp=False):
    """Reproduz o cálculo trabalhado: G≈35.3, Phi≈520 no OCR do exemplo."""
    G = sum(row["contribution"] for row in TABLE_3_1_TERMS)
    phi = finite_stack_phi(theta_deg, d001_A, N, wavelength_A)
    lp = lorentz_polarization(theta_deg) if include_lp else 1.0
    intensity = (G ** 2) * float(phi["Phi"]) * lp
    return {
        "model": "illite_001_table_3_1",
        "G": G,
        "G_squared": G ** 2,
        "Phi": phi["Phi"],
        "Lp": lp,
        "intensity": intensity,
        "warnings": [phi["warning"]] if phi.get("warning") else [],
        "source_equations": ["eq_3_16_illite_G", "eq_3_14_intensity"],
        "source_tables": ["table_3_1"],
        "source_figures": ["fig_3_20", "fig_3_21"],
    }

