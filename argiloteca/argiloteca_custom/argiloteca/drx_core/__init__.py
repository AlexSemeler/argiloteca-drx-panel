"""
Projeto: Painel DRX Argiloteca

Descrição:
Compatibility namespace for the reusable DRX core.

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
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

_custom_core = Path(__file__).resolve().parents[1].parent / "argiloteca_drx_core"
if _custom_core.exists():
    __path__.append(str(_custom_core))

from .contracts import (  # noqa: E402,F401
    DRX_ANALYSIS_RUN_SCHEMA,
    DRX_CORE_VERSION,
    DRX_EXTERNAL_JOB_SCHEMA,
    DRX_NGC_WORKFLOW_SCHEMA,
    DRX_RUN_ARTIFACT_SCHEMA,
    DRX_TECHNICAL_REPORT_SCHEMA,
    auxiliary_policy,
)
from .curves import (  # noqa: E402,F401
    CurveData,
    CurveParseError,
    calculate_d_spacing,
    calculate_two_theta,
    normalize_area,
    normalize_max,
    parse_curve_bytes,
)
