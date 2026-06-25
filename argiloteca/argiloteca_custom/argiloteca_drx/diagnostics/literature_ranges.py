"""
Argiloteca DRX V3 - faixas bibliograficas auxiliares.

Autor: Alexandre Ribas Semeler
E-mail: alexandre.semeler@ufrgs.br

Referencia aplicada:
    Lanson, B. & Bouchet, A. (1995). Identification des mineraux argileux
    par diffraction des rayons X: apport du traitement numerique.
    Bull. Centres Rech. Explor.-Prod. Elf Aquitaine, 19(1), 91-118.
    Arquivo local: /home/invenio/invenio-project/textos/
    lanson-1995-bull-centres-rech-ep-19-91.pdf

Como a logica da referencia esta aplicada neste arquivo:
    - entradas de mixed_layer usam diagnostic_behavior como partial_expansion,
      non_rational_sequence, chlorite_smectite_sequence e magnesian_mixed_layer;
    - notes impedem interpretacao de interestratificados como minerais puros;
    - as faixas sao evidencia auxiliar, nao confirmacao por tabela de picos,
      seguindo a critica de Lanson & Bouchet ao uso isolado de posicoes de pico.

Referencia aplicada para Brindley & Brown, 1980:
    - Os objetos kaolinite, dickite e nacrite usam Brindley & Brown como fonte
      bibliografica para reflexoes basais do grupo da caulinita.
    - A logica e usada em diagnostic_peaks, diagnostic_behavior,
      thermal_behavior, d060_range e notes.
    - A regra permanece em nivel de grupo quando so ha evidencia 7 A/3.57 A,
      porque Brindley & Brown nao autoriza separar especies apenas pelo pico
      basal 001.

Referencia aplicada para Meunier, Clays, 2005:
    - Os objetos de ilita/mica, esmectitas, cloritas, vermiculita,
      sepiolita, paligorsquita, talco/kerolita, serpentina e
      interestratificados usam Meunier para estruturar tipo de camada,
      expansibilidade, comportamento termico e classe octaedrica.
    - Os campos octahedral_type e d060_range codificam a separacao auxiliar
      dioctaedrico/trioctaedrico (~1.49-1.50 A, ~1.52 A, ~1.54 A).
    - Os campos diagnostic_behavior e thermal_behavior registram as respostas
      N/G/C esperadas para 2:1, 2:1:1, 1:1 e minerais fibrosos/canais.


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

REFERENCES = {
    # Fonte bibliografica principal para as faixas do grupo da caulinita usadas
    # abaixo em kaolinite, dickite e nacrite. O identificador e propagado para
    # range_comparator.compare_ranges e para a proveniencia de interpret_ngc.
    "brindley_brown_1980": "Brindley & Brown, 1980",
    "moore_reynolds_1989": "Moore & Reynolds, 1989/1997",
    "bailey_1980_1988": "Bailey, 1980/1988",
    "drits_tchoubar_1990": "Drits & Tchoubar, 1990",
    # Fonte estrutural usada em muitos objetos abaixo para tipo octaedrico,
    # d060, expansibilidade e interestratificados. O identificador e retornado
    # na proveniencia de interpret_ngc e nos matches de range.
    "meunier_2005": "Meunier, Clays, 2005",
    "lanson_bouchet_1995": "Lanson & Bouchet, 1995, Bull. Centres Rech. Explor.-Prod. Elf Aquitaine 19(1), 91-118",
    "flow_pdf": "Clay Mineral Identification Flow Diagram, oriented aggregates",
    "moore_reynolds_chapter7": "Moore & Reynolds, Identification of Clay Minerals and Associated Minerals, Chapter 7",
    "presalt_ufrgs_petrobras": "Projeto Pre-Sal UFRGS/Petrobras 2019-2023",
    "diagnostic_table": "Local diagnostic treatment table in textos/Adobe Scan 14 de mai. de 2026.pdf",
}


def peak(label, d_min, d_max, preparation=None, weight=1.0):
    """
    Cria um objeto de faixa diagnostica bibliografica.

    Aplicacao de Brindley & Brown, 1980:
        para caulinita/dickita/nacrita, esta funcao representa as reflexoes
        001 (~7 A) e 002 (~3.57 A) como intervalos auxiliares. Esses objetos
        sao lidos por range_comparator.compare_ranges em loops finitos sobre
        minerais, picos de referencia e picos observados.

    Aplicacao de Meunier, Clays, 2005:
        para minerais 2:1, 2:1:1 e fibrosos, os objetos criados aqui carregam
        as janelas d001/d00l que depois sao combinadas com diagnostic_behavior,
        thermal_behavior, octahedral_type e d060_range. A funcao nao executa
        loop; ela apenas padroniza os dicionarios consumidos pelos loops do
        comparador de ranges.
    """
    return {
        "label": label,
        "d_min": float(d_min),
        "d_max": float(d_max),
        "preparation": preparation,
        "weight": float(weight),
    }


LITERATURE_DIAGNOSTIC_RANGES = {
    # Brindley & Brown, 1980: caulinita e especies relacionadas compartilham
    # reflexoes basais proximas de 7 A e 3.57 A. A engine preserva isso como
    # evidencia auxiliar e nao como confirmacao de especie.
    "kaolinite": {
        "family": "kaolin_group",
        "diagnostic_peaks": [peak("001", 7.13, 7.20), peak("002", 3.54, 3.60)],
        "diagnostic_behavior": ["stable_after_glycol", "disappears_after_heating"],
        "thermal_behavior": "001 disappears or strongly decreases near 500-550 C.",
        "octahedral_type": "dioctahedral",
        "d060_range": [1.488, 1.502],
        "references": ["brindley_brown_1980", "flow_pdf", "diagnostic_table"],
        "notes": ["Do not separate dickite/nacrite using only the 7 A basal peak."],
    },
    # Brindley & Brown, 1980: dickita deve permanecer como hipotese do grupo da
    # caulinita quando nao houver hkl resolvido, morfologia ou contexto extra.
    "dickite": {
        "family": "kaolin_group",
        "diagnostic_peaks": [peak("001", 7.13, 7.25), peak("002", 3.54, 3.60)],
        "diagnostic_behavior": ["stable_after_glycol", "disappears_after_heating"],
        "thermal_behavior": "Destroyed on heating; hkl resolution needed for species.",
        "octahedral_type": "dioctahedral",
        "d060_range": [1.488, 1.502],
        "references": ["brindley_brown_1980", "flow_pdf"],
        "notes": ["Treat as kaolin-group candidate unless hkl/morphology supports species."],
    },
    # Brindley & Brown, 1980: nacrita tambem compete na janela de 7 A; o codigo
    # registra a faixa mas impede identificacao por 7 A isolado via notes.
    "nacrite": {
        "family": "kaolin_group",
        "diagnostic_peaks": [peak("001", 7.13, 7.25), peak("002", 3.54, 3.60)],
        "diagnostic_behavior": ["stable_after_glycol", "disappears_after_heating"],
        "thermal_behavior": "Destroyed on heating; hkl resolution needed.",
        "octahedral_type": "dioctahedral",
        "d060_range": [1.488, 1.502],
        "references": ["brindley_brown_1980", "flow_pdf"],
        "notes": ["Do not identify by 7 A alone."],
    },
    "halloysite_7a": {
        "family": "kaolin_group",
        "diagnostic_peaks": [peak("001", 7.20, 7.50)],
        "diagnostic_behavior": ["stable_after_glycol", "disappears_after_heating"],
        "thermal_behavior": "Destroyed or reduced by 450-550 C.",
        "octahedral_type": "dioctahedral",
        "d060_range": [1.488, 1.502],
        "references": ["flow_pdf", "diagnostic_table"],
        "notes": ["Tubular morphology is strong auxiliary evidence."],
    },
    "halloysite_10a": {
        "family": "kaolin_group",
        "diagnostic_peaks": [peak("hydrated_001", 9.80, 10.40), peak("dehydrated_001", 7.0, 7.5)],
        "diagnostic_behavior": ["stable_or_minor_glycol_response", "collapses_after_heating"],
        "thermal_behavior": "Hydrated 10 A form collapses toward 7 A and then is destroyed.",
        "octahedral_type": "dioctahedral",
        "d060_range": [1.488, 1.502],
        "references": ["flow_pdf", "diagnostic_table"],
        "notes": ["Tubular morphology strongly increases confidence."],
    },
    "illite": {
        "family": "illite_mica",
        "diagnostic_peaks": [peak("001", 9.84, 10.36), peak("002", 4.95, 5.05), peak("003", 3.30, 3.37)],
        "diagnostic_behavior": ["stable_after_glycol", "stable_after_heating"],
        "thermal_behavior": "10 A persists through common clay heating treatments.",
        "octahedral_type": "dioctahedral",
        "d060_range": [1.498, 1.522],
        "references": ["flow_pdf", "meunier_2005", "moore_reynolds_1989"],
        "notes": ["3.33-3.34 A overlaps quartz 101; require 10 A and preferably 5 A."],
    },
    "mica": {
        "family": "illite_mica",
        "diagnostic_peaks": [peak("001", 9.85, 10.20), peak("002", 4.95, 5.05), peak("003", 3.30, 3.37)],
        "diagnostic_behavior": ["stable_after_glycol", "stable_after_heating"],
        "thermal_behavior": "Micas persist to high temperatures relative to clay dehydration tests.",
        "octahedral_type": "unknown",
        "d060_range": [1.49, 1.55],
        "references": ["flow_pdf", "meunier_2005"],
        "notes": ["Use chemistry and d060 for muscovite/biotite/glauconite/celadonite hypotheses."],
    },
    "biotite": {
        "family": "illite_mica",
        "diagnostic_peaks": [peak("001", 9.85, 10.20)],
        "diagnostic_behavior": ["stable_after_glycol", "stable_after_heating"],
        "thermal_behavior": "Trioctahedral mica stable in standard clay treatments.",
        "octahedral_type": "trioctahedral",
        "d060_range": [1.532, 1.552],
        "references": ["flow_pdf", "meunier_2005"],
        "notes": ["Use as mica competitor when d060 is near 1.54 A."],
    },
    "glauconite": {
        "family": "illite_mica",
        "diagnostic_peaks": [peak("001", 9.85, 10.20)],
        "diagnostic_behavior": ["stable_after_glycol", "stable_after_heating"],
        "thermal_behavior": "10 A mica-like persistence.",
        "octahedral_type": "dioctahedral",
        "d060_range": [1.505, 1.525],
        "references": ["flow_pdf", "meunier_2005"],
        "notes": ["Specific hypothesis requires chemical/contextual support."],
    },
    "celadonite": {
        "family": "illite_mica",
        "diagnostic_peaks": [peak("001", 9.85, 10.20)],
        "diagnostic_behavior": ["stable_after_glycol", "stable_after_heating"],
        "thermal_behavior": "10 A mica-like persistence.",
        "octahedral_type": "dioctahedral",
        "d060_range": [1.505, 1.525],
        "references": ["flow_pdf", "meunier_2005"],
        "notes": ["Requires chemistry/context beyond N/G/C."],
    },
    "smectite": {
        "family": "smectite_group",
        "diagnostic_peaks": [peak("001_N", 12.0, 16.86, "N"), peak("001_G", 16.06, 18.31, "G"), peak("001_C", 9.65, 10.37, "C")],
        "diagnostic_behavior": ["expands_with_glycol", "collapses_after_heating"],
        "thermal_behavior": "Expands to about 17 A with ethylene glycol and collapses near 10 A after heating.",
        "octahedral_type": "unknown",
        "d060_range": [1.49, 1.54],
        "references": ["flow_pdf", "meunier_2005", "moore_reynolds_1989"],
        "notes": ["N/G/C separates expandable group, not species."],
    },
    "montmorillonite": {
        "family": "smectite_group",
        "diagnostic_peaks": [peak("001_G", 16.5, 17.8, "G"), peak("001_C", 9.7, 10.3, "C")],
        "diagnostic_behavior": ["expands_with_glycol", "collapses_after_heating"],
        "thermal_behavior": "Collapses near 10 A after heating.",
        "octahedral_type": "dioctahedral",
        "d060_range": [1.490, 1.505],
        "references": ["flow_pdf", "meunier_2005"],
        "notes": ["Differentiate from nontronite by chemistry; from trioctahedral smectite by d060/chemistry."],
    },
    "nontronite": {
        "family": "smectite_group",
        "diagnostic_peaks": [peak("001_G", 16.5, 17.8, "G"), peak("001_C", 9.7, 10.3, "C")],
        "diagnostic_behavior": ["expands_with_glycol", "collapses_after_heating"],
        "thermal_behavior": "Expandable Fe-rich dioctahedral smectite behavior.",
        "octahedral_type": "dioctahedral",
        "d060_range": [1.495, 1.525],
        "references": ["flow_pdf", "meunier_2005"],
        "notes": ["Fe-rich hypothesis requires chemistry."],
    },
    "saponite": {
        "family": "smectite_group",
        "diagnostic_peaks": [peak("001_N", 14.0, 15.5, "N"), peak("001_G", 16.5, 17.5, "G"), peak("001_C", 9.7, 10.4, "C")],
        "diagnostic_behavior": ["expands_with_glycol", "collapses_after_heating"],
        "thermal_behavior": "Trioctahedral smectite; thermal details require context.",
        "octahedral_type": "trioctahedral",
        "d060_range": [1.520, 1.545],
        "references": ["flow_pdf", "meunier_2005", "presalt_ufrgs_petrobras"],
        "notes": ["Mg/Al chemistry supports saponite against stevensite/hectorite."],
    },
    "stevensite": {
        "family": "smectite_group",
        "diagnostic_peaks": [peak("001_N", 14.0, 15.5, "N"), peak("001_G", 16.5, 17.5, "G"), peak("001_C", 9.7, 10.4, "C")],
        "diagnostic_behavior": ["expands_with_glycol", "collapses_after_heating"],
        "thermal_behavior": "Mg trioctahedral smectite; may occur in lacustrine/evaporitic systems.",
        "octahedral_type": "trioctahedral",
        "d060_range": [1.520, 1.545],
        "references": ["meunier_2005", "presalt_ufrgs_petrobras"],
        "notes": ["Treat as contextual candidate when Mg-rich/pre-salt evidence exists."],
    },
    "hectorite": {
        "family": "smectite_group",
        "diagnostic_peaks": [peak("001_G", 16.5, 17.5, "G")],
        "diagnostic_behavior": ["expands_with_glycol", "collapses_after_heating"],
        "thermal_behavior": "Trioctahedral smectite behavior.",
        "octahedral_type": "trioctahedral",
        "d060_range": [1.520, 1.545],
        "references": ["meunier_2005"],
        "notes": ["Requires Li/Mg chemistry for specific assignment."],
    },
    "vermiculite": {
        "family": "vermiculite_group",
        "diagnostic_peaks": [peak("001", 13.7, 14.8, "N"), peak("collapse", 10.0, 12.0, "C")],
        "diagnostic_behavior": ["stable_or_minor_glycol_response", "partial_or_total_collapse"],
        "thermal_behavior": "May collapse toward 10-12 A after heating.",
        "octahedral_type": "unknown",
        "d060_range": [1.49, 1.54],
        "references": ["flow_pdf", "meunier_2005"],
        "notes": ["Competes with chlorite and smectite at 14 A."],
    },
    "chlorite": {
        "family": "chlorite_group",
        "diagnostic_peaks": [peak("001", 13.7, 14.8), peak("002", 7.0, 7.25), peak("003", 4.65, 4.80), peak("004", 3.50, 3.60)],
        "diagnostic_behavior": ["stable_after_glycol", "persists_after_heating"],
        "thermal_behavior": "14 A persists; intensity may increase after 500-600 C.",
        "octahedral_type": "trioctahedral",
        "d060_range": [1.532, 1.552],
        "references": ["flow_pdf", "diagnostic_table", "meunier_2005"],
        "notes": ["7 A overlaps kaolin/serpentine; require 14/7/4.72/3.53 set."],
    },
    "dioctahedral_chlorite": {
        "family": "chlorite_group",
        "diagnostic_peaks": [peak("001", 13.7, 14.8), peak("002", 7.0, 7.25)],
        "diagnostic_behavior": ["stable_after_glycol", "persists_after_heating"],
        "thermal_behavior": "Chlorite-like persistence.",
        "octahedral_type": "dioctahedral",
        "d060_range": [1.490, 1.505],
        "references": ["flow_pdf", "meunier_2005"],
        "notes": ["d060 near 1.50 A supports dioctahedral chlorite hypothesis."],
    },
    "corrensite": {
        "family": "chlorite_smectite",
        "diagnostic_peaks": [peak("superstructure_N", 28.5, 29.8, "N"), peak("superstructure_G", 30.8, 32.2, "G"), peak("heated", 23.5, 24.8, "C")],
        "diagnostic_behavior": ["rational_sequence", "ordered_chlorite_smectite"],
        "thermal_behavior": "Ordered C/S may yield about 24 A after heating.",
        "octahedral_type": "trioctahedral",
        "d060_range": [1.520, 1.545],
        "references": ["flow_pdf", "meunier_2005"],
        "notes": ["Treat as entity or regularly interstratified C/S, not simple mixture."],
    },
    "palygorskite": {
        "family": "fibrous_channel",
        "diagnostic_peaks": [peak("110", 10.3, 10.5)],
        "diagnostic_behavior": ["stable_after_glycol", "disappears_after_heating"],
        "thermal_behavior": "Destroyed or strongly reduced by 550 C; 10.5/9.2 behavior may occur.",
        "octahedral_type": "dioctahedral",
        "d060_range": None,
        "references": ["flow_pdf", "diagnostic_table", "meunier_2005"],
        "notes": ["Fibrous morphology and hkl checks are important."],
    },
    "sepiolite": {
        "family": "fibrous_channel",
        "diagnostic_peaks": [peak("110", 12.0, 12.5)],
        "diagnostic_behavior": ["stable_after_glycol", "disappears_after_heating"],
        "thermal_behavior": "Destroyed or reduced by 550 C; 12.2 to 10.4 heating behavior may occur.",
        "octahedral_type": "trioctahedral",
        "d060_range": None,
        "references": ["flow_pdf", "diagnostic_table", "meunier_2005"],
        "notes": ["Fibrous morphology and hkl checks are important."],
    },
    "talc": {
        "family": "talc_kerolite_group",
        "diagnostic_peaks": [peak("001", 9.25, 9.45)],
        "diagnostic_behavior": ["stable_after_glycol", "stable_after_heating"],
        "thermal_behavior": "Non-expandable 2:1 Mg phyllosilicate.",
        "octahedral_type": "trioctahedral",
        "d060_range": [1.520, 1.545],
        "references": ["meunier_2005", "diagnostic_table"],
        "notes": ["Separate talc/kerolite by crystallinity, chemistry and context."],
    },
    "kerolite": {
        "family": "talc_kerolite_group",
        "diagnostic_peaks": [peak("001", 9.35, 9.45, "N"), peak("001_G", 9.35, 9.50, "G")],
        "diagnostic_behavior": ["stable_after_glycol", "non_expandable"],
        "thermal_behavior": "Mg-rich non-expandable talc-like clay; contextual in pre-salt datasets.",
        "octahedral_type": "trioctahedral",
        "d060_range": [1.520, 1.545],
        "references": ["presalt_ufrgs_petrobras", "meunier_2005"],
        "notes": ["Recognize as auxiliary contextual hypothesis, not by 9.4 A alone."],
    },
    "pyrophyllite": {
        "family": "pyrophyllite_talc",
        "diagnostic_peaks": [peak("001", 9.10, 9.30)],
        "diagnostic_behavior": ["stable_after_glycol"],
        "thermal_behavior": "Non-expandable 2:1 dioctahedral phyllosilicate.",
        "octahedral_type": "dioctahedral",
        "d060_range": [1.490, 1.505],
        "references": ["meunier_2005"],
        "notes": ["Requires powder pattern/chemistry for confident assignment."],
    },
    "serpentine": {
        "family": "serpentine_group",
        "diagnostic_peaks": [peak("001", 7.0, 7.4)],
        "diagnostic_behavior": ["stable_after_glycol", "stable_or_destroyed_after_heating"],
        "thermal_behavior": "May survive or transform depending species and temperature.",
        "octahedral_type": "trioctahedral",
        "d060_range": [1.520, 1.545],
        "references": ["flow_pdf", "diagnostic_table", "meunier_2005"],
        "notes": ["Competes with kaolin/chlorite near 7 A; morphology and hkl needed."],
    },
    "chrysotile": {
        "family": "serpentine_group",
        "diagnostic_peaks": [peak("001", 7.0, 7.4)],
        "diagnostic_behavior": ["stable_after_glycol"],
        "thermal_behavior": "Serpentine-group heating behavior.",
        "octahedral_type": "trioctahedral",
        "d060_range": [1.520, 1.545],
        "references": ["flow_pdf"],
        "notes": ["Fibrous morphology supports chrysotile over platy serpentines."],
    },
    "antigorite": {
        "family": "serpentine_group",
        "diagnostic_peaks": [peak("001", 7.0, 7.4)],
        "diagnostic_behavior": ["stable_after_glycol"],
        "thermal_behavior": "Serpentine-group heating behavior.",
        "octahedral_type": "trioctahedral",
        "d060_range": [1.520, 1.545],
        "references": ["flow_pdf"],
        "notes": ["Platy morphology and hkl checks required."],
    },
    "lizardite": {
        "family": "serpentine_group",
        "diagnostic_peaks": [peak("001", 7.0, 7.4)],
        "diagnostic_behavior": ["stable_after_glycol"],
        "thermal_behavior": "Serpentine-group heating behavior.",
        "octahedral_type": "trioctahedral",
        "d060_range": [1.520, 1.545],
        "references": ["meunier_2005"],
        "notes": ["Do not identify from 7 A alone."],
    },
    "kaolinite_smectite": {
        "family": "mixed_layer",
        "diagnostic_peaks": [],
        "diagnostic_behavior": ["partial_expansion", "non_rational_sequence"],
        "thermal_behavior": "Mixed behavior; do not report pure mineral without warning.",
        "octahedral_type": "unknown",
        "d060_range": None,
        "references": ["meunier_2005", "moore_reynolds_1989", "lanson_bouchet_1995"],
        "notes": ["K/S abbreviation in this engine is reserved for kerolite/stevensite."],
    },
    "illite_smectite": {
        "family": "mixed_layer",
        "diagnostic_peaks": [],
        "diagnostic_behavior": ["partial_expansion", "non_rational_sequence"],
        "thermal_behavior": "Intermediate 10-17 A behavior.",
        "octahedral_type": "dioctahedral",
        "d060_range": [1.490, 1.520],
        "references": ["meunier_2005", "moore_reynolds_1989", "lanson_bouchet_1995"],
        "notes": ["Rectorite if ordered and rational sequence is supported."],
    },
    "chlorite_smectite": {
        "family": "mixed_layer",
        "diagnostic_peaks": [],
        "diagnostic_behavior": ["partial_expansion", "chlorite_smectite_sequence"],
        "thermal_behavior": "14 A persistence plus expandable component.",
        "octahedral_type": "trioctahedral",
        "d060_range": [1.520, 1.545],
        "references": ["flow_pdf", "meunier_2005", "lanson_bouchet_1995"],
        "notes": ["Corrensite is the ordered entity when 29/31-32/24 A sequence is present."],
    },
    "talc_smectite": {
        "family": "mixed_layer",
        "diagnostic_peaks": [peak("talc_like", 9.30, 9.50)],
        "diagnostic_behavior": ["partial_expansion"],
        "thermal_behavior": "Talc/stevensite or talc/smectite mixed behavior.",
        "octahedral_type": "trioctahedral",
        "d060_range": [1.520, 1.545],
        "references": ["meunier_2005", "presalt_ufrgs_petrobras", "lanson_bouchet_1995"],
        "notes": ["Use Mg chemistry and pre-salt/lacustrine context where available."],
    },
    "kerolite_stevensite_mixed_layer": {
        "family": "mixed_layer",
        "diagnostic_peaks": [peak("kerolite_like", 9.30, 10.00)],
        "diagnostic_behavior": ["partial_expansion", "magnesian_mixed_layer"],
        "thermal_behavior": "Intermediate kerolite/stevensite behavior.",
        "octahedral_type": "trioctahedral",
        "d060_range": [1.520, 1.545],
        "references": ["presalt_ufrgs_petrobras", "meunier_2005", "lanson_bouchet_1995"],
        "notes": ["K/S must be reported as mixed-layer hypothesis unless chemistry/modeling confirms."],
    },
}


def get_literature_ranges():
    """
    Retorna o catalogo bibliografico usado pela engine DRX V3.

    Meunier, Clays, 2005 aparece neste retorno nos registros que exigem
    informacao estrutural: esmectitas dioctaedricas/trioctaedricas, micas,
    cloritas, kerolita/talco, argilominerais fibrosos e interestratificados.
    O chamador deve tratar esses dados como referencia auxiliar, nao como
    confirmacao isolada por faixa.
    """
    return LITERATURE_DIAGNOSTIC_RANGES
