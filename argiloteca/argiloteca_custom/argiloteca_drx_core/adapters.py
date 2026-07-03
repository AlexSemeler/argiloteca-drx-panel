"""Adaptadores puros para contratos internos do pipeline DRX.

Este modulo converte payloads ja existentes no Painel DRX da Argiloteca para
os modelos de contrato definidos em :mod:`argiloteca_drx_core.models`.
Adaptadores nao executam regras mineralogicas, nao calculam d-spacing, nao
assumem comprimento de onda e nao acessam Flask, InvenioRDM ou bibliotecas
cientificas externas. Eles servem apenas para reduzir acoplamento entre API,
servicos e visualizacao em refatoracoes futuras.
"""

from __future__ import annotations

from typing import Any

from .models import (
    Diffractogram,
    Evidence,
    MineralHypothesis,
    NgcComparison,
    Peak,
    Sample,
    Treatment,
    XrdFile,
    safe_float,
)


JsonDict = dict[str, Any]


def _as_dict(value: Any) -> JsonDict:
    """Retorna ``value`` quando for dicionario ou um dicionario vazio."""

    return value if isinstance(value, dict) else {}


def _metadata(payload: JsonDict) -> JsonDict:
    """Extrai metadados como dicionario sem assumir estrutura externa."""

    return _as_dict(_as_dict(payload).get("metadata"))


def _visualization_metadata(payload: JsonDict) -> JsonDict:
    """Extrai ``metadata.visualization`` quando existir."""

    return _as_dict(_metadata(payload).get("visualization"))


def _first_value(*values: Any) -> Any:
    """Retorna o primeiro valor presente, preservando zero e string vazia."""

    for value in values:
        if value is not None:
            return value
    return None


def _first_key(payload: JsonDict, keys: tuple[str, ...] | list[str]) -> Any:
    """Busca a primeira chave existente em um payload."""

    for key in keys:
        if key in payload:
            return payload.get(key)
    return None


def _string_or_none(value: Any) -> str | None:
    """Normaliza valores textuais opcionais."""

    if value is None:
        return None
    return str(value)


def _list_or_empty(value: Any) -> list[Any]:
    """Converte listas/tuplas em lista e rejeita escalares."""

    if isinstance(value, (list, tuple)):
        return list(value)
    return []


def _dict_list(value: Any) -> list[JsonDict]:
    """Filtra apenas dicionarios de uma sequencia."""

    return [row for row in _list_or_empty(value) if isinstance(row, dict)]


def _normalize_treatment(value: Any) -> tuple[str | None, str | None]:
    """Mapeia nomes comuns de preparo N/G/C para codigo e rotulo canonicos."""

    if value is None:
        return None, None
    raw = str(value).strip()
    normalized = raw.lower()
    aliases = {
        "n": ("N", "natural"),
        "natural": ("N", "natural"),
        "normal": ("N", "natural"),
        "g": ("G", "glycolated"),
        "glicolado": ("G", "glycolated"),
        "glicolada": ("G", "glycolated"),
        "glycolated": ("G", "glycolated"),
        "glycol": ("G", "glycolated"),
        "c": ("C", "calcined"),
        "calcinado": ("C", "calcined"),
        "calcinada": ("C", "calcined"),
        "calcined": ("C", "calcined"),
        "heated": ("C", "calcined"),
    }
    return aliases.get(normalized, (None, raw or None))


def treatment_from_payload(payload: JsonDict) -> Treatment:
    """Converte preparo experimental de payload heterogeneo para contrato.

    O adaptador usa somente valores explicitos. A inferencia registra se o
    campo veio da raiz do payload, de ``metadata`` ou se estava ausente.
    """

    payload = _as_dict(payload)
    metadata = _metadata(payload)
    root_value = _first_key(payload, ("treatment", "preparation", "treatment_label", "preparation_label"))
    metadata_value = _first_key(metadata, ("treatment", "preparation"))
    value = _first_value(root_value, metadata_value)
    code, label = _normalize_treatment(value)
    if root_value is not None:
        inference = "payload"
    elif metadata_value is not None:
        inference = "metadata"
    else:
        inference = "unknown"
    return Treatment(code=code, label=label, inference=inference)


def sample_from_payload(payload: JsonDict) -> Sample:
    """Converte identificadores explicitos de amostra para ``Sample``."""

    payload = _as_dict(payload)
    metadata = _metadata(payload)
    return Sample(
        sample_id=_string_or_none(_first_value(payload.get("sample_id"), metadata.get("sample_id"))),
        sample_base=_string_or_none(
            _first_value(payload.get("sample_base"), payload.get("sample_code"), metadata.get("sample_base"), metadata.get("sample_code"))
        ),
        record_id=_string_or_none(_first_value(payload.get("record_id"), metadata.get("record_id"))),
        title=_string_or_none(_first_value(payload.get("title"), metadata.get("title"))),
    )


def xrd_file_from_payload(payload: JsonDict) -> XrdFile:
    """Converte metadados de arquivo DRX para ``XrdFile``."""

    payload = _as_dict(payload)
    metadata = _metadata(payload)
    filename = _first_value(
        payload.get("filename"),
        payload.get("original_filename"),
        metadata.get("filename"),
        metadata.get("original_filename"),
        payload.get("id"),
        metadata.get("id"),
    )
    return XrdFile(
        filename=str(filename or ""),
        file_id=_string_or_none(_first_value(payload.get("file_id"), payload.get("id"), metadata.get("file_id"), metadata.get("id"))),
        sha256=_string_or_none(
            _first_value(payload.get("sha256"), payload.get("source_sha256"), metadata.get("sha256"), metadata.get("source_sha256"))
        ),
        format=_string_or_none(
            _first_value(payload.get("format"), payload.get("detected_format"), metadata.get("format"), metadata.get("detected_format"))
        ),
        source=_string_or_none(_first_value(payload.get("source"), metadata.get("source"))),
    )


def peak_from_payload(payload: JsonDict) -> Peak:
    """Converte um pico de payload legado para o contrato ``Peak``."""

    payload = _as_dict(payload)
    return Peak(
        peak_id=_first_value(payload.get("peak_id"), payload.get("peak_index"), payload.get("index")),
        two_theta_deg=safe_float(
            _first_value(
                payload.get("two_theta"),
                payload.get("twoTheta"),
                payload.get("center_2theta"),
                payload.get("observed_two_theta"),
                payload.get("position_two_theta_deg"),
            )
        ),
        d_angstrom=safe_float(
            _first_value(payload.get("d"), payload.get("d_spacing"), payload.get("d_angstrom"), payload.get("center_d_angstrom"))
        ),
        intensity=safe_float(_first_value(payload.get("intensity"), payload.get("intensity_abs"))),
        relative_intensity=safe_float(_first_value(payload.get("relative_intensity"), payload.get("intensity_relative"))),
        fwhm_deg=safe_float(_first_value(payload.get("fwhm"), payload.get("fwhm_deg"))),
        area=safe_float(_first_value(payload.get("area"), payload.get("integrated_intensity"))),
        source=_string_or_none(payload.get("source")),
        method=_string_or_none(_first_value(payload.get("detection_method"), payload.get("method"), payload.get("attribution_method"))),
    )


def peaks_from_payload(payload: JsonDict) -> list[Peak]:
    """Extrai a primeira lista de picos disponivel sem deduplicar."""

    payload = _as_dict(payload)
    metadata = _metadata(payload)
    candidates = (
        payload.get("peaks"),
        payload.get("advanced_peaks"),
        payload.get("detected_peaks"),
        payload.get("fit_results"),
        metadata.get("detected_peaks"),
        metadata.get("advanced_peaks"),
    )
    for rows in candidates:
        dict_rows = _dict_list(rows)
        if dict_rows:
            return [peak_from_payload(row) for row in dict_rows]
    return []


def diffractogram_from_payload(payload: JsonDict) -> Diffractogram:
    """Converte payload de curva para ``Diffractogram`` sem processar dados."""

    payload = _as_dict(payload)
    metadata = _metadata(payload)
    visualization = _visualization_metadata(payload)
    return Diffractogram(
        diffractogram_id=_string_or_none(_first_value(payload.get("diffractogram_id"), payload.get("id"))),
        two_theta=list(_list_or_empty(_first_value(payload.get("two_theta"), payload.get("twoTheta")))),
        intensity=list(_list_or_empty(payload.get("intensity"))),
        axis_mode=_string_or_none(_first_value(payload.get("axis_mode"), visualization.get("axis_mode"))),
        wavelength_angstrom=safe_float(
            _first_value(payload.get("wavelength_angstrom"), payload.get("wavelength_A"), payload.get("lambda"), metadata.get("wavelength_angstrom"))
        ),
        source_points=_first_value(payload.get("source_points"), visualization.get("source_points")),
        payload_points=_first_value(payload.get("payload_points"), visualization.get("payload_points")),
        metadata=dict(metadata),
    )


def evidence_from_payload(payload: JsonDict) -> Evidence:
    """Converte evidencia textual/estrutural para ``Evidence``."""

    payload = _as_dict(payload)
    limitations = _first_value(payload.get("limitations"), payload.get("warnings"))
    return Evidence(
        evidence_id=_string_or_none(_first_value(payload.get("evidence_id"), payload.get("id"))),
        kind=_string_or_none(_first_value(payload.get("kind"), payload.get("type"))),
        message=str(_first_value(payload.get("message"), payload.get("explanation"), "") or ""),
        observed=dict(_as_dict(payload.get("observed"))),
        source_rule=dict(_as_dict(_first_value(payload.get("source_rule"), payload.get("source")))),
        limitations=[str(row) for row in _list_or_empty(limitations)],
    )


def mineral_hypothesis_from_payload(payload: JsonDict) -> MineralHypothesis:
    """Converte candidato mineralogico para hipotese explicavel."""

    payload = _as_dict(payload)
    evidence_for = _first_value(payload.get("evidence_for"), payload.get("evidences"))
    source_rule = payload.get("source_rule")
    source_rules = _list_or_empty(payload.get("source_rules"))
    if source_rule is not None:
        source_rules.append(source_rule)
    return MineralHypothesis(
        mineral=str(_first_value(payload.get("mineral"), payload.get("label"), payload.get("target"), "") or ""),
        status=str(_first_value(payload.get("status"), payload.get("diagnostic_status"), "") or ""),
        confidence=_string_or_none(payload.get("confidence")),
        evidence_for=[evidence_from_payload(row) for row in _dict_list(evidence_for)],
        evidence_against=[evidence_from_payload(row) for row in _dict_list(payload.get("evidence_against"))],
        limitations=[str(row) for row in _list_or_empty(_first_value(payload.get("limitations"), payload.get("warnings")))],
        source_rules=[dict(_as_dict(row)) for row in source_rules if isinstance(row, dict)],
        requires_specialist_validation=bool(payload.get("requires_specialist_validation", True)),
    )


def ngc_comparison_from_payload(payload: JsonDict) -> NgcComparison:
    """Converte resultado N/G/C existente para contrato estrutural."""

    payload = _as_dict(payload)
    hypotheses = _first_value(payload.get("hypotheses"), payload.get("candidates"), payload.get("combined_candidates"))
    return NgcComparison(
        sample_base=_string_or_none(payload.get("sample_base")),
        available_treatments=[str(row) for row in _list_or_empty(payload.get("available_treatments"))],
        basal_trajectories=[dict(row) for row in _dict_list(payload.get("basal_trajectories"))],
        evidence=[evidence_from_payload(row) for row in _dict_list(payload.get("evidence"))],
        hypotheses=[mineral_hypothesis_from_payload(row) for row in _dict_list(hypotheses)],
    )


__all__ = [
    "diffractogram_from_payload",
    "evidence_from_payload",
    "mineral_hypothesis_from_payload",
    "ngc_comparison_from_payload",
    "peak_from_payload",
    "peaks_from_payload",
    "sample_from_payload",
    "treatment_from_payload",
    "xrd_file_from_payload",
]
