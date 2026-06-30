# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: mixed_layer_pattern_interpreter.py
#
# Descrição.........:
# Implementa regras explicáveis para argilominerais interestratificados e padrões 00l multi-tratamento.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Última atualização:
# 2026-06-25
#
# =============================================================================

"""
Implementa regras explicáveis para argilominerais interestratificados e padrões 00l multi-tratamento.

Responsabilidades:
    - preservar contratos públicos e estruturas JSON consumidas pelo painel;
    - registrar proveniência científica e técnica das operações realizadas;
    - manter separadas etapas de leitura, processamento, diagnóstico e exportação;
    - documentar limites de interpretação mineralógica quando houver regras DRX.

Notas científicas:
    Em módulos DRX, 2θ representa o eixo angular medido no difratograma e
    d-spacing representa o espaçamento interplanar calculado pela Lei de Bragg
    (nλ = 2d sen θ). Preparações natural, glicolada e calcinada são usadas para
    observar expansão, colapso, persistência ou destruição de picos basais.
"""

from __future__ import annotations

"""Agregador de interpretacao de padroes 00l interestratificados.

Este modulo junta marcadores de tratamento, superestrutura, ordenamento e
mistura fisica em um objeto intermediario usado pelo motor principal.
"""

from .treatment_comparator import compare_treatments
from .superstructure_detector import detect_superstructures
from .ordering_classifier import classify_ordering
from .physical_mixture_discriminator import discriminate


def interpret_pattern(peaks: dict) -> dict:
    """Interpreta um conjunto de picos normalizados por preparacao.

    Args:
        peaks: Dicionario com listas de picos por estado experimental
            padronizado, como `air_dried`, `ethylene_glycol_solvated` e
            `heated_375C`.

    Returns:
        Marcadores de comportamento, reflexoes de superestrutura, estimativa de
        ordenamento e avaliacao mistura/interestratificacao.
    """
    features = compare_treatments(peaks)
    superstructures = detect_superstructures(peaks)
    ordering = classify_ordering(features, superstructures)
    mixture = discriminate(features, superstructures)
    return {"features": features, "superstructures": superstructures, "ordering": ordering, "mixture_assessment": mixture}
