# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: interference_function.py
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

"""Função de interferência para domínios coerentes finitos."""
from __future__ import annotations
import math

def finite_stack_phi(theta_deg, d001_A, N, wavelength_A=1.5418):
    """Calcula Phi = sin^2(N*x)/sin^2(x), com x=2*pi*d*sin(theta)/lambda."""
    theta = math.radians(float(theta_deg))
    x = 2.0 * math.pi * float(d001_A) * math.sin(theta) / float(wavelength_A)
    denom = math.sin(x) ** 2
    if abs(denom) < 1e-12:
        return {"Phi": float(N) ** 2, "warning": "near_bragg_limit_used", "x": x}
    return {"Phi": (math.sin(float(N) * x) ** 2) / denom, "warning": None, "x": x}

