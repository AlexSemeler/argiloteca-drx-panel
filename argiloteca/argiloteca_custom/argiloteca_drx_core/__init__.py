"""
Projeto: Painel DRX Argiloteca

Descrição:
Reusable DRX/XRD core contracts for Argiloteca. This package is intentionally small and dependency-light. Flask/Invenio services remain responsible for routing, permissions and persistence; scientific helpers live here so they can be reused by workers, reports and tests.

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

from .contracts import (
    DRX_ANALYSIS_RUN_SCHEMA,
    DRX_CORE_VERSION,
    DRX_EXTERNAL_JOB_SCHEMA,
    DRX_NGC_WORKFLOW_SCHEMA,
    DRX_RUN_ARTIFACT_SCHEMA,
    DRX_TECHNICAL_REPORT_SCHEMA,
    auxiliary_policy,
)
from .curves import (
    CurveData,
    CurveParseError,
    calculate_d_spacing,
    calculate_two_theta,
    normalize_area,
    normalize_max,
    parse_curve_bytes,
)
from .diffractogram import Diffractogram
from .geometry import (
    BraggCalculation,
    bragg_from_two_theta,
    geometry_explanation,
    two_theta_from_d_spacing,
)
from .knowledge import (
    get_rule_indexes,
    get_scientific_knowledge,
    scientific_source_summary,
)
from .peaks import (
    group_peaks_for_ngc,
    normalize_peak,
    normalize_peaks,
)

_PEAK_DETECTOR_EXPORTS = {
    "DEFAULT_PEAK_DETECTOR_PARAMS": ("argiloteca_drx_core.peak_detector", "DEFAULT_PARAMS"),
    "detect_peaks": ("argiloteca_drx_core.peak_detector", "detect_peaks"),
    "export_explainability": ("argiloteca_drx_core.peak_detector", "export_explainability"),
}


def __getattr__(name):
    """Carrega o detector científico de picos apenas quando solicitado.

    O painel principal pode rodar em ambientes sem numpy/scipy/pybaselines.
    Por isso o detector novo fica integrado ao core, mas suas dependências só
    são importadas quando `detect_peaks` ou `export_explainability` forem
    chamados explicitamente.
    """
    if name not in _PEAK_DETECTOR_EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _PEAK_DETECTOR_EXPORTS[name]
    from importlib import import_module

    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


__all__ = [
    "CurveData",
    "CurveParseError",
    "Diffractogram",
    "BraggCalculation",
    "DRX_ANALYSIS_RUN_SCHEMA",
    "DRX_CORE_VERSION",
    "DRX_EXTERNAL_JOB_SCHEMA",
    "DRX_NGC_WORKFLOW_SCHEMA",
    "DRX_RUN_ARTIFACT_SCHEMA",
    "DRX_TECHNICAL_REPORT_SCHEMA",
    "auxiliary_policy",
    "bragg_from_two_theta",
    "calculate_d_spacing",
    "calculate_two_theta",
    "geometry_explanation",
    "get_rule_indexes",
    "get_scientific_knowledge",
    "group_peaks_for_ngc",
    "normalize_area",
    "normalize_max",
    "normalize_peak",
    "normalize_peaks",
    "parse_curve_bytes",
    "scientific_source_summary",
    "two_theta_from_d_spacing",
]
