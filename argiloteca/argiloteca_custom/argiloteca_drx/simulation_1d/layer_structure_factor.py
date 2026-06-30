# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: layer_structure_factor.py
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

"""Cálculo de G(theta) para camadas 00l."""
from __future__ import annotations
import math

def phase_coefficient(theta_deg, wavelength_A):
    """Eq. A.2: coeficiente de fase 4*pi*sin(theta)/lambda."""
    return 4.0 * math.pi * math.sin(math.radians(float(theta_deg))) / float(wavelength_A)

def layer_structure_factor(atomic_planes, theta_deg, wavelength_A=1.5418):
    """Calcula G(theta)=sum n*f*cos(4*pi*z*sin(theta)/lambda).

    Cada plano deve trazer z_A, scattering_factor e multiplier. Para o
    exemplo da ilita, scattering_factor já representa n*f(theta) e o
    multiplier representa duplicação por pseudoespelho.
    """
    total = 0.0
    details = []
    coeff = phase_coefficient(theta_deg, wavelength_A)
    for plane in atomic_planes or []:
        z = float(plane.get("z_A", 0.0))
        nf = float(plane.get("n_f_theta", plane.get("scattering_factor", 0.0)))
        multiplier = float(plane.get("multiplier", 1.0))
        cos_phi = math.cos(coeff * z)
        contribution = multiplier * nf * cos_phi
        details.append({**plane, "cos_phi": cos_phi, "contribution": contribution})
        total += contribution
    return {"G": total, "G_squared": total * total, "details": details}

def centrosymmetric_F_00l(atomic_planes):
    """Soma contribuições já expressas como n*f*cos(phi)."""
    total = sum(float(row.get("contribution", 0.0)) for row in atomic_planes or [])
    return {"F_00l": total, "F_squared": total * total}

