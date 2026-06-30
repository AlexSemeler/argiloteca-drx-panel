# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: provenance_tracker.py
#
# Descrição.........:
# Implementa regras explicáveis para argilominerais interestratificados e padrões 00l multi-tratamento.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Última atualização:
# 2026-06-25
#
# =============================================================================

"""
Implementa regras explicáveis para argilominerais interestratificados e padrões 00l multi-tratamento.

Responsabilidades:
    - preservar contratos públicos e estruturas JSON consumidas pelo painel;
    - registrar proveniência científica e técnica das operações realizadas;
    - manter separadas etapas de leitura, processamento, diagnóstico e exportação;
    - documentar limites de interpretação mineralógica quando houver regras DRX.

Notas científicas:
    Em módulos DRX, 2θ representa o eixo angular medido no difratograma e
    d-spacing representa o espaçamento interplanar calculado pela Lei de Bragg
    (nλ = 2d sen θ). Preparações natural, glicolada e calcinada são usadas para
    observar expansão, colapso, persistência ou destruição de picos basais.
"""

from __future__ import annotations

"""Carregamento de dados e proveniencia das regras do Capitulo 8."""

from importlib.resources import files
import json

DATA_PACKAGE = "argiloteca_custom.argiloteca_drx.diagnostics.data.chapter8_mixed_layer"


def load_json(name: str):
    """Carrega um artefato JSON da base `chapter8_mixed_layer`.

    Primeiro tenta `importlib.resources`, apropriado quando o pacote esta
    instalado. Se a aplicacao estiver rodando direto da arvore local, usa o
    caminho relativo ao modulo.
    """
    try:
        return json.loads((files(DATA_PACKAGE) / name).read_text(encoding="utf-8"))
    except Exception:
        from pathlib import Path
        here = Path(__file__).resolve().parents[1] / "data" / "chapter8_mixed_layer"
        return json.loads((here / name).read_text(encoding="utf-8"))


def provenance(rule: dict) -> dict:
    """Extrai o bloco `source` de uma regra para exibicao XAI."""
    return (rule or {}).get("source", {})
