# =============================================================================
# Projeto...........: Argiloteca - Painel de DRX
# Modulo............: argiloteca_drx.simulation_1d
#
# Descricao.........:
# Estruturas iniciais para simulacao 1D e comparacao observado versus calculado.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Ultima atualizacao:
# 2026-06-30
#
# =============================================================================

"""Subpacote de simulacao 1D de padroes DRX.

Este pacote fornece contratos e utilitarios pequenos para integrar o painel ao
modulo de padroes calculados. Ele nao implementa ainda um simulador NEWMOD
completo; a intencao e oferecer estruturas estaveis para armazenar parametros
instrumentais, modelos de camada, padroes calculados e residuos.

Responsabilidades:
    * representar parametros instrumentais e modelos de camada;
    * gerar padroes relativos simples para testes de integracao;
    * comparar padrao observado e calculado por residuos basicos;
    * retornar explicacoes rastreaveis para o painel XAI.
"""

from .models import InstrumentModel, LayerModel, PatternComparison, SimulationRequest
from .pattern import build_relative_pattern, compare_observed_calculated, explain_pattern_comparison

__all__ = [
    "InstrumentModel",
    "LayerModel",
    "PatternComparison",
    "SimulationRequest",
    "build_relative_pattern",
    "compare_observed_calculated",
    "explain_pattern_comparison",
]
