# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: parameter_sensitivity_analyzer.py
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

"""Sensibilidade operacional de parâmetros."""
from __future__ import annotations

def sensitivity_summary():
    """Lista parâmetros que mais afetam posição, intensidade e largura."""
    return {
        "position": ["wavelength_A", "d001_A", "zero_shift"],
        "intensity": ["G_squared", "Lorentz_polarization", "preferred_orientation", "quartz_reference"],
        "width": ["N_layers", "defect_free_distance", "instrumental_broadening"],
    }

