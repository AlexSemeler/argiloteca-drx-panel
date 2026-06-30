#!/usr/bin/env python3
"""Exporta a base executavel do Capitulo 8 para JSON auditavel.

Fonte cientifica:
    Capitulo "Identification of Mixed-Layered Clay Minerals".

Este script materializa regras de argilominerais interestratificados,
nomenclatura, principios de Mering, ordenamento R0/R1/R3, comportamento entre
tratamentos, diagnostico diferencial, perfis mixed-layer, ontologia e schemas.
Ele nao executa inferencia mineralogica nem modelagem 00l; apenas exporta a
base de conhecimento para auditoria, documentacao, InvenioRDM, OpenSearch e
validadores externos.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from argiloteca_drx.diagnostics.chapter8_mixed_layer_knowledge import get_chapter8_mixed_layer_knowledge  # noqa: E402


DEFAULT_OUTPUT = ROOT / "argiloteca_drx" / "diagnostics" / "data" / "generated"


def write_json(path: Path, payload) -> None:
    """Grava JSON com UTF-8, indentacao estavel e quebra de linha final."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def export_chapter8_mixed_layer_knowledge(output_dir: Path) -> dict:
    """Exporta todas as camadas estruturadas da base mixed-layer do Capitulo 8."""
    knowledge = get_chapter8_mixed_layer_knowledge()
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "chapter8_mixed_layer_entities.json": knowledge["entities"],
        "chapter8_nomenclature_rules.json": knowledge["nomenclature_rules"],
        "chapter8_mering_rules.json": knowledge["mering_rules"],
        "chapter8_ordering_rules.json": knowledge["ordering_rules"],
        "chapter8_treatment_behavior_rules.json": knowledge["treatment_behavior_rules"],
        "chapter8_differential_rules.json": knowledge["differential_rules"],
        "chapter8_mixed_layer_profiles.json": knowledge["mixed_layer_profiles"],
        "chapter8_mixed_layer_ontology.json": knowledge["ontology"],
        "chapter8_mixed_layer_schemas.json": knowledge["schemas"],
        "chapter8_mixed_layer_knowledge_complete.json": knowledge,
    }
    for filename, payload in files.items():
        write_json(output_dir / filename, payload)

    manifest = {
        "version": "argiloteca.drx.chapter8.mixed_layer.knowledge.export.v1",
        "policy": knowledge["source"]["policy"],
        "source_id": knowledge["source"]["source_id"],
        "source_full_title": knowledge["source"]["source_full_title"],
        "source_pdf": knowledge["source"]["local_pdf"],
        "output_dir": str(output_dir),
        "files": sorted(files),
        "counts": {
            "entities": len(knowledge["entities"]),
            "nomenclature_rules": len(knowledge["nomenclature_rules"]),
            "mering_rules": len(knowledge["mering_rules"]),
            "ordering_rules": len(knowledge["ordering_rules"]),
            "treatment_behavior_rules": len(knowledge["treatment_behavior_rules"]),
            "differential_rules": len(knowledge["differential_rules"]),
            "mixed_layer_profiles": len(knowledge["mixed_layer_profiles"]),
        },
    }
    write_json(output_dir / "chapter8_mixed_layer_export_manifest.json", manifest)
    return manifest


def main() -> int:
    """Ponto de entrada CLI para exportacao manual ou automacao."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT), help="Diretorio de saida dos JSONs exportados.")
    args = parser.parse_args()
    manifest = export_chapter8_mixed_layer_knowledge(Path(args.output_dir))
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
