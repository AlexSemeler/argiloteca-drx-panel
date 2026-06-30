# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: mixed_layer_sequence_generator.py
#
# Descrição.........:
# Implementa simulação 1D de padrões 00l, cálculo de intensidades e comparação observado × calculado.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Última atualização:
# 2026-06-25
#
# =============================================================================

"""Geração e frequência de sequências A/B."""
from __future__ import annotations
from .reichweite_model import conditional_probabilities

def sequence_frequency(sequence, component_fraction_A=0.5, Reichweite=0, N_layers=None):
    """Calcula frequência sigma simplificada para uma sequência."""
    seq = [str(x).upper() for x in sequence]
    probs = conditional_probabilities(component_fraction_A, Reichweite)
    multiplicity = 1 if N_layers is None else max(0, int(N_layers) + 1 - len(seq))
    if int(Reichweite) == 0:
        p = 1.0
        for item in seq:
            p *= probs["P_A"] if item == "A" else probs["P_B"]
        return {"sigma": multiplicity * p, "probabilities": probs}
    p = probs["P_A"] if seq[0] == "A" else probs["P_B"]
    for prev, cur in zip(seq, seq[1:]):
        p *= probs[f"P_{prev}{cur}"]
    return {"sigma": multiplicity * p, "probabilities": probs}

