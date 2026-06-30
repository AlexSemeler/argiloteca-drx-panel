# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: reichweite_model.py
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

"""Reichweite e probabilidades condicionais."""
from __future__ import annotations

def conditional_probabilities(component_fraction_A, Reichweite=0):
    """Retorna probabilidades operacionais para R0/R1."""
    pA = float(component_fraction_A)
    pB = 1.0 - pA
    if int(Reichweite) == 0:
        return {"P_A": pA, "P_B": pB, "ordering": "R0_random"}
    if pA >= 0.5:
        pBA = 1.0
        pBB = 0.0
        pAB = pB * pBA / pA if pA else 0.0
        pAA = 1.0 - pAB
    else:
        pAB = 1.0
        pAA = 0.0
        pBA = pA * pAB / pB if pB else 0.0
        pBB = 1.0 - pBA
    return {"P_A": pA, "P_B": pB, "P_AA": pAA, "P_AB": pAB, "P_BA": pBA, "P_BB": pBB, "ordering": "R1_operational"}

