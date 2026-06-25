#!/usr/bin/env python3
"""Exporta a base executavel do Capitulo 7 para JSON auditavel.

Fonte cientifica:
    X-Ray Diffraction and the Identification and Analysis of Clay Minerals,
    capitulo "Identification of Clay Minerals and Associated Minerals".

Este script transforma os objetos Python de chapter7_knowledge.py em arquivos
JSON versionados. Ele nao executa inferencia mineralogica; apenas materializa
a base de conhecimento para auditoria, documentacao, InvenioRDM, OpenSearch e
processos externos.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from argiloteca_drx.diagnostics.chapter7_knowledge import get_chapter7_knowledge  # noqa: E402


DEFAULT_OUTPUT = ROOT / "argiloteca_drx" / "diagnostics" / "data" / "generated"


def write_json(path: Path, payload) -> None:
    """Grava um payload JSON com codificacao UTF-8 e ordenacao estavel.

    A funcao cria o diretorio de destino quando necessario e grava uma quebra
    de linha final para facilitar revisao em diff. Nao altera o payload em
    memoria.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def export_chapter7_knowledge(output_dir: Path) -> dict:
    """Exporta todas as camadas da base do Capitulo 7.

    Args:
        output_dir: Diretorio onde os JSONs serao gerados.

    Returns:
        dict: Manifesto com versao, policy, fonte completa, arquivos gerados e
        contagens por camada.

    Loops:
        O unico loop percorre o dicionario local ``files`` e grava cada camada.
        Ele e finito e proporcional ao numero de artefatos exportados.
    """
    knowledge = get_chapter7_knowledge()
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "argiloteca_mineralogy_ontology.json": knowledge["ontology"],
        "chapter7_entities.json": knowledge["entities"],
        "chapter7_reflection_tables.json": knowledge["tables"],
        "chapter7_diagnostic_rules.json": knowledge["diagnostic_rules"],
        "chapter7_behavior_rules.json": knowledge["behavior_rules"],
        "chapter7_d060_rules.json": knowledge["d060_rules"],
        "chapter7_intensity_rules.json": knowledge["intensity_rules"],
        "chapter7_mineral_profiles.json": knowledge["mineral_profiles"],
        "chapter7_schemas.json": knowledge["schemas"],
        "chapter7_knowledge_complete.json": knowledge,
    }
    for filename, payload in files.items():
        write_json(output_dir / filename, payload)

    manifest = {
        "version": "argiloteca.drx.chapter7.knowledge.export.v1",
        "policy": knowledge["source"]["policy"],
        "source_id": knowledge["source"]["source_id"],
        "source_full_title": knowledge["source"]["source_full_title"],
        "source_pdf": knowledge["source"]["local_pdf"],
        "output_dir": str(output_dir),
        "files": sorted(files),
        "counts": {
            "entities": len(knowledge["entities"]),
            "tables": len(knowledge["tables"]),
            "diagnostic_rules": len(knowledge["diagnostic_rules"]),
            "behavior_rules": len(knowledge["behavior_rules"]),
            "d060_rules": len(knowledge["d060_rules"]),
            "intensity_rules": len(knowledge["intensity_rules"]),
            "mineral_profiles": len(knowledge["mineral_profiles"]),
        },
    }
    write_json(output_dir / "chapter7_export_manifest.json", manifest)
    return manifest


def main() -> int:
    """Ponto de entrada CLI para uso manual ou em automacao."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT), help="Diretorio de saida dos JSONs exportados.")
    args = parser.parse_args()
    manifest = export_chapter7_knowledge(Path(args.output_dir))
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
