"""
Checagem de conjuntos de picos companheiros.

Aplicacao de Brindley & Brown, 1980:
    - PEAK_SETS["kaolin_group"] usa o par 7 A + 3.57 A como evidencia do grupo
      da caulinita;
    - evaluate_peak_sets percorre essas faixas e informa matched/missing;
    - o objeto retornado e auxiliar e deve ser combinado com comportamento N/G/C.


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

from .diagnostic_peak_rules import peak_sets as load_peak_sets
from .evidences import find_peak

# PEAK_SETS agora vem do catalogo unico editavel em
# argiloteca/static/data/diagnostic_peak_rules_catalog.json. Mantemos o nome
# historico da constante para compatibilidade com testes e chamadas existentes.
PEAK_SETS = load_peak_sets()


def evaluate_peak_sets(peaks_by_preparation):
    """
    Avalia picos companheiros por familia.

    Loops aplicados:
        - primeiro loop achata picos por preparacao em all_peaks;
        - segundo loop percorre cada familia em PEAK_SETS;
        - terceiro loop percorre cada faixa diagnostica da familia.

    Para Brindley & Brown, 1980, a familia kaolin_group exige a leitura conjunta
    de 7 A e 3.57 A. A pontuacao mede completude do conjunto, mas nao confirma
    caulinita/dickita/nacrita sem resposta termica N/G/C e evidencias extras.
    """
    all_peaks = []
    for prep, peaks in (peaks_by_preparation or {}).items():
        for peak in peaks or []:
            all_peaks.append({**peak, "preparation": prep})
    candidates = []
    for family, rules in PEAK_SETS.items():
        matched = []
        missing = []
        for d_min, d_max, label in rules:
            peak = find_peak(all_peaks, d_min, d_max)
            if peak:
                matched.append({"label": label, "d": peak.get("d"), "preparation": peak.get("preparation")})
            else:
                missing.append(label)
        score = len(matched) / float(len(rules) or 1)
        if matched:
            candidates.append({
                "label": family,
                "score": score,
                "matched": matched,
                "missing": missing,
                "warning": "Peak-set evidence is auxiliary and cannot identify a mineral without N/G/C behavior.",
            })
    return sorted(candidates, key=lambda row: row["score"], reverse=True)
