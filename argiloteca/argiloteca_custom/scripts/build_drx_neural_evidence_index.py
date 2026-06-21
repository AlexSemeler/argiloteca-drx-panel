#!/usr/bin/env python3
"""
Projeto: Painel DRX Argiloteca

Descrição:
Build the compact auxiliary neural evidence index consumed by the DRX panel.

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

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_SOURCE_DIR = Path("/home/invenio/difract/outputs/drx_argilominerais_webmineral_full")
DEFAULT_XRDNET_SUMMARY = Path("/home/invenio/difract/models/xrdnet_argilominerais_v2_20260616/panel_summary.json")
DEFAULT_OUTPUT = Path("/home/invenio/invenio-project/argiloteca-local/instance/argiloteca_drx_neural/neural_evidence_index.json")


def utc_now_iso():
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_json(path, fallback=None):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
        fallback: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    try:
        with Path(path).open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return fallback


def normalize_key(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = str(value or "").strip().lower().replace("\\", "/")
    if not text:
        return ""
    text = re.sub(r"^[a-z]:/", "", text)
    text = re.sub(r"\.(raw|csv|dat|json)$", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def basename_key(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return normalize_key(Path(str(value or "").replace("\\", "/")).name)


def path_suffix_keys(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return []
    parts = text.split("/")
    keys = []
    for marker in ("raw-classificados", "raw", "data"):
        if marker in parts:
            suffix = "/".join(parts[parts.index(marker) + 1 :])
            if suffix:
                keys.append(normalize_key(suffix))
    keys.append(normalize_key(text))
    return [key for key in dict.fromkeys(keys) if key]


def snapshot_id_for_path(path):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    digest = hashlib.sha256(str(path or "").encode("utf-8")).hexdigest()[:20]
    return f"snapshot:{digest}"


def compact_number(value, digits=4):
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
        return round(float(value), digits)
    except (TypeError, ValueError):
        return value


def compact_match(match):
    """
    Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
    
    Args:
        match: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    observed = match.get("observed_peak") or {}
    reference = match.get("reference") or {}
    return {
        "observed_two_theta": compact_number(observed.get("two_theta")),
        "observed_d_angstrom": compact_number(observed.get("d_angstrom")),
        "observed_relative_intensity": compact_number(observed.get("relative_intensity")),
        "reference_two_theta": compact_number(reference.get("two_theta")),
        "reference_d_angstrom": compact_number(reference.get("d_angstrom")),
        "reference_relative_intensity": compact_number(reference.get("relative_intensity")),
        "delta_two_theta": compact_number(match.get("delta_two_theta")),
        "delta_d_angstrom": compact_number(match.get("delta_d_angstrom")),
        "score": compact_number(match.get("score")),
    }


def compact_candidate(candidate, max_matches):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        candidate: Valor de entrada consumido por esta etapa do fluxo.
        max_matches: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return {
        "mineral": candidate.get("mineral") or candidate.get("title_pt") or candidate.get("argilomineral_id"),
        "argilomineral_id": candidate.get("argilomineral_id"),
        "title_pt": candidate.get("title_pt"),
        "family": candidate.get("family"),
        "category": candidate.get("category"),
        "confidence": candidate.get("confidence"),
        "score": compact_number(candidate.get("score")),
        "coverage_weighted": compact_number(candidate.get("coverage_weighted")),
        "matched_lines": candidate.get("matched_lines"),
        "source": candidate.get("source"),
        "source_url": candidate.get("source_url"),
        "usage": candidate.get("usage") or "triagem_drx",
        "validation_status": candidate.get("validation_status") or "auxiliary_not_confirmatory",
        "notes": candidate.get("notes"),
        "matches": [compact_match(match) for match in (candidate.get("matches") or [])[:max_matches]],
    }


def compact_quality(quality):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        quality: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    metrics = quality.get("metrics") or {}
    wanted = (
        "coverage_fraction_of_requested_range",
        "grid_points",
        "original_points",
        "peaks_in_grid_range",
        "peaks_total",
        "points_in_grid_range",
        "reconstruction_correlation_mapped",
        "reconstruction_r_factor",
        "reconstruction_rmse",
    )
    compact_metrics = {key: compact_number(metrics.get(key)) for key in wanted if key in metrics}
    for range_key in ("range_two_theta", "requested_range_two_theta"):
        if range_key in metrics:
            compact_metrics[range_key] = metrics.get(range_key)
    return {
        "schema_version": quality.get("schema_version"),
        "metrics": compact_metrics,
        "warnings": quality.get("warnings") or [],
    }


def compact_bins(payload, max_bins):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        payload: Valor de entrada consumido por esta etapa do fluxo.
        max_bins: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    bins = payload.get("bins") or []
    ranked = sorted(
        [bin_row for bin_row in bins if isinstance(bin_row, dict)],
        key=lambda row: float(row.get("importance") or 0),
        reverse=True,
    )
    return [
        {
            "two_theta_min": compact_number(row.get("two_theta_min")),
            "two_theta_max": compact_number(row.get("two_theta_max")),
            "importance": compact_number(row.get("importance")),
            "local_peak": row.get("local_peak"),
            "notes": row.get("notes") or [],
        }
        for row in ranked[:max_bins]
    ]


def xrdnet_row_keys(row):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        row: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    values = [
        row.get("curve_id"),
        row.get("sample_id"),
        row.get("source_file"),
        row.get("source_curve"),
        row.get("curve_path"),
        row.get("prediction_path"),
    ]
    keys = set()
    for value in values:
        keys.add(normalize_key(value))
        keys.add(basename_key(value))
        keys.update(path_suffix_keys(value))
    return {key for key in keys if key}


def load_xrdnet_lookup(path):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    summary = load_json(path, fallback={}) if path else {}
    lookup = {}
    for row in summary.get("rows") or []:
        compact = {
            "curve_id": row.get("curve_id"),
            "sample_id": row.get("sample_id"),
            "source_file": row.get("source_file"),
            "source_curve": row.get("source_curve"),
            "status": row.get("status"),
            "labels": (row.get("labels") or [])[:6],
            "top_predictions": (row.get("top_predictions") or [])[:6],
        }
        for key in xrdnet_row_keys(row):
            lookup.setdefault(key, compact)
    return lookup, {
        "path": str(path) if path else "",
        "rows": len(summary.get("rows") or []),
        "model": summary.get("model"),
        "metrics": summary.get("metrics"),
        "schema_version": summary.get("schema_version"),
    }


def evidence_keys(profile, candidates_payload):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        profile: Valor de entrada consumido por esta etapa do fluxo.
        candidates_payload: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    source_curve = profile.get("source_curve")
    filename = profile.get("filename") or Path(str(source_curve or "")).name
    values = [
        profile.get("sample_id"),
        filename,
        source_curve,
        profile.get("source_sha256"),
        profile.get("record_id"),
        candidates_payload.get("sample_id"),
    ]
    keys = set()
    for value in values:
        keys.add(normalize_key(value))
        keys.add(basename_key(value))
        keys.update(path_suffix_keys(value))
    if source_curve:
        keys.add(snapshot_id_for_path(source_curve))
    return sorted(key for key in keys if key)


def find_xrdnet(profile, keys, xrdnet_lookup):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        profile: Valor de entrada consumido por esta etapa do fluxo.
        keys: Valor de entrada consumido por esta etapa do fluxo.
        xrdnet_lookup: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    for key in keys:
        row = xrdnet_lookup.get(key)
        if row:
            return row
    source_curve = profile.get("source_curve")
    if source_curve:
        return xrdnet_lookup.get(basename_key(source_curve))
    return None


def build_index(source_dir, xrdnet_summary, max_candidates, max_matches, max_bins):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        source_dir: Valor de entrada consumido por esta etapa do fluxo.
        xrdnet_summary: Valor de entrada consumido por esta etapa do fluxo.
        max_candidates: Valor de entrada consumido por esta etapa do fluxo.
        max_matches: Valor de entrada consumido por esta etapa do fluxo.
        max_bins: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    xrdnet_lookup, xrdnet_source = load_xrdnet_lookup(xrdnet_summary)
    entries = []
    skipped = []
    for candidate_path in sorted(Path(source_dir).glob("*/drx_ml_candidates.json")):
        sample_dir = candidate_path.parent
        profile = load_json(sample_dir / "drx_ml_profile.json", fallback={}) or {}
        candidates_payload = load_json(candidate_path, fallback={}) or {}
        quality = load_json(sample_dir / "drx_ml_quality.json", fallback={}) or {}
        explain_bins = load_json(sample_dir / "drx_ml_explain_bins.json", fallback={}) or {}
        if not profile and not candidates_payload:
            skipped.append(str(sample_dir))
            continue
        source_curve = profile.get("source_curve") or candidates_payload.get("source_curve")
        filename = profile.get("filename") or Path(str(source_curve or sample_dir.name)).name
        keys = evidence_keys(profile, candidates_payload)
        entry = {
            "sample_id": profile.get("sample_id") or candidates_payload.get("sample_id"),
            "filename": filename,
            "source_curve": source_curve,
            "source_sha256": profile.get("source_sha256"),
            "record_id": profile.get("record_id"),
            "diffractogram_id": snapshot_id_for_path(source_curve) if source_curve else None,
            "output_dir": str(sample_dir),
            "usage_policy": "auxiliary_not_confirmatory",
            "status": "auxiliary_neural_evidence",
            "match_keys": keys,
            "profile": {
                "original_points": profile.get("original_points"),
                "original_range_two_theta": profile.get("original_range_two_theta"),
                "diffractgpt_grid": profile.get("diffractgpt_grid"),
                "source": profile.get("source"),
            },
            "quality": compact_quality(quality),
            "candidates": [
                compact_candidate(candidate, max_matches)
                for candidate in (candidates_payload.get("candidates") or [])[:max_candidates]
            ],
            "explain_bins": compact_bins(explain_bins, max_bins),
            "warnings": list(
                dict.fromkeys(
                    (quality.get("warnings") or [])
                    + (candidates_payload.get("warnings") or [])
                    + (profile.get("warnings") or [])
                )
            ),
        }
        xrdnet = find_xrdnet(profile, keys, xrdnet_lookup)
        if xrdnet:
            entry["xrdnet"] = xrdnet
        entries.append(entry)
    return {
        "schema_version": "argiloteca.drx.neural_evidence_index.v1",
        "generated_at": utc_now_iso(),
        "source": {
            "kind": "precomputed_auxiliary_neural_evidence",
            "source_dir": str(source_dir),
            "xrdnet_summary": xrdnet_source,
            "usage_policy": "auxiliary_not_confirmatory",
        },
        "counts": {
            "entries": len(entries),
            "skipped": len(skipped),
        },
        "entries": entries,
    }


def main():
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--xrdnet-summary", type=Path, default=DEFAULT_XRDNET_SUMMARY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-candidates", type=int, default=5)
    parser.add_argument("--max-matches", type=int, default=6)
    parser.add_argument("--max-bins", type=int, default=8)
    args = parser.parse_args()

    payload = build_index(
        args.source_dir,
        args.xrdnet_summary,
        max_candidates=args.max_candidates,
        max_matches=args.max_matches,
        max_bins=args.max_bins,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"Wrote {payload['counts']['entries']} neural evidence entries to {args.output}")


if __name__ == "__main__":
    main()
