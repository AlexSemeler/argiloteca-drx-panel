"""Executable knowledge extracted from Chapter 7 clay-mineral identification.

Fundamentacao cientifica:
    Fonte local lida por OCR:
    /home/invenio/Downloads/analises.pdf

    Obra completa:
    X-Ray Diffraction and the Identification and Analysis of Clay Minerals

    Capitulo: Identification of Clay Minerals and Associated Minerals.

Autoria cientifica e curadoria do projeto:
    Alexandre Ribas Semeler
    E-mail: alexandre.semler@ufrgs.br

Politica:
    policy="argiloteca_rule_based_diagnostic". Esta base permite confirmacao
    pelas regras da Argiloteca quando evidencias convergentes atendem aos
    criterios N/G/C; ela nao confirma mineral por pico isolado.

Engenharia:
    Este modulo contem apenas dados imutaveis e funcoes puras de leitura. Nao
    executa OCR, nao faz I/O em tempo de importacao e nao mantem estado global
    mutavel.
"""

from __future__ import annotations

from copy import deepcopy

from .diagnostic_behavior_rules import POLICY

SOURCE_ID = "moore_reynolds_chapter7_ocr_analises_pdf"

# Objeto bibliografico raiz. Todos os registros derivados do Capitulo 7 apontam
# para este dicionario por meio de SOURCE_ID. Ele evita strings soltas em cada
# regra e garante que exportadores, painel e InvenioRDM usem o mesmo titulo da
# obra: X-Ray Diffraction and the Identification and Analysis of Clay Minerals.
CHAPTER7_SOURCE = {
    "source_id": SOURCE_ID,
    "source_full_title": "X-Ray Diffraction and the Identification and Analysis of Clay Minerals",
    "source_book": "X-Ray Diffraction and the Identification and Analysis of Clay Minerals",
    "chapter": "Identification of Clay Minerals and Associated Minerals",
    "local_pdf": "/home/invenio/Downloads/analises.pdf",
    "ocr_text": "/tmp/analises_ocr_combined.txt",
    "pages_ocr": 33,
    "policy": POLICY,
    "copyright_note": "Only short source locators are stored; consult local PDF/OCR for full text.",
}


def source_ref(page, table=None, figure=None, fragment=""):
    """Cria referencia bibliografica curta e rastreavel para uma regra.

    Args:
        page: Pagina do capitulo em que a regra/tabela aparece.
        table: Identificador da tabela quando a regra vem de uma tabela.
        figure: Identificador da figura quando a regra vem de uma figura.
        fragment: Fragmento curto usado como pista de auditoria.

    Returns:
        dict: Referencia normalizada. O retorno e usado em regras, perfis,
        tabelas, JSON exportado, payload InvenioRDM e secao Regra-fonte do
        painel. A funcao nao faz I/O e nao interpreta minerais; ela apenas
        padroniza proveniencia.
    """
    return {
        "source_id": SOURCE_ID,
        "source_full_title": CHAPTER7_SOURCE["source_full_title"],
        "source_book": CHAPTER7_SOURCE["source_book"],
        "chapter": CHAPTER7_SOURCE["chapter"],
        "page": page,
        "figure": figure,
        "table": table,
        "quote_fragment": fragment,
    }


# Ontologia semantica minima extraida do capitulo. Cada item registra mineral,
# grupo, reflexao ou conceito operacional com pagina e paragrafo de origem.
# Essa lista sustenta busca/auditoria e ajuda a responder "quais entidades do
# livro alimentaram a engine?" sem depender do texto bruto do OCR.
CHAPTER7_ENTITIES = [
    {"entity_id": "illite", "entity_type": "mineral_group", "name": "Illite/mica", "page": 233, "paragraph": "Illite and Glauconite", "source": SOURCE_ID},
    {"entity_id": "glauconite", "entity_type": "mineral", "name": "Glauconite", "page": 233, "paragraph": "Illite and Glauconite", "source": SOURCE_ID},
    {"entity_id": "chlorite", "entity_type": "mineral_group", "name": "Chlorite", "page": 234, "paragraph": "Chlorite and Kaolinite", "source": SOURCE_ID},
    {"entity_id": "kaolinite", "entity_type": "mineral", "name": "Kaolinite", "page": 234, "paragraph": "Chlorite and Kaolinite", "source": SOURCE_ID},
    {"entity_id": "vermiculite", "entity_type": "mineral_group", "name": "Vermiculite", "page": 240, "paragraph": "Vermiculite", "source": SOURCE_ID},
    {"entity_id": "smectite", "entity_type": "mineral_group", "name": "Smectite", "page": 241, "paragraph": "Smectite", "source": SOURCE_ID},
    {"entity_id": "montmorillonite", "entity_type": "mineral", "name": "Montmorillonite", "page": 242, "paragraph": "Smectite", "source": SOURCE_ID},
    {"entity_id": "nontronite", "entity_type": "mineral", "name": "Nontronite", "page": 243, "paragraph": "Smectite intensity", "source": SOURCE_ID},
    {"entity_id": "saponite", "entity_type": "mineral", "name": "Saponite", "page": 242, "paragraph": "Smectite intensity", "source": SOURCE_ID},
    {"entity_id": "sepiolite", "entity_type": "mineral", "name": "Sepiolite", "page": 244, "paragraph": "Sepiolite, Palygorskite, and Halloysite", "source": SOURCE_ID},
    {"entity_id": "palygorskite", "entity_type": "mineral", "name": "Palygorskite", "page": 244, "paragraph": "Sepiolite, Palygorskite, and Halloysite", "source": SOURCE_ID},
    {"entity_id": "halloysite", "entity_type": "mineral", "name": "Halloysite", "page": 244, "paragraph": "Sepiolite, Palygorskite, and Halloysite", "source": SOURCE_ID},
    {"entity_id": "quartz", "entity_type": "associated_mineral", "name": "Quartz", "page": 227, "paragraph": "Qualitative identification procedure", "source": SOURCE_ID},
    {"entity_id": "d060", "entity_type": "reflection", "name": "060 reflection", "page": 245, "paragraph": "060 reflections", "source": SOURCE_ID},
    {"entity_id": "ool_series", "entity_type": "reflection_series", "name": "OOl basal series", "page": 228, "paragraph": "General principles", "source": SOURCE_ID},
]

# Tabelas do capitulo convertidas para JSON em memoria. As tabelas 7.3, 7.4 e
# 7.6 alimentam diretamente argilominerais; as tabelas 7.8 a 7.15 registram
# minerais associados e interferencias importantes para o painel DRX. Cada
# linha mantem unidades, pagina, tabela e notas de uso para impedir que uma
# linha de d-spacing seja tratada como confirmacao isolada.
REFLECTION_TABLES = {
    "table_7_3_sepiolite_palygorskite": {
        "title": "X-ray data for sepiolite and palygorskite",
        "page": 244,
        "units": {"d": "angstrom", "two_theta": "degree CuKalpha"},
        "reference": source_ref(244, table="7.3", fragment="Table 7.3"),
        "rows": [
            {"mineral": "sepiolite", "reflection": "110", "d": 12.0, "tolerance": 0.5, "role": "diagnostic_low_angle"},
            {"mineral": "palygorskite", "reflection": "110", "d": 10.4, "tolerance": 0.2, "role": "diagnostic_low_angle"},
        ],
        "notes": ["Fibrous/channel minerals are not reliably oriented; use additional hkl and morphology."],
    },
    "table_7_4_d060": {
        "title": "060 reflections",
        "page": 245,
        "units": {"d060": "angstrom", "two_theta": "degree CuKalpha"},
        "reference": source_ref(245, table="7.4", fragment="060"),
        "rows": [
            {"mineral": "kaolinite", "d060_min": 1.488, "d060_max": 1.502, "octahedral_type": "dioctahedral"},
            {"mineral": "montmorillonite", "d060_min": 1.492, "d060_max": 1.504, "octahedral_type": "dioctahedral"},
            {"mineral": "illite_muscovite", "d060_min": 1.495, "d060_max": 1.505, "octahedral_type": "dioctahedral"},
            {"mineral": "chlorite", "d060_min": 1.538, "d060_max": 1.549, "octahedral_type": "trioctahedral"},
            {"mineral": "sepiolite", "d060_min": 1.540, "d060_max": 1.550, "octahedral_type": "trioctahedral"},
            {"mineral": "vermiculite", "d060_min": 1.535, "d060_max": 1.545, "octahedral_type": "trioctahedral_or_unknown"},
            {"mineral": "palygorskite", "d060_min": 1.55, "d060_max": 1.57, "octahedral_type": "fibrous_channel"},
        ],
        "notes": ["d060 is auxiliary; random powder mount and interference checks are required."],
    },
    "table_7_6_kaolin_polytypes": {
        "title": "Diagnostic reflections for kaolin polytypes",
        "page": 247,
        "units": {"d": "angstrom"},
        "reference": source_ref(247, table="7.6", fragment="kaolin"),
        "rows": [
            {"mineral": "kaolinite", "reflection": "001", "d": 7.15, "tolerance": 0.25},
            {"mineral": "kaolinite", "reflection": "002", "d": 3.57, "tolerance": 0.05},
            {"mineral": "dickite_nacrite", "reflection": "001", "d": 7.15, "tolerance": 0.25, "requires": "resolved_hkl"},
        ],
        "notes": ["Do not separate kaolinite, dickite and nacrite by the 7 A basal peak alone."],
    },
    "table_7_8a_silica_minerals": {
        "title": "Diffraction data for the silica minerals",
        "page": 251,
        "units": {"d": "angstrom", "two_theta": "degree CuKalpha", "intensity": "relative"},
        "reference": source_ref(251, table="7.8A", fragment="silica minerals"),
        "rows": [
            {"mineral": "low_cristobalite", "d": 4.04, "intensity": 100, "two_theta": 22.0},
            {"mineral": "low_cristobalite", "d": 3.14, "intensity": 8, "two_theta": 28.4},
            {"mineral": "low_cristobalite", "d": 2.84, "intensity": 9, "two_theta": 31.49},
            {"mineral": "low_cristobalite", "d": 2.49, "intensity": 13, "two_theta": 36.15},
            {"mineral": "low_cristobalite", "d": 1.64, "intensity": 60, "two_theta": 56.04},
            {"mineral": "high_cristobalite", "d": 4.15, "intensity": 100, "two_theta": 21.4},
            {"mineral": "high_cristobalite", "d": 2.92, "intensity": 5, "two_theta": 30.6},
            {"mineral": "high_cristobalite", "d": 2.53, "intensity": 80, "two_theta": 35.5},
            {"mineral": "high_cristobalite", "d": 2.17, "intensity": 10, "two_theta": 41.6},
            {"mineral": "high_cristobalite", "d": 2.07, "intensity": 30, "two_theta": 43.8},
            {"mineral": "low_tridymite", "d": 4.33, "intensity": 90, "two_theta": 20.52},
            {"mineral": "low_tridymite", "d": 4.11, "intensity": 100, "two_theta": 21.64},
            {"mineral": "low_tridymite", "d": 3.87, "intensity": 20, "two_theta": 23.00},
            {"mineral": "low_tridymite", "d": 3.82, "intensity": 50, "two_theta": 23.30},
            {"mineral": "low_tridymite", "d": 2.98, "intensity": 25, "two_theta": 30.04},
            {"mineral": "high_tridymite", "d": 4.37, "intensity": 100, "two_theta": 20.3},
            {"mineral": "high_tridymite", "d": 4.12, "intensity": 61, "two_theta": 21.6},
            {"mineral": "high_tridymite", "d": 3.86, "intensity": 57, "two_theta": 23.0},
            {"mineral": "high_tridymite", "d": 3.00, "intensity": 16, "two_theta": 29.8},
            {"mineral": "high_tridymite", "d": 2.52, "intensity": 13, "two_theta": 35.6},
        ],
        "notes": ["OCR reviewed manually; use as associated-mineral interference/reference table, not clay diagnosis."],
    },
    "table_7_8b_low_quartz": {
        "title": "Diffraction data for alpha low quartz",
        "page": 251,
        "units": {"d": "angstrom", "two_theta": "degree CuKalpha", "intensity": "relative"},
        "reference": source_ref(251, table="7.8B", fragment="low quartz"),
        "rows": [
            {"mineral": "quartz_low", "d": 4.27, "intensity": 22, "two_theta": 20.8, "role": "internal_standard_companion"},
            {"mineral": "quartz_low", "d": 3.342, "intensity": 100, "two_theta": 26.67, "role": "strongest; overlaps illite 003"},
            {"mineral": "quartz_low", "d": 2.457, "intensity": 8, "two_theta": 36.57},
            {"mineral": "quartz_low", "d": 2.282, "intensity": 8, "two_theta": 39.49},
            {"mineral": "quartz_low", "d": 2.237, "intensity": 4, "two_theta": 40.32},
            {"mineral": "quartz_low", "d": 2.128, "intensity": 6, "two_theta": 42.50},
            {"mineral": "quartz_low", "d": 1.979, "intensity": 4, "two_theta": 45.83},
            {"mineral": "quartz_low", "d": 1.818, "intensity": 14, "two_theta": 50.18, "role": "quartz_check_for_d060_interference"},
            {"mineral": "quartz_low", "d": 1.672, "intensity": 4, "two_theta": 54.91},
            {"mineral": "quartz_low", "d": 1.659, "intensity": 2, "two_theta": 55.38},
            {"mineral": "quartz_low", "d": 1.541, "intensity": 9, "two_theta": 60.00, "role": "can interfere with 060 interpretation"},
            {"mineral": "quartz_low", "d": 1.453, "intensity": 1, "two_theta": 64.04},
        ],
        "notes": ["Quartz is an internal standard and a competitor for illite 3.33 A and clay d060 readings."],
    },
    "table_7_9_feldspars": {
        "title": "Diffraction data for feldspars",
        "page": 253,
        "units": {"d": "angstrom", "two_theta": "degree CuKalpha"},
        "reference": source_ref(253, table="7.9", fragment="feldspars"),
        "rows": [
            {"mineral": "microcline", "d": 4.22, "two_theta": 21.06},
            {"mineral": "microcline", "d": 3.47, "two_theta": 25.66},
            {"mineral": "microcline", "d": 3.24, "two_theta": 27.53, "role": "K-feldspar indicator near 27.5"},
            {"mineral": "microcline", "d": 3.03, "two_theta": 29.50},
            {"mineral": "microcline", "d": 2.96, "two_theta": 30.20},
            {"mineral": "orthoclase", "d": 4.22, "two_theta": 21.05},
            {"mineral": "orthoclase", "d": 3.24, "two_theta": 27.53, "role": "K-feldspar indicator near 27.5"},
            {"mineral": "orthoclase", "d": 2.99, "two_theta": 29.85},
            {"mineral": "albite", "d": 4.03, "two_theta": 22.05},
            {"mineral": "albite", "d": 3.68, "two_theta": 24.90},
            {"mineral": "albite", "d": 3.19, "two_theta": 27.95, "role": "plagioclase indicator near 28"},
            {"mineral": "albite", "d": 3.18, "two_theta": 28.08},
            {"mineral": "albite", "d": 3.00, "two_theta": 29.78},
            {"mineral": "anorthite", "d": 4.04, "two_theta": 22.00},
            {"mineral": "anorthite", "d": 3.80, "two_theta": 23.40},
            {"mineral": "anorthite", "d": 3.15, "two_theta": 28.25},
            {"mineral": "anorthite", "d": 3.00, "two_theta": 29.78},
            {"mineral": "high_sanidine", "d": 4.24, "two_theta": 20.95},
            {"mineral": "high_sanidine", "d": 4.19, "two_theta": 22.95},
            {"mineral": "high_sanidine", "d": 3.00, "two_theta": 29.78},
        ],
        "notes": ["Use mainly as associated-mineral interference table; feldspars can obscure illite/polytype peaks."],
    },
    "table_7_10_zeolites": {
        "title": "Diffraction data for zeolites",
        "page": 255,
        "units": {"d": "angstrom", "two_theta": "degree CuKalpha", "intensity": "relative"},
        "reference": source_ref(255, table="7.10", fragment="zeolites"),
        "rows": [
            {"mineral": "heulandite", "d": 8.96, "intensity": 100, "two_theta": 9.9},
            {"mineral": "heulandite", "d": 7.94, "intensity": 12, "two_theta": 11.1},
            {"mineral": "heulandite", "d": 5.10, "intensity": 70, "two_theta": 17.4},
            {"mineral": "heulandite", "d": 3.98, "intensity": 65, "two_theta": 22.3},
            {"mineral": "heulandite", "d": 2.97, "intensity": 91, "two_theta": 31.0},
            {"mineral": "clinoptilolite", "d": 8.95, "intensity": 13, "two_theta": 9.9},
            {"mineral": "clinoptilolite", "d": 7.18, "intensity": 63, "two_theta": 12.3},
            {"mineral": "clinoptilolite", "d": 5.07, "intensity": 23, "two_theta": 17.5},
            {"mineral": "clinoptilolite", "d": 3.98, "intensity": 61, "two_theta": 22.3},
            {"mineral": "clinoptilolite", "d": 3.43, "intensity": 100, "two_theta": 26.0},
            {"mineral": "phillipsite", "d": 8.11, "intensity": 8, "two_theta": 10.9},
            {"mineral": "phillipsite", "d": 6.42, "intensity": 17, "two_theta": 13.8},
            {"mineral": "phillipsite", "d": 5.60, "intensity": 60, "two_theta": 15.8},
            {"mineral": "phillipsite", "d": 4.13, "intensity": 36, "two_theta": 21.5},
            {"mineral": "phillipsite", "d": 3.21, "intensity": 100, "two_theta": 27.8},
            {"mineral": "analcime", "d": 9.14, "intensity": 2, "two_theta": 9.7},
            {"mineral": "analcime", "d": 5.60, "intensity": 60, "two_theta": 15.8},
            {"mineral": "analcime", "d": 4.85, "intensity": 20, "two_theta": 18.2},
            {"mineral": "analcime", "d": 3.43, "intensity": 21, "two_theta": 26.0},
            {"mineral": "analcime", "d": 2.93, "intensity": 50, "two_theta": 30.5},
        ],
        "notes": ["Zeolites may change during gentle lab treatment and can overlap low-angle clay ranges."],
    },
    "table_7_11a_rhombohedral_carbonates": {
        "title": "Diffraction data for rhombohedral carbonates",
        "page": 256,
        "units": {"d": "angstrom", "two_theta": "degree CuKalpha", "intensity": "relative"},
        "reference": source_ref(256, table="7.11A", fragment="rhombohedral carbonates"),
        "rows": [
            {"mineral": "calcite", "d": 3.86, "intensity": 12, "two_theta": 23.0},
            {"mineral": "calcite", "d": 3.04, "intensity": 100, "two_theta": 29.43},
            {"mineral": "calcite", "d": 2.50, "intensity": 14, "two_theta": 36.00},
            {"mineral": "calcite", "d": 2.29, "intensity": 18, "two_theta": 39.43},
            {"mineral": "ankerite", "d": 2.91, "intensity": 100, "two_theta": 30.72},
            {"mineral": "ankerite", "d": 2.20, "intensity": 5, "two_theta": 41.04},
            {"mineral": "dolomite", "d": 2.89, "intensity": 100, "two_theta": 30.98},
            {"mineral": "dolomite", "d": 2.67, "intensity": 4, "two_theta": 33.56},
            {"mineral": "dolomite", "d": 2.19, "intensity": 19, "two_theta": 41.18},
            {"mineral": "siderite", "d": 3.59, "intensity": 25, "two_theta": 24.78},
            {"mineral": "siderite", "d": 2.80, "intensity": 100, "two_theta": 32.02},
            {"mineral": "siderite", "d": 2.35, "intensity": 20, "two_theta": 38.37},
        ],
        "notes": ["Carbonate identification by one strong peak is uncertain; acid treatment can confirm/removal."],
    },
    "table_7_11b_orthorhombic_carbonates_vaterite": {
        "title": "Diffraction data for orthorhombic carbonates plus vaterite",
        "page": 256,
        "units": {"d": "angstrom", "two_theta": "degree CuKalpha", "intensity": "relative"},
        "reference": source_ref(256, table="7.11B", fragment="orthorhombic carbonates"),
        "rows": [
            {"mineral": "aragonite", "d": 3.40, "intensity": 100, "two_theta": 26.24},
            {"mineral": "aragonite", "d": 3.27, "intensity": 50, "two_theta": 27.25},
            {"mineral": "aragonite", "d": 2.70, "intensity": 60, "two_theta": 33.18},
            {"mineral": "aragonite", "d": 1.98, "intensity": 55, "two_theta": 45.82},
            {"mineral": "strontianite", "d": 4.37, "intensity": 14, "two_theta": 20.34},
            {"mineral": "strontianite", "d": 3.54, "intensity": 100, "two_theta": 25.19},
            {"mineral": "strontianite", "d": 3.45, "intensity": 70, "two_theta": 25.82},
            {"mineral": "strontianite", "d": 2.84, "intensity": 20, "two_theta": 31.52},
            {"mineral": "witherite", "d": 4.56, "intensity": 9, "two_theta": 19.5},
            {"mineral": "witherite", "d": 3.72, "intensity": 100, "two_theta": 23.9},
            {"mineral": "witherite", "d": 3.67, "intensity": 53, "two_theta": 24.3},
            {"mineral": "witherite", "d": 2.63, "intensity": 24, "two_theta": 34.12},
            {"mineral": "vaterite", "d": 4.23, "intensity": 25, "two_theta": 21.0},
            {"mineral": "vaterite", "d": 3.57, "intensity": 60, "two_theta": 24.9},
            {"mineral": "vaterite", "d": 3.29, "intensity": 100, "two_theta": 27.1},
            {"mineral": "vaterite", "d": 2.73, "intensity": 90, "two_theta": 32.8},
        ],
        "notes": ["Associated-carbonate table for interference/removal by acid treatment."],
    },
    "table_7_12_apatite_pyrite_jarosite": {
        "title": "Diffraction data for two carbonate apatites, pyrite, and jarosite",
        "page": 257,
        "units": {"d": "angstrom", "two_theta": "degree CuKalpha", "intensity": "relative"},
        "reference": source_ref(257, table="7.12", fragment="apatite pyrite jarosite"),
        "rows": [
            {"mineral": "apatite_a", "d": 8.13, "intensity": 18, "two_theta": 10.9},
            {"mineral": "apatite_a", "d": 4.06, "intensity": 10, "two_theta": 21.9},
            {"mineral": "apatite_a", "d": 3.43, "intensity": 16, "two_theta": 26.0},
            {"mineral": "apatite_a", "d": 2.81, "intensity": 80, "two_theta": 31.83},
            {"mineral": "apatite_a", "d": 2.72, "intensity": 100, "two_theta": 32.97},
            {"mineral": "apatite_b", "d": 3.46, "intensity": 25, "two_theta": 25.8},
            {"mineral": "apatite_b", "d": 3.04, "intensity": 10, "two_theta": 29.4},
            {"mineral": "apatite_b", "d": 2.78, "intensity": 100, "two_theta": 32.2},
            {"mineral": "pyrite", "d": 3.13, "intensity": 35, "two_theta": 28.54},
            {"mineral": "pyrite", "d": 2.71, "intensity": 85, "two_theta": 33.97},
            {"mineral": "pyrite", "d": 2.43, "intensity": 65, "two_theta": 37.02},
            {"mineral": "pyrite", "d": 1.63, "intensity": 100, "two_theta": 56.34},
            {"mineral": "jarosite", "d": 5.93, "intensity": 45, "two_theta": 14.9},
            {"mineral": "jarosite", "d": 5.09, "intensity": 70, "two_theta": 17.4},
            {"mineral": "jarosite", "d": 3.11, "intensity": 75, "two_theta": 28.7},
            {"mineral": "jarosite", "d": 3.08, "intensity": 100, "two_theta": 29.0},
        ],
        "notes": ["Pyrite can raise background with Cu radiation; jarosite may form during sulfide oxidation."],
    },
    "table_7_13_sulfates": {
        "title": "Diffraction data for sulfates",
        "page": 257,
        "units": {"d": "angstrom", "two_theta": "degree CuKalpha", "intensity": "relative"},
        "reference": source_ref(257, table="7.13", fragment="sulfates"),
        "rows": [
            {"mineral": "anhydrite", "d": 3.50, "intensity": 100, "two_theta": 25.46, "role": "diagnostic"},
            {"mineral": "gypsum", "d": 7.61, "intensity": 48, "two_theta": 11.7, "role": "diagnostic"},
            {"mineral": "gypsum", "d": 4.28, "intensity": 9, "two_theta": 20.8},
            {"mineral": "gypsum", "d": 3.06, "intensity": 100, "two_theta": 29.1},
            {"mineral": "bassanite", "d": 6.01, "intensity": None, "two_theta": 14.75, "role": "diagnostic after heated gypsum"},
            {"mineral": "bassanite", "d": 3.00, "intensity": 100, "two_theta": 29.80},
            {"mineral": "celestite", "d": 3.45, "intensity": 100, "two_theta": 25.86},
            {"mineral": "celestite", "d": 3.30, "intensity": 98, "two_theta": 27.06},
            {"mineral": "barite", "d": 4.34, "intensity": 30, "two_theta": 20.5},
            {"mineral": "barite", "d": 3.90, "intensity": 50, "two_theta": 23.8},
            {"mineral": "barite", "d": 3.77, "intensity": 12, "two_theta": 23.58},
            {"mineral": "barite", "d": 3.58, "intensity": 39, "two_theta": 24.89},
        ],
        "notes": ["Gypsum can dehydrate to bassanite during drying; heating history matters."],
    },
    "table_7_14_oxides_hydroxides_anatase": {
        "title": "Diffraction data for lepidocrocite, goethite, gibbsite and anatase",
        "page": 258,
        "units": {"d": "angstrom", "two_theta": "degree CuKalpha", "intensity": "relative"},
        "reference": source_ref(258, table="7.14", fragment="lepidocrocite goethite gibbsite anatase"),
        "rows": [
            {"mineral": "lepidocrocite", "d": 6.26, "intensity": 100, "two_theta": 14.2},
            {"mineral": "lepidocrocite", "d": 3.29, "intensity": 90, "two_theta": 27.1},
            {"mineral": "lepidocrocite", "d": 2.47, "intensity": 80, "two_theta": 36.4},
            {"mineral": "goethite", "d": 4.98, "intensity": 12, "two_theta": 17.8},
            {"mineral": "goethite", "d": 4.18, "intensity": 100, "two_theta": 21.24},
            {"mineral": "goethite", "d": 2.69, "intensity": 35, "two_theta": 33.27},
            {"mineral": "gibbsite", "d": 4.85, "intensity": 100, "two_theta": 18.3},
            {"mineral": "gibbsite", "d": 4.37, "intensity": 70, "two_theta": 20.3},
            {"mineral": "gibbsite", "d": 4.32, "intensity": 50, "two_theta": 20.6},
            {"mineral": "anatase", "d": 3.52, "intensity": 100, "two_theta": 25.3},
            {"mineral": "anatase", "d": 2.43, "intensity": 10, "two_theta": 36.98},
            {"mineral": "anatase", "d": 1.89, "intensity": 35, "two_theta": 48.09},
        ],
        "notes": ["Hydroxides can produce broad clay-like peaks and transform with heating."],
    },
    "table_7_15_heat_treated_oxides": {
        "title": "Diffraction data for lepidocrocite, goethite, and gibbsite after heat treatment",
        "page": 258,
        "units": {"d": "angstrom", "two_theta": "degree CuKalpha", "intensity": "relative"},
        "reference": source_ref(258, table="7.15", fragment="after heat treatment"),
        "rows": [
            {"source_mineral": "lepidocrocite", "product": "maghemite_gamma_fe2o3", "d": 5.90, "intensity": 5, "two_theta": 15.0},
            {"source_mineral": "lepidocrocite", "product": "maghemite_gamma_fe2o3", "d": 4.82, "intensity": 5, "two_theta": 18.4},
            {"source_mineral": "lepidocrocite", "product": "maghemite_gamma_fe2o3", "d": 3.20, "intensity": 10, "two_theta": 27.9},
            {"source_mineral": "goethite", "product": "hematite_alpha_fe2o3", "d": 3.67, "intensity": 35, "two_theta": 24.3},
            {"source_mineral": "goethite", "product": "hematite_alpha_fe2o3", "d": 2.69, "intensity": 100, "two_theta": 33.3},
            {"source_mineral": "goethite", "product": "hematite_alpha_fe2o3", "d": 2.51, "intensity": 75, "two_theta": 35.8},
            {"source_mineral": "gibbsite", "product": "chi_al2o3", "d": 4.52, "intensity": 30, "two_theta": 19.6},
            {"source_mineral": "gibbsite", "product": "chi_al2o3", "d": 2.38, "intensity": 70, "two_theta": 37.8},
            {"source_mineral": "gibbsite", "product": "chi_al2o3", "d": 2.12, "intensity": 80, "two_theta": 42.7},
        ],
        "notes": ["Heating can destroy original hydroxide patterns and produce oxide products."],
    },
}

# Regras diagnosticas explicitas/operacionais do capitulo. Elas modelam a
# logica mineralogica em condicoes executaveis: series OOl, comportamento
# entre tratamentos, picos companheiros, interferencias e criterios de
# verificacao. O motor principal usa estas regras como fonte de explicacao e
# auditoria; a classificacao continua ocorrendo por evidencias convergentes.
DIAGNOSTIC_RULES = [
    {
        "rule_id": "chapter7_general_iterative_identification",
        "target": "identification_workflow",
        "weight": 0.6,
        "conditions": [
            {"feature": "strongest_unassigned_peak", "action": "propose_candidate"},
            {"feature": "weaker_companion_peaks", "action": "confirm_or_reject"},
            {"feature": "assigned_peak_set", "action": "remove_from_remaining_peaks"},
        ],
        "explanation": "Iteratively assign a mineral only when the strong peak and weaker companion peaks form a consistent set.",
        "source": source_ref(227, fragment="strongest peak"),
    },
    {
        "rule_id": "chapter7_ool_series_required",
        "target": "clay_mineral_identification",
        "weight": 0.8,
        "conditions": [
            {"feature": "oriented_aggregate", "required": True},
            {"feature": "basal_ool_series", "required": True},
        ],
        "explanation": "Clay-mineral identification should prioritize oriented-aggregate basal OOl series over random-powder strongest lines.",
        "source": source_ref(228, fragment="OOl"),
    },
    {
        "rule_id": "chapter7_chlorite_ool",
        "target": "chlorite",
        "weight": 1.0,
        "conditions": [
            {"feature": "peak", "reflection": "001", "d": 14.2, "tolerance": 0.5},
            {"feature": "peak", "reflection": "002", "d": 7.1, "tolerance": 0.25},
            {"feature": "peak", "reflection": "003", "d": 4.74, "tolerance": 0.12},
            {"feature": "peak", "reflection": "004", "d": 3.55, "tolerance": 0.08},
        ],
        "explanation": "Chlorite requires the persistent 14/7/4.74/3.55 A basal set, not only the 7 A overlap.",
        "source": source_ref(234, figure="7.4", fragment="chlorite"),
    },
    {
        "rule_id": "chapter7_kaolinite_chlorite_resolution",
        "target": "kaolin_vs_chlorite",
        "weight": 1.0,
        "conditions": [
            {"feature": "kaolinite_002", "d": 3.57, "tolerance": 0.05},
            {"feature": "chlorite_004", "d": 3.53, "tolerance": 0.06},
            {"feature": "heat_550c", "kaolinite": "disappears", "chlorite": "persists_or_001_increases"},
        ],
        "explanation": "Resolve the 7 A overlap by 3.57/3.53 A companions and by heating response.",
        "source": source_ref(234, fragment="550°C"),
    },
    {
        "rule_id": "chapter7_smectite_ngc",
        "target": "smectite",
        "weight": 1.0,
        "conditions": [
            {"feature": "natural_001", "d_min": 12.0, "d_max": 15.5},
            {"feature": "glycolated_001", "d": 16.9, "tolerance": 0.8},
            {"feature": "heated_or_k300", "response": "collapse_to_10A"},
        ],
        "explanation": "Smectite is supported by expansion after ethylene glycol and collapse toward 10 A after heating/K treatment.",
        "source": source_ref(241, figure="7.8", fragment="glycol"),
    },
    {
        "rule_id": "chapter7_vermiculite_operational",
        "target": "vermiculite",
        "weight": 0.85,
        "conditions": [
            {"feature": "natural_001", "d": 14.5, "tolerance": 0.8},
            {"feature": "glycerol_response", "response": "retains_14_5A"},
            {"feature": "heated_or_k300", "response": "collapses_to_10A"},
        ],
        "explanation": "Vermiculite is an operational diagnosis; use glycerol/K/heating to separate it from smectite and chlorite.",
        "source": source_ref(240, figure="7.7", fragment="glycerol"),
    },
    {
        "rule_id": "chapter7_illite_glauconite_mica",
        "target": "illite_mica",
        "weight": 0.8,
        "conditions": [
            {"feature": "peak", "reflection": "001", "d": 10.0, "tolerance": 0.4},
            {"feature": "treatment_response", "glycol": "unchanged", "heated_550c": "unchanged"},
            {"feature": "d060", "role": "separate_dioctahedral_trioctahedral"},
        ],
        "explanation": "Illite/glauconite/mica-like phases preserve 10 A through glycolation/heating; d060 helps separate mica types.",
        "source": source_ref(233, figure="7.3", fragment="illite"),
    },
    {
        "rule_id": "chapter7_fibrous_channel_minerals",
        "target": "sepiolite_palygorskite_halloysite",
        "weight": 0.7,
        "conditions": [
            {"feature": "low_angle_peak", "sepiolite": "12-12.5A", "palygorskite": "10.3-10.5A"},
            {"feature": "glycol_response", "response": "unchanged"},
            {"feature": "morphology", "value": "fibrous_or_tubular", "importance": "strong_auxiliary"},
        ],
        "explanation": "Fibrous/channel minerals need morphology and hkl checks because low-angle peaks overlap expandable clays.",
        "source": source_ref(244, table="7.3", fragment="fibrous"),
    },
    {
        "rule_id": "chapter7_quartz_internal_standard",
        "target": "quartz",
        "weight": 0.6,
        "conditions": [
            {"feature": "quartz_101", "d": 3.34, "tolerance": 0.06},
            {"feature": "quartz_100", "d": 4.26, "tolerance": 0.10},
            {"feature": "role", "value": "internal_standard_and_competitor"},
        ],
        "explanation": "Quartz can calibrate peak positions and competes with illite 3.33 A and d060-like regions.",
        "source": source_ref(227, fragment="quartz"),
    },
]

# Regras de comportamento N/G/C e tratamentos auxiliares. Esta camada traduz o
# raciocinio do capitulo para trajetorias: pico permanece, expande, colapsa,
# desaparece ou aumenta de intensidade. O treatment_interpreter.py implementa
# a deteccao numerica dessas trajetorias.
BEHAVIOR_RULES = [
    {"target": "illite_mica", "behavior": {"N": {"001": "9.8-10.4A"}, "G": {"001": "unchanged"}, "C": {"001": "unchanged"}}, "source": source_ref(233, fragment="unchanged")},
    {"target": "chlorite", "behavior": {"N": {"001": "13.7-14.8A"}, "G": {"001": "unchanged"}, "C": {"001": "persists_or_increases", "002_003_004": "weakened"}}, "source": source_ref(234, fragment="550°C")},
    {"target": "kaolin_group", "behavior": {"N": {"001": "7.0-7.4A"}, "G": {"001": "unchanged"}, "C": {"001": "disappears_or_strongly_reduced"}}, "source": source_ref(234, fragment="kaolinite")},
    {"target": "smectite", "behavior": {"N": {"001": "12-15A"}, "G": {"001": "about_17A"}, "C": {"001": "collapse_to_10A"}}, "source": source_ref(241, fragment="glycol")},
    {"target": "vermiculite", "behavior": {"N": {"001": "about_14.5A"}, "glycerol": {"001": "retains_14.5A"}, "K_or_300C": {"001": "collapse_to_10A"}}, "source": source_ref(240, fragment="vermiculite")},
    {"target": "sepiolite_palygorskite", "behavior": {"N": {"low_angle": "12A_or_10.4A"}, "G": {"low_angle": "unchanged"}, "mild_heat": {"low_angle": "mostly_unchanged"}}, "source": source_ref(244, table="7.3", fragment="sepiolite")},
]

# Regras 060. Usadas para explicar como d060 auxilia a separar minerais
# dioctaedricos/trioctaedricos. Essas regras nunca confirmam especie sozinhas,
# principalmente porque quartzo e outros minerais podem interferir nessa
# regiao.
D060_RULES = [
    {"rule_id": "chapter7_d060_dioctahedral", "if": {"d060_max": 1.505}, "then": {"octahedral_type": "dioctahedral"}, "source": source_ref(245, table="7.4", fragment="060")},
    {"rule_id": "chapter7_d060_trioctahedral", "if": {"d060_min": 1.535}, "then": {"octahedral_type": "trioctahedral"}, "source": source_ref(245, table="7.4", fragment="060")},
    {"rule_id": "chapter7_d060_quartz_warning", "if": {"d060_around": 1.54, "quartz_possible": True}, "then": {"warning": "Check quartz companion reflections before using d060 as trioctahedral evidence."}, "source": source_ref(245, fragment="1.54")},
]

# Regras de razoes de intensidade. O capitulo usa razoes como I003/I005 ou
# I002/I003 para inferencias auxiliares sobre clorita e esmectita. Aqui elas
# ficam registradas com significado e limitacoes; a engine nao usa intensidade
# isolada para confirmar mineral.
INTENSITY_RULES = [
    {
        "rule_id": "chapter7_chlorite_fe_003_005",
        "target": "chlorite",
        "ratio": "I003/I005",
        "meaning": "Auxiliary estimate of chlorite Fe content when chlorite peaks are free of interference.",
        "limitations": ["Use unoriented powder or controlled measurement where possible.", "Avoid when kaolinite/serpentine interfere with 002/004."],
        "source": source_ref(236, table="7.1", fragment="I003"),
    },
    {
        "rule_id": "chapter7_chlorite_symmetry_even_odd",
        "target": "chlorite",
        "ratio": "(I002+I004)/I003",
        "meaning": "Auxiliary evidence for Fe distribution/symmetry in chlorite.",
        "limitations": ["Requires correction for asymmetry and minimal overlap."],
        "source": source_ref(237, table="7.2", fragment="I002"),
    },
    {
        "rule_id": "chapter7_smectite_002_003",
        "target": "smectite",
        "ratio": "I002/I003",
        "meaning": "Auxiliary separation of dioctahedral/trioctahedral smectites as octahedral scattering changes.",
        "limitations": ["Fe-rich dioctahedral and Mg-rich trioctahedral patterns may converge; use d060."],
        "source": source_ref(242, figure="7.9", fragment="I002"),
    },
    {
        "rule_id": "chapter7_kaolinite_002_003",
        "target": "kaolinite",
        "ratio": "I002/I003",
        "meaning": "Auxiliary support for kaolinite when separating it from chlorite near 25 degrees two-theta.",
        "limitations": ["Use with 550 C response; do not use a single peak."],
        "source": source_ref(234, fragment="I002"),
    },
]

# Perfis mineralogicos explicaveis. Cada perfil junta reflexoes, comportamento,
# d060, razoes de intensidade e interferencias conhecidas. O painel usa estes
# perfis para a secao "Regra-fonte" e o serializer preserva os perfis no JSON
# InvenioRDM quando o candidato correspondente aparece.
MINERAL_PROFILES = {
    "chlorite": {
        "name": "chlorite",
        "group": "chlorite_group",
        "diagnostic_reflections": ["14.2A 001", "7.1A 002", "4.74A 003", "3.55A 004"],
        "supporting_reflections": ["d060 ~1.54A for trioctahedral types"],
        "behavior": BEHAVIOR_RULES[1]["behavior"],
        "intensity_rules": ["chapter7_chlorite_fe_003_005", "chapter7_chlorite_symmetry_even_odd"],
        "d060_rules": ["chapter7_d060_trioctahedral"],
        "known_interferences": ["kaolin_group at 7A/3.57A", "serpentine near 7A", "vermiculite near 14A"],
        "diagnostic_strength": {"requires_series": True, "single_peak_allowed": False},
        "references": [source_ref(234, figure="7.4", fragment="chlorite")],
    },
    "kaolin_group": {
        "name": "kaolin_group",
        "group": "kaolin_group",
        "diagnostic_reflections": ["7.15A 001", "3.57A 002"],
        "supporting_reflections": ["d060 ~1.49-1.50A", "resolved hkl for polymorphs"],
        "behavior": BEHAVIOR_RULES[2]["behavior"],
        "intensity_rules": ["chapter7_kaolinite_002_003"],
        "d060_rules": ["chapter7_d060_dioctahedral"],
        "known_interferences": ["chlorite 002/004", "serpentine 7A", "halloysite"],
        "diagnostic_strength": {"requires_thermal_loss": True, "single_peak_allowed": False},
        "references": [source_ref(234, fragment="kaolinite")],
    },
    "smectite": {
        "name": "smectite",
        "group": "smectite_group",
        "diagnostic_reflections": ["N 12-15A", "G ~16.9A", "C/K ~10A"],
        "supporting_reflections": ["higher-order 00l where measurable", "d060 for octahedral type"],
        "behavior": BEHAVIOR_RULES[3]["behavior"],
        "intensity_rules": ["chapter7_smectite_002_003"],
        "d060_rules": ["chapter7_d060_dioctahedral", "chapter7_d060_trioctahedral"],
        "known_interferences": ["illite-smectite mixed layers", "vermiculite", "chlorite-smectite"],
        "diagnostic_strength": {"requires_glycol_expansion": True, "single_peak_allowed": False},
        "references": [source_ref(241, figure="7.8", fragment="smectite")],
    },
    "vermiculite": {
        "name": "vermiculite",
        "group": "vermiculite_group",
        "diagnostic_reflections": ["N ~14.5A", "collapse after K/300C"],
        "supporting_reflections": ["d060 for dioctahedral/trioctahedral separation"],
        "behavior": BEHAVIOR_RULES[4]["behavior"],
        "intensity_rules": [],
        "d060_rules": ["chapter7_d060_dioctahedral", "chapter7_d060_trioctahedral"],
        "known_interferences": ["chlorite 14A", "smectite 14-17A", "mixed layers"],
        "diagnostic_strength": {"operational_definition": True, "single_peak_allowed": False},
        "references": [source_ref(240, figure="7.7", fragment="vermiculite")],
    },
    "illite_mica": {
        "name": "illite_mica",
        "group": "illite_mica",
        "diagnostic_reflections": ["10A 001", "5A 002", "3.33A 003"],
        "supporting_reflections": ["d060 for mica type", "quartz check at 3.34A"],
        "behavior": BEHAVIOR_RULES[0]["behavior"],
        "intensity_rules": [],
        "d060_rules": ["chapter7_d060_dioctahedral", "chapter7_d060_trioctahedral"],
        "known_interferences": ["quartz 3.34A", "palygorskite 10.4A", "collapsed smectite"],
        "diagnostic_strength": {"requires_10A_persistence": True, "single_peak_allowed": False},
        "references": [source_ref(233, figure="7.3", fragment="illite")],
    },
}

# Ontologia compacta exportavel. Ela nao tenta substituir uma ontologia OWL
# completa; serve como mapa de classes cientificas que organizam os JSONs da
# Argiloteca e os campos indexaveis no OpenSearch/PostgreSQL.
ONTOLOGY = {
    "Mineral": {"children": ["Grupo", "Especie", "Polimorfo"]},
    "Grupo": {"examples": ["kaolin_group", "chlorite_group", "smectite_group"]},
    "Especie": {"examples": ["kaolinite", "montmorillonite", "sepiolite"]},
    "Polimorfo": {"examples": ["kaolinite", "dickite", "nacrite"]},
    "Reflexao": {"children": ["OOl", "060", "hkl_auxiliar"]},
    "Tratamento": {"examples": ["natural", "glycolated", "calcined", "glycerol", "K_saturated"]},
    "Evidencia": {"children": ["structural", "behavioral", "intensity", "treatment", "morphology"]},
    "Regra": {"children": ["diagnostic_rule", "behavior_rule", "d060_rule", "intensity_rule"]},
    "Diagnostico": {"policy": POLICY, "requires_convergent_evidence": True},
    "Razao de Intensidade": {"examples": ["I003/I005", "(I002+I004)/I003", "I002/I003"]},
    "Reflexao 060": {"role": "octahedral_classifier_auxiliary"},
}

# Schemas leves usados para documentar contratos de exportacao e integracao.
# Eles ficam tambem materializados em diagnostics/data/*.json para consumo por
# InvenioRDM, indexadores ou validadores externos.
ARGILOTECA_RULE_SCHEMA = {
    "type": "object",
    "required": ["rule_id", "target", "conditions", "source"],
    "properties": {
        "rule_id": {"type": "string"},
        "target": {"type": "string"},
        "weight": {"type": "number"},
        "conditions": {"type": "array"},
        "explanation": {"type": "string"},
        "source": {"type": "object"},
    },
}

ARGILOTECA_MINERAL_SCHEMA = {
    "type": "object",
    "required": ["name", "group", "diagnostic_reflections", "behavior", "references"],
    "properties": {
        "name": {"type": "string"},
        "group": {"type": "string"},
        "diagnostic_reflections": {"type": "array"},
        "supporting_reflections": {"type": "array"},
        "behavior": {"type": "object"},
        "intensity_rules": {"type": "array"},
        "d060_rules": {"type": "array"},
        "known_interferences": {"type": "array"},
        "diagnostic_strength": {"type": "object"},
        "references": {"type": "array"},
    },
}

ARGILOTECA_BEHAVIOR_SCHEMA = {
    "type": "object",
    "required": ["target", "behavior", "source"],
    "properties": {
        "target": {"type": "string"},
        "behavior": {"type": "object"},
        "source": {"type": "object"},
    },
}


def get_chapter7_knowledge():
    """Retorna copia profunda da base para evitar mutacao por chamadores."""
    return deepcopy({
        "source": CHAPTER7_SOURCE,
        "entities": CHAPTER7_ENTITIES,
        "tables": REFLECTION_TABLES,
        "diagnostic_rules": DIAGNOSTIC_RULES,
        "behavior_rules": BEHAVIOR_RULES,
        "d060_rules": D060_RULES,
        "intensity_rules": INTENSITY_RULES,
        "mineral_profiles": MINERAL_PROFILES,
        "ontology": ONTOLOGY,
        "schemas": {
            "argiloteca_rule_schema": ARGILOTECA_RULE_SCHEMA,
            "argiloteca_mineral_schema": ARGILOTECA_MINERAL_SCHEMA,
            "argiloteca_behavior_schema": ARGILOTECA_BEHAVIOR_SCHEMA,
        },
    })


def chapter7_rule_index():
    """Indexa regras por rule_id para explicacao e auditoria."""
    return {row["rule_id"]: deepcopy(row) for row in DIAGNOSTIC_RULES + D060_RULES + INTENSITY_RULES}


def chapter7_profile(mineral_id):
    """Retorna o perfil mineralogico extraido do capitulo, se existir."""
    profile = MINERAL_PROFILES.get(mineral_id)
    return deepcopy(profile) if profile else None
