# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: residual_analyzer.py
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

"""Análise de resíduos do ajuste 1D."""
from __future__ import annotations
import numpy as np

def residuals(observed, calculated):
    """Retorna vetor de resíduos observado-calculado."""
    yo = np.asarray(observed.get("intensity") or [], dtype=float)
    yc = np.asarray(calculated.get("intensity") or [], dtype=float)
    n = min(len(yo), len(yc))
    return (yo[:n] - yc[:n]).tolist()

