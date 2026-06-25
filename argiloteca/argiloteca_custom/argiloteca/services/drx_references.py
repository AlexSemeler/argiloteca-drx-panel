"""
Projeto: Painel DRX Argiloteca

Descrição:
Versioned DRX reference-pattern parsing and peak matching.

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
import math
import re
from pathlib import Path

from .drx import ADVANCED_ALS_WAVELENGTH_CU, RawParseError, safe_text
from .drx_science_engine import simulate_cif_pattern


DRX_REFERENCE_PATTERN_SCHEMA = "argiloteca.drx.reference_pattern.v1"
DRX_REFERENCE_COMPARISON_SCHEMA = "argiloteca.drx.reference_comparison.v1"


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
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def two_theta_to_d(two_theta, wavelength=ADVANCED_ALS_WAVELENGTH_CU):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        two_theta: Valor de entrada consumido por esta etapa do fluxo.
        wavelength: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    value = _finite_float(two_theta)
    if value is None or value <= 0 or value >= 180:
        return None
    theta = math.radians(value / 2.0)
    if theta <= 0:
        return None
    return wavelength / (2.0 * math.sin(theta))


def d_to_two_theta(d_angstrom, wavelength=ADVANCED_ALS_WAVELENGTH_CU):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        d_angstrom: Valor de entrada consumido por esta etapa do fluxo.
        wavelength: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    value = _finite_float(d_angstrom)
    if value is None or value <= 0:
        return None
    ratio = wavelength / (2.0 * value)
    if ratio <= 0 or ratio >= 1:
        return None
    return math.degrees(2.0 * math.asin(ratio))


def _normalise_reference_peaks(peaks, wavelength=ADVANCED_ALS_WAVELENGTH_CU, limit=200):
    """
    Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
    
    Args:
        peaks: Valor de entrada consumido por esta etapa do fluxo.
        wavelength: Valor de entrada consumido por esta etapa do fluxo.
        limit: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    rows = []
    max_intensity = 0.0
    for index, peak in enumerate(peaks or []):
        if not isinstance(peak, dict):
            continue
        two_theta = _finite_float(
            peak.get("two_theta")
            or peak.get("2theta")
            or peak.get("twoTheta")
            or peak.get("position")
        )
        d_value = _finite_float(
            peak.get("d_angstrom")
            or peak.get("d")
            or peak.get("d_spacing")
        )
        if two_theta is None and d_value is not None:
            two_theta = d_to_two_theta(d_value, wavelength=wavelength)
        if d_value is None and two_theta is not None:
            d_value = two_theta_to_d(two_theta, wavelength=wavelength)
        intensity = _finite_float(
            peak.get("relative_intensity")
            or peak.get("intensity_relative")
            or peak.get("intensity")
            or peak.get("i")
        )
        if two_theta is None or d_value is None:
            continue
        intensity = intensity if intensity is not None else 1.0
        max_intensity = max(max_intensity, intensity)
        rows.append(
            {
                "peak_index": peak.get("peak_index") or peak.get("index") or index + 1,
                "two_theta": round(two_theta, 5),
                "d_angstrom": round(d_value, 5),
                "relative_intensity": intensity,
                "hkl": peak.get("hkl"),
                "source": peak.get("source"),
            }
        )
    if max_intensity > 0:
        for row in rows:
            row["relative_intensity"] = round((row["relative_intensity"] / max_intensity) * 100.0, 4)
    return sorted(rows, key=lambda row: row.get("relative_intensity") or 0, reverse=True)[:limit]


def _parse_json_reference(content, filename):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        content: Valor de entrada consumido por esta etapa do fluxo.
        filename: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    payload = json.loads(content.decode("utf-8-sig"))
    if isinstance(payload, list):
        metadata = {"title": Path(filename or "reference.json").stem}
        peaks = payload
    elif isinstance(payload, dict):
        metadata = {
            "title": payload.get("title") or payload.get("name") or Path(filename or "reference.json").stem,
            "mineral": payload.get("mineral"),
            "formula": payload.get("formula"),
            "source": payload.get("source"),
            "source_id": payload.get("source_id") or payload.get("cod_id") or payload.get("rruff_id"),
        }
        peaks = payload.get("peaks") or payload.get("lines") or payload.get("pattern") or []
    else:
        raise RawParseError("Referencia JSON precisa ser objeto ou lista de picos.")
    return metadata, peaks


def _split_text_row(line):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        line: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = safe_text(line).strip()
    if not text or text.startswith(("#", "//", ";")):
        return []
    return [part.strip() for part in re.split(r"[;,\t ]+", text) if part.strip()]


def _parse_text_reference(content, filename):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        content: Valor de entrada consumido por esta etapa do fluxo.
        filename: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    peaks = []
    skipped = 0
    for line in text.splitlines():
        cells = _split_text_row(line)
        if len(cells) < 1:
            skipped += 1
            continue
        first = _finite_float(cells[0])
        if first is None:
            skipped += 1
            continue
        second = _finite_float(cells[1]) if len(cells) > 1 else 1.0
        axis = "d_angstrom" if first > 20 else "two_theta"
        peaks.append({axis: first, "relative_intensity": second if second is not None else 1.0})
    return {"title": Path(filename or "reference.txt").stem, "skipped_rows": skipped}, peaks


def _parse_cif_reference(content, filename):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        content: Valor de entrada consumido por esta etapa do fluxo.
        filename: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    metadata = {
        "title": Path(filename or "reference.cif").stem,
        "source_format": "cif",
        "simulation_status": "not_available",
        "simulation_message": "Simulacao de padrao CIF requer pymatgen/engine cristalografico instalado.",
    }
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("_chemical_name_mineral") or stripped.startswith("_chemical_name_common"):
            metadata["mineral"] = stripped.split(None, 1)[1].strip("'\"") if len(stripped.split(None, 1)) > 1 else None
        elif stripped.startswith("_chemical_formula_sum"):
            metadata["formula"] = stripped.split(None, 1)[1].strip("'\"") if len(stripped.split(None, 1)) > 1 else None
        elif stripped.startswith("_database_code") or stripped.startswith("_cod_database_code"):
            metadata["source_id"] = stripped.split(None, 1)[1].strip("'\"") if len(stripped.split(None, 1)) > 1 else None
    simulated = simulate_cif_pattern(content, filename=filename)
    if simulated and simulated.get("success"):
        metadata.update(
            {
                "simulation_status": "ok",
                "simulation_message": "Padrao CIF simulado por pymatgen.XRDCalculator.",
                "simulation_engine": simulated.get("engine"),
                "formula": metadata.get("formula") or simulated.get("formula"),
                "site_count": simulated.get("sites"),
            }
        )
        return metadata, simulated.get("peaks") or []
    if simulated and simulated.get("error"):
        metadata["simulation_message"] = simulated.get("error")
    return metadata, []


def parse_reference_pattern_bytes(content, filename=None, wavelength=ADVANCED_ALS_WAVELENGTH_CU):
    """Parse a reference peak list from JSON/text, or metadata from CIF."""
    suffix = Path(filename or "").suffix.lower()
    if suffix == ".json":
        metadata, peaks = _parse_json_reference(content, filename)
        parser_format = "json_reference_pattern"
    elif suffix == ".cif":
        metadata, peaks = _parse_cif_reference(content, filename)
        parser_format = "cif_metadata_only"
    else:
        metadata, peaks = _parse_text_reference(content, filename)
        parser_format = "text_reference_pattern"
    normalised = _normalise_reference_peaks(peaks, wavelength=wavelength)
    warnings = []
    if suffix == ".cif" and not normalised:
        warnings.append("CIF lido apenas como metadado; padrao nao simulado sem motor cristalografico.")
    if not normalised and suffix != ".cif":
        raise RawParseError("Referencia sem picos numericos validos.")
    return {
        "schema_version": DRX_REFERENCE_PATTERN_SCHEMA,
        "filename": Path(filename or "reference").name,
        "parser_format": parser_format,
        "wavelength_angstrom": wavelength,
        "metadata": metadata,
        "peaks": normalised,
        "peak_count": len(normalised),
        "warnings": warnings,
        "interpretation_policy": "Padrao de referencia para comparacao assistida; nao confirma fase isoladamente.",
    }


def compare_reference_pattern(observed_peaks, reference_pattern, tolerance_two_theta=0.25, limit=80):
    """Match observed DRX peaks against one parsed reference pattern."""
    observed = _normalise_reference_peaks(observed_peaks or [], limit=500)
    reference_peaks = list(reference_pattern.get("peaks") or [])[:limit]
    matches = []
    used_observed = set()
    for ref_index, ref_peak in enumerate(reference_peaks):
        ref_two_theta = _finite_float(ref_peak.get("two_theta"))
        if ref_two_theta is None:
            continue
        best = None
        for obs_index, obs_peak in enumerate(observed):
            if obs_index in used_observed:
                continue
            obs_two_theta = _finite_float(obs_peak.get("two_theta"))
            if obs_two_theta is None:
                continue
            delta = abs(obs_two_theta - ref_two_theta)
            if delta <= tolerance_two_theta and (best is None or delta < best[0]):
                best = (delta, obs_index, obs_peak)
        if best is None:
            continue
        delta, obs_index, obs_peak = best
        used_observed.add(obs_index)
        matches.append(
            {
                "reference_peak_index": ref_peak.get("peak_index") or ref_index + 1,
                "observed_peak_index": obs_peak.get("peak_index"),
                "reference_two_theta": ref_peak.get("two_theta"),
                "observed_two_theta": obs_peak.get("two_theta"),
                "delta_two_theta": round(delta, 5),
                "reference_d_angstrom": ref_peak.get("d_angstrom"),
                "observed_d_angstrom": obs_peak.get("d_angstrom"),
                "reference_relative_intensity": ref_peak.get("relative_intensity"),
                "observed_relative_intensity": obs_peak.get("relative_intensity"),
            }
        )
    total_weight = sum(float(peak.get("relative_intensity") or 1.0) for peak in reference_peaks) or 1.0
    matched_weight = sum(float(match.get("reference_relative_intensity") or 1.0) for match in matches)
    coverage = len(matches) / len(reference_peaks) if reference_peaks else 0.0
    weighted_coverage = matched_weight / total_weight if total_weight else 0.0
    score = (coverage * 0.45) + (weighted_coverage * 0.55)
    return {
        "schema_version": DRX_REFERENCE_COMPARISON_SCHEMA,
        "reference_schema_version": reference_pattern.get("schema_version"),
        "reference_filename": reference_pattern.get("filename"),
        "reference_peak_count": len(reference_peaks),
        "observed_peak_count": len(observed),
        "matched_peak_count": len(matches),
        "coverage": round(coverage, 5),
        "weighted_coverage": round(weighted_coverage, 5),
        "score": round(score, 5),
        "tolerance_two_theta": tolerance_two_theta,
        "matches": matches[:30],
        "warnings": list(reference_pattern.get("warnings") or []),
        "interpretation_policy": "Comparacao automatica auxiliar; exige revisao de padrao completo, preparo e contexto mineralogico.",
    }
