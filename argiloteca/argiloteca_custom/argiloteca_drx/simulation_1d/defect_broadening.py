# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: defect_broadening.py
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

"""Distribuição q(N) para defect broadening Eq. A.8."""
from __future__ import annotations
import math

def q_of_N(N, defect_free_distance):
    """q(N)=exp(-(N-1)/delta)."""
    return math.exp(-(float(N) - 1.0) / float(defect_free_distance))

def defect_distribution(low_N=3, high_N=58, defect_free_distance=10):
    """Retorna distribuição normalizada de tamanhos coerentes."""
    rows = [{"N": int(N), "q": q_of_N(N, defect_free_distance)} for N in range(int(low_N), int(high_N) + 1)]
    total = sum(row["q"] for row in rows) or 1.0
    for row in rows:
        row["weight"] = row["q"] / total
    return rows

