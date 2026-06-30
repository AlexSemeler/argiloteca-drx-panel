# =============================================================================
# Projeto...........: Argiloteca - Painel de DRX
# Modulo............: pattern.py
#
# Descricao.........:
# Utilitarios pequenos para padroes 1D relativos e comparacao de residuos.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Ultima atualizacao:
# 2026-06-30
#
# =============================================================================

"""Padroes calculados relativos e comparacao observado versus calculado.

Este modulo implementa apenas uma base operacional pequena para o painel:
curvas gaussianas relativas e residuos ponto a ponto. Ele nao substitui um
modelo fisico-cristalografico completo de intensidades 00l; quando o painel
usar modelos de camada, funcao de interferencia ou Reichweite, a proveniencia
devera ser adicionada ao `SimulationRequest` e ao pacote XAI.
"""

from __future__ import annotations

import math
from typing import Iterable

from .models import PatternComparison


def _finite_float(value):
    """Converte valores numericos heterogeneos em float finito ou None."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def build_relative_pattern(
    two_theta: Iterable[float],
    peak_positions: Iterable[float],
    *,
    peak_width_deg: float = 0.2,
    scale: float = 100.0,
) -> list[float | None]:
    """Gera um padrao relativo simples em torno de posicoes 2theta.

    Args:
        two_theta: Eixo 2theta da curva calculada.
        peak_positions: Posicoes esperadas dos picos em graus 2theta.
        peak_width_deg: Largura aproximada usada no envelope gaussiano.
        scale: Intensidade maxima relativa.

    Returns:
        list[float | None]: Intensidade relativa calculada. Pontos invalidos
        no eixo retornam `None`, preservando lacunas para o grafico.

    Notes:
        Esta funcao e uma infraestrutura de comparacao visual, nao uma regra
        mineralogica. Ela nao calcula fator de estrutura de camada, funcao de
        interferencia, Lorentz-polarizacao ou orientacao preferencial.
    """
    positions = [_finite_float(position) for position in peak_positions or []]
    positions = [position for position in positions if position is not None]
    width = _finite_float(peak_width_deg) or 0.2
    sigma = max(width, 1e-6) / 2.354820045
    amplitude = _finite_float(scale) or 100.0
    values: list[float | None] = []
    for x_value in two_theta or []:
        x_number = _finite_float(x_value)
        if x_number is None:
            values.append(None)
            continue
        intensity = 0.0
        for position in positions:
            exponent = -0.5 * ((x_number - position) / sigma) ** 2
            intensity += amplitude * math.exp(exponent)
        values.append(round(intensity, 6))
    return values


def compare_observed_calculated(observed: Iterable[float], calculated: Iterable[float]) -> PatternComparison:
    """Compara intensidades observadas e calculadas por residuos absolutos.

    Args:
        observed: Intensidades observadas no difratograma.
        calculated: Intensidades calculadas no mesmo eixo 2theta.

    Returns:
        PatternComparison: Resumo de residuos. Valores `None` ou nao finitos
        sao ignorados, preservando a informacao de que a comparacao foi
        parcial quando houver lacunas.
    """
    observed_values = list(observed or [])
    calculated_values = list(calculated or [])
    warnings: list[str] = []
    if not observed_values or not calculated_values:
        return PatternComparison(0, None, None, "insufficient_data", ["Padrao observado ou calculado ausente."])
    if len(observed_values) != len(calculated_values):
        warnings.append("Padrao observado e calculado possuem comprimentos diferentes; apenas a parte comum foi comparada.")
    residuals = []
    for observed_value, calculated_value in zip(observed_values, calculated_values):
        obs = _finite_float(observed_value)
        calc = _finite_float(calculated_value)
        if obs is None or calc is None:
            continue
        residuals.append(abs(obs - calc))
    if not residuals:
        return PatternComparison(0, None, None, "insufficient_data", warnings + ["Nenhum par finito para comparar."])
    mean_abs_error = sum(residuals) / len(residuals)
    return PatternComparison(
        len(residuals),
        round(mean_abs_error, 6),
        round(max(residuals), 6),
        "valid" if not warnings else "shape_mismatch",
        warnings,
    )


def explain_pattern_comparison(comparison: PatternComparison) -> dict:
    """Gera explicacao XAI curta para comparacao observado/calculado."""
    return {
        "method": "argiloteca_1d_relative_pattern_comparison_v1",
        "status": comparison.status,
        "global_metrics": {
            "residual_count": comparison.residual_count,
            "mean_abs_error": comparison.mean_abs_error,
            "max_abs_error": comparison.max_abs_error,
        },
        "warnings": list(comparison.warnings),
        "limitations": [
            "Comparacao relativa; nao confirma mineral isoladamente.",
            "Intensidades 00l completas exigem fator de estrutura, funcao de interferencia e correcoes instrumentais.",
        ],
    }
