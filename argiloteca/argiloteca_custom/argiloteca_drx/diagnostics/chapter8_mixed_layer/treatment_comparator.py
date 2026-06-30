# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: treatment_comparator.py
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

"""Comparacao entre preparacoes para regras do Capitulo 8.

Este modulo transforma picos de diferentes estados experimentais em marcadores
curtos usados pelo motor, como expansao com EG, colapso termico e persistencia
de componente cloritico.
"""

from .peak_interpreter import find_peak


def compare_treatments(peaks: dict) -> dict:
    """Extrai comportamentos diagnosticos entre preparacoes.

    Args:
        peaks: Picos normalizados por preparacao.

    Returns:
        Dicionario com `features`, uma lista de marcadores usados por regras e
        pelo mecanismo XAI. Cada marcador representa evidencia parcial, nao
        confirmacao mineralogica isolada.
    """
    air = peaks.get("air_dried", [])
    eg = peaks.get("ethylene_glycol_solvated", [])
    heated = peaks.get("heated_375C", []) + peaks.get("dehydrated", []) + peaks.get("heated_250C", [])
    mg = peaks.get("Mg_glycerol_solvated", [])
    features = []
    # Expansao para ~17 A em EG indica componente esmectitico expansivel.
    if find_peak(eg, 16.8, 1.1):
        features.append("expands_with_eg_to_17A")
    # Pico perto de 10 A apos aquecimento/desidratacao indica colapso de
    # camadas expansivas ou padrao mica-like.
    if find_peak(heated, 10.0, 0.6):
        features.append("collapses_or_returns_to_10A_after_heating")
    # Componente ~14 A persistente em N/G/C e tratado como evidencia cloritica
    # ou 2:1:1, mas nao separa sozinho clorita de interestratificado.
    if find_peak(air, 14.2, 0.6) and find_peak(eg, 14.2, 0.7) and find_peak(heated, 14.2, 0.8):
        features.append("persistent_14A_component")
    # Periodos longos sao usados como triagem para superestrutura; a decisao
    # final depende do detector e do restante do padrao.
    if find_peak(air, 24.0, 2.5) or find_peak(eg, 29.0, 2.5) or find_peak(heated, 24.0, 2.5):
        features.append("long_period_superstructure_candidate")
    # Mg-glicerol sem mudanca relevante favorece componente vermiculitico no
    # contexto apropriado do Capitulo 8.
    if mg and find_peak(mg, 14.0, 1.0):
        features.append("mg_glycerol_unchanged_14A")
    return {"features": sorted(set(features))}
