"""Modelos de contrato para o pipeline DRX da Argiloteca.

Este modulo define estruturas pequenas, serializaveis e independentes de
Flask, InvenioRDM, NumPy, SciPy ou pandas. Elas descrevem os dados que circulam
entre parser, preprocessamento, peak-picking, comparacao N/G/C, regras
mineralogicas e visualizacao, sem executar regras cientificas nem assumir
comprimento de onda.

Os modelos sao contratos internos: preservam valores ``None``, mantem lacunas
em arrays e geram dicionarios compativeis com JSON para uso futuro em API,
relatorios e metadados InvenioRDM.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any


JsonDict = dict[str, Any]


def safe_float(value: Any) -> float | None:
    """Converte um valor para ``float`` quando possivel.

    Args:
        value: Valor numerico ou textual recebido de parsers, payloads ou
            metadados.

    Returns:
        ``float`` quando a conversao for valida; caso contrario, ``None``.

    Notes:
        Esta funcao nao aplica regra cientifica e nao converte unidades. Ela
        apenas normaliza tipos para contratos JSON.
    """

    if value is None:
        return None
    try:
        number = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def dataclass_to_dict(value: Any) -> Any:
    """Serializa dataclasses aninhadas preservando ``None``.

    Args:
        value: Dataclass, lista, tupla, dicionario ou valor escalar.

    Returns:
        Estrutura composta por dicionarios, listas e escalares serializaveis.
    """

    if is_dataclass(value):
        return {key: dataclass_to_dict(row) for key, row in asdict(value).items()}
    if isinstance(value, dict):
        return {key: dataclass_to_dict(row) for key, row in value.items()}
    if isinstance(value, (list, tuple)):
        return [dataclass_to_dict(row) for row in value]
    return value


def list_dataclass_to_dict(values: list[Any] | tuple[Any, ...] | None) -> list[Any]:
    """Serializa uma lista de dataclasses ou valores escalares.

    Args:
        values: Sequencia opcional de objetos.

    Returns:
        Lista serializavel. Valores ``None`` de entrada viram lista vazia.
    """

    return [dataclass_to_dict(value) for value in (values or [])]


def validate_axis_lengths(two_theta: list[Any] | tuple[Any, ...] | None, intensity: list[Any] | tuple[Any, ...] | None) -> JsonDict:
    """Valida se os eixos ``2theta`` e intensidade possuem o mesmo tamanho.

    Args:
        two_theta: Sequencia do eixo angular 2theta.
        intensity: Sequencia de intensidades correspondente.

    Returns:
        Dicionario com ``valid``, contagens e mensagem. A funcao nao levanta
        excecao para arrays desalinhados para permitir que a API registre o
        problema sem interromper o carregamento.
    """

    two_theta_points = len(two_theta or [])
    intensity_points = len(intensity or [])
    valid = two_theta_points == intensity_points
    return {
        "valid": valid,
        "two_theta_points": two_theta_points,
        "intensity_points": intensity_points,
        "message": "Eixos alinhados." if valid else "Eixos 2theta e intensidade possuem tamanhos diferentes.",
    }


@dataclass
class Sample:
    """Representa a amostra cientifica vinculada a um ou mais difratogramas."""

    sample_id: str | None = None
    sample_base: str | None = None
    record_id: str | None = None
    title: str | None = None

    def to_dict(self) -> JsonDict:
        """Retorna representacao JSON do contrato da amostra."""

        return dataclass_to_dict(self)

    @classmethod
    def from_dict(cls, data: JsonDict | None) -> "Sample":
        """Cria ``Sample`` a partir de um dicionario."""

        data = data or {}
        return cls(
            sample_id=data.get("sample_id"),
            sample_base=data.get("sample_base"),
            record_id=data.get("record_id"),
            title=data.get("title"),
        )


@dataclass
class XrdFile:
    """Descreve o arquivo DRX de origem e sua proveniencia tecnica."""

    filename: str
    file_id: str | None = None
    sha256: str | None = None
    format: str | None = None
    source: str | None = None

    def to_dict(self) -> JsonDict:
        """Retorna representacao JSON do arquivo DRX."""

        return dataclass_to_dict(self)

    @classmethod
    def from_dict(cls, data: JsonDict | None) -> "XrdFile":
        """Cria ``XrdFile`` a partir de payload serializado."""

        data = data or {}
        return cls(
            filename=str(data.get("filename") or ""),
            file_id=data.get("file_id"),
            sha256=data.get("sha256"),
            format=data.get("format"),
            source=data.get("source"),
        )


@dataclass
class Treatment:
    """Registra o preparo experimental associado a um difratograma."""

    code: str | None = None
    label: str | None = None
    inference: str | None = None

    def to_dict(self) -> JsonDict:
        """Retorna representacao JSON do preparo."""

        return dataclass_to_dict(self)

    @classmethod
    def from_dict(cls, data: JsonDict | None) -> "Treatment":
        """Cria ``Treatment`` a partir de um dicionario."""

        data = data or {}
        return cls(code=data.get("code"), label=data.get("label"), inference=data.get("inference"))


@dataclass
class Peak:
    """Representa um pico observado ou calculado no difratograma.

    O campo ``d_angstrom`` e opcional e nao e calculado automaticamente. O
    preenchimento depende de comprimento de onda explicito e de uma etapa
    geometrica fora deste modulo.
    """

    peak_id: str | int | None = None
    two_theta_deg: float | None = None
    d_angstrom: float | None = None
    intensity: float | None = None
    relative_intensity: float | None = None
    fwhm_deg: float | None = None
    area: float | None = None
    source: str | None = None
    method: str | None = None

    def to_dict(self) -> JsonDict:
        """Retorna representacao JSON do pico."""

        return dataclass_to_dict(self)

    @classmethod
    def from_dict(cls, data: JsonDict | None) -> "Peak":
        """Cria ``Peak`` preservando campos ausentes como ``None``."""

        data = data or {}
        return cls(
            peak_id=data.get("peak_id"),
            two_theta_deg=safe_float(data.get("two_theta_deg")),
            d_angstrom=safe_float(data.get("d_angstrom")),
            intensity=safe_float(data.get("intensity")),
            relative_intensity=safe_float(data.get("relative_intensity")),
            fwhm_deg=safe_float(data.get("fwhm_deg")),
            area=safe_float(data.get("area")),
            source=data.get("source"),
            method=data.get("method"),
        )


@dataclass
class Diffractogram:
    """Contrato de curva DRX exibida ou analisada pelo painel.

    A classe preserva arrays com ``None`` para representar lacunas. Ela nao
    suaviza, normaliza, decima, converte eixo nem calcula d-spacing.
    """

    diffractogram_id: str | None = None
    two_theta: list[float | None] = field(default_factory=list)
    intensity: list[float | None] = field(default_factory=list)
    axis_mode: str | None = None
    wavelength_angstrom: float | None = None
    source_points: int | None = None
    payload_points: int | None = None
    metadata: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        """Retorna representacao JSON do difratograma."""

        return dataclass_to_dict(self)

    @classmethod
    def from_dict(cls, data: JsonDict | None) -> "Diffractogram":
        """Cria ``Diffractogram`` a partir de payload serializado."""

        data = data or {}
        return cls(
            diffractogram_id=data.get("diffractogram_id"),
            two_theta=list(data.get("two_theta") or []),
            intensity=list(data.get("intensity") or []),
            axis_mode=data.get("axis_mode"),
            wavelength_angstrom=safe_float(data.get("wavelength_angstrom")),
            source_points=data.get("source_points"),
            payload_points=data.get("payload_points"),
            metadata=dict(data.get("metadata") or {}),
        )

    def axis_validation(self) -> JsonDict:
        """Retorna validacao de tamanho dos arrays da curva."""

        return validate_axis_lengths(self.two_theta, self.intensity)


@dataclass
class Evidence:
    """Evidencia usada para sustentar ou limitar uma hipotese mineralogica."""

    message: str
    evidence_id: str | None = None
    kind: str | None = None
    observed: JsonDict = field(default_factory=dict)
    source_rule: JsonDict = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> JsonDict:
        """Retorna representacao JSON da evidencia."""

        return dataclass_to_dict(self)

    @classmethod
    def from_dict(cls, data: JsonDict | None) -> "Evidence":
        """Cria ``Evidence`` a partir de dicionario."""

        data = data or {}
        return cls(
            evidence_id=data.get("evidence_id"),
            kind=data.get("kind"),
            message=str(data.get("message") or ""),
            observed=dict(data.get("observed") or {}),
            source_rule=dict(data.get("source_rule") or {}),
            limitations=list(data.get("limitations") or []),
        )


@dataclass
class MineralHypothesis:
    """Hipotese mineralogica explicavel e nao confirmatoria.

    O status descreve o resultado assistido do workflow. A classe nao executa
    regras, nao calcula score e mantem a necessidade de validacao especializada
    como parte explicita do contrato.
    """

    mineral: str
    status: str
    confidence: str | None = None
    evidence_for: list[Evidence] = field(default_factory=list)
    evidence_against: list[Evidence] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    source_rules: list[JsonDict] = field(default_factory=list)
    requires_specialist_validation: bool = True

    def to_dict(self) -> JsonDict:
        """Retorna representacao JSON da hipotese mineralogica."""

        return dataclass_to_dict(self)

    @classmethod
    def from_dict(cls, data: JsonDict | None) -> "MineralHypothesis":
        """Cria ``MineralHypothesis`` com evidencias aninhadas."""

        data = data or {}
        return cls(
            mineral=str(data.get("mineral") or ""),
            status=str(data.get("status") or ""),
            confidence=data.get("confidence"),
            evidence_for=[Evidence.from_dict(row) for row in (data.get("evidence_for") or [])],
            evidence_against=[Evidence.from_dict(row) for row in (data.get("evidence_against") or [])],
            limitations=list(data.get("limitations") or []),
            source_rules=list(data.get("source_rules") or []),
            requires_specialist_validation=bool(data.get("requires_specialist_validation", True)),
        )


@dataclass
class NgcComparison:
    """Resultado estrutural de comparacao entre tratamentos N/G/C."""

    sample_base: str | None = None
    available_treatments: list[str] = field(default_factory=list)
    basal_trajectories: list[JsonDict] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    hypotheses: list[MineralHypothesis] = field(default_factory=list)

    def to_dict(self) -> JsonDict:
        """Retorna representacao JSON da comparacao N/G/C."""

        return dataclass_to_dict(self)

    @classmethod
    def from_dict(cls, data: JsonDict | None) -> "NgcComparison":
        """Cria ``NgcComparison`` com evidencias e hipoteses aninhadas."""

        data = data or {}
        return cls(
            sample_base=data.get("sample_base"),
            available_treatments=list(data.get("available_treatments") or []),
            basal_trajectories=list(data.get("basal_trajectories") or []),
            evidence=[Evidence.from_dict(row) for row in (data.get("evidence") or [])],
            hypotheses=[MineralHypothesis.from_dict(row) for row in (data.get("hypotheses") or [])],
        )


__all__ = [
    "Diffractogram",
    "Evidence",
    "MineralHypothesis",
    "NgcComparison",
    "Peak",
    "Sample",
    "Treatment",
    "XrdFile",
    "dataclass_to_dict",
    "list_dataclass_to_dict",
    "safe_float",
    "validate_axis_lengths",
]
