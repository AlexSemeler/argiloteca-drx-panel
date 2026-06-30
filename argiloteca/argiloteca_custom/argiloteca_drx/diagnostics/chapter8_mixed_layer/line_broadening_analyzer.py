# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: line_broadening_analyzer.py
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

"""Analise de alargamento de linhas para o Capitulo 8.

O modulo cobre dois usos no painel: marcar picos largos como evidencia
qualitativa de interestratificacao e calcular a estimativa empirica de
serpentina em serpentina/clorita pelas equacoes 8.1 e 8.2.
"""


def beta_r(beta_005: float, beta_004: float) -> float:
    """Calcula beta relativo da Eq. 8.1 para serpentina/clorita.

    `beta_004` representa a largura de referencia sem alargamento por
    interestratificacao; `beta_005` e a largura corrigida da reflexao 005.
    """
    value = float(beta_005) ** 1.25 - float(beta_004) ** 1.25
    return max(value, 0.0) ** (1.0 / 1.25)


def percent_serpentine(beta_005: float, beta_004: float) -> float:
    """Estima percentual de serpentina pela Eq. 8.2.

    O resultado e truncado em zero porque a equacao empirica tem intercepto
    negativo. A estimativa so deve ser usada quando os requisitos instrumentais
    do Capitulo 8 forem atendidos.
    """
    br = beta_r(beta_005, beta_004)
    return max(0.0, -0.51 + 24.27 * br)


def analyze_line_broadening(peaks: dict) -> dict:
    """Marca preparacoes com picos largos para revisao no painel.

    Args:
        peaks: Picos normalizados por preparacao, com `fwhm` ou `beta` quando
            disponivel.

    Returns:
        Lista de flags qualitativas. Esta funcao nao confirma
        interestratificacao sozinha.
    """
    flags = []
    for prep, rows in (peaks or {}).items():
        broad = [p for p in rows or [] if (p.get("fwhm") or p.get("beta") or 0) and float(p.get("fwhm") or p.get("beta")) >= 0.6]
        if broad:
            flags.append({"preparation": prep, "feature": "broad_peaks_present", "count": len(broad)})
    return {"flags": flags}
