# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: clay_layer_model.py
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

"""Modelos de camada usados pela simulação 1D."""
from __future__ import annotations

def default_layer_model(mineral="illite"):
    """Retorna modelo operacional de camada."""
    if mineral == "illite":
        return {
            "layer_model_id": "illite_10A_table_3_1",
            "d001_A": 10.0,
            "validation_status": "valid_for_worked_example",
        }
    return {"layer_model_id": f"{mineral}_exploratory", "validation_status": "requires_manual_verification"}

