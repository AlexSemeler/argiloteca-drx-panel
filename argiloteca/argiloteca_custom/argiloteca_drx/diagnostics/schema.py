"""Loose schema metadata for the V3 diagnostic payload.

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

from .diagnostic_behavior_rules import POLICY

DRX_DIAGNOSTIC_SCHEMA = {
    "engine_version": "argiloteca.drx.ngc.v3",
    "policy": POLICY,
    "required_top_level": ["diagnostic_interpretation"],
}


def validate_diagnostic_payload(payload):
    interpretation = (payload or {}).get("diagnostic_interpretation", payload or {})
    return interpretation.get("policy") == POLICY and bool(interpretation.get("engine_version"))
