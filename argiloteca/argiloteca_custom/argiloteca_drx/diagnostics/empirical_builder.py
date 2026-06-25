"""Build local empirical ranges from specialist-validated patterns.

Fundamentacao cientifica revisada:
    Este arquivo integra o Painel DRX da Argiloteca, projeto fundamentado nas
    referencias cientificas revisadas para interpretacao auxiliar de DRX de
    argilominerais: Brindley & Brown (1980), Bailey (1980/1988),
    Moore & Reynolds (1989/1997), Drits & Tchoubar (1990),
    Lanson & Bouchet (1995), Meunier, Clays (2005), fluxograma USGS para
    identificacao de argilominerais por DRX e referencias empiricas Pre-Sal
    UFRGS/Petrobras.

Autoria cientifica e curadoria:
    Alexandre Ribas Semeler
    E-mail: alexandre.semler@ufrgs.br

Politica de interpretacao:
    Resultados mineralogicos sao auxiliares e nao confirmatorios. O codigo
    combina comportamento N/G/C, picos companheiros, d060, ambiguidades,
    contexto e proveniencia; nao confirma mineral por pico isolado.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import defaultdict

from .diagnostic_behavior_rules import POLICY

VALID_PREPARATIONS = {"natural", "air_dried", "N", "glycolated", "G", "calcined", "heated", "C"}


def _percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * fraction
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return ordered[int(pos)]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (pos - lower)


def _provenance_hash(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_empirical_ranges(validated_patterns: list[dict], min_samples: int = 5, range_strategy: str = "p05_p95") -> dict:
    buckets = defaultdict(list)
    ignored = 0
    for row in validated_patterns or []:
        if not isinstance(row, dict) or row.get("validation_status") != "accepted":
            ignored += 1
            continue
        try:
            d_spacing = float(row.get("d_spacing"))
        except (TypeError, ValueError):
            ignored += 1
            continue
        preparation = row.get("preparation")
        if d_spacing <= 0 or preparation not in VALID_PREPARATIONS:
            ignored += 1
            continue
        key = (row.get("mineral_id"), row.get("peak_id"), preparation)
        if not all(key):
            ignored += 1
            continue
        buckets[key].append({**row, "d_spacing": d_spacing})

    ranges = {}
    for (mineral_id, peak_id, preparation), rows in sorted(buckets.items()):
        values = [row["d_spacing"] for row in rows]
        n = len(values)
        mean = statistics.fmean(values)
        std = statistics.pstdev(values) if n > 1 else 0.0
        p05 = _percentile(values, 0.05)
        p95 = _percentile(values, 0.95)
        if range_strategy == "min_max":
            recommended = [min(values), max(values)]
        elif range_strategy == "mean_2std":
            recommended = [mean - 2 * std, mean + 2 * std]
        else:
            recommended = [p05, p95]
        provenance = {
            "sample_ids": sorted({str(row.get("sample_id")) for row in rows if row.get("sample_id")}),
            "source_record_ids": sorted({str(row.get("source_record_id")) for row in rows if row.get("source_record_id")}),
            "validated_by": sorted({str(row.get("validated_by")) for row in rows if row.get("validated_by")}),
        }
        ranges.setdefault(mineral_id, {}).setdefault(peak_id, {})[preparation] = {
            "n": n,
            "mean": mean,
            "std": std,
            "min": min(values),
            "max": max(values),
            "p05": p05,
            "p95": p95,
            "recommended_range": recommended,
            "confidence": "low" if n < min_samples else "reference_empirical",
            "provenance": provenance,
            "provenance_hash": _provenance_hash({"key": [mineral_id, peak_id, preparation], "values": values, **provenance}),
        }
    return {
        "policy": POLICY,
        "range_strategy": range_strategy,
        "min_samples": min_samples,
        "ignored_records": ignored,
        "ranges": ranges,
    }
