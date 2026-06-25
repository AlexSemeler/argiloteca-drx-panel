"""
Compara picos observados com faixas bibliograficas, empiricas e Pre-Sal.

Aplicacao de Brindley & Brown, 1980:
    - recebe LITERATURE_DIAGNOSTIC_RANGES, onde kaolinite, dickite e nacrite
      carregam referencias "brindley_brown_1980";
    - os loops desta funcao cruzam picos observados com as reflexoes 001/002
      dessas especies;
    - o resultado e retornado como literature_matches, sempre como hipotese
      auxiliar. A funcao nao confirma especie por faixa isolada.

Aplicacao de Meunier, Clays, 2005:
    - recebe LITERATURE_DIAGNOSTIC_RANGES, onde micas, esmectitas, cloritas,
      vermiculita, talco/kerolita, fibrosos e interestratificados carregam
      referencia "meunier_2005";
    - os loops cruzam picos observados com esses ranges estruturais, mas o
      retorno continua sendo apenas literature_matches;
    - a confirmacao continua proibida por faixa isolada, porque a engine usa
      comportamento N/G/C, d060, picos companheiros e ambiguidades.


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

from .literature_ranges import LITERATURE_DIAGNOSTIC_RANGES
from .presalt_reference_dataset import PRESALT_REFERENCE_DATASET


def compare_ranges(peaks_by_preparation, literature=None, empirical=None, presalt=None):
    """
    Executa comparacao por ranges.

    Loops aplicados:
        1. percorre preparacoes e picos observados para montar observed;
        2. percorre minerais bibliograficos, picos de referencia e picos
           observados para gerar literature_matches;
        3. percorre ranges empiricos locais;
        4. percorre ranges do dataset Pre-Sal.

    Brindley & Brown, 1980 entra no segundo loop quando o mineral e
    kaolinite/dickite/nacrite. Mesmo quando ha match em 7 A ou 3.57 A, a saida
    continua sendo hipotese auxiliar porque o comportamento N/G/C tem prioridade.

    Meunier, Clays, 2005 entra no mesmo segundo loop quando os registros do
    catalogo possuem references=["meunier_2005", ...]. Os matches de illite,
    smectite, chlorite, kerolite, sepiolite, palygorskite, serpentine e
    mixed_layer sao preservados como evidencia de faixa, sem elevar confianca
    sozinhos.
    """
    literature = literature or LITERATURE_DIAGNOSTIC_RANGES
    empirical = empirical or {}
    presalt = presalt or PRESALT_REFERENCE_DATASET
    observed = []
    # Loop finito por tratamento/pico; normaliza a entrada para comparacao
    # posterior sem mutar o payload original.
    for prep, peaks in (peaks_by_preparation or {}).items():
        for peak in peaks or []:
            observed.append((prep, peak))
    lit_matches = []
    # Loop onde as faixas bibliograficas sao efetivamente aplicadas. Brindley &
    # Brown responde por caulinita/dickita/nacrita; Meunier responde por
    # estrutura, d060 e comportamento esperado de 2:1, 2:1:1, fibrosos e
    # interestratificados. O match e registrado, mas nunca confirmado.
    for mineral, row in literature.items():
        for ref_peak in row.get("diagnostic_peaks") or []:
            for prep, obs in observed:
                expected_prep = ref_peak.get("preparation")
                if expected_prep and expected_prep != prep:
                    continue
                if ref_peak["d_min"] <= obs.get("d", 0) <= ref_peak["d_max"]:
                    lit_matches.append({"mineral": mineral, "family": row.get("family"), "peak": ref_peak.get("label"), "observed_d": obs.get("d"), "preparation": prep})
    empirical_matches = []
    for mineral, peaks in (empirical.get("ranges") or {}).items():
        for peak_id, prep_ranges in peaks.items():
            for prep, stats in prep_ranges.items():
                d_min, d_max = stats.get("recommended_range") or [None, None]
                if d_min is None:
                    continue
                for obs_prep, obs in observed:
                    if obs_prep == prep and d_min <= obs.get("d", 0) <= d_max:
                        empirical_matches.append({"mineral": mineral, "peak": peak_id, "observed_d": obs.get("d"), "preparation": prep, "provenance_hash": stats.get("provenance_hash")})
    presalt_matches = []
    for mineral, row in (presalt.get("minerals") or {}).items():
        for prep_name, window in (row.get("observed_peaks") or {}).items():
            d_min, d_max = window
            prep = {"natural": "N", "glycolated": "G", "calcined": "C"}.get(prep_name, prep_name)
            for obs_prep, obs in observed:
                if obs_prep == prep and d_min <= obs.get("d", 0) <= d_max:
                    presalt_matches.append({"mineral": mineral, "observed_d": obs.get("d"), "preparation": prep, "context": row.get("context")})
    return {
        "literature_matches": lit_matches,
        "empirical_matches": empirical_matches,
        "presalt_matches": presalt_matches,
        "combined_candidates": sorted({row["mineral"] for row in lit_matches + empirical_matches + presalt_matches}),
        "warnings": ["Range matches are hypotheses only; behavior N/G/C has higher priority."] if lit_matches or empirical_matches or presalt_matches else [],
    }
