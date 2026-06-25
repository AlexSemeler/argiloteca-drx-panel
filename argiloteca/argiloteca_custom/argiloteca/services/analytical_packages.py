"""
Projeto: Painel DRX Argiloteca

Descrição:
Lightweight analytical package manifests for high-volume record assets. O painel usa estes manifestos para consultar centenas ou milhares de RAWs DRX sem abrir cada arquivo no Invenio. As funcoes abaixo mantem o contrato JSON do painel, resolvem aliases de registros e calculam similaridade entre curvas.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br



Projeto:
Argiloteca / CPAA

Licença:
Preservar licença existente no repositório.

Última revisão:
2026-06-21

Observação:
Este arquivo integra o sistema de análise, comparação e interpretação de difratogramas de raios X para argilominerais.
"""

from __future__ import annotations

import json
import os
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .raw_snapshot_links import raw_snapshot_link_for_item


DEFAULT_INSTANCE_PATH = Path(os.environ.get("INVENIO_INSTANCE_PATH", "/Users/argilas/argilas/var/instance"))
DEFAULT_WORKSPACE_PATH = Path(__file__).resolve().parents[4]
ANALYTICAL_PACKAGES_DIR = Path(
    os.environ.get("ARGILOTECA_ANALYTICAL_PACKAGES_DIR", DEFAULT_INSTANCE_PATH / "argiloteca_analytical_packages")
)
STATIC_ANALYTICAL_PACKAGES_DIR = Path(__file__).resolve().parents[1] / "static" / "data" / "analytical_packages"
PACKAGE_ALIASES_PATH = Path(
    os.environ.get("ARGILOTECA_ANALYTICAL_PACKAGE_ALIASES", ANALYTICAL_PACKAGES_DIR / "aliases.json")
)
# Somente estas raizes sao aceitas para abrir RAWs locais; isso evita que uma
# entrada de manifesto aponte para caminhos arbitrarios do servidor.
SUPPORTED_RAW_ROOTS = (
    Path("/Users/visualizacao-drx/raw"),
    Path("/Users/argilas/argilas/povoamento/visualizacao-drx/raw"),
    Path("/Users/argilas/argilas/povoamento/visualizacao-drx/raw-classificados"),
    DEFAULT_WORKSPACE_PATH / "povoamento" / "visualizacao-drx" / "raw",
    DEFAULT_WORKSPACE_PATH / "povoamento" / "visualizacao-drx" / "raw-classificados",
    DEFAULT_WORKSPACE_PATH / "data" / "drx" / "raw",
    DEFAULT_WORKSPACE_PATH / "data" / "drx" / "raw-classificados",
    DEFAULT_INSTANCE_PATH / "argiloteca_drx_data" / "raw",
)
PUBLIC_RECORD_ID_RE = re.compile(r"^[a-z0-9]{5}-[a-z0-9]{5}$", re.IGNORECASE)
# Marcadores usados para remapear caminhos gravados em outra copia do workspace
# para a arvore local atual, preservando manifestos gerados em Mac/Linux.
WORKSPACE_PATH_MARKERS = (
    "povoamento/visualizacao-drx/raw-classificados/",
    "povoamento/visualizacao-drx/raw/",
    "povoamento/visualizacao-drx/saida_argiloteca_drx/",
)
WORKSPACE_PATH_MARKER_TARGETS = {
    "povoamento/visualizacao-drx/raw-classificados/": (
        DEFAULT_WORKSPACE_PATH / "povoamento" / "visualizacao-drx" / "raw-classificados",
        DEFAULT_WORKSPACE_PATH / "data" / "drx" / "raw-classificados",
    ),
    "povoamento/visualizacao-drx/raw/": (
        DEFAULT_WORKSPACE_PATH / "povoamento" / "visualizacao-drx" / "raw",
        DEFAULT_WORKSPACE_PATH / "data" / "drx" / "raw",
    ),
    "povoamento/visualizacao-drx/saida_argiloteca_drx/": (
        DEFAULT_WORKSPACE_PATH / "povoamento" / "visualizacao-drx" / "saida_argiloteca_drx",
        DEFAULT_WORKSPACE_PATH / "data" / "drx" / "saida_argiloteca_drx",
    ),
}


def manifest_path(record_id: str, analysis_type: str = "drx") -> Path:
    """Return the manifest path for one record and analysis type."""
    safe_record_id = "".join(char for char in str(record_id) if char.isalnum() or char in "-_")
    safe_analysis_type = "".join(char for char in str(analysis_type) if char.isalnum() or char in "-_")
    return ANALYTICAL_PACKAGES_DIR / safe_record_id / f"{safe_analysis_type}_manifest.json"


def _load_aliases() -> dict:
    """Load optional public-record to package-record aliases."""
    try:
        with PACKAGE_ALIASES_PATH.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}
    if isinstance(payload, dict) and isinstance(payload.get("aliases"), dict):
        return payload["aliases"]
    return payload if isinstance(payload, dict) else {}


def resolve_package_record_id(record_id: str, analysis_type: str = "drx") -> tuple[str, str | None]:
    """Resolve a record id to the record id that owns the analytical package."""
    requested_id = str(record_id or "")
    if manifest_path(requested_id, analysis_type).exists():
        return requested_id, None
    aliases = _load_aliases()
    target = aliases.get(requested_id)
    if isinstance(target, dict):
        target = target.get(analysis_type) or target.get("default") or target.get("record_id")
    if target and manifest_path(str(target), analysis_type).exists():
        return str(target), requested_id
    return requested_id, None


def _package_manifest_exists(record_id: str, analysis_type: str = "drx") -> bool:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        record_id: Valor de entrada consumido por esta etapa do fluxo.
        analysis_type: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return (
        manifest_path(record_id, analysis_type).exists()
        or (STATIC_ANALYTICAL_PACKAGES_DIR / str(record_id) / f"{analysis_type}_manifest.json").exists()
    )


def _public_record_id_for_package(record_id: str, analysis_type: str = "drx") -> str:
    """Return the public record PID for a package id when aliases/truncated ids exist."""
    package_id = str(record_id or "").strip()
    aliases = _load_aliases()
    for public_id, target in aliases.items():
        resolved = target
        if isinstance(target, dict):
            resolved = target.get(analysis_type) or target.get("default") or target.get("record_id")
        if str(resolved or "") == package_id:
            return str(public_id)
    try:
        suffix = package_id.split("-", 1)[1]
    except IndexError:
        suffix = ""
    if suffix and len(suffix) < 5:
        candidates = [
            candidate
            for candidate in _iter_package_manifest_record_ids(analysis_type)
            if candidate != package_id and candidate.startswith(package_id) and len(candidate) > len(package_id)
        ]
        if candidates:
            return sorted(candidates, key=len)[0]
    return package_id


def _safe_text(value) -> str:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return str(value or "").strip()


def _record_to_dict(result) -> dict:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        result: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if isinstance(result, dict):
        return result
    return dict(result or {})


def _read_record(record_id: str) -> dict | None:
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        record_id: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    try:
        from invenio_access.permissions import system_identity
        from invenio_rdm_records.proxies import current_rdm_records_service

        return _record_to_dict(current_rdm_records_service.read(system_identity, record_id))
    except Exception:
        return None


def _record_file_entries(record: dict) -> dict:
    """Normalize Invenio file entries to a key-indexed mapping."""
    entries = ((record.get("files") or {}).get("entries") or {})
    if isinstance(entries, dict):
        normalized = {}
        for key, value in entries.items():
            item = value if isinstance(value, dict) else {}
            item = {**item, "key": item.get("key") or key}
            normalized[item["key"]] = item
        return normalized
    if isinstance(entries, list):
        return {
            item.get("key"): item
            for item in entries
            if isinstance(item, dict) and item.get("key")
        }
    return {}


def _is_raw_filename(value: str | None) -> bool:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return _safe_text(value).lower().endswith(".raw")


def _is_drx_method(value: str | None) -> bool:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    normalized = _safe_text(value).lower()
    return normalized in {"drx", "xrd", "difracao_raios_x", "difração de raios x"}


def _infer_preparation(sample_code: str | None, filename: str | None) -> dict:
    """Infer N/G/C preparation from sample or RAW filename when possible."""
    try:
        from .drx import infer_diffractogram_treatment

        return infer_diffractogram_treatment(sample_code or "", filename or "")
    except Exception:
        return {
            "type": "indeterminado",
            "label": "Indeterminado",
            "evidence": "Preparo nao inferido pelo nome do arquivo.",
        }


def _sample_contexts(record: dict) -> dict:
    """Extract sample metadata that should travel with each package item."""
    contexts = {}
    for sample in ((record.get("custom_fields") or {}).get("arg:amostras") or []):
        if not isinstance(sample, dict):
            continue
        code = _safe_text(sample.get("codigo_amostra"))
        if not code:
            continue
        contexts[code] = {
            "sample_code": code,
            "locality": _safe_text(sample.get("local_coleta")),
            "geological_context": _safe_text(sample.get("contexto_geologico")),
            "latitude": sample.get("latitude"),
            "longitude": sample.get("longitude"),
            "campaign_id": _safe_text(sample.get("campanha_id")),
        }
    return contexts


def _build_record_upload_manifest(record_id: str, analysis_type: str = "drx") -> dict | None:
    """Build a transient DRX manifest from files already attached to a record."""
    if analysis_type != "drx":
        return None
    record = _read_record(record_id)
    if not record:
        return None

    custom_fields = record.get("custom_fields") or {}
    analyses = custom_fields.get("arg:analises") or []
    file_entries = _record_file_entries(record)
    samples = _sample_contexts(record)
    items = []
    for index, analysis in enumerate(analyses):
        if not isinstance(analysis, dict) or not _is_drx_method(analysis.get("metodo")):
            continue
        file_key = _safe_text(analysis.get("arquivo_resultado"))
        if not _is_raw_filename(file_key):
            continue
        file_entry = file_entries.get(file_key, {})
        sample_code = _safe_text(analysis.get("codigo_amostra")) or Path(file_key).stem
        preparation = _infer_preparation(sample_code, file_key)
        sample_context = samples.get(sample_code) or {}
        item = {
            "id": f"{record_id}:upload:{index}",
            "record_id": record_id,
            "sample_code": sample_code,
            "sample_base": Path(file_key).stem,
            "filename": file_key,
            "file_key": file_key,
            "raw_path": None,
            "sha256": _safe_text(file_entry.get("checksum")),
            "size_bytes": file_entry.get("size") or file_entry.get("size_bytes") or 0,
            "status": "vinculado_no_registro",
            "preparation": preparation.get("type") or "indeterminado",
            "preparation_label": preparation.get("label") or "Indeterminado",
            "preparation_evidence": preparation.get("evidence") or "Inferido do nome do arquivo.",
            "metadata": {
                "source": "invenio_record_file",
                "analysis_id": _safe_text(analysis.get("analise_id")),
                "analysis_date": _safe_text(analysis.get("data_analise")),
                "result_file": file_key,
            },
            "sample": sample_context,
            "analyses": [
                {
                    "analysis_id": _safe_text(analysis.get("analise_id")),
                    "sample_code": sample_code,
                    "method": _safe_text(analysis.get("metodo")),
                    "analysis_date": _safe_text(analysis.get("data_analise")),
                    "result_file": file_key,
                    "main_result": _safe_text(analysis.get("resultado_principal")),
                }
            ],
            "detected_peaks": [],
            "mineral_candidates": [],
        }
        items.append(item)

    if not items:
        return None

    by_preparation = Counter(item.get("preparation") or "indeterminado" for item in items)
    return {
        "record_id": record_id,
        "analysis_type": analysis_type,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "kind": "invenio_record_analyses",
            "record_id": record_id,
            "note": "Manifesto montado sob demanda a partir de arg:analises e arquivos do registro.",
        },
        "summary": {
            "total_files": len(items),
            "samples_count": len({item.get("sample_code") for item in items if item.get("sample_code")}),
            "total_size_bytes": sum(int(item.get("size_bytes") or 0) for item in items),
            "by_preparation": dict(sorted(by_preparation.items())),
            "top_minerals": [],
        },
        "items": items,
        "_requested_record_id": record_id,
        "_resolved_record_id": record_id,
        "_alias_from": None,
        "_manifest_path": None,
    }


def load_manifest(record_id: str, analysis_type: str = "drx") -> dict | None:
    """Load a package manifest if it exists."""
    resolved_record_id, alias_from = resolve_package_record_id(record_id, analysis_type)
    path = manifest_path(resolved_record_id, analysis_type)
    if not path.exists():
        static_path = STATIC_ANALYTICAL_PACKAGES_DIR / resolved_record_id / f"{analysis_type}_manifest.json"
        if static_path.exists():
            path = static_path
    try:
        with path.open("r", encoding="utf-8") as fp:
            manifest = json.load(fp)
    except FileNotFoundError:
        return _build_record_upload_manifest(record_id, analysis_type)
    manifest["_manifest_path"] = str(path)
    manifest["_requested_record_id"] = str(record_id or "")
    manifest["_resolved_record_id"] = resolved_record_id
    manifest["_alias_from"] = alias_from
    return manifest


def _matches_text(item: dict, query: str) -> bool:
    """
    Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
    
    Args:
        item: Valor de entrada consumido por esta etapa do fluxo.
        query: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not query:
        return True
    haystack = [
        item.get("sample_code"),
        item.get("sample_base"),
        item.get("filename"),
        item.get("preparation_label"),
        item.get("status"),
    ]
    for candidate in item.get("mineral_candidates") or []:
        haystack.extend([candidate.get("mineral"), candidate.get("group"), candidate.get("formula")])
    normalized = query.lower()
    return any(normalized in str(value or "").lower() for value in haystack)


def _matches_mineral(item: dict, mineral: str) -> bool:
    """
    Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
    
    Args:
        item: Valor de entrada consumido por esta etapa do fluxo.
        mineral: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not mineral:
        return True
    normalized = mineral.lower()
    return any(normalized in str(candidate.get("mineral") or "").lower() for candidate in item.get("mineral_candidates") or [])


def build_package_payload(
    record_id: str,
    analysis_type: str = "drx",
    *,
    limit: int = 100,
    offset: int = 0,
    preparation: str | None = None,
    mineral: str | None = None,
    query: str | None = None,
) -> dict:
    """Return a paginated, filterable analytical package payload."""
    manifest = load_manifest(record_id, analysis_type)
    if not manifest:
        return {
            "success": True,
            "exists": False,
            "record_id": record_id,
            "analysis_type": analysis_type,
            "summary": {},
            "items": [],
            "pagination": {"total": 0, "limit": limit, "offset": offset, "returned": 0},
            "message": "Nenhum pacote analitico foi encontrado para este registro.",
        }

    items = manifest.get("items") or []
    if preparation:
        items = [item for item in items if item.get("preparation") == preparation]
    if mineral:
        items = [item for item in items if _matches_mineral(item, mineral)]
    if query:
        items = [item for item in items if _matches_text(item, query)]

    total = len(items)
    limit = max(1, min(int(limit or 100), 500))
    offset = max(0, int(offset or 0))
    page = items[offset : offset + limit]

    return {
        "success": True,
        "exists": True,
        "record_id": record_id,
        "package_record_id": manifest.get("_resolved_record_id") or record_id,
        "package_alias_from": manifest.get("_alias_from"),
        "analysis_type": analysis_type,
        "summary": manifest.get("summary") or {},
        "source": manifest.get("source") or {},
        "generated_at": manifest.get("generated_at"),
        "manifest_path": manifest.get("_manifest_path"),
        "items": page,
        "pagination": {"total": total, "limit": limit, "offset": offset, "returned": len(page)},
    }


def _find_item(manifest: dict, *, sample_code: str | None = None, filename: str | None = None) -> dict | None:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        manifest: Valor de entrada consumido por esta etapa do fluxo.
        sample_code: Valor de entrada consumido por esta etapa do fluxo.
        filename: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    sample_key = str(sample_code or "").strip().lower()
    filename_key = Path(filename or "").name.lower()
    for item in manifest.get("items") or []:
        if sample_key and str(item.get("sample_code") or "").lower() == sample_key:
            return item
        if filename_key and Path(item.get("filename") or "").name.lower() == filename_key:
            return item
    return None


def _safe_raw_path(path: str | None) -> Path | None:
    """Resolve a RAW path only when it is inside one of the approved roots."""
    if not path:
        return None
    resolved = _remap_workspace_path(path).expanduser().resolve()
    for root in SUPPORTED_RAW_ROOTS:
        try:
            resolved.relative_to(root.resolve())
            return resolved
        except ValueError:
            continue
    return None


def _remap_workspace_path(path: str | None) -> Path:
    """Map historical workspace paths to the current checkout when possible."""
    candidate = Path(path or "").expanduser()
    if candidate.exists():
        return candidate

    text = str(path or "")
    for marker in WORKSPACE_PATH_MARKERS:
        if marker not in text:
            continue
        suffix = text.split(marker, 1)[1]
        for target_root in WORKSPACE_PATH_MARKER_TARGETS.get(marker, (DEFAULT_WORKSPACE_PATH / marker.rstrip("/"),)):
            remapped = target_root / suffix
            if remapped.exists():
                return remapped
    return candidate


def _parse_record_file_curve(record_id: str, file_key: str, max_points: int) -> tuple[dict, list[float], list[float], int]:
    """Read a RAW stored as an Invenio record file and decimate it for the UI."""
    from invenio_access.permissions import system_identity
    from invenio_rdm_records.proxies import current_rdm_records_service

    from .drx import decimate_series, parse_raw_bytes

    result = current_rdm_records_service.files.get_file_content(system_identity, record_id, file_key)
    with result.open_stream("rb") as stream:
        parsed = parse_raw_bytes(stream.read())
    two_theta, intensity = decimate_series(parsed.two_theta, parsed.intensity, max_points=max_points)
    return parsed.metadata, two_theta, intensity, len(parsed.two_theta)


def _load_advanced_curve(item: dict, max_points: int) -> dict:
    """Load a light advanced curve payload for report visualization, when available."""
    from .drx import decimate_series

    advanced_path = item.get("advanced_result_path")
    if not advanced_path:
        return {}
    path = _remap_workspace_path(advanced_path)
    if not path.exists():
        return {"available": False, "error": "Resultado avançado não encontrado."}
    try:
        with open(path, "r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except Exception as exc:
        return {"available": False, "error": f"Resultado avançado não pôde ser lido: {exc}"}
    curve = payload.get("curve") or {}
    two_theta = curve.get("two_theta") or []
    if not two_theta:
        return {
            "available": False,
            "error": "Resultado avançado sem curva 2θ.",
            "baseline_method": curve.get("baseline_method"),
            "normalization": curve.get("normalization"),
        }

    result = {
        "available": True,
        "baseline_method": curve.get("baseline_method"),
        "normalization": curve.get("normalization"),
        "points": len(two_theta),
    }
    result["two_theta"], _ = decimate_series(two_theta, two_theta, max_points=max_points)
    for key in ("intensity_raw", "intensity_filtered", "baseline", "intensity_corrected", "intensity_normalized"):
        values = curve.get(key) or []
        if len(values) == len(two_theta):
            _, result[key] = decimate_series(two_theta, values, max_points=max_points)
    return result


def _finite_float(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _median_step(axis: list[float]) -> float | None:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        axis: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    diffs = sorted(
        round(axis[index + 1] - axis[index], 8)
        for index in range(len(axis) - 1)
        if axis[index + 1] > axis[index]
    )
    if not diffs:
        return None
    return diffs[len(diffs) // 2]


def _common_two_theta_grid(
    left_two_theta: list[float],
    right_two_theta: list[float],
    max_points: int = 1200,
) -> list[float]:
    """Build the shared 2theta grid used before shape similarity scoring."""
    left = [value for value in (_finite_float(value) for value in left_two_theta or []) if value is not None]
    right = [value for value in (_finite_float(value) for value in right_two_theta or []) if value is not None]
    if not left or not right:
        return []
    start = max(min(left), min(right))
    end = min(max(left), max(right))
    if end <= start:
        return []
    left_step = _median_step(left)
    right_step = _median_step(right)
    candidates = [value for value in (left_step, right_step) if value and value > 0]
    step = max(candidates) if candidates else (end - start) / max_points
    step = max(float(step), (end - start) / max(max_points - 1, 1))
    points = int(math.floor((end - start) / step)) + 1
    return [round(start + index * step, 6) for index in range(max(0, points))]


def _resample_curve(two_theta: list[float], intensity: list[float], grid: list[float]) -> list[float]:
    """Linearly resample a curve onto a common 2theta grid."""
    pairs = []
    for theta_raw, value_raw in zip(two_theta or [], intensity or []):
        theta = _finite_float(theta_raw)
        value = _finite_float(value_raw)
        if theta is not None and value is not None:
            pairs.append((theta, value))
    pairs.sort()
    if not pairs or not grid:
        return []
    result = []
    cursor = 0
    for target in grid:
        if target <= pairs[0][0]:
            result.append(pairs[0][1])
            continue
        if target >= pairs[-1][0]:
            result.append(pairs[-1][1])
            continue
        while cursor < len(pairs) - 2 and pairs[cursor + 1][0] < target:
            cursor += 1
        left_theta, left_value = pairs[cursor]
        right_theta, right_value = pairs[cursor + 1]
        span = right_theta - left_theta
        if span <= 0:
            result.append(left_value)
            continue
        ratio = (target - left_theta) / span
        result.append(left_value + ratio * (right_value - left_value))
    return result


def _normalize_intensity(intensity: list[float]) -> list[float]:
    """Scale intensity to 0..1 so shape comparison ignores absolute counts."""
    values = [_finite_float(value) for value in intensity or []]
    finite = [value for value in values if value is not None]
    maximum = max(finite) if finite else 0.0
    if maximum <= 0:
        return [0.0 for _ in values]
    return [(value or 0.0) / maximum for value in values]


def _correlation_similarity(left: list[float], right: list[float]) -> float:
    """
    Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
    
    Args:
        left: Valor de entrada consumido por esta etapa do fluxo.
        right: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    pairs = []
    for left_raw, right_raw in zip(left or [], right or []):
        left_value = _finite_float(left_raw)
        right_value = _finite_float(right_raw)
        if left_value is not None and right_value is not None:
            pairs.append((left_value, right_value))
    if len(pairs) < 2:
        return 0.0
    left_mean = sum(left for left, _right in pairs) / len(pairs)
    right_mean = sum(right for _left, right in pairs) / len(pairs)
    numerator = sum((left - left_mean) * (right - right_mean) for left, right in pairs)
    left_den = math.sqrt(sum((left - left_mean) ** 2 for left, _right in pairs))
    right_den = math.sqrt(sum((right - right_mean) ** 2 for _left, right in pairs))
    if left_den <= 0 or right_den <= 0:
        return 0.0
    corr = numerator / (left_den * right_den)
    return round(max(0.0, min(1.0, (corr + 1.0) / 2.0)), 4)


def _euclidean_similarity(left: list[float], right: list[float]) -> float:
    """
    Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
    
    Args:
        left: Valor de entrada consumido por esta etapa do fluxo.
        right: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    pairs = []
    for left_raw, right_raw in zip(left or [], right or []):
        left_value = _finite_float(left_raw)
        right_value = _finite_float(right_raw)
        if left_value is not None and right_value is not None:
            pairs.append((left_value, right_value))
    if not pairs:
        return 0.0
    mse = sum((left - right) ** 2 for left, right in pairs) / len(pairs)
    return round(1.0 / (1.0 + math.sqrt(mse)), 4)


def _curve_shape_similarity(
    external_two_theta: list[float] | None,
    external_intensity: list[float] | None,
    package_two_theta: list[float] | None,
    package_intensity: list[float] | None,
) -> tuple[float, list[str]]:
    """Compare the full diffractogram shape without replacing peak evidence."""
    if not external_two_theta or not external_intensity or not package_two_theta or not package_intensity:
        return 0.0, []
    grid = _common_two_theta_grid(external_two_theta, package_two_theta)
    if len(grid) < 3:
        return 0.0, []
    external = _normalize_intensity(_resample_curve(external_two_theta, external_intensity, grid))
    package = _normalize_intensity(_resample_curve(package_two_theta, package_intensity, grid))
    if len(external) < 3 or len(package) < 3:
        return 0.0, []
    correlation = _correlation_similarity(external, package)
    euclidean = _euclidean_similarity(external, package)
    score = round((0.60 * correlation) + (0.40 * euclidean), 4)
    evidence = [
        "curva completa comparada: correlação %.2f; similaridade euclidiana %.2f"
        % (correlation, euclidean)
    ]
    return score, evidence


def _load_item_curve_for_similarity(
    item: dict,
    *,
    record_id: str,
    manifest: dict,
    max_points: int = 1200,
) -> tuple[list[float], list[float], str | None]:
    """Load the best available curve for comparing one package item.

    Prefer the classified RAW axis and advanced ALS curve when present, because
    package similarity should compare the same 2theta frame shown in the panel.
    """
    advanced = _load_advanced_curve(item, max_points=max_points)
    parsed = None
    try:
        from .drx import (
            align_compact_advanced_curve_to_classified_axis,
            align_raw_curve_for_classified_display,
            decimate_series,
            parse_raw_file,
        )

        raw_path = _safe_raw_path(item.get("raw_path"))
        if raw_path and raw_path.exists():
            parsed = parse_raw_file(raw_path)
            parsed = align_raw_curve_for_classified_display(
                parsed,
                filename=item.get("filename"),
                path=str(raw_path),
                sample_code=item.get("sample_code"),
            )
            advanced = align_compact_advanced_curve_to_classified_axis(
                advanced,
                parsed.two_theta,
                offset=parsed.metadata.get("two_theta_offset_applied"),
            )
            if advanced.get("available"):
                advanced_intensity = (
                    advanced.get("intensity_normalized")
                    or advanced.get("intensity_corrected")
                    or advanced.get("intensity_raw")
                    or []
                )
                if advanced.get("two_theta") and advanced_intensity:
                    return advanced.get("two_theta") or [], advanced_intensity, "curva avançada do pacote com eixo classificado"
            two_theta, intensity = decimate_series(parsed.two_theta, parsed.intensity, max_points=max_points)
            return two_theta, intensity, "arquivo RAW do pacote com eixo classificado"
    except Exception:
        parsed = None

    if advanced.get("available"):
        two_theta = advanced.get("two_theta") or []
        intensity = (
            advanced.get("intensity_normalized")
            or advanced.get("intensity_corrected")
            or advanced.get("intensity_raw")
            or []
        )
        if two_theta and intensity:
            return two_theta, intensity, "curva avançada do pacote"

    try:
        from .drx import decimate_series, parse_raw_file

        raw_path = _safe_raw_path(item.get("raw_path"))
        if raw_path and raw_path.exists():
            parsed = parse_raw_file(raw_path)
            two_theta, intensity = decimate_series(parsed.two_theta, parsed.intensity, max_points=max_points)
            return two_theta, intensity, "arquivo RAW do pacote"
    except Exception:
        pass

    if item.get("file_key"):
        try:
            _metadata, two_theta, intensity, _total_points = _parse_record_file_curve(
                manifest.get("_resolved_record_id") or record_id,
                item.get("file_key"),
                max_points,
            )
            return two_theta, intensity, "arquivo RAW do registro"
        except Exception:
            return [], [], None

    return [], [], None


def load_package_curve(
    record_id: str,
    *,
    analysis_type: str = "drx",
    sample_code: str | None = None,
    filename: str | None = None,
    max_points: int = 3000,
) -> dict | None:
    """Load one curve from a package manifest on demand."""
    manifest = load_manifest(record_id, analysis_type)
    if not manifest:
        return None
    item = _find_item(manifest, sample_code=sample_code, filename=filename)
    if not item:
        return None
    from .drx import (
        RawParseError,
        align_compact_advanced_curve_to_classified_axis,
        align_raw_curve_for_classified_display,
        decimate_series,
        parse_raw_file,
    )

    advanced_curve = None
    try:
        raw_path = _safe_raw_path(item.get("raw_path"))
        if raw_path and raw_path.exists():
            parsed = parse_raw_file(raw_path)
            parsed = align_raw_curve_for_classified_display(
                parsed,
                filename=item.get("filename"),
                path=str(raw_path),
                sample_code=item.get("sample_code"),
            )
            two_theta, intensity = decimate_series(parsed.two_theta, parsed.intensity, max_points=max_points)
            metadata = {
                **parsed.metadata,
                "source": "arquivo RAW do pacote com eixo classificado",
            }
            total_points = len(parsed.two_theta)
            advanced_curve = align_compact_advanced_curve_to_classified_axis(
                _load_advanced_curve(item, max_points=max_points),
                parsed.two_theta,
                offset=parsed.metadata.get("two_theta_offset_applied"),
            )
        elif item.get("file_key"):
            metadata, two_theta, intensity, total_points = _parse_record_file_curve(
                manifest.get("_resolved_record_id") or record_id,
                item.get("file_key"),
                max_points,
            )
        else:
            advanced_curve = _load_advanced_curve(item, max_points=max_points)
            two_theta = advanced_curve.get("two_theta") or []
            intensity = (
                advanced_curve.get("intensity_normalized")
                or advanced_curve.get("intensity_corrected")
                or advanced_curve.get("intensity_raw")
                or []
            )
            if not (advanced_curve.get("available") and two_theta and intensity):
                return {
                    "success": False,
                    "error": "Arquivo bruto nao encontrado ou fora das pastas autorizadas.",
                    "item": item,
                    "advanced_curve": advanced_curve,
                }
            metadata = {
                "source": "advanced_result",
                "original_filename": item.get("filename"),
                "sample_code": item.get("sample_code"),
            }
            total_points = advanced_curve.get("points") or len(two_theta)
    except RawParseError as exc:
        return {"success": False, "error": str(exc), "item": item}
    except Exception as exc:
        return {"success": False, "error": f"Arquivo do registro nao pode ser lido: {exc}", "item": item}

    return {
        "success": True,
        "record_id": record_id,
        "package_record_id": manifest.get("_resolved_record_id") or record_id,
        "package_alias_from": manifest.get("_alias_from"),
        "analysis_type": analysis_type,
        "sample_code": item.get("sample_code"),
        "filename": item.get("filename"),
        "item": item,
        "metadata": metadata,
        "advanced_curve": advanced_curve or _load_advanced_curve(item, max_points=max_points),
        "two_theta": two_theta,
        "intensity": intensity,
        "render_points": len(two_theta),
        "total_points": total_points,
    }


def _round_float(value, digits=6):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
        digits: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return round(value, digits)


def _metadata_similarity(left: dict, right: dict) -> tuple[float, list[str]]:
    """Score acquisition metadata that helps distinguish identical RAW files."""
    evidence = []
    score = 0.0
    total = 0.0
    checks = (
        ("two_theta_start", 0.02, "2theta inicial"),
        ("two_theta_end", 0.05, "2theta final"),
        ("step", 0.0005, "passo"),
    )
    for key, tolerance, label in checks:
        total += 1
        left_value = _round_float(left.get(key), 8)
        right_value = _round_float(right.get(key), 8)
        if left_value is None or right_value is None:
            continue
        if abs(left_value - right_value) <= tolerance:
            score += 1
            evidence.append(f"{label} compatível ({left_value:g})")
    total += 1
    left_points = left.get("points")
    right_points = right.get("points")
    try:
        left_points = int(left_points)
        right_points = int(right_points)
    except (TypeError, ValueError):
        left_points = right_points = None
    if left_points and right_points:
        diff = abs(left_points - right_points)
        if diff == 0:
            score += 1
            evidence.append(f"mesmo número de pontos ({left_points})")
        elif diff / max(left_points, right_points) <= 0.02:
            score += 0.75
            evidence.append(f"número de pontos muito próximo ({left_points} x {right_points})")
    return (score / total if total else 0.0), evidence


def _relative_delta(left, right) -> float | None:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        left: Valor de entrada consumido por esta etapa do fluxo.
        right: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    left = _round_float(left, 8)
    right = _round_float(right, 8)
    if left is None or right is None:
        return None
    scale = max(abs(left), abs(right), 1.0)
    return abs(left - right) / scale


def _peak_value(peak: dict, *keys):
    """
    Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
    
    Args:
        peak: Valor de entrada consumido por esta etapa do fluxo.
        *keys: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    for key in keys:
        value = _round_float(peak.get(key), 8)
        if value is not None:
            return value
    return None


def _peak_width(peak: dict) -> float | None:
    """
    Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
    
    Args:
        peak: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return _peak_value(peak, "fwhm", "width_estimate", "width", "peak_width")


def _peak_d_spacing(peak: dict) -> float | None:
    """
    Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
    
    Args:
        peak: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return _peak_value(peak, "d", "d_spacing", "d_angstrom", "center_d_angstrom")


def _enrich_peak_with_fit(peak: dict, fit_by_index: dict[int, dict]) -> dict:
    """Attach advanced fit/FWHM fields to a peak when the index matches."""
    result = dict(peak or {})
    peak_index = result.get("peak_index") or result.get("index")
    try:
        fit = fit_by_index.get(int(peak_index))
    except (TypeError, ValueError):
        fit = None
    if fit:
        result.setdefault("fwhm", fit.get("fwhm"))
        result.setdefault("center_2theta", fit.get("center_2theta"))
        result.setdefault("center_d_angstrom", fit.get("center_d_angstrom"))
        result.setdefault("fit_quality", fit.get("fit_quality"))
        result.setdefault("model_name", fit.get("model_name"))
        result.setdefault("fit_method", fit.get("fit_method") or fit.get("method"))
    return result


def _fwhm_weight(*peaks: dict) -> tuple[float, str]:
    """Choose how much FWHM should influence a peak match."""
    text = " ".join(
        str(value or "").lower()
        for peak in peaks
        for value in (peak.get("fit_quality"), peak.get("model_name"), peak.get("fit_method"))
    )
    if any(marker in text for marker in ("low", "fallback", "failed", "measured_fallback")):
        return 0.05, "peso baixo por ajuste/FWHM pouco confiável"
    if any(marker in text for marker in ("medium", "measured")):
        return 0.10, "peso intermediário por ajuste moderado"
    return 0.15, "peso integral por ajuste sem alerta"


def _fit_by_peak_index(fit_results: list[dict]) -> dict[int, dict]:
    """
    Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
    
    Args:
        fit_results: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    lookup = {}
    for index, fit in enumerate(fit_results or [], start=1):
        peak_id = str(fit.get("peak_id") or "")
        number = None
        if ":" in peak_id:
            try:
                number = int(peak_id.rsplit(":", 1)[-1])
            except ValueError:
                number = None
        lookup[number or index] = fit
    return lookup


def _peak_similarity(
    external_peaks: list[dict],
    package_peaks: list[dict],
    package_fit_results: list[dict] | None = None,
) -> tuple[float, list[str], list[dict]]:
    """Compare diagnostic peak positions, d-spacings, intensities and FWHM."""
    fit_lookup = _fit_by_peak_index(package_fit_results or [])
    external_top = [
        peak
        for peak in (external_peaks or [])[:8]
        if _round_float(peak.get("two_theta"), 4) is not None or _peak_d_spacing(peak) is not None
    ]
    package_top = [
        _enrich_peak_with_fit(peak, fit_lookup)
        for peak in (package_peaks or [])[:12]
        if _round_float(peak.get("two_theta"), 4) is not None or _peak_d_spacing(peak) is not None
    ]
    if not external_top or not package_top:
        return 0.0, [], []
    matched = []
    used = set()
    for peak in external_top:
        two_theta = _round_float(peak.get("two_theta"), 4)
        best_index = None
        best_score = None
        best_details = None
        for index, candidate in enumerate(package_top):
            if index in used:
                continue
            candidate_two_theta = _round_float(candidate.get("two_theta"), 4)
            external_d = _peak_d_spacing(peak)
            candidate_d = _peak_d_spacing(candidate)
            delta_t = abs(two_theta - candidate_two_theta) if two_theta is not None and candidate_two_theta is not None else None
            delta_d = abs(external_d - candidate_d) if external_d is not None and candidate_d is not None else None
            position_scores = []
            if delta_t is not None and delta_t <= 0.15:
                position_scores.append(1.0 - (delta_t / 0.15))
            if delta_d is not None and delta_d <= 0.10:
                position_scores.append(1.0 - (delta_d / 0.10))
            if not position_scores:
                continue
            position_score = max(position_scores)
            external_intensity = _peak_value(peak, "relative_intensity", "intensity_relative")
            package_intensity = _peak_value(candidate, "relative_intensity", "intensity_relative")
            intensity_delta = _relative_delta(external_intensity, package_intensity)
            intensity_score = None if intensity_delta is None else max(0.0, 1.0 - min(intensity_delta / 0.50, 1.0))
            external_width = _peak_width(peak)
            package_width = _peak_width(candidate)
            width_delta = _relative_delta(external_width, package_width)
            width_score = None if width_delta is None else max(0.0, 1.0 - min(width_delta / 0.75, 1.0))
            width_weight, width_note = _fwhm_weight(peak, candidate)

            weighted_score = position_score * 0.60
            weight = 0.60
            if intensity_score is not None:
                weighted_score += intensity_score * 0.25
                weight += 0.25
            if width_score is not None:
                weighted_score += width_score * width_weight
                weight += width_weight
            score = weighted_score / weight
            if best_score is None or score > best_score:
                best_score = score
                best_index = index
                best_details = {
                    "delta_t": delta_t,
                    "delta_d": delta_d,
                    "position_score": position_score,
                    "intensity_delta": intensity_delta,
                    "intensity_score": intensity_score,
                    "width_delta": width_delta,
                    "width_score": width_score,
                    "width_weight": width_weight,
                    "width_note": width_note,
                    "score": score,
                }
        if best_index is not None:
            used.add(best_index)
            matched.append((peak, package_top[best_index], best_details or {}))
    evidence = []
    matched_payload = []
    for peak, candidate, details in matched[:4]:
        fragments = []
        peak_two_theta = _round_float(peak.get("two_theta"), 4)
        candidate_two_theta = _round_float(candidate.get("two_theta"), 4)
        if peak_two_theta is not None and candidate_two_theta is not None:
            fragments.append("2theta %.2f semelhante a %.2f" % (peak_two_theta, candidate_two_theta))
        peak_d = _peak_d_spacing(peak)
        candidate_d = _peak_d_spacing(candidate)
        if peak_d is not None and candidate_d is not None:
            fragments.append("d %.2f Å semelhante a %.2f Å" % (peak_d, candidate_d))
        row = "pico em " + "; ".join(fragments)
        if details.get("intensity_delta") is not None:
            row += "; intensidade relativa compatível (diferença %.0f%%)" % (details["intensity_delta"] * 100)
        if details.get("width_delta") is not None:
            row += "; largura/FWHM compatível (diferença %.0f%%; %s)" % (
                details["width_delta"] * 100,
                details.get("width_note") or "peso FWHM aplicado",
            )
        evidence.append(row)
        external_intensity = _peak_value(peak, "relative_intensity", "intensity_relative")
        package_intensity = _peak_value(candidate, "relative_intensity", "intensity_relative")
        external_width = _peak_width(peak)
        package_width = _peak_width(candidate)
        matched_payload.append(
            {
                "external_two_theta": peak_two_theta,
                "package_two_theta": candidate_two_theta,
                "delta_two_theta": round(details["delta_t"], 5) if details.get("delta_t") is not None else None,
                "external_d": peak_d,
                "package_d": candidate_d,
                "delta_d": round(details["delta_d"], 5) if details.get("delta_d") is not None else None,
                "external_relative_intensity": external_intensity,
                "package_relative_intensity": package_intensity,
                "relative_intensity_delta_percent": round(details["intensity_delta"] * 100, 2)
                if details.get("intensity_delta") is not None
                else None,
                "external_fwhm": external_width,
                "package_fwhm": package_width,
                "package_fit_quality": candidate.get("fit_quality"),
                "package_fit_model": candidate.get("model_name"),
                "fwhm_weight": details.get("width_weight"),
                "fwhm_weight_note": details.get("width_note"),
                "fwhm_delta_percent": round(details["width_delta"] * 100, 2)
                if details.get("width_delta") is not None
                else None,
                "score": round(details.get("score", 0.0), 4),
            }
        )
    if not matched:
        return 0.0, [], []
    average_quality = sum(item[2].get("score", 0.0) for item in matched) / len(matched)
    coverage = len(matched) / max(len(external_top), 1)
    return round(coverage * average_quality, 4), evidence, matched_payload


def _candidate_similarity(external_candidates: list[dict], package_candidates: list[dict]) -> tuple[float, list[str]]:
    """Score overlap between classifier mineral candidates."""
    external_names = {
        str(candidate.get("mineral") or "").strip().lower()
        for candidate in external_candidates or []
        if candidate.get("mineral")
    }
    package_names = {
        str(candidate.get("mineral") or "").strip().lower()
        for candidate in package_candidates or []
        if candidate.get("mineral")
    }
    if not external_names or not package_names:
        return 0.0, []
    overlap = sorted(external_names.intersection(package_names))
    evidence = [f"candidato mineralógico também aparece: {name.title()}" for name in overlap[:3]]
    return len(overlap) / max(len(external_names), 1), evidence


def _iter_package_manifest_record_ids(analysis_type: str = "drx") -> list[str]:
    """List package ids from dynamic and static manifest locations."""
    record_ids = set()
    for root in (ANALYTICAL_PACKAGES_DIR, STATIC_ANALYTICAL_PACKAGES_DIR):
        try:
            for path in root.glob(f"*/{analysis_type}_manifest.json"):
                if path.parent.name:
                    record_ids.add(path.parent.name)
        except Exception:
            continue
    return sorted(record_ids)


def _record_link_fields(record_id: str) -> dict:
    """Return public record/package URLs for a package id."""
    public_record_id = _public_record_id_for_package(record_id)
    record_url = f"/records/{public_record_id}" if PUBLIC_RECORD_ID_RE.match(public_record_id or "") else None
    package_url = f"/analises/{public_record_id}" if PUBLIC_RECORD_ID_RE.match(public_record_id or "") else None
    return {
        "record_id": public_record_id,
        "package_record_id": record_id,
        "record_url": record_url,
        "package_url": package_url,
    }


def _apply_raw_snapshot_link_to_match(match: dict, item: dict, raw_sha256: str | None = None) -> dict:
    """Prefer curated snapshot-to-record links when a global RAW match exists."""
    link = raw_snapshot_link_for_item(item, raw_sha256=raw_sha256)
    if not link:
        return match
    return {
        **match,
        "record_id": link.get("record_id"),
        "package_record_id": link.get("package_record_id") or link.get("record_id"),
        "record_url": link.get("record_url"),
        "package_url": link.get("package_url"),
        "source": "raw_snapshot_link",
        "raw_snapshot_link_path": link.get("raw_snapshot_link_path"),
        "evidence": (match.get("evidence") or []) + ["RAW do snapshot geral vinculado a registro por manifesto curatorial."],
    }


def _score_external_against_package_item(
    *,
    record_id: str,
    manifest: dict,
    item: dict,
    original_filename: str,
    raw_sha256: str | None,
    metadata: dict | None,
    two_theta: list[float] | None,
    intensity: list[float] | None,
    detected_peaks: list[dict] | None,
    mineral_candidates: list[dict] | None,
    load_curve: bool = True,
) -> dict:
    """Score one uploaded RAW against one package item using complementary evidence."""
    external_stem = Path(original_filename or "").stem.lower()
    item_filename = Path(item.get("filename") or "").name
    item_stem = Path(item_filename).stem.lower()
    evidence = []
    exact_match = False
    if raw_sha256 and item.get("sha256") == raw_sha256:
        exact_match = True
        evidence.append("hash SHA-256 idêntico ao arquivo do pacote")
    if external_stem and external_stem in {item_stem, str(item.get("sample_code") or "").lower()}:
        exact_match = True
        evidence.append("nome/código da amostra coincide com arquivo já indexado")

    metadata_score, metadata_evidence = _metadata_similarity(metadata or {}, item.get("metadata") or {})
    package_curve_source = None
    if load_curve:
        package_two_theta, package_intensity, package_curve_source = _load_item_curve_for_similarity(
            item,
            record_id=record_id,
            manifest=manifest,
        )
        curve_score, curve_evidence = _curve_shape_similarity(
            two_theta,
            intensity,
            package_two_theta,
            package_intensity,
        )
    else:
        curve_score, curve_evidence = 0.0, []
    if curve_evidence and package_curve_source:
        curve_evidence = [f"{curve_evidence[0]}; fonte: {package_curve_source}"]
    peak_score, peak_evidence, matched_peaks = _peak_similarity(
        detected_peaks or [],
        item.get("detected_peaks") or item.get("peaks") or [],
        item.get("fit_results") or [],
    )
    candidate_score, candidate_evidence = _candidate_similarity(mineral_candidates or [], item.get("mineral_candidates") or [])
    if curve_evidence:
        score = (metadata_score * 0.18) + (curve_score * 0.32) + (peak_score * 0.35) + (candidate_score * 0.15)
        score_components = {
            "metadata": round(metadata_score, 4),
            "curve": round(curve_score, 4),
            "peak": round(peak_score, 4),
            "candidate": round(candidate_score, 4),
        }
    else:
        score = (metadata_score * 0.25) + (peak_score * 0.55) + (candidate_score * 0.20)
        score_components = {
            "metadata": round(metadata_score, 4),
            "curve": None,
            "peak": round(peak_score, 4),
            "candidate": round(candidate_score, 4),
        }
    if exact_match:
        score = 1.0
    evidence.extend(metadata_evidence[:3])
    evidence.extend(curve_evidence[:2])
    evidence.extend(peak_evidence[:4])
    evidence.extend(candidate_evidence[:2])
    return {
        **_record_link_fields(record_id),
        "sample_code": item.get("sample_code"),
        "filename": item.get("filename"),
        "preparation": item.get("preparation"),
        "preparation_label": item.get("preparation_label"),
        "score": round(score, 4),
        "metadata_score": round(metadata_score, 4),
        "curve_score": round(curve_score, 4) if curve_evidence else None,
        "peak_score": round(peak_score, 4),
        "candidate_score": round(candidate_score, 4),
        "score_components": score_components,
        "matched_peaks": matched_peaks,
        "evidence": evidence[:8],
        "mineral_candidates": (item.get("mineral_candidates") or [])[:4],
        "detected_peaks": (item.get("detected_peaks") or [])[:6],
        "has_interpretation": bool(item.get("mineral_candidates") or item.get("detected_peaks")),
        "exact": exact_match,
        "source": "pacote_analitico",
    }


def _top_matches_by_record(matches: list[dict], limit: int = 5) -> list[dict]:
    """Return the strongest match for each public Argiloteca record."""
    grouped = {}
    for match in sorted(matches or [], key=lambda item: item.get("score", 0), reverse=True):
        record_id = match.get("record_id") or match.get("package_record_id")
        if not record_id or record_id in grouped:
            continue
        grouped[record_id] = match
        if len(grouped) >= max(1, limit):
            break
    return list(grouped.values())


def _compare_external_curve_to_all_packages(
    *,
    original_filename: str,
    raw_sha256: str | None,
    metadata: dict | None,
    two_theta: list[float] | None,
    intensity: list[float] | None,
    detected_peaks: list[dict] | None,
    mineral_candidates: list[dict] | None,
    analysis_type: str,
    limit: int,
) -> dict:
    """Scan all DRX packages for a likely existing RAW match."""
    results = []
    exact = []
    total_items_checked = 0
    record_ids = _iter_package_manifest_record_ids(analysis_type)
    for package_record_id in record_ids:
        manifest = load_manifest(package_record_id, analysis_type)
        if not manifest:
            continue
        items = manifest.get("items") or []
        total_items_checked += len(items)
        for item in items:
            match = _score_external_against_package_item(
                record_id=manifest.get("_resolved_record_id") or package_record_id,
                manifest=manifest,
                item=item,
                original_filename=original_filename,
                raw_sha256=raw_sha256,
                metadata=metadata,
                two_theta=two_theta,
                intensity=intensity,
                detected_peaks=detected_peaks,
                mineral_candidates=mineral_candidates,
                load_curve=False,
            )
            if match.get("exact"):
                exact.append(match)
            elif match.get("score", 0) >= 0.35:
                results.append(match)

    ranked_matches = sorted(exact + results, key=lambda item: item.get("score", 0), reverse=True)
    matches = (exact or ranked_matches)[: max(1, limit)]
    record_matches = _top_matches_by_record(ranked_matches, limit=max(1, limit))
    best = matches[0] if matches else None
    if best and best.get("exact"):
        status = "igual"
        message = "Este RAW já existe em um pacote analítico DRX da Argiloteca."
    elif best and best.get("score", 0) >= 0.62:
        status = "muito_parecido"
        message = "Foi encontrado um RAW muito parecido em pacote analítico DRX da Argiloteca."
    elif best:
        status = "parecido"
        message = "Foram encontrados RAWs parcialmente semelhantes em pacotes analíticos DRX da Argiloteca."
    else:
        status = "sem_semelhante_forte"
        message = "Nenhum RAW fortemente semelhante foi encontrado nos pacotes analíticos DRX da Argiloteca."
    return {
        "available": True,
        "record_id": best.get("record_id") if best else None,
        "source": "pacotes_analiticos_drx",
        "status": status,
        "message": message,
        "best_match": best,
        "matches": matches,
        "record_matches": record_matches,
        "total_items_checked": total_items_checked,
        "total_records_checked": len(record_ids),
    }


def compare_external_curve_to_package(
    record_id: str | None,
    *,
    original_filename: str,
    raw_sha256: str | None = None,
    metadata: dict | None = None,
    two_theta: list[float] | None = None,
    intensity: list[float] | None = None,
    detected_peaks: list[dict] | None = None,
    mineral_candidates: list[dict] | None = None,
    analysis_type: str = "drx",
    limit: int = 5,
    global_package_scan: bool = True,
) -> dict:
    """Compare one temporary external RAW curve with package/snapshot evidence.

    When no context record is supplied, the lookup first checks the module-wide
    RAW snapshot and then optionally scans all analytical packages. With a
    context record, the comparison stays inside that record package.
    """
    if not record_id:
        try:
            from .drx import list_raw_snapshot_items

            external_name = Path(original_filename or "").name.lower()
            external_stem = Path(original_filename or "").stem.lower()
            snapshot_payload = list_raw_snapshot_items(
                filters={"q": external_stem or external_name},
                limit=200,
                offset=0,
            )
            snapshot_items = snapshot_payload.get("items") or []
            matches = []
            for item in snapshot_items:
                item_filename = Path(item.get("filename") or item.get("original_filename") or "").name
                item_stem = Path(item_filename).stem.lower()
                sample_code = str(item.get("sample_code") or "").lower()
                exact_match = bool(
                    external_name
                    and (
                        external_name == item_filename.lower()
                        or external_stem in {item_stem, sample_code}
                    )
                )
                if not exact_match:
                    continue
                match = {
                    "sample_code": item.get("sample_code"),
                    "filename": item.get("filename"),
                    "preparation": item.get("preparation"),
                    "preparation_label": item.get("preparation_label"),
                    "score": 1.0,
                    "metadata_score": 1.0,
                    "curve_score": None,
                    "peak_score": None,
                    "candidate_score": None,
                    "score_components": {
                        "metadata": 1.0,
                        "curve": None,
                        "peak": None,
                        "candidate": None,
                    },
                    "matched_peaks": [],
                    "evidence": ["nome/código da amostra coincide com RAW do snapshot geral"],
                    "mineral_candidates": (item.get("mineral_candidates") or [])[:4],
                    "detected_peaks": (item.get("detected_peaks") or item.get("peaks") or [])[:6],
                    "has_interpretation": bool(item.get("mineral_candidates") or item.get("detected_peaks") or item.get("peaks")),
                    "exact": True,
                    "source": "snapshot_geral_raw",
                    "diffractogram_id": item.get("diffractogram_id") or item.get("id"),
                }
                matches.append(_apply_raw_snapshot_link_to_match(match, item, raw_sha256))
            if matches:
                linked_matches = [match for match in matches if match.get("record_id")]
                if global_package_scan:
                    package_match = _compare_external_curve_to_all_packages(
                        original_filename=original_filename,
                        raw_sha256=raw_sha256,
                        metadata=metadata,
                        two_theta=two_theta,
                        intensity=intensity,
                        detected_peaks=detected_peaks,
                        mineral_candidates=mineral_candidates,
                        analysis_type=analysis_type,
                        limit=limit,
                    )
                    if package_match.get("best_match"):
                        return package_match
                if linked_matches:
                    best_linked = linked_matches[0]
                    return {
                        "available": True,
                        "record_id": best_linked.get("record_id"),
                        "source": "raw_snapshot_link",
                        "status": "igual",
                        "message": "Este RAW já existe no snapshot geral e está vinculado a um registro da Argiloteca.",
                        "best_match": best_linked,
                        "matches": linked_matches[: max(1, limit)],
                        "total_items_checked": len(snapshot_items),
                    }
                return {
                    "available": True,
                    "record_id": None,
                    "source": "snapshot_geral_raw",
                    "status": "igual",
                    "message": "Este RAW já existe no snapshot geral do módulo DRX da Argiloteca.",
                    "best_match": matches[0],
                    "matches": matches[: max(1, limit)],
                        "total_items_checked": len(snapshot_items),
                    }
            if not global_package_scan:
                return {
                    "available": True,
                    "record_id": None,
                    "source": "snapshot_geral_raw",
                    "status": "sem_varredura_global",
                    "message": "Comparação ampla com todos os pacotes DRX foi omitida para manter o upload temporário rápido.",
                    "best_match": None,
                    "matches": [],
                    "snapshot_items_checked": len(snapshot_items),
                    "global_package_scan": False,
                }
            package_match = _compare_external_curve_to_all_packages(
                original_filename=original_filename,
                raw_sha256=raw_sha256,
                metadata=metadata,
                two_theta=two_theta,
                intensity=intensity,
                detected_peaks=detected_peaks,
                mineral_candidates=mineral_candidates,
                analysis_type=analysis_type,
                limit=limit,
            )
            if package_match.get("best_match"):
                return package_match
            package_match["message"] = "Nenhum RAW com o mesmo nome foi encontrado no snapshot geral; nenhum semelhante forte apareceu nos pacotes analíticos DRX."
            package_match["snapshot_items_checked"] = len(snapshot_items)
            return package_match
        except Exception as exc:
            return {
                "available": False,
                "message": f"Não foi possível comparar com o snapshot geral do módulo DRX: {exc}",
            }
    manifest = load_manifest(record_id, analysis_type)
    if not manifest:
        return {"available": False, "record_id": record_id, "message": "Registro sem pacote analítico DRX indexado."}

    results = []
    exact = []
    for item in manifest.get("items") or []:
        match = _score_external_against_package_item(
            record_id=record_id,
            manifest=manifest,
            item=item,
            original_filename=original_filename,
            raw_sha256=raw_sha256,
            metadata=metadata,
            two_theta=two_theta,
            intensity=intensity,
            detected_peaks=detected_peaks,
            mineral_candidates=mineral_candidates,
        )
        if match.get("exact"):
            exact.append(match)
        elif match.get("score", 0) >= 0.35:
            results.append(match)

    matches = exact or sorted(results, key=lambda item: item.get("score", 0), reverse=True)[: max(1, limit)]
    best = matches[0] if matches else None
    if best and best.get("exact"):
        status = "igual"
        message = "Este RAW já existe no pacote analítico da Argiloteca e possui interpretação associada."
    elif best and best.get("score", 0) >= 0.62:
        status = "muito_parecido"
        message = "Foi encontrado um RAW muito parecido no pacote analítico do registro."
    elif best:
        status = "parecido"
        message = "Foram encontrados RAWs parcialmente semelhantes no pacote analítico do registro."
    else:
        status = "sem_semelhante_forte"
        message = "Nenhum RAW fortemente semelhante foi encontrado no pacote analítico do registro."

    return {
        "available": True,
        "record_id": record_id,
        "status": status,
        "message": message,
        "best_match": best,
        "matches": matches,
        "record_matches": _top_matches_by_record(matches, limit=max(1, limit)),
        "total_items_checked": len(manifest.get("items") or []),
    }
