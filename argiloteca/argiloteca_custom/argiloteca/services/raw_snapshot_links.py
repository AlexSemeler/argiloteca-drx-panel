"""
Projeto: Painel DRX Argiloteca

Descrição:
Optional links from module-wide RAW snapshots to public Argiloteca records. O snapshot geral de RAWs pode existir antes do pacote analitico por registro. Este modulo mantem uma ponte curatorial leve entre esses RAWs e os PIDs publicos da Argiloteca/Invenio, sem depender de acesso ao banco em tempo de UI.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br


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

import hashlib
import json
import os
import re
from functools import lru_cache
from pathlib import Path


DEFAULT_WORKSPACE_PATH = Path(__file__).resolve().parents[4]
DEFAULT_INSTANCE_PATH = Path(
    os.environ.get(
        "INVENIO_INSTANCE_PATH",
        DEFAULT_WORKSPACE_PATH / "var" / "instance",
    )
)
ANALYTICAL_PACKAGES_DIR = Path(
    os.environ.get("ARGILOTECA_ANALYTICAL_PACKAGES_DIR", DEFAULT_INSTANCE_PATH / "argiloteca_analytical_packages")
)
STATIC_ANALYTICAL_PACKAGES_DIR = Path(__file__).resolve().parents[1] / "static" / "data" / "analytical_packages"
RAW_SNAPSHOT_LINKS_PATH = Path(
    os.environ.get("ARGILOTECA_RAW_SNAPSHOT_LINKS_PATH", ANALYTICAL_PACKAGES_DIR / "raw_snapshot_links.jsonl")
)
STATIC_RAW_SNAPSHOT_LINKS_PATH = STATIC_ANALYTICAL_PACKAGES_DIR / "raw_snapshot_links.jsonl"
# Identificadores derivados de caminho preservam rastreabilidade sem expor RAWs
# como registros publicos quando ainda nao ha pacote analitico dedicado.
SNAPSHOT_ID_PREFIX = "snapshot:"
PUBLIC_RECORD_ID_RE = re.compile(r"^[a-z0-9]{5}-[a-z0-9]{5}$", re.IGNORECASE)


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


def snapshot_id_for_path(path) -> str:
    """Create a stable local snapshot id from a RAW path-like value."""
    digest = hashlib.sha256(str(path or "").encode("utf-8")).hexdigest()[:20]
    return f"{SNAPSHOT_ID_PREFIX}{digest}"


def _record_url(record_id):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        record_id: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    value = _safe_text(record_id)
    return f"/records/{value}" if PUBLIC_RECORD_ID_RE.match(value) else None


def _package_url(record_id):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        record_id: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    value = _safe_text(record_id)
    return f"/analises/{value}" if PUBLIC_RECORD_ID_RE.match(value) else None


def _link_sources():
    """Return link manifests in priority order, avoiding duplicate paths."""
    seen = set()
    paths = []
    for path in (RAW_SNAPSHOT_LINKS_PATH, STATIC_RAW_SNAPSHOT_LINKS_PATH):
        path = Path(path)
        marker = str(path)
        if marker in seen:
            continue
        seen.add(marker)
        paths.append(path)
    return paths


def _iter_link_rows(path):
    """Read JSON/JSONL link rows defensively from optional manifests."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    if not text.strip():
        return []
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return []
        if isinstance(payload, dict):
            payload = payload.get("links") or payload.get("items") or []
        return payload if isinstance(payload, list) else []

    rows = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _normalized_link(row, source_path):
    """Normalize one curatorial link row into the payload used by the panel."""
    if not isinstance(row, dict):
        return None
    record_id = _safe_text(row.get("record_id") or row.get("public_record_id"))
    if not record_id:
        return None
    package_record_id = _safe_text(row.get("package_record_id")) or record_id
    record_url = _safe_text(row.get("record_url")) or _record_url(record_id)
    package_url = _safe_text(row.get("package_url")) or _package_url(record_id)
    link = {
        "record_id": record_id,
        "package_record_id": package_record_id,
        "record_url": record_url,
        "package_url": package_url,
        "source": "raw_snapshot_link",
        "raw_snapshot_link_path": str(source_path),
    }
    for field in (
        "diffractogram_id",
        "raw_path",
        "path",
        "filename",
        "original_filename",
        "sample_code",
        "sha256",
        "raw_sha256",
        "note",
    ):
        value = row.get(field)
        if value not in (None, "", [], {}):
            link[field] = value
    raw_path = _safe_text(link.get("raw_path") or link.get("path"))
    if raw_path and not link.get("diffractogram_id"):
        link["diffractogram_id"] = snapshot_id_for_path(raw_path)
    return link


def _index_key(kind, value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        kind: Valor de entrada consumido por esta etapa do fluxo.
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = _safe_text(value)
    if not text:
        return None
    if kind == "filename":
        text = Path(text).name
    return (kind, text.casefold())


def _link_keys(link):
    """Build all lookup keys accepted for the same physical RAW."""
    keys = []
    for kind, value in (
        ("diffractogram_id", link.get("diffractogram_id")),
        ("sha256", link.get("sha256") or link.get("raw_sha256")),
        ("raw_path", link.get("raw_path") or link.get("path")),
        ("filename", link.get("filename") or link.get("original_filename")),
        ("sample_code", link.get("sample_code")),
    ):
        key = _index_key(kind, value)
        if key:
            keys.append(key)
    raw_path = link.get("raw_path") or link.get("path")
    if raw_path:
        key = _index_key("diffractogram_id", snapshot_id_for_path(raw_path))
        if key:
            keys.append(key)
    return keys


def _add_index(index, key, link):
    """Index a key only when it maps unambiguously to one public record."""
    existing = index.get(key)
    if existing is None and key in index:
        return
    if existing and existing.get("record_id") != link.get("record_id"):
        index[key] = None
        return
    index[key] = link


@lru_cache(maxsize=1)
def load_raw_snapshot_links():
    """Load and index snapshot links once per process for API lookups."""
    links = []
    index = {}
    for path in _link_sources():
        for row in _iter_link_rows(path):
            link = _normalized_link(row, path)
            if not link:
                continue
            links.append(link)
            for key in _link_keys(link):
                _add_index(index, key, link)
    return {
        "available": bool(links),
        "links": links,
        "index": index,
        "paths": [str(path) for path in _link_sources()],
    }


def raw_snapshot_link_for_values(
    *,
    diffractogram_id=None,
    sha256=None,
    raw_sha256=None,
    raw_path=None,
    path=None,
    filename=None,
    original_filename=None,
    sample_code=None,
):
    """Resolve a snapshot link from any RAW identifier available in context."""
    payload = load_raw_snapshot_links()
    index = payload.get("index") or {}
    candidates = (
        ("diffractogram_id", diffractogram_id),
        ("sha256", sha256 or raw_sha256),
        ("raw_path", raw_path or path),
        ("filename", filename or original_filename),
        ("sample_code", sample_code),
    )
    for kind, value in candidates:
        key = _index_key(kind, value)
        if not key:
            continue
        link = index.get(key)
        if link:
            return dict(link)
    raw_path_value = raw_path or path
    if raw_path_value:
        key = _index_key("diffractogram_id", snapshot_id_for_path(raw_path_value))
        link = index.get(key)
        if link:
            return dict(link)
    return None


def raw_snapshot_link_for_item(item, *, raw_sha256=None):
    """Resolve a snapshot link from a package/snapshot item payload."""
    item = item or {}
    return raw_snapshot_link_for_values(
        diffractogram_id=item.get("diffractogram_id") or item.get("id"),
        sha256=item.get("sha256") or item.get("raw_sha256") or raw_sha256,
        raw_path=item.get("raw_path") or item.get("path"),
        filename=item.get("filename") or item.get("original_filename"),
        sample_code=item.get("sample_code"),
    )
