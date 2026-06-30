# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: sample_length_correction.py
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

"""Correção de projeção de feixe longo Eq. A.6."""
from __future__ import annotations
import math

def beam_footprint_length(theta_deg, goniometer_radius_cm, divergence_slit_deg):
    """LB = Ro * alpha(rad) / sin(theta)."""
    theta = math.radians(float(theta_deg))
    if abs(math.sin(theta)) < 1e-12:
        return float("inf")
    return float(goniometer_radius_cm) * math.radians(float(divergence_slit_deg)) / math.sin(theta)

def sample_length_factor(theta_deg, goniometer_radius_cm, divergence_slit_deg, sample_length_cm):
    """Multiplica intensidade por sample_length/LB quando LB excede a amostra."""
    lb = beam_footprint_length(theta_deg, goniometer_radius_cm, divergence_slit_deg)
    sample = float(sample_length_cm)
    if lb <= sample:
        return {"factor": 1.0, "LB_cm": lb, "applied": False}
    return {"factor": sample / lb, "LB_cm": lb, "applied": True}

