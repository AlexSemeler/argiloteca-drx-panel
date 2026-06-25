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

__all__ = [
    "CurveData",
    "CurveParseError",
    "DRX_ANALYSIS_RUN_SCHEMA",
    "DRX_CORE_VERSION",
    "DRX_EXTERNAL_JOB_SCHEMA",
    "DRX_NGC_WORKFLOW_SCHEMA",
    "DRX_RUN_ARTIFACT_SCHEMA",
    "DRX_TECHNICAL_REPORT_SCHEMA",
    "auxiliary_policy",
    "calculate_d_spacing",
    "calculate_two_theta",
    "normalize_area",
    "normalize_max",
    "parse_curve_bytes",
]
