#!/usr/bin/env python3
"""
Projeto: Painel DRX Argiloteca

Descrição:
Simulate a powder XRD pattern from CIF using pymatgen. This script is intentionally executed by an isolated scientific venv instead of the InvenioRDM application venv.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br


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

from __future__ import annotations

import json
import sys
from pathlib import Path

from pymatgen.analysis.diffraction.xrd import XRDCalculator
from pymatgen.core import Structure


def _hkl_label(entry):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        entry: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    hkls = []
    for item in entry or []:
        hkl = item.get("hkl") if isinstance(item, dict) else None
        if hkl is not None:
            hkls.append(str(tuple(hkl)))
    return ", ".join(hkls[:3]) if hkls else None


def main(argv):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        argv: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if len(argv) < 2:
        raise SystemExit("usage: simulate_cif_xrd_pattern.py <input.cif> [wavelength]")
    cif_path = Path(argv[1])
    wavelength = argv[2] if len(argv) > 2 else "CuKa"
    structure = Structure.from_file(cif_path)
    calculator = XRDCalculator(wavelength=wavelength)
    pattern = calculator.get_pattern(structure)
    peaks = []
    hkls = getattr(pattern, "hkls", []) or []
    d_hkls = getattr(pattern, "d_hkls", []) or []
    for index, (two_theta, intensity) in enumerate(zip(pattern.x, pattern.y), start=1):
        peaks.append(
            {
                "peak_index": index,
                "two_theta": round(float(two_theta), 6),
                "relative_intensity": round(float(intensity), 6),
                "d_angstrom": round(float(d_hkls[index - 1]), 6) if index - 1 < len(d_hkls) else None,
                "hkl": _hkl_label(hkls[index - 1]) if index - 1 < len(hkls) else None,
                "source": "pymatgen.XRDCalculator",
            }
        )
    payload = {
        "success": True,
        "source_format": "cif",
        "engine": "pymatgen.XRDCalculator",
        "wavelength": wavelength,
        "formula": structure.composition.reduced_formula,
        "sites": len(structure),
        "peaks": peaks,
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv)
