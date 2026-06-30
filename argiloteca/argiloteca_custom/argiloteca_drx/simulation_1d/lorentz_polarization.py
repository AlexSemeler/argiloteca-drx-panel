# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: lorentz_polarization.py
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

"""Fator Lorentz-polarização Eq. A.4."""
from __future__ import annotations
import math

def lorentz_polarization(theta_deg, orientation_y=1.0):
    """Lp = ((1 + cos^2(2theta)) * y) / sin(theta)."""
    theta = math.radians(float(theta_deg))
    if abs(math.sin(theta)) < 1e-12:
        return float("inf")
    return ((1.0 + math.cos(2.0 * theta) ** 2) * float(orientation_y)) / math.sin(theta)

