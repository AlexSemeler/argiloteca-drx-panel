#!/usr/bin/env python3
"""
Projeto: Painel DRX Argiloteca

Descrição:
Optional CIF powder XRD simulation using pymatgen when installed.

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

from argiloteca_custom.scripts.open_patterns.fetch_open_patterns import simulate_cif_pattern


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
    parser.add_argument("cif")
    parser.add_argument("--wavelength-a", type=float, default=1.5406)
    args = parser.parse_args(argv)
    result = simulate_cif_pattern(args.cif, wavelength_a=args.wavelength_a)
    if result is None:
        raise SystemExit("pymatgen indisponível ou CIF inválido; simulação não executada.")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

