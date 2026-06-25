"""
Projeto: Painel DRX Argiloteca

Descrição:
Versioned scientific contracts shared by DRX services and workers.

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

DRX_CORE_VERSION = "argiloteca_drx_core.20260620"
DRX_ANALYSIS_RUN_SCHEMA = "argiloteca.drx.analysis_run.v1"
DRX_DIAGNOSTIC_RULES_SCHEMA = "argiloteca.drx.diagnostic_rules.v1"
DRX_EXTERNAL_JOB_SCHEMA = "argiloteca.drx.external_job.v1"
DRX_NGC_WORKFLOW_SCHEMA = "argiloteca.drx.ngc_workflow.v1"
DRX_RUN_ARTIFACT_SCHEMA = "argiloteca.drx.run_artifact.v1"
DRX_TECHNICAL_REPORT_SCHEMA = "argiloteca.drx.technical_report.v1"


def auxiliary_policy(kind="drx"):
    """Return the standard non-confirmatory interpretation policy."""
    if kind == "neural":
        return "Evidencia neural auxiliar, experimental e nao confirmatoria; requer curadoria mineralogica."
    if kind == "reference":
        return "Comparacao com referencia e auxiliar; nao confirma fase mineralogica isoladamente."
    return "Evidencia assistida para comparacao DRX; nao substitui curadoria mineralogica."
