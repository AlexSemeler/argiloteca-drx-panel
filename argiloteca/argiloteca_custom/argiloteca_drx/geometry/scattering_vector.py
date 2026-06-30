# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: scattering_vector.py
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


def scattering_vector_magnitude_from_d(d_A: float) -> float:
    """Return |s| = 1/d for a reciprocal-lattice point convention used here."""
    return 1.0 / float(d_A)


def scattering_vector_magnitude_from_theta(lambda_A: float, theta_deg: float) -> float:
    """Return |s| = 2 sin(theta)/lambda."""
    return 2.0 * math.sin(math.radians(float(theta_deg))) / float(lambda_A)
