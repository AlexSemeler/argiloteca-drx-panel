#!/usr/bin/env python3
"""Exporta a base executavel do Capitulo 3 para JSON auditavel.

Fonte cientifica:
    Capitulo "Diffraction I: Geometry".

Este script materializa geometria de difracao, equacoes, regras de Bragg,
metodos experimentais, ontologia e schemas em arquivos JSON versionados. Ele
nao executa interpretacao mineralogica; apenas exporta a base de conhecimento
fisico-geometrica para auditoria, documentacao, InvenioRDM, OpenSearch e
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

from argiloteca_drx.diagnostics.chapter3_geometry_knowledge import get_chapter3_geometry_knowledge  # noqa: E402


DEFAULT_OUTPUT = ROOT / "argiloteca_drx" / "diagnostics" / "data" / "generated"


def write_json(path: Path, payload) -> None:
    """Grava JSON com UTF-8, indentacao estavel e quebra de linha final."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def export_chapter3_geometry_knowledge(output_dir: Path) -> dict:
    """Exporta todas as camadas estruturadas da base geometrica do Capitulo 3."""
    knowledge = get_chapter3_geometry_knowledge()
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "chapter3_geometry_entities.json": knowledge["entities"],
        "chapter3_geometry_equations.json": knowledge["equations"],
        "chapter3_geometry_rules.json": knowledge["geometry_rules"],
        "chapter3_geometry_method_profiles.json": knowledge["method_profiles"],
        "chapter3_geometry_ontology.json": knowledge["ontology"],
        "chapter3_geometry_schemas.json": knowledge["schemas"],
        "chapter3_geometry_knowledge_complete.json": knowledge,
    }
    for filename, payload in files.items():
        write_json(output_dir / filename, payload)

    manifest = {
        "version": "argiloteca.drx.chapter3.geometry.knowledge.export.v1",
        "policy": knowledge["source"]["policy"],
        "source_id": knowledge["source"]["source_id"],
        "source_full_title": knowledge["source"]["source_full_title"],
        "source_pdf": knowledge["source"]["local_pdf"],
        "output_dir": str(output_dir),
        "files": sorted(files),
        "counts": {
            "entities": len(knowledge["entities"]),
            "equations": len(knowledge["equations"]),
            "geometry_rules": len(knowledge["geometry_rules"]),
            "method_profiles": len(knowledge["method_profiles"]),
        },
    }
    write_json(output_dir / "chapter3_geometry_export_manifest.json", manifest)
    return manifest


def main() -> int:
    """Ponto de entrada CLI para exportacao manual ou automacao."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT), help="Diretorio de saida dos JSONs exportados.")
    args = parser.parse_args()
    manifest = export_chapter3_geometry_knowledge(Path(args.output_dir))
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
