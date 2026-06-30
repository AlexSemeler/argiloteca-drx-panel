# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: interlayer_complex_model.py
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

"""Modelos de intercamada e regras de expansão/colapso."""
from __future__ import annotations

def interlayer_model(complex_name="K"):
    """Retorna estado de intercamada para simulação."""
    aliases = {"ethylene_glycol": "two_glycol_layers", "EG": "two_glycol_layers", "water": "one_or_two_water_layers"}
    name = aliases.get(complex_name, complex_name)
    return {"interlayer_complex": name, "requires_recompute": True}

