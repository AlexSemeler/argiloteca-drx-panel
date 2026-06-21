"""
Projeto: Painel DRX Argiloteca

Descrição:
Reusable DRX/XRD core contracts for Argiloteca. This package is intentionally small and dependency-light. Flask/Invenio services remain responsible for routing, permissions and persistence; scientific helpers live here so they can be reused by workers, reports and tests.

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
