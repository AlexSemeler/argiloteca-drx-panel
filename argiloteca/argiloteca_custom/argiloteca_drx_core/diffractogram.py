"""Modelo de difratograma para visualizacao e auditoria geometrica.

Este modulo define a classe `Diffractogram`, usada como representacao
canonica de uma curva 1D de DRX no nucleo reutilizavel da Argiloteca. A classe
nao interpreta mineralogia: ela valida eixo 2θ/intensidade, calcula dominios,
normaliza intensidade para exibicao, projeta o eixo d-spacing pela Lei de
Bragg e produz payloads compactos para o painel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from .curves import CU_K_ALPHA_WAVELENGTH, CurveData, normalize_max
from .geometry import bragg_from_two_theta


def _finite_float(value):
    """Converte valores numericos heterogeneos em float finito."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _round_or_none(value, digits=6):
    """Arredonda valores opcionais preservando `None`."""
    number = _finite_float(value)
    return round(number, digits) if number is not None else None


@dataclass
class Diffractogram:
    """Curva 1D de DRX preparada para visualizacao no Painel Argiloteca.

    A classe encapsula os dados essenciais de um difratograma medido em 2θ,
    preservando a separacao entre geometria e interpretacao mineralogica. O
    calculo de d-spacing segue o Capitulo 3: o angulo medido no eixo do
    difratograma e 2θ, enquanto a Lei de Bragg usa θ = 2θ/2.

    Attributes:
        two_theta:
            Eixo experimental em graus 2θ.
        intensity:
            Intensidade observada em contagens ou unidade relativa do arquivo.
        metadata:
            Metadados de origem, preparo, instrumento e processamento.
        wavelength_angstrom:
            Comprimento de onda usado nas conversoes de geometria.
        curve_id:
            Identificador opcional para relacionar a curva ao registro/painel.
    """

    two_theta: list[float]
    intensity: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)
    wavelength_angstrom: float = CU_K_ALPHA_WAVELENGTH
    curve_id: str | None = None

    @classmethod
    def from_curve_data(cls, curve: CurveData, **kwargs):
        """Cria um `Diffractogram` a partir do parser leve de curvas."""
        return cls(
            two_theta=list(curve.two_theta or []),
            intensity=list(curve.intensity or []),
            metadata=dict(curve.metadata or {}),
            **kwargs,
        )

    @classmethod
    def from_payload(cls, payload, **kwargs):
        """Cria uma curva a partir do contrato JSON usado pelo painel."""
        payload = payload or {}
        metadata = dict(payload.get("metadata") or {})
        metadata.update(kwargs.pop("metadata", {}) or {})
        return cls(
            two_theta=list(payload.get("two_theta") or []),
            intensity=list(payload.get("intensity") or []),
            metadata=metadata,
            **kwargs,
        )

    def cleaned_points(self):
        """Retorna pares 2θ/intensidade finitos, preservando a ordem original."""
        points = []
        for x_value, y_value in zip(self.two_theta or [], self.intensity or []):
            x_number = _finite_float(x_value)
            y_number = _finite_float(y_value)
            if x_number is None or y_number is None:
                continue
            points.append((x_number, y_number))
        return points

    def validation(self):
        """Valida se a curva e adequada para visualizacao quantitativa.

        Returns:
            dict:
                Status, contagem de pontos e avisos. Uma curva `valid` pode ser
                desenhada; uma curva `invalid` deve ser tratada como ausente ou
                incompleta pela interface.
        """
        points = self.cleaned_points()
        warnings = []
        if len(points) < 2:
            return {"status": "invalid", "points": len(points), "warnings": ["Curva sem pontos suficientes."]}
        if len(self.two_theta or []) != len(self.intensity or []):
            warnings.append("Eixo 2θ e intensidade possuem comprimentos diferentes; pontos excedentes foram ignorados.")
        if not all(points[index][0] <= points[index + 1][0] for index in range(len(points) - 1)):
            warnings.append("Eixo 2θ nao esta monotonicamente crescente; a visualizacao deve preservar ordem de arquivo.")
        if self.wavelength_angstrom <= 0:
            warnings.append("Comprimento de onda invalido; eixo d-spacing nao deve ser exibido.")
        return {"status": "valid", "points": len(points), "warnings": warnings}

    def x_domain(self):
        """Retorna o intervalo 2θ usado para enquadrar o grafico."""
        points = self.cleaned_points()
        if not points:
            return {"min": None, "max": None, "unit": "degree_2theta"}
        values = [point[0] for point in points]
        return {"min": round(min(values), 6), "max": round(max(values), 6), "unit": "degree_2theta"}

    def y_domain(self):
        """Retorna o intervalo de intensidade observado."""
        points = self.cleaned_points()
        if not points:
            return {"min": None, "max": None, "unit": "counts_or_relative"}
        values = [point[1] for point in points]
        return {"min": round(min(values), 6), "max": round(max(values), 6), "unit": "counts_or_relative"}

    def normalized_intensity(self):
        """Normaliza intensidade para escala 0-100 usada em sobreposicoes."""
        values = [point[1] for point in self.cleaned_points()]
        normalized, _maximum = normalize_max(values)
        return [round(value * 100.0, 6) for value in normalized]

    def d_spacing_axis(self, digits=6):
        """Calcula eixo d-spacing a partir de 2θ pela Lei de Bragg.

        Notes:
            Capitulo 3, Lei de Bragg: `d = λ / (2 sen θ)` com `θ = 2θ / 2`.
            O eixo d diminui quando 2θ aumenta; por isso ele deve ser exibido
            como eixo auxiliar, nao como substituto silencioso do eixo medido.
        """
        if self.wavelength_angstrom <= 0:
            return []
        return [
            _round_or_none(bragg_from_two_theta(point[0], self.wavelength_angstrom).d_spacing_angstrom, digits)
            for point in self.cleaned_points()
        ]

    def decimated(self, max_points=5000):
        """Reduz a curva para visualizacao mantendo amostragem regular."""
        points = self.cleaned_points()
        if max_points is None or max_points <= 0 or len(points) <= max_points:
            return points
        step = max(1, math.ceil(len(points) / max_points))
        return points[::step]

    def visualization_summary(self, rendered_points=None):
        """Resume a curva para cabecalho, tooltip e diagnostico visual."""
        validation = self.validation()
        source_points = validation["points"]
        rendered_count = source_points if rendered_points is None else int(rendered_points)
        axis_mode = "classified_or_aligned_axis" if self.metadata.get("two_theta_offset_applied") is not None else "loaded_axis"
        return {
            "curve_id": self.curve_id,
            "status": validation["status"],
            "points": rendered_count,
            "source_points": source_points,
            "rendered_points": rendered_count,
            "decimated": rendered_count < source_points,
            "axis_mode": axis_mode,
            "axis_reproduces_loaded_file": axis_mode == "loaded_axis",
            "axis_reproduces_classified_display": axis_mode == "classified_or_aligned_axis",
            "x_domain": self.x_domain(),
            "y_domain": self.y_domain(),
            "wavelength_angstrom": round(float(self.wavelength_angstrom), 6),
            "geometry_rule_id": "chapter3_two_theta_to_d_spacing",
            "geometry_explanation": "2θ e o eixo medido; d-spacing e calculado com θ = 2θ/2 pela Lei de Bragg.",
            "warnings": validation["warnings"],
        }

    def to_visualization_payload(self, max_points=5000, include_d_spacing=False, include_normalized=True):
        """Serializa a curva no formato consumido pelo painel de visualizacao."""
        points = self.decimated(max_points=max_points)
        two_theta = [round(point[0], 6) for point in points]
        intensity = [round(point[1], 6) for point in points]
        payload = {
            "metadata": {
                **dict(self.metadata or {}),
                "visualization": self.visualization_summary(rendered_points=len(points)),
            },
            "two_theta": two_theta,
            "intensity": intensity,
        }
        if include_normalized:
            normalized, _maximum = normalize_max(intensity)
            payload["intensity_normalized"] = [round(value * 100.0, 6) for value in normalized]
        if include_d_spacing:
            payload["d_spacing"] = [
                _round_or_none(bragg_from_two_theta(value, self.wavelength_angstrom).d_spacing_angstrom, 6)
                for value in two_theta
            ]
        return payload
