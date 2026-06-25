"""
Projeto: Painel DRX Argiloteca

Descrição:
Versioned CIF-to-XRD simulation contract for DRX workflows.

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
from pathlib import Path

from .drx_references import _normalise_reference_peaks
from .drx_science_engine import simulate_cif_pattern


DRX_CIF_SIMULATION_SCHEMA = "argiloteca.drx.cif_simulation.v1"
_ALLOWED_WAVELENGTHS = {"CuKa", "CuKa1", "CuKa2", "MoKa", "CrKa", "FeKa", "CoKa"}


def _normalise_wavelength_label(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = str(value or "CuKa").strip()
    return text if text in _ALLOWED_WAVELENGTHS else "CuKa"


def build_cif_simulation_payload(content, *, filename=None, wavelength=None, max_peaks=200):
    """Simulate a powder XRD pattern from CIF bytes via the isolated engine."""
    content = content or b""
    filename = Path(filename or "reference.cif").name
    wavelength_label = _normalise_wavelength_label(wavelength)
    simulation = simulate_cif_pattern(content, filename=filename, wavelength=wavelength_label)
    source_sha256 = hashlib.sha256(content).hexdigest()
    if not simulation.get("success"):
        return {
            "success": False,
            "schema_version": DRX_CIF_SIMULATION_SCHEMA,
            "filename": filename,
            "source_sha256": source_sha256,
            "wavelength": wavelength_label,
            "error": simulation.get("error") or "Falha ao simular padrao CIF.",
            "engine": simulation.get("engine") or "pymatgen.XRDCalculator",
            "engine_python": simulation.get("engine_python"),
            "simulation": simulation,
            "interpretation_policy": "Padrao CIF simulado para comparacao auxiliar; nao confirma fase mineralogica isoladamente.",
        }
    peaks = _normalise_reference_peaks(simulation.get("peaks") or [], limit=max_peaks)
    return {
        "success": True,
        "schema_version": DRX_CIF_SIMULATION_SCHEMA,
        "filename": filename,
        "source_sha256": source_sha256,
        "source_format": "cif",
        "engine": simulation.get("engine") or "pymatgen.XRDCalculator",
        "engine_python": simulation.get("engine_python"),
        "wavelength": wavelength_label,
        "formula": simulation.get("formula"),
        "site_count": simulation.get("sites"),
        "peak_count": len(peaks),
        "peaks": peaks,
        "provenance": {
            "input_filename": filename,
            "input_sha256": source_sha256,
            "simulation_engine": simulation.get("engine") or "pymatgen.XRDCalculator",
            "source_format": "cif",
            "wavelength": wavelength_label,
        },
        "warnings": [
            "Padrao calculado a partir de CIF; comparar com amostra real exige preparacao, parametros instrumentais e revisao especialista."
        ],
        "interpretation_policy": "Padrao CIF simulado para comparacao auxiliar; nao confirma fase mineralogica isoladamente.",
    }
