# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: superstructure_detector.py
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

"""Deteccao auxiliar de reflexoes de superestrutura e periodos longos."""

from .peak_interpreter import find_peak


def detect_superstructures(peaks: dict) -> list[dict]:
    """Procura reflexoes longas indicativas de ordenamento.

    Args:
        peaks: Picos normalizados por preparacao.

    Returns:
        Lista de evidencias de superestrutura. A presenca dessas reflexoes
        aumenta a hipotese de R1/corrensita/hydrobioite, mas ainda precisa ser
        interpretada com o restante do padrao 00l.
    """
    out = []
    all_peaks = []
    for rows in (peaks or {}).values():
        all_peaks.extend(rows or [])
    for center, label in [(24.0, "corrensite_or_chlorite_smectite_long_period"), (29.0, "corrensite_low_charge"), (31.0, "corrensite_EG"), (12.0, "mica_vermiculite_or_hydrobioite")]:
        peak = find_peak(all_peaks, center, 1.2)
        if peak:
            out.append({"label": label, "d_A": peak.get("d_A"), "evidence": "long-period or superstructure reflection"})
    return out
