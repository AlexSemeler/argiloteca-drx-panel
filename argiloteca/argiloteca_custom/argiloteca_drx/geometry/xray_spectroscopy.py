# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: xray_spectroscopy.py
#
# Descrição.........:
# Implementa geometria de DRX, Lei de Bragg, conversão 2θ/d-spacing e validação físico-cristalográfica.
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
Implementa geometria de DRX, Lei de Bragg, conversão 2θ/d-spacing e validação físico-cristalográfica.

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

import math


def wavelength_from_known_d(d_A: float, theta_deg: float, order: int = 1) -> float:
    """Compute wavelength from known analyzer d and theta."""
    return 2.0 * float(d_A) * math.sin(math.radians(float(theta_deg))) / float(order)
