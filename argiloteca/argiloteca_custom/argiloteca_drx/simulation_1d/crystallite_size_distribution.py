"""Distribuições de N para simulação de largura de pico."""
from __future__ import annotations

def uniform_distribution(low_N=3, high_N=14):
    """Distribuição q(N)=1 normalizada."""
    values = list(range(int(low_N), int(high_N) + 1))
    weight = 1.0 / float(len(values) or 1)
    return [{"N": n, "weight": weight} for n in values]

