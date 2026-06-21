#!/usr/bin/env python3
"""Generate portable metrics for the Argiloteca DRX panel.

The panel itself is served by Invenio/Flask, but the publication package needs a
small command that can be run in a plain checkout to prove what data is available
for the DRX interface.  This script therefore reads only JSON/JSONL artifacts
from disk and emits a compact metrics report.

The defaults follow the local Argiloteca layout.  Every input can be overridden
with command-line flags so the same code can run in CI, on Linux, or on a copied
DRX package without editing source files.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_SNAPSHOT = (
    REPO_ROOT
    / "povoamento"
    / "visualizacao-drx"
    / "saida_argiloteca_drx"
    / "classificacao_mineralogica_raw.json"
)
DEFAULT_TREATMENT_SNAPSHOT = (
    REPO_ROOT
    / "povoamento"
    / "visualizacao-drx"
    / "saida_argiloteca_drx"
    / "classificacao_tratamento_raw.json"
)
DEFAULT_PACKAGES_DIR = REPO_ROOT / "var" / "instance" / "argiloteca_analytical_packages"
DEFAULT_STATIC_PACKAGES_DIR = (
    REPO_ROOT
    / "argiloteca"
    / "argiloteca_custom"
    / "argiloteca"
    / "static"
    / "data"
    / "analytical_packages"
)
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "drx_panel_metrics.json"
# Este script e deliberadamente derivado-only: le snapshots/manifestos e grava
# apenas um relatorio em reports/, sem tocar em RAWs ou classificacoes.


def read_json(path: Path) -> Any:
    """Read JSON and return ``None`` when the file is unavailable or invalid."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def rows_from_payload(payload: Any) -> list[dict[str, Any]]:
    """Normalize the common snapshot/manifest shapes used by the DRX pipeline."""
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("items", "results", "rows", "diffractograms"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def public_record_id(value: Any) -> str | None:
    """Return only IDs that look like public InvenioRDM record PIDs."""
    text = str(value or "").strip()
    if len(text) == 11 and text[5] == "-":
        return text
    return None


def count_minerals(rows: list[dict[str, Any]]) -> Counter:
    """Count mineral candidates by display name."""
    counter: Counter = Counter()
    for row in rows:
        candidates = row.get("candidates") or row.get("mineral_candidates") or []
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("mineral"):
                counter[str(candidate["mineral"]).strip()] += 1
    return counter


def count_scores(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Bucket candidate scores into simple ranges for dashboard QA."""
    buckets = Counter({"0.00-0.29": 0, "0.30-0.54": 0, "0.55-0.74": 0, "0.75-1.00": 0})
    for row in rows:
        for candidate in row.get("candidates") or row.get("mineral_candidates") or []:
            if not isinstance(candidate, dict):
                continue
            try:
                score = float(candidate.get("score"))
            except (TypeError, ValueError):
                continue
            if score >= 0.75:
                buckets["0.75-1.00"] += 1
            elif score >= 0.55:
                buckets["0.55-0.74"] += 1
            elif score >= 0.30:
                buckets["0.30-0.54"] += 1
            else:
                buckets["0.00-0.29"] += 1
    return dict(buckets)


def load_package_manifests(paths: list[Path]) -> list[dict[str, Any]]:
    """Load each DRX analytical package once, preferring the first directory hit."""
    manifests: dict[str, dict[str, Any]] = {}
    for root in paths:
        if not root.exists():
            continue
        for path in sorted(root.glob("*/drx_manifest.json")):
            record_id = path.parent.name
            if record_id in manifests:
                continue
            payload = read_json(path)
            if isinstance(payload, dict):
                payload["_manifest_path"] = str(path)
                manifests[record_id] = payload
    return list(manifests.values())


def build_metrics(args: argparse.Namespace) -> dict[str, Any]:
    """Assemble the full report consumed by Git/CI/release notes."""
    raw_payload = read_json(args.raw_snapshot)
    treatment_payload = read_json(args.treatment_snapshot)
    raw_rows = rows_from_payload(raw_payload)
    treatment_rows = rows_from_payload(treatment_payload)
    package_manifests = load_package_manifests(args.packages_dir)
    package_items = [item for manifest in package_manifests for item in rows_from_payload(manifest)]

    treatment_counter = Counter(
        str(row.get("treatment") or row.get("preparation") or "indeterminado")
        for row in treatment_rows or raw_rows
    )
    status_counter = Counter(str(row.get("status") or "sem_status") for row in raw_rows)
    package_record_ids = [public_record_id(manifest.get("record_id")) for manifest in package_manifests]
    package_record_ids = [record_id for record_id in package_record_ids if record_id]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "raw_snapshot": str(args.raw_snapshot),
            "raw_snapshot_exists": args.raw_snapshot.exists(),
            "treatment_snapshot": str(args.treatment_snapshot),
            "treatment_snapshot_exists": args.treatment_snapshot.exists(),
            "package_dirs": [str(path) for path in args.packages_dir],
        },
        "raw_snapshot": {
            "total_rows": len(raw_rows),
            "status": dict(status_counter),
            "with_candidates": sum(1 for row in raw_rows if row.get("candidates") or row.get("mineral_candidates")),
            "with_detected_peaks": sum(1 for row in raw_rows if row.get("peaks") or row.get("detected_peaks")),
            "top_minerals": count_minerals(raw_rows).most_common(args.top),
            "score_buckets": count_scores(raw_rows),
        },
        "treatments": {
            "total_rows": len(treatment_rows),
            "by_treatment": dict(treatment_counter),
        },
        "analytical_packages": {
            "total_manifests": len(package_manifests),
            "public_record_ids": sorted(set(package_record_ids)),
            "total_items": len(package_items),
            "items_with_candidates": sum(1 for item in package_items if item.get("mineral_candidates")),
            "items_with_advanced_results": sum(1 for item in package_items if item.get("advanced_result_path")),
            "items_with_fit_results": sum(1 for item in package_items if item.get("fit_results")),
            "items_with_valid_record_id": sum(1 for item in package_items if public_record_id(item.get("record_id"))),
            "top_minerals": count_minerals(package_items).most_common(args.top),
            "score_buckets": count_scores(package_items),
        },
    }


def parse_args() -> argparse.Namespace:
    """Parse paths and output controls for portable DRX metrics."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-snapshot", type=Path, default=DEFAULT_RAW_SNAPSHOT)
    parser.add_argument("--treatment-snapshot", type=Path, default=DEFAULT_TREATMENT_SNAPSHOT)
    parser.add_argument(
        "--packages-dir",
        type=Path,
        action="append",
        default=[DEFAULT_PACKAGES_DIR, DEFAULT_STATIC_PACKAGES_DIR],
        help="Directory containing */drx_manifest.json. Can be passed more than once.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--top", type=int, default=20, help="Number of top minerals to keep.")
    parser.add_argument("--stdout", action="store_true", help="Print JSON instead of writing only to --output.")
    return parser.parse_args()


def main() -> int:
    """Write the metrics artifact and optionally echo it to stdout."""
    args = parse_args()
    metrics = build_metrics(args)
    text = json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + "\n", encoding="utf-8")
    if args.stdout:
        print(text)
    else:
        print(f"Métricas DRX gravadas em {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
