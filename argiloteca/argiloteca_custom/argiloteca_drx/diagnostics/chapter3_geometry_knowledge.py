"""Base executavel do Capitulo 3: Diffraction I: Geometry.

Fundamentacao cientifica:
    Fonte local de curadoria:
    /home/invenio/invenio-project/textos/difracao-geomentria.pdf

    Capitulo:
    Diffraction I: Geometry.

Politica:
    Esta base nao identifica minerais. Ela documenta e audita as regras
    geometricas usadas antes de qualquer interpretacao mineralogica: 2θ, θ,
    d-spacing, comprimento de onda, Lei de Bragg, Laue, rede reciproca, esfera
    de Ewald, metodos de difracao e condicoes nao ideais.

Engenharia:
    Modulo de dados imutaveis e funcoes puras. Nao le PDF em tempo de
    importacao e nao executa calculos automaticamente.
"""

from __future__ import annotations

from copy import deepcopy

from .diagnostic_behavior_rules import POLICY

SOURCE_ID = "diffraction_geometry_chapter3_pdf"

CHAPTER3_SOURCE = {
    "source_id": SOURCE_ID,
    "source_full_title": "Diffraction I: Geometry",
    "source_book": "X-Ray Diffraction and the Identification and Analysis of Clay Minerals",
    "chapter": "Diffraction I: Geometry",
    "local_pdf": "/home/invenio/invenio-project/textos/difracao-geomentria.pdf",
    "policy": POLICY,
    "scope": "geometria de difracao; nao inclui regras de intensidade do capitulo seguinte",
    "copyright_note": "Only short source locators are stored; consult local PDF/OCR for full text.",
}


def source_ref(section, page=None, equation=None, figure=None, table=None, fragment=""):
    """Cria referencia bibliografica curta para regras geometricas."""
    return {
        "source_id": SOURCE_ID,
        "source_full_title": CHAPTER3_SOURCE["source_full_title"],
        "source_book": CHAPTER3_SOURCE["source_book"],
        "chapter": CHAPTER3_SOURCE["chapter"],
        "section": section,
        "page": page,
        "equation": equation,
        "figure": figure,
        "table": table,
        "quote_fragment": fragment,
    }


CHAPTER3_ENTITIES = [
    {"entity_id": "two_theta", "entity_type": "angle", "name": "diffraction angle 2theta", "symbol": "2θ", "unit": "degree", "source": SOURCE_ID},
    {"entity_id": "theta", "entity_type": "angle", "name": "Bragg angle theta", "symbol": "θ", "unit": "degree_or_radian", "source": SOURCE_ID},
    {"entity_id": "wavelength_lambda", "entity_type": "physical_quantity", "name": "wavelength", "symbol": "λ", "unit": "angstrom", "source": SOURCE_ID},
    {"entity_id": "d_spacing", "entity_type": "physical_quantity", "name": "interplanar spacing", "symbol": "d", "unit": "angstrom", "source": SOURCE_ID},
    {"entity_id": "bragg_law", "entity_type": "equation", "name": "Bragg law", "symbol": "nλ = 2d sinθ", "source": SOURCE_ID},
    {"entity_id": "laue_equations", "entity_type": "equation_set", "name": "Laue equations", "source": SOURCE_ID},
    {"entity_id": "reciprocal_lattice", "entity_type": "geometric_model", "name": "reciprocal lattice", "source": SOURCE_ID},
    {"entity_id": "ewald_sphere", "entity_type": "geometric_model", "name": "Ewald sphere", "source": SOURCE_ID},
    {"entity_id": "powder_diffraction", "entity_type": "method", "name": "powder diffraction method", "source": SOURCE_ID},
    {"entity_id": "nonideal_peak_broadening", "entity_type": "uncertainty_source", "name": "nonideal peak broadening", "source": SOURCE_ID},
]


EQUATIONS = [
    {
        "equation_id": "chapter3_bragg_law",
        "name": "Bragg law",
        "latex": "n\\lambda = 2d\\sin\\theta",
        "variables": ["n", "lambda", "d", "theta"],
        "computational_use": ["two_theta_to_d_spacing", "d_spacing_to_two_theta"],
        "source": source_ref("3-3", equation="Bragg law", fragment="n lambda = 2 d sin theta"),
    },
    {
        "equation_id": "chapter3_first_order_bragg",
        "name": "First-order Bragg form",
        "latex": "\\lambda = 2d\\sin\\theta",
        "variables": ["lambda", "d", "theta"],
        "computational_use": ["braggDSpacing", "_two_theta_to_d_spacing"],
        "source": source_ref("3-3", equation="first-order Bragg", fragment="lambda = 2 d sin theta"),
    },
    {
        "equation_id": "chapter3_observability",
        "name": "Bragg observability condition",
        "latex": "\\lambda < 2d",
        "variables": ["lambda", "d"],
        "computational_use": ["braggTwoTheta", "_d_spacing_to_two_theta"],
        "source": source_ref("3-3", equation="observability", fragment="sin theta < 1"),
    },
    {
        "equation_id": "chapter3_laue_equations",
        "name": "Laue equations",
        "latex": "a(cos\\alpha-cos\\alpha_0)=h\\lambda; b(cos\\beta-cos\\beta_0)=k\\lambda; c(cos\\gamma-cos\\gamma_0)=l\\lambda",
        "variables": ["a", "b", "c", "alpha", "beta", "gamma", "h", "k", "l", "lambda"],
        "computational_use": ["future_hkl_indexer", "future_reciprocal_lattice_validator"],
        "source": source_ref("3-4", equation="Laue equations", fragment="cos"),
    },
    {
        "equation_id": "chapter3_cubic_direction",
        "name": "Cubic diffraction direction",
        "latex": "\\sin^2\\theta = \\lambda^2(h^2+k^2+l^2)/(4a^2)",
        "variables": ["theta", "lambda", "h", "k", "l", "a"],
        "computational_use": ["future_hkl_indexer"],
        "source": source_ref("3-6", equation="cubic sin2theta", fragment="cubic"),
    },
]


GEOMETRY_RULES = [
    {
        "rule_id": "chapter3_theta_two_theta_convention",
        "rule_type": "angle_convention",
        "target": "bragg_calculation",
        "conditions": [{"feature": "measured_axis", "value": "two_theta"}],
        "result": {"theta": "two_theta / 2"},
        "warning": "Do not insert measured 2theta directly into Bragg law as theta.",
        "source": source_ref("3-3", equation="Bragg law", fragment="theta is Bragg angle"),
    },
    {
        "rule_id": "chapter3_two_theta_to_d_spacing",
        "rule_type": "bragg_geometry",
        "target": "d_spacing_calculation",
        "conditions": [{"feature": "two_theta", "operator": ">", "value": 0}, {"feature": "lambda", "operator": ">", "value": 0}],
        "calculation": "d = lambda / (2 * sin(two_theta / 2))",
        "outputs": ["d_spacing_angstrom"],
        "source": source_ref("3-3", equation="Bragg law", fragment="lambda = 2d sin theta"),
    },
    {
        "rule_id": "chapter3_d_spacing_to_two_theta",
        "rule_type": "bragg_geometry",
        "target": "expected_peak_position",
        "conditions": [{"feature": "lambda/(2*d)", "operator": "<=", "value": 1}],
        "calculation": "two_theta = 2 * asin(lambda / (2*d))",
        "outputs": ["two_theta_degree"],
        "source": source_ref("3-3", equation="Bragg law", fragment="sin theta < 1"),
    },
    {
        "rule_id": "chapter3_geometry_does_not_guarantee_intensity",
        "rule_type": "scope_limitation",
        "target": "hkl_or_peak_candidate",
        "conditions": [{"feature": "reflection", "value": "geometrically_possible"}],
        "result": "position can be predicted but intensity is not guaranteed",
        "warning": "Intensity, systematic absences and structure factors are outside the geometry-only rule.",
        "source": source_ref("3-6", fragment="directions not intensities"),
    },
    {
        "rule_id": "chapter3_nonideal_peak_broadening",
        "rule_type": "uncertainty",
        "target": "peak_width",
        "conditions": ["finite_crystallite_size", "strain", "beam_divergence", "finite_spectral_width", "imperfect_crystal"],
        "result": "peak width can increase independently of mineral identity",
        "source": source_ref("3-10", fragment="nonideal conditions"),
    },
]


METHOD_PROFILES = {
    "powder_diffraction": {
        "method_id": "powder_diffraction",
        "lambda_behavior": "fixed",
        "theta_behavior": "variable",
        "sample_type": "randomly_oriented_polycrystalline_powder",
        "observable_pattern": "cones/rings converted to peaks in diffractometer scan",
        "source": source_ref("3-8", figure="3-17", fragment="powder cone"),
    },
    "laue_method": {
        "method_id": "laue_method",
        "lambda_behavior": "variable",
        "theta_behavior": "fixed",
        "sample_type": "single_crystal",
        "observable_pattern": "spot pattern",
        "source": source_ref("3-8", figure="3-9", fragment="Laue"),
    },
    "xray_spectrometer": {
        "method_id": "xray_spectrometer",
        "known": ["d_spacing", "theta"],
        "unknown": "wavelength",
        "calculation": "lambda = 2*d*sin(theta)",
        "source": source_ref("3-7", figure="3-8", fragment="spectrometer"),
    },
}


ONTOLOGY = {
    "DiffractionGeometry": {"children": ["Wave", "BraggGeometry", "LaueGeometry", "ReciprocalLattice", "EwaldConstruction", "DiffractionMethod"]},
    "BraggGeometry": {"children": ["two_theta", "theta", "lambda", "d_spacing", "order_n"]},
    "Calculation": {"examples": ["two_theta_to_d_spacing", "d_spacing_to_two_theta"]},
    "Uncertainty": {"examples": ["finite_crystallite_size", "strain", "beam_divergence", "finite_spectral_width"]},
    "Rule": {"children": ["angle_convention", "bragg_geometry", "scope_limitation", "uncertainty"]},
}


SCHEMAS = {
    "argiloteca_diffraction_geometry_rule_schema": {
        "type": "object",
        "required": ["rule_id", "rule_type", "target", "source"],
        "properties": {
            "rule_id": {"type": "string"},
            "rule_type": {"type": "string"},
            "target": {"type": "string"},
            "conditions": {"type": ["array", "object"]},
            "calculation": {"type": "string"},
            "outputs": {"type": "array"},
            "source": {"type": "object"},
        },
    },
    "argiloteca_equation_schema": {
        "type": "object",
        "required": ["equation_id", "name", "latex", "source"],
    },
}


def get_chapter3_geometry_knowledge():
    """Retorna copia profunda da base geometrica do Capitulo 3."""
    return deepcopy({
        "source": CHAPTER3_SOURCE,
        "entities": CHAPTER3_ENTITIES,
        "equations": EQUATIONS,
        "geometry_rules": GEOMETRY_RULES,
        "method_profiles": METHOD_PROFILES,
        "ontology": ONTOLOGY,
        "schemas": SCHEMAS,
    })


def chapter3_rule_index():
    """Indexa regras geometricas por rule_id para explicacao e auditoria."""
    return {row["rule_id"]: deepcopy(row) for row in GEOMETRY_RULES}


def chapter3_equation_index():
    """Indexa equacoes por equation_id para rastrear calculos."""
    return {row["equation_id"]: deepcopy(row) for row in EQUATIONS}
