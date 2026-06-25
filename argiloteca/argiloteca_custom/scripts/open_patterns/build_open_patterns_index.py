#!/usr/bin/env python3
"""
Projeto: Painel DRX Argiloteca

Descrição:
Build compact panel index and coverage from normalized open patterns.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br



Projeto:
Argiloteca / CPAA

Licença:
Preservar licença existente no repositório.

Última revisão:
2026-06-21

Observação:
Este arquivo integra o sistema de análise, comparação e interpretação de difratogramas de raios X para argilominerais.
"""

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from argiloteca_custom.scripts.open_patterns.common import (
    build_coverage,
    build_panel_index,
    discover_vocabulary_path,
    load_argiloteca_vocabulary,
    read_jsonl,
    write_curation_queue,
    write_jsonl,
)


def main(argv=None):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        argv: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vocabulary")
    parser.add_argument("--out", default="data/open_patterns")
    args = parser.parse_args(argv)
    out = Path(args.out)
    vocab_path = Path(args.vocabulary) if args.vocabulary else discover_vocabulary_path(Path.cwd())
    vocabulary = load_argiloteca_vocabulary(vocab_path)
    records = read_jsonl(out / "normalized" / "open_patterns_index.jsonl")
    panel = build_panel_index(records)
    write_jsonl(out / "panel" / "open_patterns_index.jsonl", panel)
    coverage = build_coverage(vocabulary, records)
    (out / "manifests").mkdir(parents=True, exist_ok=True)
    (out / "manifests" / "coverage_by_mineral.json").write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_curation_queue(out / "manifests" / "curation_queue.csv", records)
    print(json.dumps({"records": len(records), "panel_records": len(panel)}, indent=2))


if __name__ == "__main__":
    main()

