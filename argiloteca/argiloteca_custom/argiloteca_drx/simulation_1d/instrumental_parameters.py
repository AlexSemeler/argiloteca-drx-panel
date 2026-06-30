# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: instrumental_parameters.py
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

"""Perfil instrumental default extraído da Table A.1."""
from __future__ import annotations

DEFAULT_INSTRUMENT = {
    "wavelength_A": 1.5418,
    "divergence_slit_deg": 1.0,
    "goniometer_radius_cm": 20.0,
    "soller_slit_1_deg": 6.6,
    "soller_slit_2_deg": 2.0,
    "sample_length_cm": 3.6,
    "quartz_reference_intensity_cps": 25000,
}

def instrument_profile(overrides=None):
    """Combina defaults da Table A.1 com parâmetros do usuário."""
    profile = dict(DEFAULT_INSTRUMENT)
    profile.update(overrides or {})
    return profile


