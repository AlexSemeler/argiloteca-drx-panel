# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: debeye_waller.py
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

"""Correção Debye-Waller Eq. A.7."""
from __future__ import annotations
import math

def debye_waller_factor(f0, B, theta_deg, wavelength_A):
    """Aplica f = f0 exp(-B sin(theta)^2 / lambda^2)."""
    theta = math.radians(float(theta_deg))
    return float(f0) * math.exp(-float(B) * (math.sin(theta) ** 2) / (float(wavelength_A) ** 2))

