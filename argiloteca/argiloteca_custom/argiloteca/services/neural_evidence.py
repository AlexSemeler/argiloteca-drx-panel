"""
Projeto: Painel DRX Argiloteca

Descrição:
Auxiliary neural evidence lookup for the DRX comparison panel. The service reads a compact, precomputed JSON index. It intentionally does not scan the DiffractGPT/XRDNet output tree during web requests.

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
import os
import re
from functools import lru_cache
from pathlib import Path


DEFAULT_INSTANCE_PATH = Path(
    os.environ.get(
        "INVENIO_INSTANCE_PATH",
        Path(__file__).resolve().parents[3] / "var" / "instance",
    )
)
DEFAULT_LOCAL_INSTANCE_PATH = Path(__file__).resolve().parents[4] / "instance"
NEURAL_EVIDENCE_INDEX_PATH = Path(
    os.environ.get(
        "ARGILOTECA_DRX_NEURAL_EVIDENCE_INDEX",
        (
            DEFAULT_INSTANCE_PATH / "argiloteca_drx_neural" / "neural_evidence_index.json"
            if (DEFAULT_INSTANCE_PATH / "argiloteca_drx_neural" / "neural_evidence_index.json").exists()
            else DEFAULT_LOCAL_INSTANCE_PATH / "argiloteca_drx_neural" / "neural_evidence_index.json"
        ),
    )
)


def _normalize_key(value):
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


def _basename_key(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return _normalize_key(Path(str(value or "").replace("\\", "/")).name)


def _path_suffix_keys(value):
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
    keys = []
    parts = text.split("/")
    for marker in ("raw-classificados", "raw", "data"):
        if marker in parts:
            suffix = "/".join(parts[parts.index(marker) + 1 :])
            if suffix:
                keys.append(_normalize_key(suffix))
    keys.append(_normalize_key(text))
    return [key for key in dict.fromkeys(keys) if key]


def _entry_keys(entry):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        entry: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    keys = set()
    for field in (
        "diffractogram_id",
        "sample_id",
        "filename",
        "source_curve",
        "source_sha256",
        "record_id",
    ):
        value = entry.get(field)
        if value:
            keys.add(_normalize_key(value))
            if field in {"filename", "source_curve"}:
                keys.add(_basename_key(value))
                keys.update(_path_suffix_keys(value))
    for key in entry.get("match_keys") or []:
        if key:
            keys.add(_normalize_key(key))
    return {key for key in keys if key}


def _metadata_keys(diffractogram_id, metadata=None):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        diffractogram_id: Valor de entrada consumido por esta etapa do fluxo.
        metadata: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    metadata = metadata or {}
    keys = set()
    values = [
        diffractogram_id,
        metadata.get("id"),
        metadata.get("diffractogram_id"),
        metadata.get("sample_code"),
        metadata.get("sample_base"),
        metadata.get("filename"),
        metadata.get("original_filename"),
        metadata.get("raw_path"),
        metadata.get("source_curve"),
        metadata.get("curve_path"),
        metadata.get("advanced_result_path"),
        metadata.get("sha256"),
        metadata.get("source_sha256"),
    ]
    traceability = metadata.get("traceability") if isinstance(metadata.get("traceability"), dict) else {}
    values.extend(
        [
            traceability.get("raw_path"),
            traceability.get("source_curve"),
            traceability.get("filename"),
        ]
    )
    for value in values:
        if not value:
            continue
        keys.add(_normalize_key(value))
        keys.add(_basename_key(value))
        keys.update(_path_suffix_keys(value))
    return {key for key in keys if key}


@lru_cache(maxsize=4)
def _load_index_cached(index_path, mtime):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        index_path: Valor de entrada consumido por esta etapa do fluxo.
        mtime: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    path = Path(index_path)
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    entries = payload.get("entries") or []
    by_key = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        for key in _entry_keys(entry):
            by_key.setdefault(key, index)
    return {
        "payload": payload,
        "entries": entries,
        "by_key": by_key,
        "mtime": mtime,
    }


def load_neural_evidence_index(path=None):
    """Load the compact neural evidence index with cache invalidation by mtime."""
    index_path = Path(path or NEURAL_EVIDENCE_INDEX_PATH)
    if not index_path.exists():
        return {
            "available": False,
            "index_path": str(index_path),
            "entries": [],
            "by_key": {},
            "payload": {},
        }
    mtime = index_path.stat().st_mtime
    loaded = _load_index_cached(str(index_path), mtime)
    return {
        "available": True,
        "index_path": str(index_path),
        **loaded,
    }


def neural_evidence_for_diffractogram(diffractogram_id, metadata=None, path=None):
    """Return auxiliary neural evidence matched to a selected DRX curve."""
    index = load_neural_evidence_index(path=path)
    if not index.get("available"):
        return {
            "success": False,
            "available": False,
            "error": "Indice de evidencia neural auxiliar nao encontrado.",
            "index_path": index.get("index_path"),
        }
    lookup_keys = _metadata_keys(diffractogram_id, metadata=metadata)
    matched_key = None
    entry = None
    for key in lookup_keys:
        entry_index = index["by_key"].get(key)
        if entry_index is not None:
            entry = index["entries"][entry_index]
            matched_key = key
            break
    if not entry:
        return {
            "success": False,
            "available": True,
            "matched": False,
            "error": "Nenhuma evidencia neural auxiliar corresponde a este difratograma.",
            "lookup_keys": sorted(lookup_keys)[:16],
            "index_path": index.get("index_path"),
        }
    return {
        "success": True,
        "available": True,
        "matched": True,
        "matched_key": matched_key,
        "schema_version": index["payload"].get("schema_version"),
        "generated_at": index["payload"].get("generated_at"),
        "usage_policy": "auxiliary_not_confirmatory",
        "source": index["payload"].get("source") or {},
        "evidence": entry,
    }
