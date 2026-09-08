"""Behavior rule catalog constants.

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
    Diagnosticos automaticos sao hipoteses compativeis ou candidatos fortes.
    Confirmacao mineralogica e reservada a uma decisao curatorial humana
    registrada, mesmo quando criterios N/G/C convergentes sao atendidos.
"""

ENGINE_VERSION = "argiloteca.drx.ngc.v3"
POLICY = "argiloteca_rule_based_diagnostic"
STRONG_CANDIDATE_BY_RULES = "strong_candidate_by_rules"
# Nome preservado somente para compatibilidade de importacao. O valor antigo
# nao deve mais ser emitido como se representasse confirmacao cientifica.
CONFIRMED_BY_RULES = STRONG_CANDIDATE_BY_RULES
PROBABLE_BY_RULES = "probable_by_rules"
POSSIBLE_BY_RULES = "possible_by_rules"

BEHAVIOR_RULES = [
    {"rule_id": "smectite_expand_collapse", "requires": ["expands_with_glycol", "collapses_after_heating"], "target": "smectite_group"},
    {"rule_id": "chlorite_stable_14", "requires": ["stable_after_glycol", "persists_after_heating"], "target": "chlorite_group"},
    {"rule_id": "kaolin_7_disappears", "requires": ["stable_after_glycol", "disappears_after_heating"], "target": "kaolin_group"},
    {"rule_id": "corrensite_ordered_cs", "requires": ["ordered_chlorite_smectite", "rational_sequence"], "target": "corrensite"},
]
