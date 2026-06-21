#!/usr/bin/env python3
"""
Projeto: Painel DRX Argiloteca

Descrição:
Fetch and normalize open DRX/crystallographic patterns for Argiloteca. Dry-run is the default. Real downloads require --execute.

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
import json
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from argiloteca_custom.scripts.open_patterns.common import (  # noqa: E402
    DEFAULT_WAVELENGTH_A,
    amcsd_download_plan,
    build_cod_cif_url,
    build_cod_search_url,
    build_coverage,
    build_panel_index,
    discover_vocabulary_path,
    download_url,
    ensure_dirs,
    load_argiloteca_vocabulary,
    normalized_pattern,
    parse_simple_peaks,
    parse_simple_xy,
    query_names_for_term,
    read_jsonl,
    rruff_download_plan,
    safe_extract_zip,
    save_source_licenses,
    sha256_file,
    slug,
    utc_now_iso,
    write_curation_queue,
    write_jsonl,
)


def _log(message, verbose=False):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        message: Valor de entrada consumido por esta etapa do fluxo.
        verbose: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if verbose:
        print(message)


def _source_set(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return {item.strip().lower() for item in str(value or "").split(",") if item.strip()}


def _relative(path, base):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
        base: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    try:
        return str(Path(path).resolve().relative_to(Path(base).resolve()))
    except Exception:
        return str(path)


def _name_from_rruff_filename(path):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    stem = Path(path).stem
    parts = re.split(r"__+", stem)
    for part in parts:
        if part and not re.match(r"^(R\d+|\d+|Powder|Xray|Data|XY|RAW|Processed)$", part, flags=re.I):
            text = part.replace("_", " ").strip()
            if text:
                return text
    return stem.replace("_", " ")


def _term_by_slug(vocabulary):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        vocabulary: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    index = {}
    for term in vocabulary:
        index[slug(term.get("mineral"))] = term
        index[slug(term.get("id"))] = term
    return index


def normalize_rruff_files(out_dir, vocabulary, wavelength_a=DEFAULT_WAVELENGTH_A, verbose=False):
    """Normalize already downloaded/extracted RRUFF files."""
    out_dir = Path(out_dir)
    raw_dir = out_dir / "raw" / "rruff"
    index = _term_by_slug(vocabulary)
    records = []
    for path in sorted(raw_dir.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in {".txt", ".xy", ".dif", ".dat"}:
            continue
        matched_name = _name_from_rruff_filename(path)
        term = index.get(slug(matched_name))
        if not term:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        checksum = sha256_file(path)
        if suffix in {".txt", ".xy", ".dat"}:
            profile = parse_simple_xy(text)
            peaks = parse_simple_peaks(text, wavelength_a=wavelength_a)
            data_kind = "measured_powder_xrd"
            pattern_kind = "experimental"
        else:
            profile = {"two_theta_deg": [], "intensity": []}
            peaks = parse_simple_peaks(text, wavelength_a=wavelength_a)
            data_kind = "dif_reference"
            pattern_kind = "reference_lines"
        warnings = []
        if not peaks and not profile.get("points_count"):
            warnings.append("Parser RRUFF não encontrou picos/perfil no arquivo.")
        record = normalized_pattern(
            term,
            "RRUFF",
            path.stem,
            matched_name,
            data_kind,
            pattern_kind,
            source_record_url="https://rruff.info/",
            source_file_url=None,
            checksum_sha256=checksum,
            profile={"two_theta_deg": profile.get("two_theta_deg", []), "intensity": profile.get("intensity", [])},
            peaks=peaks,
            preparation="powder",
            treatment="none",
            wavelength_A=wavelength_a,
            radiation="CuKa",
            warnings=warnings,
        )
        record["local_path_relativo"] = _relative(path, out_dir)
        records.append(record)
        _log(f"RRUFF normalized: {path}", verbose)
    write_jsonl(out_dir / "normalized" / "rruff_patterns.jsonl", records)
    return records


def _parse_cif_metadata(text):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        text: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    def find_value(key):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            key: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        match = re.search(rf"^{re.escape(key)}\s+(.+)$", text, flags=re.M)
        if not match:
            return None
        value = match.group(1).strip().strip("'\"")
        return value if value not in {"?", "."} else None

    cell = {}
    for key, field in [
        ("_cell_length_a", "a"),
        ("_cell_length_b", "b"),
        ("_cell_length_c", "c"),
        ("_cell_angle_alpha", "alpha"),
        ("_cell_angle_beta", "beta"),
        ("_cell_angle_gamma", "gamma"),
    ]:
        value = find_value(key)
        if value:
            try:
                cell[field] = float(re.sub(r"\(.+\)$", "", value))
            except ValueError:
                cell[field] = value
    return {
        "formula": find_value("_chemical_formula_sum") or find_value("_chemical_formula_structural"),
        "space_group": find_value("_space_group_name_H-M_alt") or find_value("_symmetry_space_group_name_H-M"),
        "cell": cell,
    }


def normalize_amcsd_files(out_dir, vocabulary, wavelength_a=DEFAULT_WAVELENGTH_A, verbose=False):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        out_dir: Valor de entrada consumido por esta etapa do fluxo.
        vocabulary: Valor de entrada consumido por esta etapa do fluxo.
        wavelength_a: Valor de entrada consumido por esta etapa do fluxo.
        verbose: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    out_dir = Path(out_dir)
    raw_dir = out_dir / "raw" / "amcsd"
    index = _term_by_slug(vocabulary)
    records = []
    for path in sorted(raw_dir.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in {".cif", ".dif"}:
            continue
        matched_name = path.stem.split("_")[0].replace("-", " ")
        term = index.get(slug(matched_name))
        if not term:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        checksum = sha256_file(path)
        if suffix == ".cif":
            meta = _parse_cif_metadata(text)
            record = normalized_pattern(
                term,
                "AMCSD",
                path.stem,
                matched_name,
                "cif_structure",
                "reference_lines",
                source_record_url="https://rruff.geo.arizona.edu/AMS/",
                source_file_url=None,
                checksum_sha256=checksum,
                cif={
                    "local_path": _relative(path, out_dir),
                    "formula": meta.get("formula"),
                    "space_group": meta.get("space_group"),
                    "cell": meta.get("cell"),
                },
                formula=meta.get("formula"),
                wavelength_A=wavelength_a,
                radiation="unknown",
                warnings=["CIF/AMCSD é estrutura cristalográfica; não representa tratamento N/G/C."],
            )
        else:
            peaks = parse_simple_peaks(text, wavelength_a=wavelength_a)
            record = normalized_pattern(
                term,
                "AMCSD",
                path.stem,
                matched_name,
                "dif_reference",
                "reference_lines",
                source_record_url="https://rruff.geo.arizona.edu/AMS/",
                source_file_url=None,
                checksum_sha256=checksum,
                peaks=peaks,
                wavelength_A=wavelength_a,
                warnings=[] if peaks else ["Parser AMCSD DIF não encontrou picos."],
            )
        record["local_path_relativo"] = _relative(path, out_dir)
        records.append(record)
        _log(f"AMCSD normalized: {path}", verbose)
    write_jsonl(out_dir / "normalized" / "amcsd_patterns.jsonl", records)
    return records


def _cod_id_from_result(item):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        item: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if isinstance(item, dict):
        for key in ("file", "cod_id", "id", "svnrevision"):
            value = str(item.get(key) or "").strip()
            match = re.search(r"(\d{7})", value)
            if match:
                return match.group(1)
    elif isinstance(item, str):
        match = re.search(r"(\d{7})", item)
        if match:
            return match.group(1)
    return None


def _load_cod_search_results(path):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(payload, dict):
        for key in ("results", "data", "records"):
            if isinstance(payload.get(key), list):
                return payload[key]
        return [payload]
    return payload if isinstance(payload, list) else []


def normalize_cod_files(out_dir, vocabulary, wavelength_a=DEFAULT_WAVELENGTH_A, simulate=False, verbose=False):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        out_dir: Valor de entrada consumido por esta etapa do fluxo.
        vocabulary: Valor de entrada consumido por esta etapa do fluxo.
        wavelength_a: Valor de entrada consumido por esta etapa do fluxo.
        simulate: Valor de entrada consumido por esta etapa do fluxo.
        verbose: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    out_dir = Path(out_dir)
    search_dir = out_dir / "raw" / "cod" / "search"
    cif_dir = out_dir / "raw" / "cod" / "cif"
    records = []
    for term in vocabulary:
        search_file = search_dir / f"{term['id']}.json"
        if not search_file.exists():
            continue
        for item in _load_cod_search_results(search_file):
            cod_id = _cod_id_from_result(item)
            if not cod_id:
                continue
            cif_path = cif_dir / f"{cod_id}.cif"
            if not cif_path.exists():
                continue
            text = cif_path.read_text(encoding="utf-8", errors="ignore")
            meta = _parse_cif_metadata(text)
            record = normalized_pattern(
                term,
                "COD",
                cod_id,
                item.get("mineral") if isinstance(item, dict) else term.get("mineral"),
                "cif_structure",
                "reference_lines",
                source_record_url=build_cod_cif_url(cod_id),
                source_file_url=build_cod_cif_url(cod_id),
                checksum_sha256=sha256_file(cif_path),
                cif={
                    "local_path": _relative(cif_path, out_dir),
                    "formula": meta.get("formula"),
                    "space_group": meta.get("space_group"),
                    "cell": meta.get("cell"),
                },
                formula=meta.get("formula"),
                wavelength_A=wavelength_a,
                radiation="unknown",
                warnings=["COD CIF é estrutura cristalográfica; não representa tratamento N/G/C."],
            )
            record["local_path_relativo"] = _relative(cif_path, out_dir)
            records.append(record)
            _log(f"COD normalized: {cif_path}", verbose)
            if simulate:
                sim = simulate_cif_pattern(cif_path, wavelength_a=wavelength_a)
                if sim:
                    sim_record = dict(record)
                    sim_record["data_kind"] = "simulated_powder_xrd"
                    sim_record["pattern_kind"] = "simulated"
                    sim_record["peaks"] = sim["peaks"]
                    sim_record["warnings"] = list(record.get("warnings") or []) + [
                        "Padrão simulado de CIF não representa tratamento natural/glicolado/calcinado."
                    ]
                    records.append(sim_record)
    write_jsonl(out_dir / "normalized" / "cod_cifs.jsonl", [r for r in records if r["data_kind"] == "cif_structure"])
    write_jsonl(out_dir / "normalized" / "cod_simulated_patterns.jsonl", [r for r in records if r["data_kind"] == "simulated_powder_xrd"])
    return records


def simulate_cif_pattern(cif_path, wavelength_a=DEFAULT_WAVELENGTH_A):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        cif_path: Valor de entrada consumido por esta etapa do fluxo.
        wavelength_a: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    try:
        from pymatgen.analysis.diffraction.xrd import XRDCalculator
        from pymatgen.core import Structure
    except Exception:
        return None
    structure = Structure.from_file(str(cif_path))
    calculator = XRDCalculator(wavelength=wavelength_a)
    pattern = calculator.get_pattern(structure, two_theta_range=(2, 70))
    peaks = []
    for two_theta, intensity, hkls, d_a in zip(pattern.x, pattern.y, pattern.hkls, pattern.d_hkls):
        hkl = None
        if hkls and isinstance(hkls[0], dict):
            hkl = "".join(str(v) for v in hkls[0].get("hkl", ()))
        peaks.append({
            "d_A": round(float(d_a), 5),
            "two_theta_deg": round(float(two_theta), 5),
            "intensity": round(float(intensity), 4),
            "relative_intensity": round(float(intensity), 4),
            "hkl": hkl,
            "source_peak_id": None,
        })
    return {"peaks": peaks}


def download_archives(out_dir, plans, execute=False, delay_seconds=1.0, force_refresh=False, verbose=False):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        out_dir: Valor de entrada consumido por esta etapa do fluxo.
        plans: Valor de entrada consumido por esta etapa do fluxo.
        execute: Valor de entrada consumido por esta etapa do fluxo.
        delay_seconds: Valor de entrada consumido por esta etapa do fluxo.
        force_refresh: Valor de entrada consumido por esta etapa do fluxo.
        verbose: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    manifest = []
    for item in plans:
        source = item["source"].lower()
        target = Path(out_dir) / "raw" / source / item["name"]
        row = {"source": item["source"], "name": item["name"], "url": item["url"], "target": str(target)}
        if not execute:
            row["status"] = "dry_run"
            manifest.append(row)
            continue
        result = download_url(item["url"], target, delay_seconds=delay_seconds, force_refresh=force_refresh)
        row.update(result)
        if row.get("status") in {"downloaded", "cached"} and target.suffix.lower() == ".zip":
            extract_dir = target.with_suffix("")
            row["extracted_files"] = safe_extract_zip(target, extract_dir)
        manifest.append(row)
        _log(f"Downloaded {item['url']} -> {target}", verbose)
    return manifest


def fetch_cod(out_dir, vocabulary, execute=False, max_results=10, delay_seconds=2.0, force_refresh=False, verbose=False):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        out_dir: Valor de entrada consumido por esta etapa do fluxo.
        vocabulary: Valor de entrada consumido por esta etapa do fluxo.
        execute: Valor de entrada consumido por esta etapa do fluxo.
        max_results: Valor de entrada consumido por esta etapa do fluxo.
        delay_seconds: Valor de entrada consumido por esta etapa do fluxo.
        force_refresh: Valor de entrada consumido por esta etapa do fluxo.
        verbose: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    out_dir = Path(out_dir)
    manifest = []
    for term in vocabulary:
        if str(term.get("category") or "").lower() == "group":
            # Group terms are represented by species children; do not query as pure species.
            continue
        queries = query_names_for_term(term)[:2]
        for query in queries:
            search_url = build_cod_search_url(query, max_results=max_results)
            search_target = out_dir / "raw" / "cod" / "search" / f"{term['id']}.json"
            row = {"source": "COD", "argiloteca_id": term["id"], "query": query, "url": search_url, "target": str(search_target)}
            if not execute:
                row["status"] = "dry_run"
                manifest.append(row)
                continue
            result = download_url(search_url, search_target, delay_seconds=delay_seconds, force_refresh=force_refresh)
            row.update(result)
            manifest.append(row)
            if row.get("status") == "download_error":
                continue
            for item in _load_cod_search_results(search_target)[:max_results]:
                cod_id = _cod_id_from_result(item)
                if not cod_id:
                    continue
                cif_url = build_cod_cif_url(cod_id)
                cif_target = out_dir / "raw" / "cod" / "cif" / f"{cod_id}.cif"
                cif_row = {"source": "COD", "argiloteca_id": term["id"], "cod_id": cod_id, "url": cif_url, "target": str(cif_target)}
                cif_row.update(download_url(cif_url, cif_target, delay_seconds=delay_seconds, force_refresh=force_refresh))
                manifest.append(cif_row)
                _log(f"COD fetched {cod_id}", verbose)
    return manifest


def build_outputs(out_dir, vocabulary, simulate_cod=False, wavelength_a=DEFAULT_WAVELENGTH_A, verbose=False):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        out_dir: Valor de entrada consumido por esta etapa do fluxo.
        vocabulary: Valor de entrada consumido por esta etapa do fluxo.
        simulate_cod: Valor de entrada consumido por esta etapa do fluxo.
        wavelength_a: Valor de entrada consumido por esta etapa do fluxo.
        verbose: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    records = []
    records.extend(normalize_rruff_files(out_dir, vocabulary, wavelength_a=wavelength_a, verbose=verbose))
    records.extend(normalize_amcsd_files(out_dir, vocabulary, wavelength_a=wavelength_a, verbose=verbose))
    records.extend(normalize_cod_files(out_dir, vocabulary, wavelength_a=wavelength_a, simulate=simulate_cod, verbose=verbose))

    normalized_path = Path(out_dir) / "normalized" / "open_patterns_index.jsonl"
    write_jsonl(normalized_path, records)

    panel_records = build_panel_index(records)
    panel_path = Path(out_dir) / "panel" / "open_patterns_index.jsonl"
    write_jsonl(panel_path, panel_records)

    # Also create a source-like path inside data/open_patterns; caller can copy to static/src if desired.
    compact_path = Path(out_dir) / "normalized" / "open_patterns_panel_index.jsonl"
    write_jsonl(compact_path, panel_records)

    coverage = build_coverage(vocabulary, records)
    coverage_path = Path(out_dir) / "manifests" / "coverage_by_mineral.json"
    coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    write_curation_queue(Path(out_dir) / "manifests" / "curation_queue.csv", records)
    save_source_licenses(out_dir)
    return {
        "records": len(records),
        "normalized_index": str(normalized_path),
        "panel_index": str(panel_path),
        "coverage": str(coverage_path),
    }


def parse_args(argv=None):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        argv: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vocabulary", help="Path to Argiloteca WebMineral manifest or argilominerais.jsonl")
    parser.add_argument("--sources", default="rruff,amcsd,cod")
    parser.add_argument("--out", default="data/open_patterns")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True)
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--include-raw", action="store_true")
    parser.add_argument("--include-refinement", action="store_true")
    parser.add_argument("--include-amc", action="store_true")
    parser.add_argument("--max-cod-results-per-term", type=int, default=10)
    parser.add_argument("--delay-seconds", type=float, default=2.0)
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--simulate-cod-patterns", action="store_true")
    parser.add_argument("--wavelength-a", type=float, default=DEFAULT_WAVELENGTH_A)
    parser.add_argument("--radiation", default="CuKa")
    parser.add_argument("--output-panel-index", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        argv: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    args = parse_args(argv)
    execute = bool(args.execute)
    sources = _source_set(args.sources)
    out_dir = ensure_dirs(args.out)

    vocabulary_path = Path(args.vocabulary) if args.vocabulary else discover_vocabulary_path(Path.cwd())
    if not vocabulary_path:
        raise SystemExit("Vocabulário Argiloteca não encontrado; use --vocabulary.")
    vocabulary = load_argiloteca_vocabulary(vocabulary_path)
    if not vocabulary:
        raise SystemExit(f"Vocabulário vazio ou inválido: {vocabulary_path}")

    download_manifest = {
        "generated_at": utc_now_iso(),
        "mode": "execute" if execute else "dry_run",
        "vocabulary": str(vocabulary_path),
        "sources": sorted(sources),
        "downloads": [],
        "cod_requests": [],
    }

    plans = []
    if "rruff" in sources:
        plans.extend(rruff_download_plan(include_raw=args.include_raw, include_refinement=args.include_refinement))
    if "amcsd" in sources:
        plans.extend(amcsd_download_plan(include_amc=args.include_amc))
    if plans:
        download_manifest["downloads"] = download_archives(
            out_dir,
            plans,
            execute=execute,
            delay_seconds=min(args.delay_seconds, 1.0) if execute else args.delay_seconds,
            force_refresh=args.force_refresh,
            verbose=args.verbose,
        )

    if "cod" in sources:
        download_manifest["cod_requests"] = fetch_cod(
            out_dir,
            vocabulary,
            execute=execute,
            max_results=args.max_cod_results_per_term,
            delay_seconds=args.delay_seconds,
            force_refresh=args.force_refresh,
            verbose=args.verbose,
        )

    manifest_path = out_dir / "manifests" / "downloads_manifest.json"
    manifest_path.write_text(json.dumps(download_manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    outputs = build_outputs(
        out_dir,
        vocabulary,
        simulate_cod=args.simulate_cod_patterns,
        wavelength_a=args.wavelength_a,
        verbose=args.verbose,
    )

    summary = {
        "success": True,
        "mode": "execute" if execute else "dry_run",
        "vocabulary_terms": len(vocabulary),
        "downloads_manifest": str(manifest_path),
        **outputs,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
