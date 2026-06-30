# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: observed_pattern_loader.py
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

"""Normalização de padrão observado para comparação."""
from __future__ import annotations
import numpy as np

def normalize_observed(two_theta, intensity):
    """Retorna eixo/intensidade normalizados ao máximo."""
    x = np.asarray(two_theta, dtype=float)
    y = np.asarray(intensity, dtype=float)
    max_y = float(np.max(y)) if y.size else 1.0
    if max_y <= 0:
        max_y = 1.0
    return {"two_theta": x.tolist(), "intensity": (y / max_y).tolist()}

