# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: chapter8_mixed_layer/__init__.py
#
# Descrição.........:
# Expõe o motor de interpretação de argilominerais interestratificados baseado
# no Capítulo 8 para uso pelo painel DRX e por rotinas de diagnóstico em lote.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Última atualização:
# 2026-06-25
#
# =============================================================================

"""Pacote executavel do Capitulo 8 para argilominerais interestratificados.

Fundamentacao cientifica revisada:
    Este pacote transforma regras do Capitulo 8, Identification of
    Mixed-Layered Clay Minerals, em uma camada auxiliar do Painel DRX da
    Argiloteca. A interpretacao combina padrao 00l completo, comportamento
    entre preparacoes, ordenamento, superestrutura, alargamento de linhas,
    estimativa de composicao e diagnostico diferencial.

Politica de interpretacao:
    Nenhum pico isolado confirma interestratificacao. O pacote retorna
    candidatos explicaveis e rastreaveis, preservando ambiguidades quando
    faltam preparacoes ou evidencias de padrao completo.
"""

from .diagnostic_engine import diagnose_mixed_layer_pattern

__all__ = ["diagnose_mixed_layer_pattern"]
