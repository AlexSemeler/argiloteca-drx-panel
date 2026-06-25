"""
Projeto: Painel DRX Argiloteca

Descrição:
Reference-pattern index with provenance for DRX/XRD workflows.

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


Fundamentacao cientifica revisada:
    Este arquivo integra o Painel DRX da Argiloteca, projeto fundamentado nas
    referencias cientificas revisadas para interpretacao auxiliar de DRX de
    argilominerais: Brindley & Brown (1980), Bailey (1980/1988),
    Moore & Reynolds (1989/1997), Drits & Tchoubar (1990),
    Lanson & Bouchet (1995), Meunier, Clays (2005), fluxograma USGS para
    identificacao de argilominerais por DRX e referencias empiricas Pre-Sal
    UFRGS/Petrobras.

Autoria cientifica e curadoria:
    Alexandre Ribas Semeler
    E-mail: alexandre.semler@ufrgs.br

Politica de interpretacao:
    Resultados mineralogicos sao auxiliares e nao confirmatorios. O codigo
    combina comportamento N/G/C, picos companheiros, d060, ambiguidades,
    contexto e proveniencia; nao confirma mineral por pico isolado.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path

from .drx import ADVANCED_ALS_WAVELENGTH_CU
from .drx_references import two_theta_to_d


DRX_REFERENCE_INDEX_SCHEMA = "argiloteca.drx.reference_index.v1"
DRX_INDEXED_REFERENCE_PATTERN_SCHEMA = "argiloteca.drx.indexed_reference_pattern.v1"
DEFAULT_RRUFF_ODR_MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "static"
    / "data"
    / "rruff_odr_argilominerais_20260619"
    / "rruff_odr_curves_manifest.json"
)
DEFAULT_CIF_COD_REFERENCE_MANIFEST = (
    Path(os.environ.get("INVENIO_INSTANCE_PATH") or Path(__file__).resolve().parents[4] / "instance")
    / "argiloteca_drx_references"
    / "cif_cod_reference_index.json"
)


def _normalise_key(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = str(value or "").strip().casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _compact_peak(peak, intensity_max=None):
    """
    Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
    
    Args:
        peak: Valor de entrada consumido por esta etapa do fluxo.
        intensity_max: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    two_theta = peak.get("two_theta")
    try:
        two_theta = float(two_theta)
    except (TypeError, ValueError):
        two_theta = None
    intensity = peak.get("intensity") or peak.get("relative_intensity")
    try:
        intensity = float(intensity)
    except (TypeError, ValueError):
        intensity = None
    if intensity is not None and intensity_max:
        intensity = max(0.0, min(100.0, intensity * 100.0 / intensity_max))
    return {
        "two_theta": round(two_theta, 5) if two_theta is not None else None,
        "d_angstrom": round(two_theta_to_d(two_theta, wavelength=ADVANCED_ALS_WAVELENGTH_CU), 5) if two_theta else None,
        "relative_intensity": round(float(intensity or 0.0), 4),
    }


def _rruff_manifest_path():
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return Path(os.environ.get("ARGILOTECA_DRX_RRUFF_ODR_MANIFEST") or DEFAULT_RRUFF_ODR_MANIFEST)


def _cif_cod_manifest_path():
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return Path(os.environ.get("ARGILOTECA_DRX_CIF_COD_REFERENCE_MANIFEST") or DEFAULT_CIF_COD_REFERENCE_MANIFEST)


def _source_entry(source, manifest_path, rows, warnings):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        source: Valor de entrada consumido por esta etapa do fluxo.
        manifest_path: Valor de entrada consumido por esta etapa do fluxo.
        rows: Valor de entrada consumido por esta etapa do fluxo.
        warnings: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return {
        "source": source,
        "manifest_path": str(manifest_path),
        "status": "available" if rows else ("warning" if warnings else "empty"),
        "reference_count": len(rows),
    }


def _reference_search_key(*values):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        *values: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return _normalise_key(" ".join(str(value or "") for value in values))


def _load_cif_cod_rows(manifest_path):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        manifest_path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    rows = []
    warnings = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return rows, ["Manifesto CIF/COD nao encontrado."]
    except json.JSONDecodeError:
        return rows, ["Manifesto CIF/COD invalido."]
    entries = manifest.get("references") if isinstance(manifest, dict) else manifest
    if not isinstance(entries, list):
        return rows, ["Manifesto CIF/COD precisa conter uma lista em references."]
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or ("COD" if item.get("cod_id") else "CIF")).strip().upper()
        reference_id = item.get("reference_id") or "%s:%s" % (
            source.lower(),
            item.get("cod_id") or item.get("source_id") or item.get("sha256") or index,
        )
        peak_items = [peak for peak in (item.get("peaks") or [])[:80] if isinstance(peak, dict)]
        peak_intensities = []
        for peak in peak_items:
            try:
                peak_intensities.append(float(peak.get("intensity") or peak.get("relative_intensity") or 0.0))
            except (TypeError, ValueError):
                continue
        intensity_max = max(peak_intensities) if peak_intensities else None
        peaks = [_compact_peak(peak, intensity_max=intensity_max) for peak in peak_items]
        rows.append(
            {
                "reference_id": reference_id,
                "source": source,
                "source_status": item.get("source_status") or "curated_cif_cod_manifest",
                "argilomineral_id": item.get("argilomineral_id"),
                "mineral_name": item.get("mineral_name") or item.get("title") or item.get("name"),
                "formula": item.get("formula"),
                "cod_id": item.get("cod_id"),
                "file_type": item.get("file_type") or "cif",
                "local_path": item.get("local_path") or item.get("cif_path"),
                "source_sha256": item.get("source_sha256") or item.get("sha256"),
                "point_count": item.get("point_count"),
                "peak_count": len(peaks),
                "peaks": peaks,
                "provenance": {
                    **(item.get("provenance") or {}),
                    "manifest_path": str(manifest_path),
                    "source_format": "cif",
                    "integration_policy": "padrao CIF/COD indexado para comparacao assistida; nao confirma fase mineralogica isoladamente",
                },
                "search_key": _reference_search_key(
                    item.get("argilomineral_id"),
                    item.get("mineral_name"),
                    item.get("title"),
                    item.get("name"),
                    item.get("formula"),
                    item.get("cod_id"),
                ),
            }
        )
    return rows, warnings


@lru_cache(maxsize=2)
def load_reference_index():
    """Build a compact cached reference index from curated/static manifests."""
    manifest_path = _rruff_manifest_path()
    rows = []
    warnings = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        manifest = []
        warnings.append("Manifesto RRUFF ODR nao encontrado.")
    except json.JSONDecodeError:
        manifest = []
        warnings.append("Manifesto RRUFF ODR invalido.")
    for index, item in enumerate(manifest or []):
        if not isinstance(item, dict):
            continue
        peak_items = [peak for peak in (item.get("peaks") or [])[:40] if isinstance(peak, dict)]
        peak_intensities = []
        for peak in peak_items:
            try:
                peak_intensities.append(float(peak.get("intensity") or peak.get("relative_intensity") or 0.0))
            except (TypeError, ValueError):
                continue
        intensity_max = max(peak_intensities) if peak_intensities else None
        peaks = [_compact_peak(peak, intensity_max=intensity_max) for peak in peak_items]
        rows.append(
            {
                "reference_id": "rruff_odr:%s:%s:%s" % (
                    item.get("argilomineral_id") or "unknown",
                    item.get("rruff_id") or item.get("sample_id") or index,
                    item.get("file_type") or "curve",
                ),
                "source": "RRUFF_ODR",
                "source_status": "curated_static_manifest",
                "argilomineral_id": item.get("argilomineral_id"),
                "mineral_name": item.get("mineral_name"),
                "file_type": item.get("file_type"),
                "local_path": item.get("local_path"),
                "point_count": len(item.get("points") or []),
                "peak_count": len(peaks),
                "peaks": peaks,
                "provenance": {
                    "manifest_path": str(manifest_path),
                    "license_policy": "RRUFF/ODR somente como referencia auxiliar curada; verificar termos da fonte antes de redistribuir.",
                    "integration_policy": "comparacao assistida; nao confirma fase mineralogica isoladamente",
                },
                "search_key": _reference_search_key(item.get("argilomineral_id"), item.get("mineral_name")),
            }
        )
    cif_cod_path = _cif_cod_manifest_path()
    cif_cod_rows, cif_cod_warnings = _load_cif_cod_rows(cif_cod_path)
    rows.extend(cif_cod_rows)
    warnings.extend(cif_cod_warnings)
    return {
        "schema_version": DRX_REFERENCE_INDEX_SCHEMA,
        "sources": [
            _source_entry("RRUFF_ODR", manifest_path, [row for row in rows if row.get("source") == "RRUFF_ODR"], []),
            _source_entry("CIF_COD", cif_cod_path, cif_cod_rows, cif_cod_warnings),
        ],
        "warnings": warnings,
        "references": rows,
    }


def search_reference_index(query=None, source=None, limit=25):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        query: Valor de entrada consumido por esta etapa do fluxo.
        source: Valor de entrada consumido por esta etapa do fluxo.
        limit: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    index = load_reference_index()
    q = _normalise_key(query)
    source_key = str(source or "").strip().casefold()
    matches = []
    for row in index.get("references") or []:
        if source_key and str(row.get("source") or "").casefold() != source_key:
            continue
        if q and q not in row.get("search_key", ""):
            continue
        compact = {key: value for key, value in row.items() if key != "search_key"}
        compact["peaks"] = compact.get("peaks", [])[:12]
        matches.append(compact)
        if len(matches) >= limit:
            break
    return {
        "success": True,
        "schema_version": index.get("schema_version"),
        "sources": index.get("sources") or [],
        "warnings": index.get("warnings") or [],
        "query": query or "",
        "source": source or "",
        "total": len(matches),
        "references": matches,
    }


def reference_pattern_from_index(reference_id):
    """Return one indexed reference as a reference-pattern compatible payload."""
    wanted = str(reference_id or "").strip()
    if not wanted:
        return {"success": False, "error": "Informe reference_id."}
    index = load_reference_index()
    for row in index.get("references") or []:
        if row.get("reference_id") != wanted:
            continue
        return {
            "success": True,
            "schema_version": DRX_INDEXED_REFERENCE_PATTERN_SCHEMA,
            "reference_index_schema_version": index.get("schema_version"),
            "reference_id": row.get("reference_id"),
            "filename": row.get("local_path") or row.get("reference_id"),
            "source": row.get("source"),
            "source_status": row.get("source_status"),
            "metadata": {
                "title": row.get("mineral_name") or row.get("argilomineral_id"),
                "mineral": row.get("mineral_name"),
                "argilomineral_id": row.get("argilomineral_id"),
                "formula": row.get("formula"),
                "cod_id": row.get("cod_id"),
                "file_type": row.get("file_type"),
                "local_path": row.get("local_path"),
                "source_sha256": row.get("source_sha256"),
                "provenance": row.get("provenance") or {},
            },
            "peaks": list(row.get("peaks") or []),
            "peak_count": len(row.get("peaks") or []),
            "warnings": list(index.get("warnings") or []),
            "interpretation_policy": "Referencia indexada para comparacao assistida; nao confirma fase mineralogica isoladamente.",
        }
    return {"success": False, "error": "Referencia DRX indexada nao encontrada.", "reference_id": wanted}
