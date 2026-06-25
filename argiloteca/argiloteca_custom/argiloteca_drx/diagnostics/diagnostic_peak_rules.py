"""Catalogo central de faixas diagnosticas DRX da Argiloteca.

Este modulo carrega o arquivo visivel:

    argiloteca/static/data/diagnostic_peak_rules_catalog.json

Objetivo:
    manter os valores de picos/ranges em um unico local editavel, evitando que
    o painel, scripts batch e servicos Python usem copias divergentes.

Politica:
    policy="argiloteca_rule_based_diagnostic". As faixas sao janelas de
    evidencia; nenhuma funcao deste modulo confirma mineral por pico isolado.
"""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path


CATALOG_PATH = (
    Path(__file__).resolve().parents[2]
    / "argiloteca"
    / "static"
    / "data"
    / "diagnostic_peak_rules_catalog.json"
)


def _range_tuple(row):
    """Converte um objeto JSON de faixa em tupla ``(d_min, d_max)``."""
    return (float(row["d_min"]), float(row["d_max"]))


@lru_cache(maxsize=1)
def load_peak_rule_catalog():
    """Carrega e valida minimamente o catalogo central de picos.

    Returns:
        dict: Conteudo do JSON.

    Raises:
        FileNotFoundError: se o catalogo nao existir.
        ValueError: se a policy ou secoes essenciais estiverem ausentes.
    """
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if data.get("policy") != "argiloteca_rule_based_diagnostic":
        raise ValueError("diagnostic_peak_rules_catalog.json deve declarar policy argiloteca_rule_based_diagnostic")
    if not isinstance(data.get("named_ranges"), dict):
        raise ValueError("diagnostic_peak_rules_catalog.json sem named_ranges")
    return data


def named_range(range_id):
    """Retorna ``(d_min, d_max)`` para uma faixa nomeada."""
    return _range_tuple(load_peak_rule_catalog()["named_ranges"][range_id])


def range_target(range_id, default=None):
    """Retorna o valor-alvo de uma faixa, quando declarado no catalogo."""
    value = load_peak_rule_catalog()["named_ranges"][range_id].get("target", default)
    return None if value is None else float(value)


def mapped_ranges(section):
    """Converte uma secao que mapeia nome local -> range_id em tuplas.

    Exemplo:
        ``workflow_diagnostic_ranges`` vira ``{"chlorite_14a": (13.58, 14.87)}``.
    """
    catalog = load_peak_rule_catalog()
    named = catalog["named_ranges"]
    return {
        key: _range_tuple(named[range_id])
        for key, range_id in (catalog.get(section) or {}).items()
    }


def targeted_basal_ranges(as_tuple=False):
    """Retorna os ranges direcionados para peak-picking basal.

    Args:
        as_tuple: quando ``True``, retorna tupla de dicionarios para constantes
            historicas como ``TARGETED_BASAL_PEAK_RANGES``.
    """
    catalog = load_peak_rule_catalog()
    rows = []
    for range_id, item in (catalog.get("targeted_basal_ranges") or {}).items():
        d_min, d_max = named_range(item["range"])
        row = {
            "range_id": range_id,
            "mineral": item["mineral"],
            "label": item["label"],
            "d_min": d_min,
            "d_max": d_max,
            "rule_source": catalog["named_ranges"][item["range"]].get("rule_source"),
        }
        rows.append(row)
    return tuple(rows) if as_tuple else {row["range_id"]: {k: v for k, v in row.items() if k != "range_id"} for row in rows}


def simple_analysis_ranges():
    """Retorna ranges simples usados por ``argiloteca.services.drx_analysis``."""
    rows = []
    for item in load_peak_rule_catalog().get("simple_analysis_ranges") or []:
        d_min, d_max = named_range(item["range"])
        rows.append({**item, "d_min": d_min, "d_max": d_max})
    return tuple(rows)


def peak_sets():
    """Retorna conjuntos de picos companheiros consumidos por peak_sets.py."""
    catalog = load_peak_rule_catalog()
    named = catalog["named_ranges"]
    out = {}
    for family, rows in (catalog.get("peak_sets") or {}).items():
        converted = []
        for row in rows:
            if row.get("range"):
                d_min, d_max = _range_tuple(named[row["range"]])
            else:
                d_min, d_max = float(row["d_min"]), float(row["d_max"])
            converted.append((d_min, d_max, row["label"]))
        out[family] = converted
    return out


def frontend_rules_payload():
    """Retorna somente as secoes que o JavaScript usa na interface."""
    catalog = load_peak_rule_catalog()
    return {
        "version": catalog.get("version"),
        "policy": catalog.get("policy"),
        "named_ranges": catalog.get("named_ranges", {}),
        "frontend_sem_titulo_ranges": catalog.get("frontend_sem_titulo_ranges", {}),
        "frontend_mineral_reflection_rules": catalog.get("frontend_mineral_reflection_rules", []),
    }
