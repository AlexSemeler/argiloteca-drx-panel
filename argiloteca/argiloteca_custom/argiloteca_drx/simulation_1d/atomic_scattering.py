# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: atomic_scattering.py
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

"""Fatores de espalhamento atômico simplificados para modo operacional.

O anexo indica que fatores de Wright/Klug-Alexander devem ser usados para
cálculo rigoroso. Esta tabela é uma aproximação de baixa/média angulação
para manter o painel funcional; o XAI marca uso exploratório.
"""
from __future__ import annotations

ELECTRON_APPROX = {
    "H": 1.0, "O": 7.6, "OH": 7.6, "Si": 13.2, "Al": 12.1,
    "Mg": 11.25, "Fe": 24.0, "K": 17.9, "Ca": 18.0, "Na": 10.0,
    "C": 6.0,
}

def scattering_factor(species, theta_deg=None, wavelength_A=1.5418):
    """Retorna fator aproximado; use biblioteca validada para ajuste final."""
    return float(ELECTRON_APPROX.get(str(species), 0.0))

