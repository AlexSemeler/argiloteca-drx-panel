"""Local empirical reference for Brazilian pre-salt magnesian clays.

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


PRESALT_REFERENCE_DATASET = {
    "source": "Projeto Pre-Sal UFRGS/Petrobras 2019-2023",
    "policy": POLICY,
    "minerals": {
        "kerolite": {
            "observed_peaks": {"natural": [9.35, 9.45], "glycolated": [9.44, 9.45]},
            "behavior": ["non_expandable", "stable_after_glycol"],
            "context": ["presalt", "magnesian_clays"],
            "confidence": "reference_empirical",
        },
        "stevensite": {
            "observed_peaks": {"natural": [14.0, 15.5], "glycolated": [16.5, 17.2], "calcined": [9.8, 10.4]},
            "behavior": ["expands_with_glycol", "collapses_after_heating"],
            "context": ["presalt", "lacustrine", "evaporitic", "magnesian_clays"],
            "confidence": "reference_empirical",
        },
        "saponite": {
            "observed_peaks": {"natural": [14.0, 15.5], "glycolated": [16.5, 17.2], "calcined": [9.8, 10.4]},
            "behavior": ["expands_with_glycol", "collapses_after_heating", "trioctahedral_smectite"],
            "context": ["magnesian_clays"],
            "confidence": "reference_empirical",
        },
        "corrensite": {
            "observed_peaks": {"natural": [28.5, 29.8], "glycolated": [30.8, 32.2], "calcined": [23.5, 24.8]},
            "behavior": ["ordered_chlorite_smectite", "rational_sequence"],
            "context": ["presalt", "magnesian_clays"],
            "confidence": "reference_empirical",
        },
        "kerolite_stevensite_mixed_layer": {
            "observed_peaks": {"natural": [9.0, 10.0], "glycolated": [9.4, 17.1]},
            "behavior": ["partial_expansion", "magnesian_mixed_layer"],
            "context": ["presalt", "lacustrine", "evaporitic", "magnesian_clays"],
            "confidence": "reference_empirical",
        },
        "sepiolite": {
            "observed_peaks": {"natural": [12.0, 12.5], "glycolated": [12.0, 12.5]},
            "behavior": ["stable_after_glycol", "fibrous_channel"],
            "context": ["magnesian_clays"],
            "confidence": "reference_empirical",
        },
        "palygorskite": {
            "observed_peaks": {"natural": [10.3, 10.5], "glycolated": [10.3, 10.5]},
            "behavior": ["stable_after_glycol", "fibrous_channel"],
            "context": ["magnesian_clays"],
            "confidence": "reference_empirical",
        },
    },
}


def load_presalt_reference_dataset():
    return PRESALT_REFERENCE_DATASET
