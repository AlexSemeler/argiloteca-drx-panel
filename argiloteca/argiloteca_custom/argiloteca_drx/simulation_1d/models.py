# =============================================================================
# Projeto...........: Argiloteca - Painel de DRX
# Modulo............: models.py
#
# Descricao.........:
# Modelos de dados para simulacao 1D e comparacao observado/calculado.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Ultima atualizacao:
# 2026-06-30
#
# =============================================================================

"""Contratos de dados para simulacao 1D de DRX.

As classes deste modulo sao intencionalmente simples e serializaveis. Elas
registram parametros usados na geracao de padroes calculados e na comparacao
com curvas observadas, sem alterar regras mineralogicas ou o difratograma
carregado pelo usuario.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InstrumentModel:
    """Parametros instrumentais usados por um modelo 1D.

    Attributes:
        wavelength_angstrom: Comprimento de onda usado nas posicoes 2theta.
        radiation: Rotulo da radiacao, quando informado pelo experimento.
        divergence_slit: Fenda de divergencia, se houver perfil instrumental.
        receiving_slit: Fenda receptora, se houver perfil instrumental.
        goniometer_radius_mm: Raio do goniometro em milimetros.
        sample_length_mm: Comprimento da amostra exposta ao feixe.
        metadata: Campo livre para manter perfil, fonte e versao.
    """

    wavelength_angstrom: float | None = None
    radiation: str | None = None
    divergence_slit: str | None = None
    receiving_slit: str | None = None
    goniometer_radius_mm: float | None = None
    sample_length_mm: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LayerModel:
    """Modelo minimo de camada usado por padroes calculados.

    Attributes:
        name: Nome do mineral, componente ou camada.
        d001_angstrom: Espacamento basal de referencia.
        source: Proveniencia bibliografica ou catalogo interno.
        parameters: Parametros estruturais adicionais, como intercamada,
            Reichweite, proporcao de componentes ou tamanho de dominio.
    """

    name: str
    d001_angstrom: float | None = None
    source: dict[str, Any] | None = None
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SimulationRequest:
    """Entrada para simulacao ou comparacao 1D.

    Attributes:
        two_theta: Eixo 2theta que sera usado para calcular ou comparar curvas.
        observed_intensity: Intensidade observada, quando houver comparacao.
        instrument: Parametros instrumentais associados ao padrao.
        layer_model: Modelo mineralogico/estrutural selecionado.
        metadata: Metadados do painel, preparo e proveniencia.
    """

    two_theta: list[float]
    observed_intensity: list[float] | None = None
    instrument: InstrumentModel = field(default_factory=InstrumentModel)
    layer_model: LayerModel | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PatternComparison:
    """Resumo de residuos entre padrao observado e calculado.

    Attributes:
        residual_count: Numero de pontos comparados.
        mean_abs_error: Erro absoluto medio.
        max_abs_error: Maior erro absoluto observado.
        status: `valid`, `insufficient_data` ou `shape_mismatch`.
        warnings: Avisos sobre tamanho, dados ausentes ou comparacao limitada.
    """

    residual_count: int
    mean_abs_error: float | None
    max_abs_error: float | None
    status: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serializa o resumo para JSON/API."""
        return {
            "residual_count": self.residual_count,
            "mean_abs_error": self.mean_abs_error,
            "max_abs_error": self.max_abs_error,
            "status": self.status,
            "warnings": list(self.warnings),
        }
