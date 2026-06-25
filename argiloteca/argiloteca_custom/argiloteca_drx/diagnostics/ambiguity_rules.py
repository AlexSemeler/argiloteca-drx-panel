"""Mandatory ambiguity checks for clay XRD interpretation.

Aplicacao de Moore & Reynolds, X-Ray Diffraction and the Identification and
Analysis of Clay Minerals:
    - O quartzo e tratado como competidor/padrao interno: 3.33-3.34 A pode
      inflar ilita/mica, e ~1.54 A pode interferir na leitura d060.
    - A separacao caulinita/clorita em 7 A exige aquecimento, picos
      companheiros e, quando necessario, tratamento quimico/intercalacao.
    - Vermiculita, esmectita e interestratificados em 14 A exigem resposta a
      glicol/glicerol, K-saturacao ou aquecimento moderado; a janela nao deve
      ser resolvida por pico isolado.
    - Picos de sepiolita/paligorsquita podem simular fases expansivas; por
      isso morfologia e reflexoes adicionais permanecem como criterios.

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

from .evidences import has_peak


def evaluate_ambiguities(peaks_by_preparation, behaviors=None, metadata=None):
    """
    Avalia janelas diagnosticas que Moore & Reynolds descrevem como
    mineralogicamente ambíguas.

    A funcao percorre todos os picos normalizados uma unica vez para montar a
    lista de entrada e depois aplica regras pequenas por janela. O retorno e
    consumido pelo motor de confianca, pelo painel e pela lista de proximos
    testes.
    """
    peaks = []
    for rows in (peaks_by_preparation or {}).values():
        peaks.extend(rows or [])
    ambiguities = []
    if has_peak(peaks, 6.95, 7.45):
        ambiguities.append({
            "window": "7 A",
            "candidates": ["kaolinite", "chlorite", "serpentine", "halloysite", "dickite", "nacrite"],
            "resolve_by": ["14 A", "3.57 A", "3.53 A", "chlorite 003/004", "disappearance at 550 C", "formamide/DMSO if halloysite/kaolinite remains unresolved", "morphology", "resolved hkl"],
            "reference": "Moore & Reynolds: kaolinite/chlorite overlap near 7 A requires companion peaks and heating/chemical tests.",
        })
    if has_peak(peaks, 9.3, 10.6):
        ambiguities.append({
            "window": "10 A",
            "candidates": ["illite_mica", "halloysite_10a", "palygorskite", "collapsed_smectite", "I/S", "kerolite"],
            "resolve_by": ["N-G-C trajectory", "5 A", "3.33 A", "10.5 A", "fibrous/tubular morphology", "d060"],
        })
    if has_peak(peaks, 11.8, 12.6):
        ambiguities.append({
            "window": "12 A",
            "candidates": ["sepiolite", "Na-smectite", "palygorskite shoulder", "one-water-layer smectite"],
            "resolve_by": ["glycolation", "fibrous morphology", "thermal destruction/collapse", "d060"],
        })
    if has_peak(peaks, 13.4, 14.9):
        ambiguities.append({
            "window": "14 A",
            "candidates": ["chlorite", "vermiculite", "Mg/Ca-smectite", "swelling_chlorite", "corrensite_partial"],
            "resolve_by": ["expansion to 17 A", "glycerol solvation", "K saturation", "heating near 300 C for vermiculite collapse", "persistence after 550 C for chlorite", "collapse to 10-12 A", "7/4.72/3.53 A", "d060"],
            "reference": "Moore & Reynolds: operational vermiculite/smectite separation needs glycerol/K/heat response, not only 14 A.",
        })
    if has_peak(peaks, 3.30, 3.38):
        ambiguities.append({
            "window": "3.33-3.34 A",
            "candidates": ["illite", "quartz"],
            "resolve_by": ["10 A", "5 A", "quartz pattern", "quartz 4.26 A and 1.82 A companion peaks", "expanded high-resolution scan if broad clay peak overlaps sharp quartz"],
            "reference": "Moore & Reynolds: quartz 3.34 A is common and can be used as internal standard/competitor.",
        })
    if has_peak(peaks, 1.535, 1.550):
        ambiguities.append({
            "window": "d060/quartz 1.54 A",
            "candidates": ["trioctahedral_clay_060", "quartz"],
            "resolve_by": ["check quartz 1.82 A", "check quartz 3.34 A", "random powder mount", "avoid d060-only identification"],
            "reference": "Moore & Reynolds: quartz near d=1.542 A can interfere with 060 interpretation.",
        })
    return ambiguities
