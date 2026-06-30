# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: pattern_comparator.py
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

"""Comparação observado × calculado."""
from __future__ import annotations
import numpy as np

def compare_patterns(observed, calculated):
    """Calcula RMSE e correlação entre perfis já no mesmo eixo."""
    yo = np.asarray(observed.get("intensity") or [], dtype=float)
    yc = np.asarray(calculated.get("intensity") or [], dtype=float)
    n = min(len(yo), len(yc))
    if n == 0:
        return {"status": "insufficient_data", "rmse": None, "correlation": None}
    yo = yo[:n]
    yc = yc[:n]
    if np.max(np.abs(yc)) > 0:
        yc = yc / np.max(np.abs(yc))
    if np.max(np.abs(yo)) > 0:
        yo = yo / np.max(np.abs(yo))
    rmse = float(np.sqrt(np.mean((yo - yc) ** 2)))
    corr = float(np.corrcoef(yo, yc)[0, 1]) if n > 2 and np.std(yo) and np.std(yc) else None
    status = "compatible" if rmse <= 0.25 else "possible" if rmse <= 0.45 else "incompatible"
    return {"status": status, "rmse": rmse, "correlation": corr}

