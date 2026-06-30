"""Construção de padrão calculado 00l simplificado."""
from __future__ import annotations
import math
import numpy as np
from .interference_function import finite_stack_phi
from .lorentz_polarization import lorentz_polarization

def gaussian(x, center, fwhm):
    sigma = float(fwhm) / 2.354820045
    return np.exp(-0.5 * ((x - center) / max(sigma, 1e-9)) ** 2)

def build_00l_pattern(two_theta_axis, d001_A=10.0, wavelength_A=1.5418, orders=(1,2,3,4,5), G_squared=1246.09, N=20, scale=1.0, fwhm_deg=0.18):
    """Gera perfil 00l aproximado usando posições de Bragg e envelopes gaussianos."""
    x = np.asarray(two_theta_axis, dtype=float)
    y = np.zeros_like(x)
    peaks = []
    for order in orders:
        d = float(d001_A) / float(order)
        arg = float(wavelength_A) / (2.0 * d)
        if arg <= 0 or arg >= 1:
            continue
        theta = math.degrees(math.asin(arg))
        tt = 2.0 * theta
        phi = finite_stack_phi(theta, d001_A, N, wavelength_A)["Phi"]
        lp = lorentz_polarization(theta)
        intensity = float(scale) * G_squared * phi * lp / (order ** 2)
        y += intensity * gaussian(x, tt, fwhm_deg)
        peaks.append({"order": order, "two_theta": tt, "d_A": d, "relative_intensity": intensity})
    return {"two_theta": x.tolist(), "intensity": y.tolist(), "calculated_peaks": peaks}

def general_1d_intensity(*args, **kwargs):
    """Placeholder auditável para Eq. A.1; requer tabelas completas verificadas."""
    return {"validation_status": "requires_manual_verification", "reason": "Eq. A.1 symbol layout and full atom tables require manual verification."}

