# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: xai_simulation_explainer.py
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

"""Explicações XAI para simulação 1D."""
from __future__ import annotations

def explain_simulation(candidate_model, comparison, equations=None, tables=None, figures=None, warnings=None):
    """Monta payload XAI de simulação."""
    status = comparison.get("status", "ambiguous")
    confidence = {"compatible": 0.72, "possible": 0.45, "incompatible": 0.15}.get(status, 0.0)
    return {
        "candidate_model": candidate_model,
        "diagnostic_status": "probable" if status == "compatible" else status,
        "confidence": confidence,
        "equations_used": equations or [],
        "tables_used": tables or [],
        "figures_used": figures or [],
        "evidence_for": [{"evidence": "observed pattern compared with calculated 00l model", "metric": comparison.get("rmse"), "rule_id": "positions_only_not_confirmation"}],
        "evidence_against": [] if status != "incompatible" else [{"evidence": "calculated profile incompatible with observed profile", "metric": comparison.get("rmse")}],
        "ambiguous_evidence": [],
        "missing_data": [],
        "warnings": warnings or [],
        "next_best_tests": ["verify instrument profile", "compare treatment-specific patterns"],
    }

