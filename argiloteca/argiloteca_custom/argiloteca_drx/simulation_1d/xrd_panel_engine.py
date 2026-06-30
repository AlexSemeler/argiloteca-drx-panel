# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: xrd_panel_engine.py
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

"""Ponto de entrada do motor de simulação 1D do painel."""
from __future__ import annotations
import numpy as np
from .calculated_pattern_builder import build_00l_pattern
from .instrumental_parameters import instrument_profile
from .observed_pattern_loader import normalize_observed
from .pattern_comparator import compare_patterns
from .xai_simulation_explainer import explain_simulation

def simulate_candidate_pattern(candidate_model="illite", two_theta_axis=None, parameters=None):
    """Simula um padrão 00l simplificado para o candidato."""
    params = dict(parameters or {})
    instrument = instrument_profile(params.get("instrument"))
    axis = two_theta_axis if two_theta_axis is not None else np.linspace(3.0, 35.0, 1601)
    if candidate_model in {"illite", "illite_001", "illite_mica"}:
        return build_00l_pattern(axis, d001_A=params.get("d001_A", 10.0), wavelength_A=instrument["wavelength_A"], G_squared=params.get("G_squared", 1246.09), N=params.get("N", 20), scale=params.get("scale", 1.0), fwhm_deg=params.get("fwhm_deg", 0.18))
    return build_00l_pattern(axis, d001_A=params.get("d001_A", 14.0), wavelength_A=instrument["wavelength_A"], G_squared=params.get("G_squared", 1000.0), N=params.get("N", 12), scale=params.get("scale", 1.0), fwhm_deg=params.get("fwhm_deg", 0.25))

def simulate_and_compare(two_theta, intensity, candidate_model="illite", parameters=None):
    """Compara padrão observado com padrão calculado 00l e retorna XAI."""
    observed = normalize_observed(two_theta, intensity)
    calculated = simulate_candidate_pattern(candidate_model, observed["two_theta"], parameters)
    comparison = compare_patterns(observed, calculated)
    explanation = explain_simulation(candidate_model, comparison, equations=["eq_3_14_intensity", "eq_3_9_layer_G"], tables=["table_3_1", "table_A_1"], figures=["fig_3_21"], warnings=["calculated pattern is supportive evidence, not standalone confirmation"])
    return {
        "engine_version": "argiloteca.xrd_1d_simulation.v1",
        "candidate_model": candidate_model,
        "observed": observed,
        "calculated": calculated,
        "comparison": comparison,
        "xai": explanation,
    }

