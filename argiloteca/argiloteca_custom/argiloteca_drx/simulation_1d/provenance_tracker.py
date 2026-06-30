# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: provenance_tracker.py
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

"""Carregamento dos artefatos JSON da base de simulação 1D."""
from __future__ import annotations
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "diagnostics" / "data" / "xrd_1d_simulation"

def load_json(name):
    """Carrega um JSON de regras/equações/tabelas da simulação 1D."""
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))

def provenance(source):
    """Normaliza a fonte para exibição no painel XAI."""
    return dict(source or {})

