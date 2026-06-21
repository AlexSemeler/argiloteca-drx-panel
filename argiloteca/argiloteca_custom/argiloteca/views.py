"""
Projeto: Painel DRX Argiloteca

Descrição:
Rotas adicionais da Argiloteca para mapas, geoquimica e painel DRX. Este arquivo conecta templates e APIs Flask aos servicos cientificos. O foco e manter formatos JSON, rotas e atributos consumidos pelo frontend estaveis.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br

Colaboradores:
- Lucas Jantsch
- Arthur Oliveira

Instituição:
Universidade Federal do Rio Grande do Sul (UFRGS)

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
import csv
import hashlib
import os
import re
import sys
import time
import traceback
from pathlib import Path

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for

from .mineralogia import (
    build_authorized_mineral_catalog,
    build_mineral_profile,
    normalize_lookup_key,
    resolve_external_reference,
    resolve_mineral_group,
    resolve_mineral_name,
    resolve_short_description,
)

from .services.geoquimica import (
    build_aggregated_dataset,
    build_network,
    extract_subject_mineral_map,
    extract_subject_terms,
    find_record_detail,
    parse_float,
    record_title,
)
from .services.drx import (
    DiffractogramData,
    RawParseError,
    apply_two_theta_axis_alignment,
    calculate_quartz_axis_offset,
    decimate_series,
    infer_diffractogram_sample_base,
    infer_diffractogram_treatment,
    import_raw_path,
    import_raw_upload,
    build_raw_snapshot_comparison_suggestions,
    list_records_with_drx,
    list_raw_snapshot_items,
    load_diffractogram_data,
    parse_diffractogram_bytes,
    parse_raw_bytes,
    record_exists,
    record_import_error,
)
from .services.neural_evidence import neural_evidence_for_diffractogram
from .services.analytical_packages import (
    build_package_payload,
    compare_external_curve_to_package,
    load_manifest,
    load_package_curve,
    resolve_package_record_id,
)
from .services.drx_analysis import build_drx_analysis_run
from .services.drx_report import build_drx_technical_report, render_drx_technical_report_html
from .services.drx_references import compare_reference_pattern, parse_reference_pattern_bytes
from .services.drx_science_engine import science_engine_status
from .services.drx_reference_index import reference_pattern_from_index, search_reference_index
from .services.drx_external_jobs import get_external_job, list_external_jobs, submit_external_job
from .services.drx_cif_simulation import build_cif_simulation_payload
from .services.drx_ngc_workflow import build_ngc_workflow
from .services.drx_selection_report import build_drx_selection_report, render_drx_selection_report_html
from .services.drx_runs import get_drx_run, list_drx_runs, persist_drx_run


_ARGILO_API_CACHE = {}
_ARGILO_API_CACHE_TTL = 600
# Snapshots locais permitem abrir o painel em modo leve quando nao ha consulta
# dinamica ao Invenio; requests com filtros caem para os builders de servico.
_DEFAULT_APP_ROOT = Path(os.environ.get("APP_ROOT", Path(__file__).resolve().parents[2]))
_REPO_ROOT = _DEFAULT_APP_ROOT.parent
_INSTANCE_PATH = Path(os.environ.get("INVENIO_INSTANCE_PATH", _DEFAULT_APP_ROOT / "var" / "instance"))
_FALLBACK_INSTANCE_PATH = _REPO_ROOT / "var" / "instance"
_POINTS_SNAPSHOT_PATH = _INSTANCE_PATH / "argiloteca_points_snapshot.json"
_GEO_AGG_SNAPSHOT_PATH = _INSTANCE_PATH / "argiloteca_geoquimica_agregada_snapshot.json"
_GEO_NET_SNAPSHOT_PATH = _INSTANCE_PATH / "argiloteca_geoquimica_rede_snapshot.json"
_MINING_AREAS_PATH = _REPO_ROOT / "povoamento" / "outputs" / "argilominerais_areas_mineracao.json"
_MINING_GEOJSON_DIR = _REPO_ROOT / "povoamento" / "fontes_oficiais" / "sigmine_geojson"
_PUBLISH_REPORT_PATHS = (
    _REPO_ROOT / "extrator_pdfs_execucao" / "saida" / "publish_report.tsv",
    _REPO_ROOT / "povoamento" / "outputs" / "publish_report.tsv",
)
DRX_TEMP_UPLOAD_MAX_BYTES = int(os.environ.get("ARGILOTECA_DRX_TEMP_UPLOAD_MAX_BYTES", str(25 * 1024 * 1024)))
DRX_REFERENCE_UPLOAD_MAX_BYTES = int(os.environ.get("ARGILOTECA_DRX_REFERENCE_UPLOAD_MAX_BYTES", str(10 * 1024 * 1024)))


def _is_generic_record_title(title, record_id):
    """
    Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
    
    Args:
        title: Valor de entrada consumido por esta etapa do fluxo.
        record_id: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = str(title or "").strip()
    return not text or text == str(record_id or "").strip() or text.lower() == f"registro {record_id}".lower()


def _record_title_from_snapshots(record_ids):
    """Resolve titles from local snapshots before falling back to generic ids."""
    candidates = [str(value or "").strip() for value in record_ids if str(value or "").strip()]
    if not candidates:
        return None

    for geo_path in _snapshot_paths(_GEO_AGG_SNAPSHOT_PATH):
        geo_snapshot = _read_json_snapshot(geo_path)
        if isinstance(geo_snapshot, dict):
            for row in geo_snapshot.get("records") or []:
                if not isinstance(row, dict) or str(row.get("record_id") or "") not in candidates:
                    continue
                title = row.get("record_title")
                if title and not _is_generic_record_title(title, row.get("record_id")):
                    return str(title).strip()

    for points_path in _snapshot_paths(_POINTS_SNAPSHOT_PATH):
        points_snapshot = _read_json_snapshot(points_path)
        if isinstance(points_snapshot, dict):
            for point in points_snapshot.get("points") or []:
                if not isinstance(point, dict) or str(point.get("record_id") or "") not in candidates:
                    continue
                title = point.get("title")
                if title and not _is_generic_record_title(title, point.get("record_id")):
                    return str(title).strip()
    return None


def _package_record_id_for_context(record_id):
    """Resolve the package-owning id for DRX context pages and aliases."""
    try:
        package_record_id, _alias_from = resolve_package_record_id(record_id, "drx")
        if package_record_id and package_record_id != record_id:
            return package_record_id
    except Exception:
        pass

    for instance_path in (_INSTANCE_PATH, _FALLBACK_INSTANCE_PATH):
        aliases_path = instance_path / "argiloteca_analytical_packages" / "aliases.json"
        payload = _read_json_snapshot(aliases_path)
        aliases = payload.get("aliases") if isinstance(payload, dict) else None
        target = aliases.get(record_id) if isinstance(aliases, dict) else None
        if isinstance(target, dict):
            target = target.get("drx") or target.get("default") or target.get("record_id")
        if target:
            return str(target)
    return None


def _read_record_detail_by_pid(record_id):
    """Read one record through Invenio when the runtime service is available."""
    try:
        from invenio_access.permissions import system_identity
        from invenio_rdm_records.proxies import current_rdm_records_service

        result = current_rdm_records_service.read(system_identity, record_id)
        if hasattr(result, "to_dict"):
            return result.to_dict()
        if isinstance(result, dict):
            return result
        return dict(result)
    except Exception:
        return None


def _record_title_from_publish_reports(record_id):
    """Find a stable title in generated publish reports, when present."""
    record_id = str(record_id or "").strip()
    if not record_id:
        return None
    for path in _PUBLISH_REPORT_PATHS:
        try:
            with open(path, "r", encoding="utf-8") as fp:
                reader = csv.DictReader(fp, delimiter="\t")
                for row in reader:
                    row_record_id = str(row.get("record_id") or row.get("id") or "").strip()
                    if row_record_id != record_id:
                        continue
                    title = str(row.get("title") or "").strip()
                    if title and not _is_generic_record_title(title, record_id):
                        return title
        except Exception:
            continue
    return None


def _package_manifest_context(record_id):
    """Return title/link context recorded in a DRX package manifest."""
    try:
        manifest = load_manifest(record_id, "drx")
    except Exception:
        return {}
    if not isinstance(manifest, dict):
        return {}
    source = manifest.get("source") or {}
    summary = manifest.get("summary") or {}
    return {
        "title": source.get("title") or summary.get("title"),
        "doi_url": source.get("doi_url"),
        "record_url": source.get("record_url"),
    }


def _record_title_for_context(record_id, *, local_only=False):
    """Resolve the best available title for pages opened from package context."""
    record_id = str(record_id or "").strip()
    if not record_id:
        return None
    package_context = _package_manifest_context(record_id)
    if package_context.get("title"):
        return package_context["title"]

    package_record_id = _package_record_id_for_context(record_id)
    if local_only:
        for candidate_id in (record_id, package_record_id):
            title = _record_title_from_publish_reports(candidate_id)
            if not _is_generic_record_title(title, candidate_id):
                return title
        title = _record_title_from_snapshots([record_id, package_record_id])
        if not _is_generic_record_title(title, record_id):
            return title
        return record_id

    title = None
    detail = None
    try:
        detail = find_record_detail(record_id)
        title = record_title(detail) if detail else None
    except Exception:
        title = None
    if not _is_generic_record_title(title, record_id):
        return title

    detail = _read_record_detail_by_pid(record_id)
    try:
        title = record_title(detail) if detail else None
    except Exception:
        title = None
    if not _is_generic_record_title(title, record_id):
        return title

    title = _record_title_from_publish_reports(record_id)
    if not _is_generic_record_title(title, record_id):
        return title

    if package_record_id:
        detail = _read_record_detail_by_pid(package_record_id)
        try:
            title = record_title(detail) if detail else None
        except Exception:
            title = None
        if not _is_generic_record_title(title, package_record_id):
            return title
        title = _record_title_from_publish_reports(package_record_id)
        if not _is_generic_record_title(title, package_record_id):
            return title

    return _record_title_from_snapshots([record_id, package_record_id]) or title or record_id


def _load_json_snapshot(path):
    """Load a snapshot only for unfiltered API requests."""
    if request.args:
        return None
    return _read_json_snapshot(path)


def _snapshot_paths(path):
    """Return primary and fallback instance paths for one snapshot file."""
    path = Path(path)
    paths = [path]
    try:
        relative = path.relative_to(_INSTANCE_PATH)
    except ValueError:
        relative = None
    if relative is not None and _FALLBACK_INSTANCE_PATH != _INSTANCE_PATH:
        fallback = _FALLBACK_INSTANCE_PATH / relative
        if fallback not in paths:
            paths.append(fallback)
    return paths


def _read_json_snapshot(path):
    """Read the first valid JSON snapshot from primary/fallback locations."""
    path = Path(path)
    for candidate_path in _snapshot_paths(path):
        try:
            with open(candidate_path, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception:
            continue
    return None

def _load_points_snapshot():
    """Load georeferenced point snapshot when no runtime filters are active."""
    if (
        request.args.get("record_id")
        or request.args.get("mineral_term")
        or request.args.get("has_global_composition")
    ):
        return None
    return _load_json_snapshot(_POINTS_SNAPSHOT_PATH)


def _load_mining_area_records():
    """Load derived SIGMINE mining-area records for the map overlay."""
    records = _read_json_snapshot(_MINING_AREAS_PATH)
    return records if isinstance(records, list) else []


def _mining_term_matches(record, mineral_term):
    """Check if a mining-area row belongs to the requested argilomineral."""
    if not mineral_term:
        return True
    profile = build_mineral_profile(mineral_term)
    candidates = [mineral_term]
    if profile:
        candidates.extend(
            [
                profile.get("slug"),
                profile.get("id"),
                profile.get("nome"),
                profile.get("nome_pt"),
                profile.get("nome_en"),
                profile.get("nome_cientifico_padronizado"),
            ]
        )
    target_keys = {normalize_lookup_key(item) for item in candidates if item}
    record_keys = {
        normalize_lookup_key(record.get("argilomineral_relacionado")),
        normalize_lookup_key(record.get("termo_busca_sigmine")),
        normalize_lookup_key(record.get("substancia_sigmine")),
    }
    return bool(target_keys.intersection(record_keys))


def _safe_mining_geojson_path(record):
    """Resolve SIGMINE GeoJSON paths only inside the derived output directory."""
    raw_path = Path(record.get("arquivo_geojson") or "")
    if raw_path.exists() and _MINING_GEOJSON_DIR in raw_path.parents:
        return raw_path
    fallback = _MINING_GEOJSON_DIR / raw_path.name
    if fallback.exists():
        return fallback
    return None


def _load_mining_features(mineral_term=None, limit=1000):
    """Return GeoJSON features enriched with SIGMINE and Argiloteca context."""
    selected = [
        record
        for record in _load_mining_area_records()
        if _mining_term_matches(record, mineral_term)
    ]
    features = []
    seen = set()
    for record in selected:
        geojson_path = _safe_mining_geojson_path(record)
        if not geojson_path:
            continue
        geojson = _read_json_snapshot(geojson_path)
        if not isinstance(geojson, dict):
            continue
        processo = str(record.get("processo") or "")
        for feature in geojson.get("features") or []:
            props = dict(feature.get("properties") or {})
            if processo and str(props.get("PROCESSO") or props.get("DSProcesso") or "") != processo:
                continue
            feature_id = (
                record.get("id_local"),
                props.get("PROCESSO") or props.get("DSProcesso"),
                record.get("argilomineral_relacionado"),
            )
            if feature_id in seen:
                continue
            seen.add(feature_id)
            enriched = dict(feature)
            enriched["properties"] = {
                **props,
                "id_local": record.get("id_local", ""),
                "argilomineral_relacionado": record.get("argilomineral_relacionado", ""),
                "substancia_sigmine": record.get("substancia_sigmine", ""),
                "termo_busca_sigmine": record.get("termo_busca_sigmine", ""),
                "processo": record.get("processo", ""),
                "fase": record.get("fase", ""),
                "tipo_area": record.get("tipo_area", ""),
                "titular_explorador": record.get("titular_explorador", ""),
                "nome_mina": record.get("nome_mina", ""),
                "uso_sigmine": record.get("uso_sigmine", ""),
                "area_ha": record.get("area_ha", ""),
                "uf": record.get("uf", ""),
                "ultimo_evento": record.get("ultimo_evento", ""),
                "arquivo_kml": _relative_repo_path(record.get("arquivo_kml")),
                "arquivo_kml_nome": Path(record.get("arquivo_kml") or "").name,
                "fonte": record.get("fonte", "ANM - SIGMINE / Geoinformação Mineral"),
            }
            features.append(enriched)
            if len(features) >= limit:
                return features
    return features


def _relative_repo_path(value):
    """
    Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not value:
        return ""
    try:
        path = Path(value)
        return str(path.relative_to(_REPO_ROOT)) if path.is_absolute() else str(path)
    except Exception:
        return str(value)


def _cache_key(prefix, *parts):
    """
    Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
    
    Args:
        prefix: Valor de entrada consumido por esta etapa do fluxo.
        *parts: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return (prefix,) + tuple(parts)


def _cache_get(key):
    """Return a cached API payload if still within the short TTL."""
    cached = _ARGILO_API_CACHE.get(key)
    if not cached:
        return None
    timestamp, payload = cached
    if time.time() - timestamp > _ARGILO_API_CACHE_TTL:
        _ARGILO_API_CACHE.pop(key, None)
        return None
    return payload


def _cache_set(key, payload):
    """Store a JSON-ready payload in the process-local API cache."""
    _ARGILO_API_CACHE[key] = (time.time(), payload)
    return payload


def _short_map_text(value, limit=220):
    """
    Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
        limit: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = _safe_text(value)
    if not text:
        return None
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _request_cache_key(prefix):
    """
    Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
    
    Args:
        prefix: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return (prefix, tuple(sorted((key, tuple(request.args.getlist(key))) for key in request.args)))


def _bounded_int_arg(name, default, minimum=1, maximum=250):
    """Parse an integer request argument within safe API bounds."""
    try:
        value = int(request.args.get(name) or default)
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


def _bounded_float_arg(name, default, minimum=0.1, maximum=5.0):
    """Parse a float request argument within safe DRX method bounds."""
    try:
        value = float(request.args.get(name) or request.form.get(name) or default)
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(float(value), maximum))


def _upload_too_large_response(limit_bytes):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        limit_bytes: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    limit_mb = limit_bytes / (1024 * 1024)
    return jsonify({"success": False, "error": "Arquivo excede o limite de %.1f MB para upload temporario DRX." % limit_mb}), 413


def _request_exceeds_upload_limit(limit_bytes):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        limit_bytes: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    content_length = request.content_length
    return content_length is not None and content_length > limit_bytes


def _read_limited_upload(uploaded, limit_bytes):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        uploaded: Valor de entrada consumido por esta etapa do fluxo.
        limit_bytes: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    content = uploaded.read(limit_bytes + 1)
    if len(content) > limit_bytes:
        return None
    return content


def _identify_drx_candidates(two_theta, intensity):
    """Return mineral candidates for an on-demand DRX curve when available.

    A classificacao e auxiliar para upload temporario; falhas viram metadados
    de erro para o painel, sem bloquear a visualizacao da curva.
    """
    try:
        if str(_REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(_REPO_ROOT))
        from src.drx.mineral_identification import identify_mineral_candidates

        return identify_mineral_candidates(two_theta, intensity)
    except Exception as exc:
        return {
            "peaks": [],
            "candidates": [],
            "classification_error": str(exc),
        }


def _build_technical_report_for_curve(diffractogram_id, curve_payload, max_points=3000, include_processing=False):
    """Build the versioned technical report for an already loaded DRX curve."""
    curve_payload = curve_payload or {}
    metadata = curve_payload.get("metadata") or {}
    two_theta = curve_payload.get("two_theta") or []
    intensity = curve_payload.get("intensity") or []
    if not two_theta or not intensity:
        return None
    filename = (
        metadata.get("original_filename")
        or metadata.get("filename")
        or metadata.get("sample_code")
        or diffractogram_id
    )
    sample_code = metadata.get("sample_code") or Path(str(filename)).stem
    source_sha256 = (
        metadata.get("source_sha256")
        or metadata.get("sha256")
        or hashlib.sha256(json.dumps([two_theta[:20], intensity[:20], len(two_theta)], sort_keys=True).encode("utf-8")).hexdigest()
    )
    parsed = DiffractogramData(
        two_theta=two_theta,
        intensity=intensity,
        metadata={
            **metadata,
            "parser_format": metadata.get("parser_format") or metadata.get("curve_source") or "loaded_curve",
            "detected_format": metadata.get("detected_format") or "loaded diffractogram curve",
            "points": len(two_theta),
            "two_theta_start": two_theta[0],
            "two_theta_end": two_theta[-1],
        },
    )
    identification = {
        "peaks": metadata.get("detected_peaks") or metadata.get("peaks") or [],
        "candidates": metadata.get("mineral_candidates") or [],
        "reference_source": metadata.get("mineral_classification_source"),
        "classification_error": metadata.get("mineral_classification_error"),
    }
    analysis_payload = build_drx_analysis_run(
        filename=str(filename),
        sample_code=str(sample_code),
        source_sha256=source_sha256,
        parsed=parsed,
        identification=identification,
        preparation=metadata.get("preparation") or metadata.get("treatment"),
        max_points=max_points,
        stored=True,
        wavelength_angstrom=metadata.get("wavelength_angstrom") or _bounded_float_arg("wavelength_angstrom", 1.5406),
    )
    report = build_drx_technical_report(
        analysis_run=analysis_payload["analysis_run"],
        advanced_processing=analysis_payload["advanced_processing"],
        identification=identification,
        diagnostic_evidence=analysis_payload["diagnostic_evidence"],
    )
    payload = {
        "success": True,
        "diffractogram_id": diffractogram_id,
        "analysis_run": analysis_payload["analysis_run"],
        "technical_report": report,
        "diagnostic_evidence": analysis_payload["diagnostic_evidence"],
    }
    if include_processing:
        payload["advanced_processing"] = analysis_payload["advanced_processing"]
    return payload


def _safe_float(value):
    """
    Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if value in (None, "", []):
        return None
    try:
        return float(str(value).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def _safe_title(metadata: dict, record_id):
    """
    Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
    
    Args:
        metadata: Valor de entrada consumido por esta etapa do fluxo.
        record_id: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    title = metadata.get("title")

    if isinstance(title, str) and title.strip():
        return title.strip()

    if isinstance(title, dict):
        for key in ("pt-BR", "pt", "en", "en-US"):
            value = title.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        for value in title.values():
            if isinstance(value, str) and value.strip():
                return value.strip()

    return f"Registro {record_id}"


def _safe_text(value):
    """
    Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if value in (None, "", [], {}):
        return None

    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, dict):
        for key in ("pt-BR", "pt", "en", "en-US"):
            nested = _safe_text(value.get(key))
            if nested:
                return nested

        for nested_value in value.values():
            nested = _safe_text(nested_value)
            if nested:
                return nested

    if isinstance(value, list):
        for item in value:
            nested = _safe_text(item)
            if nested:
                return nested

    return str(value).strip() or None


def _has_meaningful_value(value):
    """
    Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if value in (None, "", [], {}):
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_has_meaningful_value(nested) for nested in value.values())
    if isinstance(value, list):
        return any(_has_meaningful_value(item) for item in value)
    return True


def _record_has_global_composition(custom_fields: dict) -> bool:
    """
    Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
    
    Args:
        custom_fields: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return _has_meaningful_value(custom_fields.get("arg:composicao_quimica_global"))


def _matches_global_composition_filter(has_global_composition: bool, filter_value: str | None) -> bool:
    """
    Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
    
    Args:
        has_global_composition: Valor de entrada consumido por esta etapa do fluxo.
        filter_value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    normalized = (filter_value or "").strip().lower()
    if not normalized:
        return True
    if normalized in {"sim", "yes", "true", "1", "with", "cadastrada"}:
        return has_global_composition
    if normalized in {"nao", "não", "no", "false", "0", "without", "ausente"}:
        return not has_global_composition
    return True


def _resolve_local_mineral_url_value(mineral_or_term):
    """
    Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
    
    Args:
        mineral_or_term: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if isinstance(mineral_or_term, dict):
        candidate = (
            mineral_or_term.get("nome")
            or mineral_or_term.get("nome_cientifico_padronizado")
            or mineral_or_term.get("nome_pt")
            or mineral_or_term.get("nome_en")
            or mineral_or_term.get("id")
        )
    else:
        candidate = mineral_or_term

    profile = build_mineral_profile(candidate)
    if not profile or not profile.get("slug"):
        return None
    return url_for("argiloteca.argilomineral_detail", term=profile["slug"])


def _mineral_alias_key(value):
    """
    Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    normalized = normalize_lookup_key(value)
    if not normalized:
        return None
    return normalized.replace(" ", "-")


def _authorized_mineral_alias_map(catalog):
    """Build frontend aliases from authorized mineral names and slugs."""
    aliases = {}
    for mineral in catalog or []:
        slug = _safe_text(mineral.get("slug") or mineral.get("id"))
        if not slug:
            continue
        for value in (
            slug,
            mineral.get("id"),
            mineral.get("nome"),
            mineral.get("nome_pt"),
            mineral.get("nome_en"),
            mineral.get("nome_cientifico_padronizado"),
        ):
            key = _mineral_alias_key(value)
            if key and key not in aliases:
                aliases[key] = slug
    return aliases


def _record_dataset_info(metadata: dict) -> dict:
    """Detect external dataset badges, currently PANGAEA, from record metadata."""
    description = _safe_text(metadata.get("description"))
    identifiers = metadata.get("identifiers") or []
    doi = ""
    for item in identifiers:
        if not isinstance(item, dict):
            continue
        identifier = _safe_text(item.get("identifier"))
        if identifier and "10.1594/pangaea" in identifier.lower():
            doi = identifier
            break
    is_pangaea = "pangaea" in description.lower() or bool(doi)
    return {
        "dataset_included": bool(is_pangaea),
        "dataset_source": "PANGAEA" if is_pangaea else "",
        "dataset_doi": doi,
        "dataset_badge": "Dataset PANGAEA incluído" if is_pangaea else "",
    }


def _make_point(
    *,
    record_id,
    title,
    kind,
    label,
    lat,
    lon,
    alt=None,
    group=None,
    description=None,
    point_index=1,
    sample_code=None,
    sample_location=None,
    sample_context=None,
    dataset_info=None,
    has_global_composition=False,
):
    """Build one map point while preserving the frontend field contract."""
    link = f"/records/{record_id}"
    dataset_info = dataset_info or {}

    return {
        "id": record_id,
        "point_id": f"{record_id}:{kind}:{point_index}",
        "record_id": record_id,
        "nome": label,
        "grupo": group,
        "latitude": lat,
        "longitude": lon,
        "altitude": alt,
        "descricao": description,
        "link": link,
        "title": title,
        "kind": kind,
        "label": label,
        "group": group,
        "lat": lat,
        "lon": lon,
        "alt": alt,
        "url": link,
        "sample_code": sample_code,
        "sample_location": sample_location,
        "sample_context": sample_context,
        "dataset_included": dataset_info.get("dataset_included", False),
        "dataset_source": dataset_info.get("dataset_source", ""),
        "dataset_doi": dataset_info.get("dataset_doi", ""),
        "dataset_badge": dataset_info.get("dataset_badge", ""),
        "has_global_composition": bool(has_global_composition),
    }


def _append_unique(target, value):
    """
    Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
    
    Args:
        target: Valor de entrada consumido por esta etapa do fluxo.
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = _safe_text(value)
    if text and text not in target:
        target.append(text)


def _coordinate_group_key(point: dict):
    """
    Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
    
    Args:
        point: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    lat = _safe_float(point.get("latitude") if "latitude" in point else point.get("lat"))
    lon = _safe_float(point.get("longitude") if "longitude" in point else point.get("lon"))
    if lat is None or lon is None:
        return None
    return (
        point.get("record_id") or point.get("id") or "",
        round(lat, 6),
        round(lon, 6),
    )


def _group_points_by_record_coordinate(points: list[dict]) -> list[dict]:
    """Collapse repeated record/coordinate markers into a single map marker."""
    grouped = {}
    order = []

    for point in points:
        if not isinstance(point, dict):
            continue
        key = _coordinate_group_key(point)
        if key is None:
            continue

        if key not in grouped:
            grouped[key] = {
                **point,
                "point_id": f"{key[0]}:coord:{key[1]}:{key[2]}",
                "coordinate_group_id": f"{key[0]}:{key[1]}:{key[2]}",
                "grouped_points_count": 0,
                "sample_count": 0,
                "mineral_count": 0,
                "sample_codes": [],
                "sample_locations": [],
                "sample_contexts": [],
                "argilominerais": [],
                "mineral_groups": [],
                "grouped_labels": [],
                "grouped_kinds": [],
            }
            order.append(key)

        bucket = grouped[key]
        existing_grouped_count = int(point.get("grouped_points_count") or 0)
        bucket["grouped_points_count"] += existing_grouped_count or 1
        kind = point.get("kind") or ""
        _append_unique(bucket["grouped_kinds"], kind)
        _append_unique(bucket["grouped_labels"], point.get("label") or point.get("nome"))

        if kind == "amostra":
            bucket["sample_count"] += 1
            _append_unique(bucket["sample_codes"], point.get("sample_code") or point.get("codigo_amostra") or point.get("label"))
            _append_unique(bucket["sample_locations"], point.get("sample_location") or point.get("local_coleta"))
            _append_unique(bucket["sample_contexts"], point.get("sample_context") or point.get("contexto_geologico"))
        elif kind == "argilomineral":
            bucket["mineral_count"] += 1
            _append_unique(bucket["argilominerais"], point.get("label") or point.get("nome"))
            _append_unique(bucket["mineral_groups"], point.get("group") or point.get("grupo"))
        elif kind == "agrupado":
            bucket["sample_count"] += int(point.get("sample_count") or 0)
            bucket["mineral_count"] += int(point.get("mineral_count") or 0)
            for value in point.get("sample_codes") or []:
                _append_unique(bucket["sample_codes"], value)
            for value in point.get("sample_locations") or []:
                _append_unique(bucket["sample_locations"], value)
            for value in point.get("sample_contexts") or []:
                _append_unique(bucket["sample_contexts"], value)
            for value in point.get("argilominerais") or []:
                _append_unique(bucket["argilominerais"], value)
            for value in point.get("mineral_groups") or []:
                _append_unique(bucket["mineral_groups"], value)

        if point.get("dataset_included"):
            bucket["dataset_included"] = True
            for field in ("dataset_source", "dataset_doi", "dataset_badge"):
                if point.get(field):
                    bucket[field] = point.get(field)

        if point.get("has_global_composition"):
            bucket["has_global_composition"] = True

    collapsed = []
    for key in order:
        point = grouped[key]
        if point["grouped_points_count"] > 1:
            point["kind"] = "agrupado"
            point["label"] = f"{point['grouped_points_count']} ocorrencias no mesmo ponto"
            point["nome"] = point["label"]
        collapsed.append(point)

    return collapsed


def _group_points_payload(payload: dict) -> dict:
    """Add grouped-marker accounting to a points API payload."""
    points = payload.get("points") or []
    if not isinstance(points, list):
        return payload
    if payload.get("grouped_by_coordinate"):
        return {
            **payload,
            "total_markers": payload.get("total_markers") or len(points),
            "total_points": payload.get("total_points") or len(points),
        }

    grouped_points = _group_points_by_record_coordinate(points)
    grouped_records = {
        point.get("record_id")
        for point in grouped_points
        if point.get("record_id")
    }
    dataset_records = {
        point.get("record_id")
        for point in grouped_points
        if point.get("dataset_included") and point.get("record_id")
    }

    return {
        **payload,
        "grouped_by_coordinate": True,
        "total_raw_points": len(points),
        "total_markers": len(grouped_points),
        "total_points": len(grouped_points),
        "georeferenced_records": len(grouped_records) or payload.get("georeferenced_records"),
        "dataset_records": len(dataset_records),
        "points": grouped_points,
    }


def _extract_points_from_record(record: dict) -> list[dict]:
    """Extract sample and mineral map points from one published record."""
    points = []

    metadata = record.get("metadata", {}) or {}
    custom_fields = (
        record.get("custom_fields")
        or metadata.get("custom_fields")
        or {}
    )

    record_id = record.get("id") or record.get("uuid") or "sem-id"
    title = _safe_title(metadata, record_id)
    record_description = _short_map_text(metadata.get("description"))
    dataset_info = _record_dataset_info(metadata)
    has_global_composition = _record_has_global_composition(custom_fields)

    samples = custom_fields.get("arg:amostras", []) or []
    structured_sample_points = 0
    structured_samples_present = False
    if isinstance(samples, list):
        for idx, sample in enumerate(samples, start=1):
            if not isinstance(sample, dict):
                continue
            structured_samples_present = True

            lat = _safe_float(sample.get("latitude"))
            lon = _safe_float(sample.get("longitude"))
            alt = sample.get("altitude_m")

            if lat is None or lon is None:
                continue

            sample_code = _safe_text(sample.get("codigo_amostra"))
            sample_location = _safe_text(sample.get("local_coleta"))
            sample_context = _safe_text(sample.get("contexto_geologico"))

            points.append(
                _make_point(
                    record_id=record_id,
                    title=title,
                    kind="amostra",
                    label=sample_code or title,
                    lat=lat,
                    lon=lon,
                    alt=alt,
                    description=record_description,
                    point_index=idx,
                    sample_code=sample_code,
                    sample_location=sample_location,
                    sample_context=sample_context,
                    dataset_info=dataset_info,
                    has_global_composition=has_global_composition,
                )
            )
            structured_sample_points += 1

    # Legacy coordinates are used only when there is no structured sample model at all.
    if structured_sample_points == 0 and not structured_samples_present:
        lat = _safe_float(custom_fields.get("arg:amostra_latitude"))
        lon = _safe_float(custom_fields.get("arg:amostra_longitude"))
        alt = custom_fields.get("arg:amostra_altitude")

        if lat is not None and lon is not None:
            points.append(
                _make_point(
                    record_id=record_id,
                    title=title,
                    kind="amostra",
                    label=title,
                    lat=lat,
                    lon=lon,
                    alt=alt,
                    description=record_description,
                    point_index=1,
                    sample_location=_safe_text(custom_fields.get("arg:amostra_local_coleta")),
                    dataset_info=dataset_info,
                    has_global_composition=has_global_composition,
                )
            )

    minerais = custom_fields.get("arg:argilominerais", []) or []
    if isinstance(minerais, list):
        for idx, mineral in enumerate(minerais, start=1):
            if not isinstance(mineral, dict):
                continue

            mlat = _safe_float(mineral.get("latitude"))
            mlon = _safe_float(mineral.get("longitude"))
            malt = mineral.get("altitude")

            if mlat is None or mlon is None:
                continue

            nome = mineral.get("nome") or f"Argilomineral {idx}"
            grupo = mineral.get("grupo")
            descricao = _short_map_text(mineral.get("descricao") or mineral.get("descricao_curta")) or record_description

            points.append(
                _make_point(
                    record_id=record_id,
                    title=title,
                    kind="argilomineral",
                    label=nome,
                    lat=mlat,
                    lon=mlon,
                    alt=malt,
                    group=grupo,
                    description=descricao,
                    point_index=idx,
                    dataset_info=dataset_info,
                    has_global_composition=has_global_composition,
                )
            )

    return points


def _record_has_mineral(record: dict, mineral_term: str | None) -> bool:
    """Match a record against a mineral term using local profile aliases."""
    profile = build_mineral_profile(mineral_term)
    candidate_values = []

    if profile:
        candidate_values.extend(
            [
                mineral_term,
                profile.get("id"),
                profile.get("slug"),
                profile.get("nome"),
                profile.get("nome_pt"),
                profile.get("nome_en"),
                profile.get("nome_cientifico_padronizado"),
                profile.get("broader"),
                profile.get("external_id"),
            ]
        )
        candidate_values.extend(profile.get("aliases") or [])
    else:
        candidate_values.append(mineral_term)

    targets = {
        normalize_lookup_key(value)
        for value in candidate_values
        if normalize_lookup_key(value)
    }
    if not targets:
        return True

    metadata = record.get("metadata", {}) or {}
    custom_fields = (
        record.get("custom_fields")
        or metadata.get("custom_fields")
        or {}
    )
    minerais = custom_fields.get("arg:argilominerais", []) or []
    if not isinstance(minerais, list):
        return False

    for mineral in minerais:
        if not isinstance(mineral, dict):
            continue
        candidates = (
            mineral.get("id"),
            mineral.get("nome"),
            mineral.get("nome_cientifico_padronizado"),
            mineral.get("nome_pt"),
            mineral.get("nome_en"),
            mineral.get("grupo"),
            mineral.get("external_id"),
        )
        for candidate in candidates:
            if normalize_lookup_key(candidate) in targets:
                return True

    subject_map = extract_subject_mineral_map(record)
    subject_candidates = (
        (subject_map.get("subjects") or [])
        + (subject_map.get("matched_subjects") or [])
        + (subject_map.get("mineral_names") or [])
        + (subject_map.get("mineral_groups") or [])
        + (extract_subject_terms(record) or [])
    )
    for candidate in subject_candidates:
        if normalize_lookup_key(candidate) in targets:
            return True

    return False


def _iter_text_values(value):
    """
    Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if value in (None, "", [], {}):
        return
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for nested in value.values():
            yield from _iter_text_values(nested)
        return
    if isinstance(value, list):
        for item in value:
            yield from _iter_text_values(item)
        return
    yield str(value)


def _mineral_lookup_targets(mineral_term: str | None) -> set[str]:
    """Build normalized lookup keys for one requested mineral term."""
    if not (mineral_term or "").strip():
        return set()
    profile = build_mineral_profile(mineral_term)
    candidate_values = [mineral_term]
    if profile:
        candidate_values.extend(
            [
                profile.get("id"),
                profile.get("slug"),
                profile.get("nome"),
                profile.get("nome_pt"),
                profile.get("nome_en"),
                profile.get("nome_cientifico_padronizado"),
                profile.get("broader"),
                profile.get("external_id"),
            ]
        )
        candidate_values.extend(profile.get("aliases") or [])
    return {
        normalize_lookup_key(value)
        for value in candidate_values
        if normalize_lookup_key(value)
    }


def _node_has_mineral_term(node: dict, targets: set[str]) -> bool:
    """Check a geoquimica network node against mineral target aliases."""
    if not targets:
        return True
    candidate_fields = (
        "argilominerais",
        "argilominerais_subject",
        "subjects",
        "subjects_mapeados",
        "grupos_minerais",
        "grupo_mineralogico_dominante",
    )
    for field in candidate_fields:
        for value in _iter_text_values(node.get(field)):
            if normalize_lookup_key(value) in targets:
                return True
    return False


def _build_argilomineral_points_payload_from_snapshots(
    mineral_term: str | None,
    has_global_composition: str | None = None,
):
    """Build map points from static snapshots for filtered mineral pages."""
    points_snapshot = _read_json_snapshot(_POINTS_SNAPSHOT_PATH)
    if not isinstance(points_snapshot, dict):
        return None

    composition_filter = (has_global_composition or "").strip()
    points_all = [
        point
        for point in (points_snapshot.get("points") or [])
        if isinstance(point, dict) and point.get("record_id")
    ]
    matching_record_ids = {point.get("record_id") for point in points_all}
    source_parts = ["points_snapshot"]

    geo_record_ids = set()
    geo_snapshot = _read_json_snapshot(_GEO_AGG_SNAPSHOT_PATH)
    if isinstance(geo_snapshot, dict):
        geo_record_ids = {
            row.get("record_id")
            for row in (geo_snapshot.get("records") or [])
            if isinstance(row, dict) and row.get("record_id")
        }
        if geo_record_ids:
            source_parts.append("geoquimica_agregada_snapshot")

    if composition_filter:
        if not geo_record_ids:
            return None
        matching_record_ids = {
            record_id
            for record_id in matching_record_ids
            if _matches_global_composition_filter(record_id in geo_record_ids, composition_filter)
        }

    targets = _mineral_lookup_targets(mineral_term)
    nodes = []
    if targets:
        network_snapshot = _read_json_snapshot(_GEO_NET_SNAPSHOT_PATH)
        if not isinstance(network_snapshot, dict):
            return None
        nodes = network_snapshot.get("nodes") or []
        mineral_record_ids = {
            node.get("id")
            for node in nodes
            if isinstance(node, dict) and node.get("id") and _node_has_mineral_term(node, targets)
        }
        matching_record_ids = matching_record_ids.intersection(mineral_record_ids)
        source_parts.append("geoquimica_rede_snapshot")

    points = [
        {
            **point,
            "has_global_composition": (
                point.get("record_id") in geo_record_ids
                if geo_record_ids
                else bool(point.get("has_global_composition"))
            ),
        }
        for point in points_all
        if point.get("record_id") in matching_record_ids
    ]
    georeferenced_records = {point.get("record_id") for point in points if point.get("record_id")}
    dataset_records = {
        point.get("record_id")
        for point in points
        if point.get("dataset_included") and point.get("record_id")
    }
    return _group_points_payload({
        "success": True,
        "record_id": None,
        "mineral_term": mineral_term,
        "has_global_composition": composition_filter or None,
        "total_hits": len(nodes) if targets else len(points_all),
        "matched_records": len(matching_record_ids),
        "georeferenced_records": len(georeferenced_records),
        "dataset_records": len(dataset_records),
        "total_points": len(points),
        "points": points,
        "source": "+".join(source_parts),
    })


def _build_argilomineral_points_payload(
    record_id: str | None = None,
    mineral_term: str | None = None,
    has_global_composition: str | None = None,
):
    """Build the map payload from snapshots or, when needed, the live service."""
    from invenio_access.permissions import system_identity
    from invenio_rdm_records.proxies import current_rdm_records_service

    record_filter = (record_id or "").strip()
    mineral_filter = (mineral_term or "").strip()
    composition_filter = (has_global_composition or "").strip()

    if (mineral_filter or composition_filter) and not record_filter:
        snapshot_payload = _build_argilomineral_points_payload_from_snapshots(
            mineral_filter,
            composition_filter,
        )
        if snapshot_payload is not None:
            return snapshot_payload

    hits = []
    page = 1
    page_size = 1000
    while True:
        result = current_rdm_records_service.search(
            identity=system_identity,
            params={
                "size": page_size,
                "page": page,
                "sort": "newest",
            },
        )
        page_hits = list(getattr(result, "hits", []) or [])
        hits.extend(page_hits)
        if len(page_hits) < page_size:
            break
        page += 1

    points = []
    matched_records = 0
    georeferenced_records = 0

    for hit in hits:
        if hasattr(hit, "to_dict"):
            try:
                hit = hit.to_dict()
            except Exception:
                pass

        record = {}
        if isinstance(hit, dict):
            if isinstance(hit.get("_source"), dict):
                record = hit["_source"]
            else:
                record = hit

        if not isinstance(record, dict) or not record:
            continue

        current_record_id = record.get("id") or record.get("uuid") or ""
        custom_fields = (
            record.get("custom_fields")
            or record.get("metadata", {}).get("custom_fields")
            or {}
        )
        has_composition = _record_has_global_composition(custom_fields)

        if record_filter and current_record_id != record_filter:
            continue
        if mineral_filter and not _record_has_mineral(record, mineral_filter):
            continue
        if not _matches_global_composition_filter(has_composition, composition_filter):
            continue

        matched_records += 1
        record_points = _extract_points_from_record(record)
        if record_points:
            georeferenced_records += 1
            points.extend(record_points)

    dataset_records = {point.get("record_id") for point in points if point.get("dataset_included") and point.get("record_id")}

    return _group_points_payload({
        "success": True,
        "record_id": record_filter or None,
        "mineral_term": mineral_filter or None,
        "has_global_composition": composition_filter or None,
        "total_hits": len(hits),
        "matched_records": matched_records,
        "georeferenced_records": georeferenced_records,
        "dataset_records": len(dataset_records),
        "total_points": len(points),
        "points": points,
    })


def create_blueprint(app):
    """Register the Argiloteca routes on the Flask app."""
    blueprint = Blueprint(
        "argiloteca",
        __name__,
        template_folder="./templates",
        static_folder="./static",
        static_url_path="/argiloteca/static",
    )

    @blueprint.app_context_processor
    def inject_argiloteca_template_helpers():
        """Expose mineral helpers and authorized slugs to templates."""
        mineral_options = []
        for mineral in build_authorized_mineral_catalog():
            slug = mineral.get("slug")
            if not slug:
                continue
            label = (
                mineral.get("nome_pt")
                or mineral.get("nome")
                or mineral.get("nome_cientifico_padronizado")
                or mineral.get("nome_en")
                or slug
            )
            mineral_options.append(
                {
                    "label": label,
                    "term": slug,
                    "url": url_for("argiloteca.argilomineral_detail", term=slug),
                }
            )

        mineral_options.sort(key=lambda item: (item["label"] or "").casefold())

        return {
            "argilo_resolve_mineral_group": resolve_mineral_group,
            "argilo_resolve_mineral_name": resolve_mineral_name,
            "argilo_resolve_mineral_reference": resolve_external_reference,
            "argilo_resolve_mineral_summary": resolve_short_description,
            "argilo_resolve_mineral_profile": build_mineral_profile,
            "argilo_local_mineral_url": _resolve_local_mineral_url_value,
            "argilo_frontpage_mineral_options": mineral_options,
        }

    @blueprint.route("/argilominerais/<term>", endpoint="argilomineral_detail")
    def argilomineral_detail(term):
        """Render the public mineral profile page."""
        profile = build_mineral_profile(term)
        if not profile:
            abort(404)
        map_summary = _build_argilomineral_points_payload(mineral_term=profile.get("slug") or profile.get("id"))
        return render_template(
            "semantic-ui/argiloteca/argilomineral_detail.html",
            mineral=profile,
            map_summary=map_summary,
        )

    @blueprint.route("/api/argiloteca/argilominerais/<term>/relatorio", endpoint="api_argilomineral_relatorio")
    @blueprint.route("/argiloteca/argilominerais/<term>/relatorio")
    def api_argilomineral_relatorio(term):
        """Return the scientific report blocks for one authorized mineral."""
        profile = build_mineral_profile(term)
        if not profile:
            return jsonify({"success": False, "error": "Argilomineral nao encontrado no vocabulario da Argiloteca."}), 404
        canonical_name = (
            profile.get("nome_cientifico_padronizado")
            or profile.get("nome_en")
            or profile.get("nome")
            or term
        )
        technical_blocks = [
            {"title": f"Chemistry of {canonical_name}", "value": profile.get("quimica_mindat")},
            {"title": "X-Ray Powder Diffraction", "value": profile.get("difracao_raios_x_po_mindat")},
            {"title": "In Petrology", "value": profile.get("petrologia_mindat")},
            {
                "title": f"References for {canonical_name}",
                "value": profile.get("referencias_mindat"),
                "items": profile.get("referencias_mindat_itens") or [],
            },
        ]
        return jsonify(
            {
                "success": True,
                "slug": profile.get("slug") or term,
                "title": profile.get("nome_pt") or profile.get("nome") or canonical_name,
                "canonical_name": canonical_name,
                "page_url": url_for("argiloteca.argilomineral_detail", term=profile.get("slug") or term),
                "classic_description": profile.get("classic_description"),
                "technical_blocks": [
                    block for block in technical_blocks if block.get("value") or block.get("items")
                ],
                "curatorial_facts": profile.get("curatorial_facts") or [],
                "scientific_source_blocks": profile.get("scientific_source_blocks") or [],
            }
        )

    @blueprint.route("/argilominerais", endpoint="argilomineral_lookup")
    def argilomineral_lookup():
        """Redirect a free-text mineral lookup to the canonical mineral page."""
        term = (request.args.get("term") or "").strip()
        if not term:
            return redirect(url_for("invenio_app_rdm.frontpage"))

        profile = build_mineral_profile(term)
        if not profile or not profile.get("slug"):
            abort(404)

        return redirect(url_for("argiloteca.argilomineral_detail", term=profile["slug"]))

    @blueprint.route(
        "/catalogo-autorizado-de-nomes-para-argilominerais",
        endpoint="catalogo_autorizado_argilominerais",
    )
    def catalogo_autorizado_argilominerais():
        """Render the controlled Argiloteca mineral-name catalog."""
        return render_template(
            "semantic-ui/argiloteca/catalogo_autorizado_argilominerais.html",
            minerais=build_authorized_mineral_catalog(),
        )

    @blueprint.route("/mapa-argilominerais", endpoint="mapa_argilominerais")
    def mapa_argilominerais():
        """Render the map shell; data is loaded through the points API."""
        mineral_profile = build_mineral_profile(request.args.get("mineral_term"))
        return render_template(
            "semantic-ui/argiloteca/mapa_argilominerais.html",
            mineral_profile=mineral_profile,
        )

    @blueprint.route(
        "/argiloteca/pontos",
        endpoint="api_pontos_argilominerais",
    )
    def api_pontos_argilominerais():
        """Return georeferenced samples/minerals for map visualization."""
        try:
            snapshot = _load_points_snapshot()
            if snapshot is not None and not request.args:
                return jsonify(_group_points_payload(snapshot))
            cache_key = _cache_key(
                "pontos",
                request.args.get("record_id") or "",
                request.args.get("mineral_term") or "",
                request.args.get("has_global_composition") or "",
            )
            cached = _cache_get(cache_key)
            if cached is not None:
                return jsonify(cached)
            payload = _build_argilomineral_points_payload(
                record_id=request.args.get("record_id"),
                mineral_term=request.args.get("mineral_term"),
                has_global_composition=request.args.get("has_global_composition"),
            )
            return jsonify(_cache_set(cache_key, payload))

        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "points": [],
                }
            ), 500

    @blueprint.route(
        "/argiloteca/mineracao/areas",
        endpoint="api_areas_mineracao_argilominerais",
    )
    def api_areas_mineracao_argilominerais():
        """Return derived SIGMINE mining features related to argilominerals."""
        try:
            limit = _bounded_int_arg("limit", 1000, minimum=1, maximum=5000)
            features = _load_mining_features(
                mineral_term=request.args.get("mineral_term"),
                limit=limit,
            )
            return jsonify(
                {
                    "success": True,
                    "source": "ANM - SIGMINE / Geoinformação Mineral",
                    "total_features": len(features),
                    "feature_collection": {
                        "type": "FeatureCollection",
                        "features": features,
                    },
                }
            )
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "feature_collection": {"type": "FeatureCollection", "features": []},
                }
            ), 500

    @blueprint.route("/geoquimica/rede", endpoint="geoquimica_rede")
    def geoquimica_rede():
        """
        Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        return render_template("semantic-ui/argiloteca/geoquimica_rede.html")

    @blueprint.route("/geoquimica/composicao-global", endpoint="geoquimica_agregada")
    def geoquimica_agregada():
        """
        Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        return render_template("semantic-ui/argiloteca/geoquimica_agregada.html")

    @blueprint.route("/drx/comparacao", endpoint="drx_comparacao")
    def drx_comparacao():
        """Render the DRX comparison panel, optionally scoped to one record."""
        context_record_id = (request.args.get("record_id") or "").strip()
        context_record_title = _record_title_for_context(context_record_id) if context_record_id else None
        authorized_mineral_catalog = build_authorized_mineral_catalog()
        authorized_mineral_slugs = sorted(
            {mineral.get("slug") for mineral in authorized_mineral_catalog if mineral.get("slug")}
        )
        return render_template(
            "semantic-ui/argiloteca/drx_comparacao.html",
            authorized_mineral_slugs=authorized_mineral_slugs,
            authorized_mineral_aliases=_authorized_mineral_alias_map(authorized_mineral_catalog),
            context_record_id=context_record_id,
            context_record_title=context_record_title or context_record_id,
            context_source=(request.args.get("source") or "").strip(),
        )

    @blueprint.route("/analises/", endpoint="analises_index")
    def analises_index():
        """Render the analytical-package index shell."""
        authorized_mineral_catalog = build_authorized_mineral_catalog()
        authorized_mineral_slugs = sorted(
            {mineral.get("slug") for mineral in authorized_mineral_catalog if mineral.get("slug")}
        )
        return render_template(
            "semantic-ui/argiloteca/analises_index.html",
            authorized_mineral_slugs=authorized_mineral_slugs,
            authorized_mineral_aliases=_authorized_mineral_alias_map(authorized_mineral_catalog),
        )

    @blueprint.route("/analises/<record_id>", endpoint="pacote_analitico")
    def pacote_analitico(record_id):
        """Render the analytical package page for one record/package id."""
        record_title_value = _record_title_for_context(record_id, local_only=True)
        package_context = _package_manifest_context(record_id)
        record_href = f"/records/{record_id}" if re.match(r"^[a-z0-9]{5}-[a-z0-9]{5}$", record_id or "", re.I) else None
        if not record_href:
            record_href = package_context.get("doi_url") or package_context.get("record_url")
        authorized_mineral_catalog = build_authorized_mineral_catalog()
        return render_template(
            "semantic-ui/argiloteca/pacote_analitico.html",
            record_id=record_id,
            record_title=record_title_value or record_id,
            record_href=record_href,
            authorized_mineral_slugs=sorted(
                {mineral.get("slug") for mineral in authorized_mineral_catalog if mineral.get("slug")}
            ),
            authorized_mineral_aliases=_authorized_mineral_alias_map(authorized_mineral_catalog),
        )

    @blueprint.route(
        "/api/argiloteca/analises/<record_id>",
        endpoint="api_pacote_analitico",
    )
    @blueprint.route("/argiloteca/analises/<record_id>")
    def api_pacote_analitico(record_id):
        """Return a paginated analytical package payload."""
        try:
            payload = build_package_payload(
                record_id,
                analysis_type=request.args.get("analysis_type") or "drx",
                limit=_bounded_int_arg("limit", 100, maximum=500),
                offset=_bounded_int_arg("offset", 0, minimum=0, maximum=1000000),
                preparation=request.args.get("preparation") or None,
                mineral=request.args.get("mineral") or None,
                query=request.args.get("q") or None,
            )
            return jsonify(payload)
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "items": [],
                }
            ), 500

    @blueprint.route(
        "/api/argiloteca/analises/<record_id>/drx/curva",
        endpoint="api_pacote_analitico_drx_curva",
    )
    @blueprint.route("/argiloteca/analises/<record_id>/drx/curva")
    def api_pacote_analitico_drx_curva(record_id):
        """Return one DRX curve from an analytical package."""
        try:
            payload = load_package_curve(
                record_id,
                analysis_type=request.args.get("analysis_type") or "drx",
                sample_code=request.args.get("sample_code") or None,
                filename=request.args.get("filename") or None,
                max_points=_bounded_int_arg("max_points", 2500, maximum=5000),
            )
            if payload is None:
                return jsonify({"success": False, "error": "Curva nao encontrada no pacote analitico."}), 404
            status = 200 if payload.get("success") else 400
            return jsonify(payload), status
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ), 500

    @blueprint.route(
        "/api/argiloteca/drx/registros",
        endpoint="api_drx_registros",
    )
    @blueprint.route("/argiloteca/drx/registros")
    def api_drx_registros():
        """Return imported DRX entries already associated with records."""
        try:
            filters = {
                "q": request.args.get("q") or None,
                "sample_code": request.args.get("sample_code") or None,
                "argilomineral": request.args.get("argilomineral") or None,
                "mineral_group": request.args.get("mineral_group") or None,
            }
            payload = list_records_with_drx(
                filters=filters,
                size=_bounded_int_arg("size", 500, maximum=5000),
            )
            return jsonify(payload)
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "records": [],
                }
            ), 500

    @blueprint.route(
        "/api/argiloteca/drx/raw-snapshot",
        endpoint="api_drx_raw_snapshot",
    )
    @blueprint.route("/argiloteca/drx/raw-snapshot")
    def api_drx_raw_snapshot():
        """Return the module-wide RAW snapshot list with optional filters."""
        try:
            filters = {
                "q": request.args.get("q") or None,
                "sample_code": request.args.get("sample_code") or None,
                "preparation": request.args.get("preparation") or None,
                "argilomineral": request.args.get("argilomineral") or None,
                "mineral_group": request.args.get("mineral_group") or None,
                "status": request.args.get("status") or None,
            }
            payload = list_raw_snapshot_items(
                filters=filters,
                limit=_bounded_int_arg("limit", 80, minimum=1, maximum=500),
                offset=_bounded_int_arg("offset", 0, minimum=0, maximum=1000000),
            )
            return jsonify(payload)
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "items": [],
                }
            ), 500

    @blueprint.route(
        "/api/argiloteca/drx/raw-snapshot/sugestoes",
        endpoint="api_drx_raw_snapshot_sugestoes",
    )
    @blueprint.route("/argiloteca/drx/raw-snapshot/sugestoes")
    def api_drx_raw_snapshot_sugestoes():
        """Return N/G/C and mineral-based comparison suggestions from snapshots."""
        try:
            filters = {
                "q": request.args.get("q") or None,
                "sample_code": request.args.get("sample_code") or None,
                "preparation": request.args.get("preparation") or None,
                "argilomineral": request.args.get("argilomineral") or None,
                "mineral_group": request.args.get("mineral_group") or None,
                "status": request.args.get("status") or None,
            }
            payload = build_raw_snapshot_comparison_suggestions(
                filters=filters,
                limit=_bounded_int_arg("limit", 1000, minimum=1, maximum=5000),
            )
            return jsonify(payload)
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "suggestions": [],
                }
            ), 500

    @blueprint.route(
        "/api/argiloteca/drx/difratogramas/<diffractogram_id>",
        endpoint="api_drx_difratograma",
    )
    @blueprint.route("/argiloteca/drx/difratogramas/<diffractogram_id>")
    def api_drx_difratograma(diffractogram_id):
        """Return decimated curve data for one imported or snapshot diffractogram."""
        try:
            payload = load_diffractogram_data(diffractogram_id)
            if payload is None:
                return jsonify({"success": False, "error": "Difratograma nao encontrado"}), 404
            two_theta, intensity = decimate_series(payload.get("two_theta") or [], payload.get("intensity") or [])
            return jsonify(
                {
                    "success": True,
                    "metadata": payload.get("metadata") or {},
                    "two_theta": two_theta,
                    "intensity": intensity,
                    "render_points": len(two_theta),
                    "total_points": len(payload.get("two_theta") or []),
                }
            )
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ), 500

    @blueprint.route(
        "/api/argiloteca/drx/technical-report/<diffractogram_id>",
        endpoint="api_drx_technical_report",
    )
    @blueprint.route("/argiloteca/drx/technical-report/<diffractogram_id>")
    @blueprint.route("/argiloteca/drx/technical-report/<diffractogram_id>.json")
    def api_drx_technical_report(diffractogram_id):
        """Return a versioned backend technical report for one DRX curve."""
        try:
            curve_payload = load_diffractogram_data(diffractogram_id)
            if curve_payload is None:
                return jsonify({"success": False, "error": "Difratograma nao encontrado"}), 404
            payload = _build_technical_report_for_curve(
                diffractogram_id,
                curve_payload,
                max_points=_bounded_int_arg("max_points", 3000, maximum=5000),
            )
            if payload is None:
                return jsonify({"success": False, "error": "Curva sem pontos para relatorio tecnico."}), 404
            return jsonify(payload)
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ), 500

    @blueprint.route("/argiloteca/drx/reports/technical/<diffractogram_id>", endpoint="drx_technical_report_html")
    @blueprint.route("/argiloteca/drx/reports/technical/<diffractogram_id>.html")
    def drx_technical_report_html(diffractogram_id):
        """Render a backend HTML technical report for one DRX curve."""
        try:
            curve_payload = load_diffractogram_data(diffractogram_id)
            if curve_payload is None:
                return "Difratograma nao encontrado", 404
            payload = _build_technical_report_for_curve(
                diffractogram_id,
                curve_payload,
                max_points=_bounded_int_arg("max_points", 3000, maximum=5000),
            )
            if payload is None:
                return "Curva sem pontos para relatorio tecnico.", 404
            return render_drx_technical_report_html(payload["technical_report"]), 200, {"Content-Type": "text/html; charset=utf-8"}
        except Exception as e:
            return f"Erro ao gerar relatorio tecnico DRX: {e}", 500

    @blueprint.route("/argiloteca/drx/reports/selection/<run_id>.html")
    @blueprint.route("/argiloteca/drx/reports/selection/<run_id>")
    def drx_selection_report_html(run_id):
        """Render a persisted selection/run report as printable backend HTML."""
        payload = get_drx_run(run_id)
        if not payload.get("success"):
            return payload.get("error") or "Run DRX nao encontrado.", 404
        report = payload.get("selection_report") or payload.get("technical_report") or {}
        if report.get("schema_version") == "argiloteca.drx.selection_report.v1":
            html = render_drx_selection_report_html(report)
        else:
            html = render_drx_technical_report_html(report)
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}

    @blueprint.route("/argiloteca/drx/reports/selection/<run_id>.pdf")
    def drx_selection_report_pdf(run_id):
        """PDF endpoint placeholder with explicit HTML fallback policy."""
        payload = get_drx_run(run_id)
        if not payload.get("success"):
            return payload.get("error") or "Run DRX nao encontrado.", 404
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Geracao PDF backend indisponivel neste ambiente; use o HTML imprimivel.",
                    "html_url": url_for("argiloteca.drx_selection_report_html", run_id=run_id),
                    "run_id": run_id,
                }
            ),
            501,
        )

    @blueprint.route(
        "/api/argiloteca/drx/science-engine/status",
        endpoint="api_drx_science_engine_status",
    )
    @blueprint.route("/argiloteca/drx/science-engine/status")
    def api_drx_science_engine_status():
        """Return availability and package versions for the isolated DRX engine."""
        payload = science_engine_status()
        return jsonify({"success": bool(payload.get("available")), "engine": payload})

    @blueprint.route(
        "/api/argiloteca/drx/cif/simulate",
        methods=["POST"],
        endpoint="api_drx_cif_simulate",
    )
    @blueprint.route("/argiloteca/drx/cif/simulate", methods=["POST"])
    def api_drx_cif_simulate():
        """Simulate an auxiliary reference XRD pattern from an uploaded CIF."""
        if _request_exceeds_upload_limit(DRX_REFERENCE_UPLOAD_MAX_BYTES):
            return _upload_too_large_response(DRX_REFERENCE_UPLOAD_MAX_BYTES)
        uploaded = request.files.get("cif_file") or request.files.get("file")
        if not uploaded:
            return jsonify({"success": False, "error": "Envie um arquivo .cif para simulacao DRX."}), 400
        original_filename = uploaded.filename or "reference.cif"
        if Path(original_filename).suffix.lower() != ".cif":
            return jsonify({"success": False, "error": "A simulacao aceita apenas arquivos .cif."}), 400
        try:
            content = _read_limited_upload(uploaded, DRX_REFERENCE_UPLOAD_MAX_BYTES)
            if content is None:
                return _upload_too_large_response(DRX_REFERENCE_UPLOAD_MAX_BYTES)
            payload = build_cif_simulation_payload(
                content,
                filename=original_filename,
                wavelength=request.form.get("wavelength") or request.args.get("wavelength") or "CuKa",
                max_peaks=_bounded_int_arg("max_peaks", 200, minimum=1, maximum=500),
            )
            return jsonify(payload), 200 if payload.get("success") else 503
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ), 500

    @blueprint.route(
        "/api/argiloteca/drx/workflows/ngc",
        methods=["POST"],
        endpoint="api_drx_ngc_workflow",
    )
    @blueprint.route("/argiloteca/drx/workflows/ngc", methods=["POST"])
    def api_drx_ngc_workflow():
        """Build an auxiliary N/G/C clay-mineral workflow interpretation."""
        try:
            body = request.get_json(silent=True) or {}
            items = [item for item in body.get("items") or [] if isinstance(item, dict)]
            for diffractogram_id in body.get("diffractogram_ids") or []:
                curve_payload = load_diffractogram_data(diffractogram_id)
                if curve_payload is None:
                    items.append(
                        {
                            "id": diffractogram_id,
                            "warnings": ["Difratograma nao encontrado."],
                        }
                    )
                    continue
                metadata = curve_payload.get("metadata") or {}
                report_payload = _build_technical_report_for_curve(
                    diffractogram_id,
                    curve_payload,
                    max_points=_bounded_int_arg("max_points", 3000, maximum=5000),
                    include_processing=True,
                )
                advanced_processing = (report_payload or {}).get("advanced_processing") or {}
                filename = metadata.get("original_filename") or metadata.get("filename") or diffractogram_id
                sample_code = metadata.get("sample_code") or Path(str(filename)).stem
                items.append(
                    {
                        "id": diffractogram_id,
                        "filename": filename,
                        "sample_code": sample_code,
                        "sample_base": infer_diffractogram_sample_base(sample_code, filename),
                        "preparation": metadata.get("preparation") or metadata.get("treatment"),
                        "peaks": advanced_processing.get("peaks") or metadata.get("detected_peaks") or [],
                        "targeted_basal_peaks": advanced_processing.get("targeted_basal_peaks")
                        or metadata.get("targeted_basal_peaks")
                        or [],
                        "advanced_peaks": advanced_processing.get("peaks") or [],
                        "fit_results": advanced_processing.get("fit_results") or [],
                        "metadata": metadata,
                    }
                )
            payload = build_ngc_workflow(items)
            return jsonify(payload)
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ), 500

    @blueprint.route(
        "/api/argiloteca/drx/reports/selection",
        methods=["POST"],
        endpoint="api_drx_selection_report",
    )
    @blueprint.route("/argiloteca/drx/reports/selection", methods=["POST"])
    def api_drx_selection_report():
        """Return a reproducible backend report for the selected DRX set."""
        try:
            body = request.get_json(silent=True) or {}
            items = [item for item in body.get("items") or [] if isinstance(item, dict)]
            for diffractogram_id in body.get("diffractogram_ids") or []:
                curve_payload = load_diffractogram_data(diffractogram_id)
                if curve_payload is None:
                    items.append(
                        {
                            "id": diffractogram_id,
                            "warnings": ["Difratograma nao encontrado."],
                        }
                    )
                    continue
                metadata = curve_payload.get("metadata") or {}
                report_payload = _build_technical_report_for_curve(
                    diffractogram_id,
                    curve_payload,
                    max_points=_bounded_int_arg("max_points", 3000, maximum=5000),
                    include_processing=True,
                )
                advanced_processing = (report_payload or {}).get("advanced_processing") or {}
                filename = metadata.get("original_filename") or metadata.get("filename") or diffractogram_id
                sample_code = metadata.get("sample_code") or Path(str(filename)).stem
                items.append(
                    {
                        "id": diffractogram_id,
                        "filename": filename,
                        "sample_code": sample_code,
                        "sample_base": infer_diffractogram_sample_base(sample_code, filename),
                        "preparation": metadata.get("preparation") or metadata.get("treatment"),
                        "peaks": advanced_processing.get("peaks") or metadata.get("detected_peaks") or [],
                        "metadata": metadata,
                    }
                )
            ngc_workflow = body.get("ngc_workflow") if isinstance(body.get("ngc_workflow"), dict) else build_ngc_workflow(items)
            payload = build_drx_selection_report(
                items=items,
                ngc_workflow=ngc_workflow,
                view_parameters=body.get("view_parameters") if isinstance(body.get("view_parameters"), dict) else {},
            )
            return jsonify(payload)
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ), 500

    @blueprint.route("/api/argiloteca/drx/runs", methods=["GET", "POST"], endpoint="api_drx_runs")
    @blueprint.route("/argiloteca/drx/runs", methods=["GET", "POST"])
    def api_drx_runs():
        """List or persist versioned DRX analysis artifacts."""
        try:
            if request.method == "GET":
                return jsonify(
                    list_drx_runs(
                        record_id=request.args.get("record_id") or None,
                        sample_code=request.args.get("sample_code") or None,
                        limit=_bounded_int_arg("limit", 50, minimum=1, maximum=250),
                    )
                )
            body = request.get_json(silent=True) or {}
            diffractogram_id = body.get("diffractogram_id") or request.form.get("diffractogram_id")
            analysis_run = body.get("analysis_run") if isinstance(body.get("analysis_run"), dict) else None
            technical_report = body.get("technical_report") if isinstance(body.get("technical_report"), dict) else None
            selection_report = body.get("selection_report") if isinstance(body.get("selection_report"), dict) else None
            inputs = body.get("inputs") if isinstance(body.get("inputs"), dict) else {}
            outputs = body.get("outputs") if isinstance(body.get("outputs"), dict) else {}
            parameters = body.get("parameters") if isinstance(body.get("parameters"), dict) else {}
            if diffractogram_id and not analysis_run:
                curve_payload = load_diffractogram_data(diffractogram_id)
                if curve_payload is None:
                    return jsonify({"success": False, "error": "Difratograma nao encontrado"}), 404
                report_payload = _build_technical_report_for_curve(
                    diffractogram_id,
                    curve_payload,
                    max_points=_bounded_int_arg("max_points", 3000, maximum=5000),
                    include_processing=True,
                )
                if report_payload is None:
                    return jsonify({"success": False, "error": "Curva sem pontos para run DRX."}), 404
                analysis_run = report_payload.get("analysis_run")
                technical_report = report_payload.get("technical_report")
                metadata = curve_payload.get("metadata") or {}
                inputs = {
                    **inputs,
                    "diffractogram_id": diffractogram_id,
                    "metadata": {
                        key: metadata.get(key)
                        for key in ("sample_code", "original_filename", "filename", "source_sha256", "record_id")
                        if metadata.get(key) is not None
                    },
                }
                outputs = {
                    **outputs,
                    "peak_count": len((report_payload.get("advanced_processing") or {}).get("peaks") or []),
                    "fit_count": len((report_payload.get("advanced_processing") or {}).get("fit_results") or []),
                }
            if not (analysis_run or technical_report or selection_report):
                return jsonify({"success": False, "error": "Informe diffractogram_id, analysis_run, technical_report ou selection_report."}), 400
            payload = persist_drx_run(
                analysis_run=analysis_run,
                technical_report=technical_report,
                selection_report=selection_report,
                inputs=inputs,
                outputs=outputs,
                parameters=parameters,
                record_id=body.get("record_id") or request.form.get("record_id"),
                sample_code=body.get("sample_code") or request.form.get("sample_code"),
                run_id=body.get("run_id") or request.form.get("run_id"),
            )
            return jsonify(payload), 201
        except Exception as e:
            return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500

    @blueprint.route("/api/argiloteca/drx/runs/<run_id>", endpoint="api_drx_run_detail")
    @blueprint.route("/argiloteca/drx/runs/<run_id>")
    def api_drx_run_detail(run_id):
        """Return one persisted DRX run artifact."""
        payload = get_drx_run(run_id)
        return jsonify(payload), 200 if payload.get("success") else 404

    @blueprint.route(
        "/api/argiloteca/drx/references",
        endpoint="api_drx_references",
    )
    @blueprint.route("/argiloteca/drx/references")
    def api_drx_references():
        """Search compact DRX reference-pattern indexes with provenance."""
        try:
            payload = search_reference_index(
                query=request.args.get("q") or request.args.get("query"),
                source=request.args.get("source"),
                limit=_bounded_int_arg("limit", 25, minimum=1, maximum=100),
            )
            return jsonify(payload)
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ), 500

    @blueprint.route(
        "/api/argiloteca/drx/jobs/external",
        methods=["GET", "POST"],
        endpoint="api_drx_external_job_submit",
    )
    @blueprint.route("/argiloteca/drx/jobs/external", methods=["GET", "POST"])
    def api_drx_external_job_submit():
        """Register a GSAS-II/DARA-style job for out-of-request execution."""
        if request.method == "GET":
            return jsonify(
                list_external_jobs(
                    status=request.args.get("status") or None,
                    limit=_bounded_int_arg("limit", 50, minimum=1, maximum=250),
                )
            )
        payload = request.get_json(silent=True) or request.form.to_dict(flat=True) or {}
        engine = payload.get("engine") or request.args.get("engine")
        result = submit_external_job(engine, payload=payload)
        return jsonify(result), 202 if result.get("success") else 400

    @blueprint.route(
        "/api/argiloteca/drx/jobs/external/<job_id>",
        endpoint="api_drx_external_job_status",
    )
    @blueprint.route("/argiloteca/drx/jobs/external/<job_id>")
    def api_drx_external_job_status(job_id):
        """Return the persisted status of a registered external DRX job."""
        result = get_external_job(job_id)
        return jsonify(result), 200 if result.get("success") else 404

    @blueprint.route(
        "/api/argiloteca/drx/references/compare/<diffractogram_id>",
        methods=["POST"],
        endpoint="api_drx_reference_compare",
    )
    @blueprint.route("/argiloteca/drx/references/compare/<diffractogram_id>", methods=["POST"])
    def api_drx_reference_compare(diffractogram_id):
        """Compare one selected DRX curve against an uploaded reference pattern."""
        if _request_exceeds_upload_limit(DRX_REFERENCE_UPLOAD_MAX_BYTES):
            return _upload_too_large_response(DRX_REFERENCE_UPLOAD_MAX_BYTES)
        uploaded = request.files.get("reference_file") or request.files.get("file")
        if not uploaded:
            return jsonify({"success": False, "error": "Envie um arquivo de referencia .json, .csv, .txt, .xy, .dat ou .cif."}), 400
        original_filename = uploaded.filename or "referencia.json"
        suffix = Path(original_filename).suffix.lower()
        if suffix not in {".json", ".csv", ".txt", ".xy", ".dat", ".cif"}:
            return jsonify({"success": False, "error": "Referencia precisa ser .json, .csv, .txt, .xy, .dat ou .cif."}), 400
        try:
            curve_payload = load_diffractogram_data(diffractogram_id)
            if curve_payload is None:
                return jsonify({"success": False, "error": "Difratograma nao encontrado"}), 404
            report_payload = _build_technical_report_for_curve(
                diffractogram_id,
                curve_payload,
                max_points=_bounded_int_arg("max_points", 3000, maximum=5000),
                include_processing=True,
            )
            if report_payload is None:
                return jsonify({"success": False, "error": "Curva sem pontos para comparacao."}), 404
            reference_content = _read_limited_upload(uploaded, DRX_REFERENCE_UPLOAD_MAX_BYTES)
            if reference_content is None:
                return _upload_too_large_response(DRX_REFERENCE_UPLOAD_MAX_BYTES)
            wavelength_angstrom = _bounded_float_arg("wavelength_angstrom", 1.5406)
            reference_pattern = parse_reference_pattern_bytes(
                reference_content,
                filename=original_filename,
                wavelength=wavelength_angstrom,
            )
            comparison = compare_reference_pattern(
                report_payload["advanced_processing"].get("peaks") or [],
                reference_pattern,
                tolerance_two_theta=float(request.form.get("tolerance_two_theta") or request.args.get("tolerance_two_theta") or 0.25),
            )
            technical_report = build_drx_technical_report(
                analysis_run=report_payload["analysis_run"],
                advanced_processing=report_payload["advanced_processing"],
                identification={
                    "peaks": [],
                    "candidates": [],
                    "reference_source": "uploaded_reference_pattern",
                },
                diagnostic_evidence=report_payload["diagnostic_evidence"],
                reference_comparison=comparison,
            )
            return jsonify(
                {
                    "success": True,
                    "diffractogram_id": diffractogram_id,
                    "reference_pattern": reference_pattern,
                    "reference_comparison": comparison,
                    "technical_report": technical_report,
                }
            )
        except RawParseError as e:
            return jsonify({"success": False, "error": str(e)}), 400
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ), 500

    @blueprint.route(
        "/api/argiloteca/drx/references/compare-indexed/<diffractogram_id>",
        methods=["POST"],
        endpoint="api_drx_reference_compare_indexed",
    )
    @blueprint.route("/argiloteca/drx/references/compare-indexed/<diffractogram_id>", methods=["POST"])
    def api_drx_reference_compare_indexed(diffractogram_id):
        """Compare one selected DRX curve against a curated indexed reference."""
        try:
            body = request.get_json(silent=True) or {}
            reference_id = (body.get("reference_id") or request.form.get("reference_id") or request.args.get("reference_id") or "").strip()
            if not reference_id:
                return jsonify({"success": False, "error": "Informe reference_id da referencia indexada."}), 400
            curve_payload = load_diffractogram_data(diffractogram_id)
            if curve_payload is None:
                return jsonify({"success": False, "error": "Difratograma nao encontrado"}), 404
            report_payload = _build_technical_report_for_curve(
                diffractogram_id,
                curve_payload,
                max_points=_bounded_int_arg("max_points", 3000, maximum=5000),
                include_processing=True,
            )
            if report_payload is None:
                return jsonify({"success": False, "error": "Curva sem pontos para comparacao."}), 404
            reference_pattern = reference_pattern_from_index(reference_id)
            if not reference_pattern.get("success"):
                return jsonify(reference_pattern), 404
            comparison = compare_reference_pattern(
                report_payload["advanced_processing"].get("peaks") or [],
                reference_pattern,
                tolerance_two_theta=float(body.get("tolerance_two_theta") or request.args.get("tolerance_two_theta") or 0.25),
            )
            comparison["reference_id"] = reference_id
            comparison["reference_source"] = reference_pattern.get("source")
            technical_report = build_drx_technical_report(
                analysis_run=report_payload["analysis_run"],
                advanced_processing=report_payload["advanced_processing"],
                identification={
                    "peaks": [],
                    "candidates": [],
                    "reference_source": "indexed_reference_pattern",
                },
                diagnostic_evidence=report_payload["diagnostic_evidence"],
                reference_comparison=comparison,
            )
            return jsonify(
                {
                    "success": True,
                    "diffractogram_id": diffractogram_id,
                    "reference_pattern": reference_pattern,
                    "reference_comparison": comparison,
                    "technical_report": technical_report,
                }
            )
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ), 500

    @blueprint.route(
        "/api/argiloteca/drx/neural-evidence/<diffractogram_id>",
        endpoint="api_drx_neural_evidence",
    )
    @blueprint.route("/argiloteca/drx/neural-evidence/<diffractogram_id>")
    def api_drx_neural_evidence(diffractogram_id):
        """Return precomputed auxiliary neural evidence for one DRX curve."""
        try:
            curve_payload = load_diffractogram_data(diffractogram_id) or {}
            metadata = curve_payload.get("metadata") or {}
            payload = neural_evidence_for_diffractogram(diffractogram_id, metadata=metadata)
            status = 200 if payload.get("success") else 404
            if payload.get("available") and not payload.get("matched"):
                status = 404
            if not payload.get("available"):
                status = 503
            return jsonify(payload), status
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ), 500

    @blueprint.route(
        "/api/argiloteca/drx/externo/curva",
        methods=["POST"],
        endpoint="api_drx_externo_curva",
    )
    @blueprint.route("/argiloteca/drx/externo/curva", methods=["POST"])
    def api_drx_externo_curva():
        """Parse and compare a temporary external diffractogram upload.

        O upload nao e persistido. A rota alinha o eixo por heuristica N/G/C ou
        quartzo 101 para RAW, calcula evidencias ALS/FWHM e compara com
        snapshot/pacotes.
        """
        if _request_exceeds_upload_limit(DRX_TEMP_UPLOAD_MAX_BYTES):
            return _upload_too_large_response(DRX_TEMP_UPLOAD_MAX_BYTES)
        uploaded = request.files.get("file")
        if not uploaded:
            return jsonify({"success": False, "error": "Envie um arquivo .raw, .csv, .txt, .xy ou .dat para comparação temporária."}), 400
        original_filename = uploaded.filename or "arquivo_externo.raw"
        suffix = Path(original_filename).suffix.lower()
        if suffix not in {".raw", ".csv", ".txt", ".xy", ".dat"}:
            return jsonify({"success": False, "error": "O arquivo externo precisa ter extensão .raw, .csv, .txt, .xy ou .dat."}), 400
        try:
            content = _read_limited_upload(uploaded, DRX_TEMP_UPLOAD_MAX_BYTES)
            if content is None:
                return _upload_too_large_response(DRX_TEMP_UPLOAD_MAX_BYTES)
            raw_sha256 = hashlib.sha256(content).hexdigest()
            parsed = parse_diffractogram_bytes(content, filename=original_filename)
            sample_code = request.form.get("sample_code") or Path(original_filename).stem
            treatment = infer_diffractogram_treatment(sample_code, original_filename)
            current_start = parsed.metadata.get("two_theta_start")
            external_target_start = None
            # Alguns RAWs glicolados externos chegam iniciando perto de 3 graus,
            # enquanto os pares N/G/C locais sao exibidos ancorados em 2 graus.
            is_raw_upload = suffix == ".raw"
            if is_raw_upload and treatment.get("type") == "glicolado" and current_start is not None and abs(float(current_start) - 3.0) <= 0.25:
                external_target_start = 2.0
            quartz_offset = None if (not is_raw_upload or external_target_start is not None) else calculate_quartz_axis_offset(parsed.two_theta, parsed.intensity)
            if external_target_start is not None or quartz_offset:
                parsed = apply_two_theta_axis_alignment(
                    parsed,
                    filename=original_filename,
                    sample_code=sample_code,
                    sample_base=infer_diffractogram_sample_base(sample_code, original_filename),
                    treatment=treatment.get("type"),
                    target_start=external_target_start,
                    absolute_offset=quartz_offset,
                    manual_corrections={},
                )
                if external_target_start is not None and parsed.metadata.get("two_theta_offset_applied") is not None:
                    parsed.metadata["two_theta_alignment_method"] = "ngc_external_glycolated_start_heuristic"
                    parsed.metadata["curve_source"] = "arquivo_externo_com_eixo_ajustado"
                elif quartz_offset and parsed.metadata.get("two_theta_offset_applied") is not None:
                    parsed.metadata["curve_source"] = "arquivo_externo_calibrado_por_quartzo_101"
            max_points = _bounded_int_arg("max_points", 3000, maximum=5000)
            identification = _identify_drx_candidates(parsed.two_theta, parsed.intensity)
            analysis_payload = build_drx_analysis_run(
                filename=original_filename,
                sample_code=sample_code,
                source_sha256=raw_sha256,
                parsed=parsed,
                identification=identification,
                preparation=treatment.get("type"),
                max_points=max_points,
                stored=False,
                wavelength_angstrom=_bounded_float_arg("wavelength_angstrom", 1.5406),
            )
            advanced_processing = analysis_payload["advanced_processing"]
            advanced_summary = analysis_payload["advanced_summary"]
            advanced_curve = analysis_payload["advanced_curve"]
            analysis_run = analysis_payload["analysis_run"]
            diagnostic_evidence = analysis_payload["diagnostic_evidence"]
            technical_report = build_drx_technical_report(
                analysis_run=analysis_run,
                advanced_processing=advanced_processing,
                identification=identification,
                diagnostic_evidence=diagnostic_evidence,
            )
            record_id = (request.form.get("record_id") or request.args.get("record_id") or "").strip()
            similarity_scope = (
                request.form.get("similarity_scope")
                or request.args.get("similarity_scope")
                or ("record" if record_id else "snapshot")
            ).strip().lower()
            # A comparacao global e opt-in porque varrer todos os pacotes DRX e
            # mais caro que verificar o contexto do registro ou o snapshot geral.
            package_similarity = compare_external_curve_to_package(
                record_id,
                original_filename=original_filename,
                raw_sha256=raw_sha256,
                metadata=parsed.metadata,
                two_theta=parsed.two_theta,
                intensity=parsed.intensity,
                detected_peaks=advanced_processing.get("peaks") or identification.get("peaks") or [],
                mineral_candidates=identification.get("candidates") or [],
                global_package_scan=similarity_scope in {"all", "global", "packages", "pacotes"},
            )
            two_theta, intensity = decimate_series(
                parsed.two_theta,
                parsed.intensity,
                max_points=max_points,
            )
            metadata = {
                **parsed.metadata,
                "original_filename": original_filename,
                "sample_code": sample_code,
                "source": "arquivo_externo_temporario",
                "source_sha256": raw_sha256,
                "stored": False,
                "mineral_classification_source": identification.get("reference_source"),
                "mineral_classification_error": identification.get("classification_error"),
                "advanced_summary": advanced_summary,
                "advanced_curve": advanced_curve,
                "peak_processing": advanced_processing.get("peak_processing") or {},
                "xrd_method": advanced_processing.get("xrd_method") or {},
                "qc_flags": advanced_processing.get("qc_flags") or [],
            }
            metadata["analysis_run"] = analysis_run
            metadata["diagnostic_evidence"] = diagnostic_evidence
            metadata["technical_report"] = technical_report
            return jsonify(
                {
                    "success": True,
                    "sample_code": sample_code,
                    "filename": original_filename,
                    "analysis_run": analysis_run,
                    "technical_report": technical_report,
                    "diagnostic_evidence": diagnostic_evidence,
                    "metadata": metadata,
                    "detected_peaks": identification.get("peaks") or [],
                    "advanced_peaks": advanced_processing.get("peaks") or [],
                    "fit_results": advanced_processing.get("fit_results") or [],
                    "qc_flags": advanced_processing.get("qc_flags") or [],
                    "mineral_evidence": advanced_processing.get("mineral_evidence") or [],
                    "mineral_characterization": advanced_processing.get("mineral_characterization") or [],
                    "basal_tracking": advanced_processing.get("basal_tracking") or {},
                    "advanced_summary": advanced_summary,
                    "advanced_curve": advanced_curve,
                    "mineral_candidates": identification.get("candidates") or [],
                    "package_similarity": package_similarity,
                    "two_theta": two_theta,
                    "intensity": intensity,
                    "render_points": len(two_theta),
                    "total_points": len(parsed.two_theta),
                }
            )
        except RawParseError as e:
            return jsonify({"success": False, "error": str(e)}), 400
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ), 500

    @blueprint.route(
        "/api/argiloteca/drx/importar",
        methods=["POST"],
        endpoint="api_drx_importar",
    )
    @blueprint.route("/argiloteca/drx/importar", methods=["POST"])
    def api_drx_importar():
        """Import a RAW into the local DRX index for one published record."""
        body = request.get_json(silent=True) or {}
        record_id = (request.form.get("record_id") or body.get("record_id") or "").strip()
        sample_code = request.form.get("sample_code") or body.get("sample_code")
        local_path = request.form.get("path") or body.get("path")
        uploaded = request.files.get("file")

        if not record_id:
            return jsonify({"success": False, "error": "Informe o record_id do registro de argila."}), 400
        if not uploaded and not local_path:
            return jsonify({"success": False, "error": "Envie um arquivo .raw ou informe um caminho local autorizado."}), 400

        try:
            if not record_exists(record_id, size=_bounded_int_arg("record_lookup_size", 5000, maximum=10000)):
                return jsonify(
                    {
                        "success": False,
                        "error": "Registro de argila nao encontrado. Informe um record_id publicado da Argiloteca.",
                    }
                ), 404
            if uploaded:
                item = import_raw_upload(record_id=record_id, storage=uploaded, sample_code=sample_code)
            else:
                item = import_raw_path(record_id=record_id, path=local_path, sample_code=sample_code)
            return jsonify({"success": True, "diffractogram": item}), 201
        except RawParseError as e:
            original_name = uploaded.filename if uploaded else Path(local_path or "arquivo.raw").name
            item = record_import_error(record_id, original_name, str(e), sample_code=sample_code)
            return jsonify({"success": False, "error": str(e), "diffractogram": item}), 422
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ), 500

    @blueprint.route(
        "/api/argiloteca/geoquimica/rede",
        endpoint="api_geoquimica_rede",
    )
    @blueprint.route("/argiloteca/geoquimica/rede")
    def api_geoquimica_rede():
        """Return the geoquimica analogy network or its local snapshot."""
        try:
            snapshot = _load_json_snapshot(_GEO_NET_SNAPSHOT_PATH)
            if snapshot is not None and not request.args:
                return jsonify(snapshot)
            filters = {
                "classe_geoquimica": request.args.get("classe_geoquimica") or None,
                "mineral_group": request.args.get("mineral_group") or None,
                "argilomineral": request.args.get("argilomineral") or None,
                "ambiente_formacao": request.args.get("ambiente_formacao") or None,
                "rocha_hospedeira": request.args.get("rocha_hospedeira") or None,
                "era_geologica": request.args.get("era_geologica") or None,
                "relation_type": request.args.get("relation_type") or None,
                "analogy_class": request.args.get("analogy_class") or None,
                "confidence_class": request.args.get("confidence_class") or None,
                "analysis_mode": request.args.get("analysis_mode") or None,
                "sio2_min": parse_float(request.args.get("sio2_min")),
                "sio2_max": parse_float(request.args.get("sio2_max")),
                "al2o3_min": parse_float(request.args.get("al2o3_min")),
                "al2o3_max": parse_float(request.args.get("al2o3_max")),
                "fe2o3_min": parse_float(request.args.get("fe2o3_min")),
                "fe2o3_max": parse_float(request.args.get("fe2o3_max")),
                "tio2_min": parse_float(request.args.get("tio2_min")),
                "tio2_max": parse_float(request.args.get("tio2_max")),
                "fracao_min": parse_float(request.args.get("fracao_min")),
                "fracao_max": parse_float(request.args.get("fracao_max")),
                "razao_si_al_min": parse_float(request.args.get("razao_si_al_min")),
                "razao_si_al_max": parse_float(request.args.get("razao_si_al_max")),
            }

            cache_key = _request_cache_key("geoquimica_rede")
            cached = _cache_get(cache_key)
            if cached is not None:
                return jsonify(cached)
            network = build_network(
                filters=filters,
                metric=request.args.get("metric", "cosine"),
                edge_mode=request.args.get("edge_mode", "knn"),
                k=parse_float(request.args.get("k")) or 3,
                threshold=parse_float(request.args.get("threshold")) or 0.8,
                analysis_mode=request.args.get("analysis_mode", "composite"),
                size=_bounded_int_arg("size", 120, maximum=250),
            )
            return jsonify(_cache_set(cache_key, network))
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "nodes": [],
                    "edges": [],
                    "clusters": [],
                }
            ), 500

    @blueprint.route(
        "/api/argiloteca/geoquimica/agregada",
        endpoint="api_geoquimica_agregada",
    )
    @blueprint.route("/argiloteca/geoquimica/agregada")
    def api_geoquimica_agregada():
        """Return aggregated geochemical rows or their local snapshot."""
        try:
            snapshot = _load_json_snapshot(_GEO_AGG_SNAPSHOT_PATH)
            if snapshot is not None and not request.args:
                return jsonify(snapshot)
            filters = {
                "q": request.args.get("q") or None,
                "eon": request.args.get("eon") or None,
                "era": request.args.get("era") or None,
                "periodo": request.args.get("periodo") or None,
                "epoca": request.args.get("epoca") or None,
                "mineral_group": request.args.get("mineral_group") or None,
                "argilomineral": request.args.get("argilomineral") or None,
                "has_sample": request.args.get("has_sample") or None,
                "sio2_min": parse_float(request.args.get("sio2_min")),
                "sio2_max": parse_float(request.args.get("sio2_max")),
                "al2o3_min": parse_float(request.args.get("al2o3_min")),
                "al2o3_max": parse_float(request.args.get("al2o3_max")),
                "fe2o3_min": parse_float(request.args.get("fe2o3_min")),
                "fe2o3_max": parse_float(request.args.get("fe2o3_max")),
                "mgo_min": parse_float(request.args.get("mgo_min")),
                "mgo_max": parse_float(request.args.get("mgo_max")),
            }
            cache_key = _request_cache_key("geoquimica_agregada")
            cached = _cache_get(cache_key)
            if cached is not None:
                return jsonify(cached)
            dataset = build_aggregated_dataset(filters=filters, size=_bounded_int_arg("size", 200, maximum=500))
            return jsonify(_cache_set(cache_key, dataset))
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "records": [],
                }
            ), 500

    @blueprint.route(
        "/api/argiloteca/geoquimica/registro/<record_id>",
        endpoint="api_geoquimica_registro",
    )
    @blueprint.route("/argiloteca/geoquimica/registro/<record_id>")
    def api_geoquimica_registro(record_id):
        """Return normalized geoquimica detail for one record."""
        try:
            detail = find_record_detail(record_id)
            if not detail:
                return jsonify({"success": False, "error": "Registro nao encontrado"}), 404
            return jsonify({"success": True, "record": detail})
        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ), 500

    return blueprint
