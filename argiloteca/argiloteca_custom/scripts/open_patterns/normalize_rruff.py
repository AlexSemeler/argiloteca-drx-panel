#!/usr/bin/env python3
"""
Projeto: Painel DRX Argiloteca

Descrição:
Normalize locally downloaded RRUFF files into Argiloteca JSONL.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br

Colaboradores:
- Lucas Jantsch
- Arthur Oliveira

Instituição:
Universidade Federal do Rio Grande do Sul (UFRGS)

Projeto:
Argiloteca / CPAA

Licença:
Preservar licença existente no repositório.

Última revisão:
2026-06-21

Observação:
Este arquivo integra o sistema de análise, comparação e interpretação de difratogramas de raios X para argilominerais.
"""

from pathlib import Path
import argparse
import json
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from argiloteca_custom.scripts.open_patterns.common import discover_vocabulary_path, load_argiloteca_vocabulary
from argiloteca_custom.scripts.open_patterns.fetch_open_patterns import normalize_rruff_files


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
    vocab_path = Path(args.vocabulary) if args.vocabulary else discover_vocabulary_path(Path.cwd())
    records = normalize_rruff_files(args.out, load_argiloteca_vocabulary(vocab_path))
    print(json.dumps({"records": len(records)}, indent=2))


if __name__ == "__main__":
    main()

