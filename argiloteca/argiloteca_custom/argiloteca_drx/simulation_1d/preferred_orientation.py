# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: preferred_orientation.py
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

"""Modelo simples de orientação preferencial para o painel."""
from __future__ import annotations

def orientation_factor(sigma_star=None, mode="oriented_aggregate"):
    """Retorna y operacional; fórmula completa de Reynolds exige perfil instrumental."""
    if sigma_star is None:
        return 1.0
    sigma = max(float(sigma_star), 1e-6)
    if mode == "random_powder":
        return 1.0
    return min(25.0, max(0.1, 12.0 / sigma))

