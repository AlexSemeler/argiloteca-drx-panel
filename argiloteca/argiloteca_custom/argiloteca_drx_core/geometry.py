"""Geometria de difracao reutilizavel pelo Painel DRX.

Este modulo concentra regras do Capitulo 3 ("Diffraction I: Geometry") em
funcoes pequenas e sem dependencia de Flask/Invenio. Ele valida a convencao
2θ/θ, aplica a Lei de Bragg e devolve explicacoes rastreaveis para uso no
painel, nos workers e nos testes.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from .curves import CU_K_ALPHA_WAVELENGTH, calculate_d_spacing, calculate_two_theta


@dataclass(frozen=True)
class BraggCalculation:
    """Resultado auditavel de um calculo de Bragg.

    Attributes:
        two_theta_deg: Angulo medido no eixo experimental do difratograma.
        theta_deg: Angulo de Bragg usado na equacao.
        wavelength_angstrom: Comprimento de onda aplicado.
        d_spacing_angstrom: Espacamento interplanar calculado.
        status: `valid`, `invalid` ou `insufficient_data`.
        rule_id: Regra geometrica usada como proveniencia.
        warning: Aviso cientifico quando o calculo e incompleto ou invalido.
    """

    two_theta_deg: float | None
    theta_deg: float | None
    wavelength_angstrom: float
    d_spacing_angstrom: float | None
    status: str
    rule_id: str
    warning: str | None = None


def bragg_from_two_theta(two_theta, wavelength_angstrom=CU_K_ALPHA_WAVELENGTH) -> BraggCalculation:
    """Calcula d-spacing a partir de 2θ com rastreabilidade do Capitulo 3."""
    try:
        two_theta_value = float(two_theta)
        wavelength_value = float(wavelength_angstrom)
    except (TypeError, ValueError):
        return BraggCalculation(None, None, CU_K_ALPHA_WAVELENGTH, None, "insufficient_data", "chapter3_two_theta_to_d_spacing", "2θ ou λ ausente/invalido.")
    if two_theta_value <= 0 or wavelength_value <= 0:
        return BraggCalculation(two_theta_value, None, wavelength_value, None, "invalid", "chapter3_two_theta_to_d_spacing", "2θ e λ devem ser positivos.")
    theta = two_theta_value / 2.0
    d_spacing = calculate_d_spacing(two_theta_value, wavelength=wavelength_value)
    return BraggCalculation(two_theta_value, theta, wavelength_value, d_spacing, "valid" if d_spacing else "invalid", "chapter3_two_theta_to_d_spacing")


def two_theta_from_d_spacing(d_spacing, wavelength_angstrom=CU_K_ALPHA_WAVELENGTH):
    """Calcula a posicao 2θ esperada de uma reflexao com d-spacing conhecido."""
    try:
        d_value = float(d_spacing)
        wavelength_value = float(wavelength_angstrom)
    except (TypeError, ValueError):
        return {
            "two_theta_deg": None,
            "status": "insufficient_data",
            "rule_id": "chapter3_d_spacing_to_two_theta",
            "warning": "d-spacing ou λ ausente/invalido.",
        }
    two_theta = calculate_two_theta(d_value, wavelength=wavelength_value)
    ratio = wavelength_value / (2.0 * d_value) if d_value > 0 else math.inf
    return {
        "two_theta_deg": two_theta,
        "theta_deg": (two_theta / 2.0) if two_theta is not None else None,
        "wavelength_angstrom": wavelength_value,
        "d_spacing_angstrom": d_value,
        "observability_ratio": ratio,
        "status": "valid" if two_theta is not None else "invalid",
        "rule_id": "chapter3_d_spacing_to_two_theta",
        "warning": None if two_theta is not None else "Reflexao nao observavel para λ/(2d) > 1.",
    }


def geometry_explanation(two_theta=None, d_spacing=None, wavelength_angstrom=CU_K_ALPHA_WAVELENGTH):
    """Gera explicacao curta para calculos geometricos exibidos no painel."""
    if two_theta is not None:
        calc = bragg_from_two_theta(two_theta, wavelength_angstrom=wavelength_angstrom)
        return {
            "rule_id": calc.rule_id,
            "status": calc.status,
            "input": {"two_theta_deg": calc.two_theta_deg, "wavelength_angstrom": calc.wavelength_angstrom},
            "output": {"theta_deg": calc.theta_deg, "d_spacing_angstrom": calc.d_spacing_angstrom},
            "explanation": "O eixo medido e 2θ; a Lei de Bragg usa θ = 2θ/2 antes de calcular d = λ/(2 sen θ).",
            "warning": calc.warning,
        }
    return {
        "rule_id": "chapter3_d_spacing_to_two_theta",
        "status": two_theta_from_d_spacing(d_spacing, wavelength_angstrom=wavelength_angstrom)["status"],
        "input": {"d_spacing_angstrom": d_spacing, "wavelength_angstrom": wavelength_angstrom},
        "output": {"two_theta_deg": two_theta_from_d_spacing(d_spacing, wavelength_angstrom=wavelength_angstrom)["two_theta_deg"]},
        "explanation": "Uma janela mineralogica em Å e projetada no eixo 2θ por 2θ = 2 arcsen(λ/(2d)).",
    }
