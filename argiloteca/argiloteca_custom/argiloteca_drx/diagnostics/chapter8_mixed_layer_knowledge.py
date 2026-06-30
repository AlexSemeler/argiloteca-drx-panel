"""Base executavel do Capitulo 8: Identification of Mixed-Layered Clay Minerals.

Fundamentacao cientifica:
    Fonte local de curadoria:
    /home/invenio/invenio-project/textos/capitulo8.pdf

    Obra completa:
    X-Ray Diffraction and the Identification and Analysis of Clay Minerals

Politica:
    policy="argiloteca_rule_based_diagnostic". A base gera hipoteses e
    explicacoes para argilominerais interestratificados. Ela nao confirma
    interestratificacao por pico isolado e preserva ambiguidades entre mistura
    fisica, mineral discreto e sequencia estrutural mista.

Engenharia:
    Modulo de dados imutaveis e funcoes puras. Nao executa OCR, modelagem
    NEWMOD-like ou ajuste observado-calculado em tempo de importacao.
"""

from __future__ import annotations

from copy import deepcopy

from .diagnostic_behavior_rules import POLICY

SOURCE_ID = "moore_reynolds_chapter8_mixed_layer_pdf"

CHAPTER8_SOURCE = {
    "source_id": SOURCE_ID,
    "source_full_title": "Identification of Mixed-Layered Clay Minerals",
    "source_book": "X-Ray Diffraction and the Identification and Analysis of Clay Minerals",
    "chapter": "Identification of Mixed-Layered Clay Minerals",
    "local_pdf": "/home/invenio/invenio-project/textos/capitulo8.pdf",
    "policy": POLICY,
    "scope": "mixed-layered/interstratified clay minerals by 00l patterns and treatment behavior",
    "copyright_note": "Only short source locators are stored; consult local PDF/OCR for full text.",
}


def source_ref(page=None, section="", table=None, figure=None, equation=None, fragment=""):
    """Cria referencia bibliografica curta para regras do Capitulo 8."""
    return {
        "source_id": SOURCE_ID,
        "source_full_title": CHAPTER8_SOURCE["source_full_title"],
        "source_book": CHAPTER8_SOURCE["source_book"],
        "chapter": CHAPTER8_SOURCE["chapter"],
        "section": section,
        "page": page,
        "table": table,
        "figure": figure,
        "equation": equation,
        "quote_fragment": fragment,
    }


CHAPTER8_ENTITIES = [
    {"entity_id": "mixed_layered_clay_mineral", "entity_type": "concept", "name": "mixed-layered clay mineral", "source": SOURCE_ID},
    {"entity_id": "interstratification", "entity_type": "concept", "name": "interstratification", "source": SOURCE_ID},
    {"entity_id": "reichweite", "entity_type": "ordering_parameter", "name": "Reichweite", "source": SOURCE_ID},
    {"entity_id": "R0", "entity_type": "ordering", "name": "random interstratification", "source": SOURCE_ID},
    {"entity_id": "R1", "entity_type": "ordering", "name": "ordered nearest-neighbor interstratification", "source": SOURCE_ID},
    {"entity_id": "R3", "entity_type": "ordering", "name": "longer-range ordered interstratification", "source": SOURCE_ID},
    {"entity_id": "superstructure_reflection", "entity_type": "reflection", "name": "superstructure reflection", "source": SOURCE_ID},
    {"entity_id": "physical_mixture", "entity_type": "diagnostic_alternative", "name": "physical mixture of discrete minerals", "source": SOURCE_ID},
    {"entity_id": "illite_smectite", "entity_type": "mineral_system", "name": "illite/smectite", "source": SOURCE_ID},
    {"entity_id": "chlorite_smectite", "entity_type": "mineral_system", "name": "chlorite/smectite", "source": SOURCE_ID},
    {"entity_id": "corrensite", "entity_type": "mineral_system", "name": "corrensite", "source": SOURCE_ID},
    {"entity_id": "kaolinite_smectite", "entity_type": "mineral_system", "name": "kaolinite/smectite", "source": SOURCE_ID},
    {"entity_id": "mica_vermiculite", "entity_type": "mineral_system", "name": "mica/vermiculite", "source": SOURCE_ID},
]


NOMENCLATURE_RULES = [
    {
        "rule_id": "chapter8_mixed_layer_name_components_ordering",
        "rule_type": "nomenclature",
        "target": "mixed_layer_mineral",
        "meaning": "name must preserve components, component proportion when known, and ordering type",
        "example": "R1 illite(0.7)/smectite",
        "source": source_ref(section="Nomenclature", fragment="R1 illite/smectite"),
    },
    {
        "rule_id": "chapter8_reichweite_ordering_definition",
        "rule_type": "nomenclature",
        "target": "Reichweite",
        "meaning": "range of ordering relationships among layers; R0 random, R1 nearest-neighbor, R3 longer-range",
        "source": source_ref(section="Ordering", fragment="Reichweite"),
    },
]


MERING_RULES = [
    {
        "rule_id": "chapter8_mering_composite_reflection_between_end_members",
        "rule_type": "mering_principle",
        "target": "mixed_layer_00l_pattern",
        "principle": "composite_reflection_position",
        "formal_statement": "Composite 00l reflections occur between end-member positions and migrate systematically with composition.",
        "diagnostic_implication": "peak migration supports interstratification more than fixed independent peaks",
        "limitations": ["requires full 00l pattern and treatment comparison"],
        "source": source_ref(section="Mering principles", fragment="between end members"),
    },
    {
        "rule_id": "chapter8_mering_broadening_intermediate_composition",
        "rule_type": "mering_principle",
        "target": "line_broadening",
        "principle": "line_broadening",
        "formal_statement": "Reflections broaden when end-member layer spacings differ, especially at intermediate compositions.",
        "diagnostic_implication": "broad peaks or shoulders can support mixed-layer hypotheses but are not diagnostic alone",
        "limitations": ["crystallite size, defects and instrument broadening can also broaden peaks"],
        "source": source_ref(section="Mering principles", fragment="broadening"),
    },
    {
        "rule_id": "chapter8_ordered_superstructure_reflections",
        "rule_type": "mering_principle",
        "target": "ordered_interstratification",
        "principle": "superstructure",
        "formal_statement": "Ordered interstratifications can produce superstructure reflections.",
        "diagnostic_implication": "superstructure reflections support R1/R3 ordering when coherent with the 00l pattern",
        "limitations": ["absence of superstructure does not by itself prove R0"],
        "source": source_ref(section="Ordering", fragment="superstructure"),
    },
]


ORDERING_RULES = [
    {
        "rule_id": "chapter8_R0_random_interstratification",
        "rule_type": "ordering",
        "target": "R0",
        "target_ordering": "R0",
        "conditions": [{"feature": "superstructure_reflection", "presence": False}, {"feature": "peak_series", "value": "non-rational_or_broad"}],
        "diagnostic_implication": "random or unresolved ordering; report as R0|unknown when evidence is incomplete",
        "source": source_ref(section="Ordering", fragment="R0"),
    },
    {
        "rule_id": "chapter8_R1_ordered_interstratification",
        "rule_type": "ordering",
        "target": "R1",
        "target_ordering": "R1",
        "conditions": [{"feature": "superstructure_reflection", "presence": True}, {"feature": "sequence", "value": "regular_or_nearest_neighbor"}],
        "diagnostic_implication": "ordered mixed-layer candidate such as corrensite or rectorite",
        "source": source_ref(section="Ordering", fragment="R1"),
    },
    {
        "rule_id": "chapter8_R3_long_range_ordering",
        "rule_type": "ordering",
        "target": "R3",
        "target_ordering": "R3",
        "conditions": [{"feature": "long_range_superstructure", "presence": True}],
        "diagnostic_implication": "longer-range ordered interstratification; requires stronger pattern evidence",
        "source": source_ref(section="Ordering", fragment="R3"),
    },
]


TREATMENT_BEHAVIOR_RULES = [
    {
        "rule_id": "chapter8_corrensite_ngc_sequence",
        "rule_type": "treatment_behavior",
        "target": "corrensite",
        "behavior": {"natural": "~29 A", "ethylene_glycol": "~31-32 A", "heated": "~24 A support"},
        "diagnostic_implication": "ordered chlorite/smectite sequence rather than simple chlorite plus smectite when coherent",
        "source": source_ref(figure="8.9-8.11", section="Chlorite/smectite", fragment="corrensite"),
    },
    {
        "rule_id": "chapter8_partial_expansion_mixed_layer_warning",
        "rule_type": "treatment_behavior",
        "target": "illite_smectite_or_mixed_layer",
        "behavior": {"ethylene_glycol": "partial expansion or intermediate displacement", "heated": "partial collapse or broad residual"},
        "diagnostic_implication": "favor mixed-layer hypothesis over pure discrete mineral assignment",
        "source": source_ref(section="Illite/smectite", fragment="partial expansion"),
    },
    {
        "rule_id": "chapter8_chlorite_smectite_vs_chlorite_vermiculite_ambiguity",
        "rule_type": "differential_diagnosis",
        "target": "chlorite_smectite_vs_chlorite_vermiculite",
        "conditions": [{"feature": "ethylene_glycol_expansion", "presence": "unclear_or_absent"}],
        "diagnostic_implication": "retain ambiguity and recommend Mg/glycerol or K/heating context",
        "source": source_ref(section="Chlorite/smectite", fragment="glycerol"),
    },
]


DIFFERENTIAL_RULES = [
    {
        "rule_id": "chapter8_no_single_peak_mixed_layer_diagnosis",
        "rule_type": "differential_diagnosis",
        "target": "mixed_layer_diagnosis",
        "question": "mixed_layer_or_single_peak_match",
        "conditions_supporting_interstratification": ["systematic peak migration", "broad/asymmetric 00l reflections", "treatment-dependent shift", "superstructure reflection"],
        "conditions_supporting_physical_mixture": ["fixed independent end-member peaks", "no systematic migration", "separate discrete mineral series"],
        "ambiguous_conditions": ["noise", "poor crystallinity", "overlap", "missing preparations"],
        "source": source_ref(section="General principles", fragment="not isolated peaks"),
    },
    {
        "rule_id": "chapter8_physical_mixture_vs_interstratification",
        "rule_type": "differential_diagnosis",
        "target": "physical_mixture_vs_interstratification",
        "question": "physical_mixture_or_interstratification",
        "conditions_supporting_interstratification": ["composite reflections", "coherent 00l sequence", "migration between end members"],
        "conditions_supporting_physical_mixture": ["two independent peak sets remain fixed through treatments"],
        "required_additional_tests": ["full 00l pattern", "ethylene glycol", "heating/dehydration", "calculated pattern comparison"],
        "source": source_ref(section="General principles", fragment="physical mixture"),
    },
]


MIXED_LAYER_PROFILES = {
    "corrensite": {
        "profile_id": "corrensite_profile",
        "components": ["chlorite", "smectite"],
        "known_ordering": ["R1"],
        "diagnostic_reflections": ["N ~29 A", "G ~31-32 A", "heated ~24 A"],
        "minimum_required_evidence": ["long-spacing reflection", "treatment behavior", "exclude simple mixture"],
        "rules": ["chapter8_corrensite_ngc_sequence", "chapter8_R1_ordered_interstratification"],
        "source": source_ref(figure="8.9-8.11", fragment="corrensite"),
    },
    "illite_smectite": {
        "profile_id": "illite_smectite_profile",
        "components": ["illite", "smectite"],
        "known_ordering": ["R0", "R1", "R3"],
        "diagnostic_reflections": ["EG low-angle 00l shifts", "broad intermediate reflections", "possible superstructure"],
        "minimum_required_evidence": ["EG preparation", "00l pattern", "exclude illite+smectite discrete mixture"],
        "rules": ["chapter8_partial_expansion_mixed_layer_warning", "chapter8_mering_broadening_intermediate_composition"],
        "source": source_ref(figure="8.1-8.8", fragment="illite/smectite"),
    },
    "chlorite_smectite": {
        "profile_id": "chlorite_smectite_profile",
        "components": ["chlorite", "smectite"],
        "known_ordering": ["R0", "R1"],
        "diagnostic_reflections": ["14 A chlorite-like component", "expandable smectite-like component"],
        "minimum_required_evidence": ["treatment behavior", "distinguish from chlorite/vermiculite"],
        "rules": ["chapter8_chlorite_smectite_vs_chlorite_vermiculite_ambiguity"],
        "source": source_ref(figure="8.12-8.15", fragment="chlorite/smectite"),
    },
    "kaolinite_smectite": {
        "profile_id": "kaolinite_smectite_profile",
        "components": ["kaolinite", "smectite"],
        "known_ordering": ["R0", "R1"],
        "diagnostic_reflections": ["7 A component", "expandable component", "heated 375 C behavior"],
        "minimum_required_evidence": ["air-dried", "ethylene glycol", "heated pattern"],
        "rules": ["chapter8_no_single_peak_mixed_layer_diagnosis"],
        "source": source_ref(figure="8.16-8.22", fragment="kaolinite/smectite"),
    },
}


ONTOLOGY = {
    "MixedLayerClayMineral": {"children": ["Component", "Ordering", "Superstructure", "TreatmentState", "DifferentialDiagnosis"]},
    "Ordering": {"children": ["R0", "R1", "R3", "Reichweite"]},
    "Reflection": {"children": ["basal_00l", "composite_reflection", "superstructure_reflection"]},
    "TreatmentState": {"examples": ["air_dried", "ethylene_glycol_solvated", "heated", "dehydrated", "Mg_glycerol_solvated"]},
    "DiagnosticRule": {"children": ["mering_principle", "ordering", "treatment_behavior", "differential_diagnosis"]},
}


SCHEMAS = {
    "argiloteca_mixed_layer_rule_schema": {
        "type": "object",
        "required": ["rule_id", "rule_type", "target", "source"],
        "properties": {
            "rule_id": {"type": "string"},
            "rule_type": {"type": "string"},
            "target": {"type": "string"},
            "conditions": {"type": ["array", "object"]},
            "diagnostic_implication": {"type": "string"},
            "source": {"type": "object"},
        },
    },
    "argiloteca_mixed_layer_profile_schema": {
        "type": "object",
        "required": ["profile_id", "components", "known_ordering", "rules"],
    },
}


def get_chapter8_mixed_layer_knowledge():
    """Retorna copia profunda da base de interestratificados do Capitulo 8."""
    return deepcopy({
        "source": CHAPTER8_SOURCE,
        "entities": CHAPTER8_ENTITIES,
        "nomenclature_rules": NOMENCLATURE_RULES,
        "mering_rules": MERING_RULES,
        "ordering_rules": ORDERING_RULES,
        "treatment_behavior_rules": TREATMENT_BEHAVIOR_RULES,
        "differential_rules": DIFFERENTIAL_RULES,
        "mixed_layer_profiles": MIXED_LAYER_PROFILES,
        "ontology": ONTOLOGY,
        "schemas": SCHEMAS,
    })


def chapter8_rule_index():
    """Indexa regras do Capitulo 8 por rule_id para explicacao e auditoria."""
    rules = NOMENCLATURE_RULES + MERING_RULES + ORDERING_RULES + TREATMENT_BEHAVIOR_RULES + DIFFERENTIAL_RULES
    return {row["rule_id"]: deepcopy(row) for row in rules}


def chapter8_profile(profile_id):
    """Retorna perfil mixed-layer por id mineral/sistema, se existir."""
    profile = MIXED_LAYER_PROFILES.get(profile_id)
    return deepcopy(profile) if profile else None
