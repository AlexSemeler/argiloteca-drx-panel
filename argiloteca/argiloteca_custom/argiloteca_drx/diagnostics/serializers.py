"""Serialization helpers for InvenioRDM custom fields.

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

from .diagnostic_behavior_rules import POLICY


def serialize_for_invenio(diagnostic_interpretation):
    data = diagnostic_interpretation or {}
    return {
        "argiloteca:d_rx_diagnostic": {
            "policy": data.get("policy", POLICY),
            "policy_scope": data.get("policy_scope", "rule_based_confirmation_within_argiloteca_ngc_engine"),
            "diagnostic_labels": data.get("diagnostic_labels", ["confirmed_by_rules", "probable_by_rules", "possible_by_rules"]),
            "engine_version": data.get("engine_version", "argiloteca.drx.ngc.v3"),
            "method": data.get("method", "literature_empirical_presalt_flow_meunier_ngc_behavior"),
            "literature_candidates": data.get("literature_candidates", []),
            "empirical_candidates": data.get("empirical_candidates", []),
            "presalt_candidates": data.get("presalt_candidates", []),
            "combined_candidates": data.get("combined_candidates", []),
            "range_comparison": data.get("range_comparison", {}),
            "behavior_interpretation": data.get("behavior_interpretation", {}),
            "octahedral_classification": data.get("octahedral_classification", {}),
            "mixed_layer_candidates": data.get("mixed_layer_candidates", []),
            "ambiguities": data.get("ambiguities", []),
            "warnings": data.get("warnings", []),
            "recommended_next_tests": data.get("recommended_next_tests", []),
            "provenance": data.get("provenance", {}),
            "source_rule_index": data.get("source_rule_index", {}),
            "source_mineral_profiles": data.get("source_mineral_profiles", {}),
        }
    }
