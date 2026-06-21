"""
Projeto: Painel DRX Argiloteca

Descrição:
Open crystallographic pattern ingestion utilities for the DRX panel. The module intentionally keeps external reference patterns separate from Argiloteca N/G/C diagnostic rules. Open databases are auxiliary evidence only.

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

import csv
import hashlib
import json
import math
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
import urllib.error
import zipfile
from datetime import datetime, timezone
from pathlib import Path


RRUFF_POWDER_URLS = {
    "DIF.zip": "https://www.rruff.net/zipped_data_files/powder/DIF.zip",
    "XY_Processed.zip": "https://www.rruff.net/zipped_data_files/powder/XY_Processed.zip",
    "XY_RAW.zip": "https://www.rruff.net/zipped_data_files/powder/XY_RAW.zip",
    "Refinement_Data.zip": "https://www.rruff.net/zipped_data_files/powder/Refinement_Data.zip",
    "Refinement_Output_Data.zip": "https://www.rruff.net/zipped_data_files/powder/Refinement_Output_Data.zip",
}

AMCSD_URLS = {
    "cif.zip": "https://www.rruff.net/AMS/zipped_files/cif.zip",
    "dif.zip": "https://www.rruff.net/AMS/zipped_files/dif.zip",
    "amc.zip": "https://www.rruff.net/AMS/zipped_files/amc.zip",
}

COD_RESULT_ENDPOINT = "https://www.crystallography.net/cod/result"
COD_FILE_ENDPOINT = "https://www.crystallography.net/cod/{cod_id}.cif"
COD_HKL_ENDPOINT = "https://www.crystallography.net/cod/{cod_id}.hkl"
DEFAULT_WAVELENGTH_A = 1.5406

SOURCE_LICENSES = {
    "RRUFF": {
        "license": "RRUFF terms",
        "url": "https://rruff.info/",
        "notes": "Use local provenance and RRUFF terms; review before redistribution.",
    },
    "AMCSD": {
        "license": "AMCSD/RRUFF terms",
        "url": "https://rruff.geo.arizona.edu/AMS/",
        "notes": "Open crystallographic data via RRUFF/AMCSD endpoints.",
    },
    "COD": {
        "license": "COD open data terms",
        "url": "https://www.crystallography.net/cod/",
        "notes": "Preserve COD ID, CIF URL, and any CIF-level license metadata.",
    },
    "WebMineralLocal": {
        "license": "local cached reference metadata",
        "url": "https://webmineral.com/",
        "notes": "Auxiliary local vocabulary/reference lines only.",
    },
}


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


def normalize_mineral_name(value):
    """Return a stable ASCII matching key while preserving semantic words."""
    text = str(value or "").strip()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.replace("’", "'").replace("`", "'").replace("'", "")
    text = re.sub(r"[()\\[\\]{}\"“”]", " ", text)
    text = re.sub(r"[-_/]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9+ ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def name_tokens(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return [token for token in normalize_mineral_name(value).split() if token]


def slug(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return "_".join(name_tokens(value))


def discover_vocabulary_path(root=None):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        root: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    root = Path(root or Path.cwd())
    candidates = [
        root / "data" / "drx" / "webmineral" / "webmineral_argilominerais_vocabulario_manifest.json",
        root / "data" / "drx" / "saida_argiloteca_drx" / "webmineral_argilominerais_vocabulario.json",
        root / "povoamento" / "visualizacao-drx" / "webmineral" / "webmineral_argilominerais_vocabulario_manifest.json",
        root / "povoamento" / "visualizacao-drx" / "saida_argiloteca_drx" / "webmineral_argilominerais_vocabulario.json",
        root / "app" / "app_data" / "data" / "vocabularies" / "argilominerais.jsonl",
        root / "instance" / "app_data" / "data" / "vocabularies" / "argilominerais.jsonl",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _record_from_manifest(raw):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        raw: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not isinstance(raw, dict):
        return None
    mineral = raw.get("mineral") or raw.get("title_en") or raw.get("id")
    title_pt = raw.get("title_pt")
    chemistry = raw.get("chemistry") if isinstance(raw.get("chemistry"), dict) else {}
    crystallography = raw.get("crystallography") if isinstance(raw.get("crystallography"), dict) else {}
    return {
        "id": str(raw.get("id") or slug(mineral)),
        "mineral": str(mineral or "").strip(),
        "title_pt": title_pt or "",
        "category": raw.get("category") or "",
        "family": raw.get("family") or "",
        "lines": raw.get("lines") or [],
        "chemical_formula": chemistry.get("chemical_formula") or raw.get("chemical_formula") or raw.get("formula") or "",
        "cell_parameters": crystallography.get("cell_parameters") or raw.get("cell_parameters") or {},
        "structure_reference": raw.get("structure_reference") or "",
        "source": raw.get("source") or raw.get("webmineral_url") or "",
        "webmineral_url": raw.get("webmineral_url") or raw.get("source") or "",
        "synonyms": raw.get("synonyms") or [],
    }


def _record_from_jsonl(raw):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        raw: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not isinstance(raw, dict):
        return None
    title = raw.get("title") if isinstance(raw.get("title"), dict) else {}
    props = raw.get("props") if isinstance(raw.get("props"), dict) else {}
    mineral = title.get("en") or raw.get("mineral") or raw.get("id")
    return {
        "id": str(raw.get("id") or slug(mineral)),
        "mineral": str(mineral or "").strip(),
        "title_pt": title.get("pt") or raw.get("title_pt") or "",
        "category": props.get("category") or raw.get("category") or "",
        "family": props.get("family") or raw.get("family") or "",
        "lines": raw.get("lines") or [],
        "chemical_formula": props.get("chemical_formula") or raw.get("chemical_formula") or "",
        "cell_parameters": props.get("cell_parameters") or raw.get("cell_parameters") or {},
        "structure_reference": props.get("structure_reference") or raw.get("structure_reference") or "",
        "source": props.get("source") or raw.get("source") or "",
        "webmineral_url": raw.get("webmineral_url") or "",
        "synonyms": props.get("synonyms") or raw.get("synonyms") or [],
    }


def load_argiloteca_vocabulary(path):
    """Load Argiloteca clay vocabulary from WebMineral manifest JSON or JSONL."""
    path = Path(path)
    records = []
    if path.suffix.lower() == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = _record_from_jsonl(json.loads(line))
            except json.JSONDecodeError:
                continue
            if record and record["id"] and record["mineral"]:
                records.append(record)
        return records

    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_records = payload.get("records") if isinstance(payload, dict) else payload
    if not isinstance(raw_records, list):
        return []
    for raw in raw_records:
        record = _record_from_manifest(raw)
        if record and record["id"] and record["mineral"]:
            records.append(record)
    return records


def query_names_for_term(term):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        term: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    names = [term.get("mineral"), *(term.get("synonyms") or [])]
    # Portuguese labels are display labels, not primary external queries.
    names = [name for name in names if name and normalize_mineral_name(name)]
    seen = set()
    out = []
    for name in names:
        key = normalize_mineral_name(name)
        if key not in seen:
            seen.add(key)
            out.append(name)
    return out


def build_cod_search_url(mineral_name, max_results=None, include_duplicates=False, include_errors=False, include_theoretical=False):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        mineral_name: Valor de entrada consumido por esta etapa do fluxo.
        max_results: Valor de entrada consumido por esta etapa do fluxo.
        include_duplicates: Valor de entrada consumido por esta etapa do fluxo.
        include_errors: Valor de entrada consumido por esta etapa do fluxo.
        include_theoretical: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    params = {
        "text": mineral_name,
        "format": "json",
        "include_duplicates": "1" if include_duplicates else "0",
        "include_errors": "1" if include_errors else "0",
        "include_theoretical": "1" if include_theoretical else "0",
    }
    if max_results:
        params["limit"] = str(max_results)
    return f"{COD_RESULT_ENDPOINT}?{urllib.parse.urlencode(params)}"


def build_cod_cif_url(cod_id):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        cod_id: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return COD_FILE_ENDPOINT.format(cod_id=str(cod_id).strip())


def build_cod_hkl_url(cod_id):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        cod_id: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return COD_HKL_ENDPOINT.format(cod_id=str(cod_id).strip())


def rruff_download_plan(include_raw=False, include_refinement=False):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        include_raw: Valor de entrada consumido por esta etapa do fluxo.
        include_refinement: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    names = ["DIF.zip", "XY_Processed.zip"]
    if include_raw:
        names.append("XY_RAW.zip")
    if include_refinement:
        names.extend(["Refinement_Data.zip", "Refinement_Output_Data.zip"])
    return [{"source": "RRUFF", "name": name, "url": RRUFF_POWDER_URLS[name]} for name in names]


def amcsd_download_plan(include_amc=False):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        include_amc: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    names = ["cif.zip", "dif.zip"]
    if include_amc:
        names.append("amc.zip")
    return [{"source": "AMCSD", "name": name, "url": AMCSD_URLS[name]} for name in names]


def sha256_file(path):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    digest = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_dirs(out_dir):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        out_dir: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    out = Path(out_dir)
    for rel in [
        "raw/rruff",
        "raw/amcsd",
        "raw/cod/search",
        "raw/cod/cif",
        "normalized",
        "manifests",
        "panel",
    ]:
        (out / rel).mkdir(parents=True, exist_ok=True)
    return out


def user_agent():
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    base = os.environ.get("ARGILOTECA_USER_AGENT") or "ArgilotecaOpenPatterns/1.0"
    email = os.environ.get("ARGILOTECA_CONTACT_EMAIL")
    return f"{base} ({email})" if email and email not in base else base


def download_url(url, target, delay_seconds=1.0, force_refresh=False):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        url: Valor de entrada consumido por esta etapa do fluxo.
        target: Valor de entrada consumido por esta etapa do fluxo.
        delay_seconds: Valor de entrada consumido por esta etapa do fluxo.
        force_refresh: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    target = Path(target)
    if target.exists() and not force_refresh:
        return {"status": "cached", "path": str(target), "sha256": sha256_file(target)}
    target.parent.mkdir(parents=True, exist_ok=True)
    if delay_seconds:
        time.sleep(delay_seconds)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent(),
            "Accept": "application/zip,application/octet-stream,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.8,pt-BR;q=0.6",
            "Connection": "close",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            target.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        return {
            "status": "download_error",
            "path": str(target),
            "error": f"HTTP {exc.code}: {exc.reason}",
            "url": url,
        }
    except urllib.error.URLError as exc:
        return {
            "status": "download_error",
            "path": str(target),
            "error": str(exc.reason),
            "url": url,
        }
    return {"status": "downloaded", "path": str(target), "sha256": sha256_file(target)}


def safe_extract_zip(zip_path, target_dir):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        zip_path: Valor de entrada consumido por esta etapa do fluxo.
        target_dir: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            name = member.filename
            if name.endswith("/") or ".." in Path(name).parts:
                continue
            dest = target_dir / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(dest, "wb") as dst:
                dst.write(src.read())
            extracted.append(str(dest))
    return extracted


def d_from_two_theta(two_theta_deg, wavelength_a=DEFAULT_WAVELENGTH_A):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        two_theta_deg: Valor de entrada consumido por esta etapa do fluxo.
        wavelength_a: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    theta = math.radians(float(two_theta_deg) / 2.0)
    sine = math.sin(theta)
    return wavelength_a / (2.0 * sine) if sine > 0 else None


def two_theta_from_d(d_a, wavelength_a=DEFAULT_WAVELENGTH_A):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        d_a: Valor de entrada consumido por esta etapa do fluxo.
        wavelength_a: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    ratio = wavelength_a / (2.0 * float(d_a))
    if ratio <= 0 or ratio >= 1:
        return None
    return math.degrees(2.0 * math.asin(ratio))


def parse_simple_xy(text):
    """Parse two-column 2theta/intensity text."""
    points = []
    for line in str(text or "").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";", "//")):
            continue
        parts = re.split(r"[\s,;\t]+", line)
        if len(parts) < 2:
            continue
        try:
            two_theta = float(parts[0].replace(",", "."))
            intensity = float(parts[1].replace(",", "."))
        except ValueError:
            continue
        if math.isfinite(two_theta) and math.isfinite(intensity):
            points.append((two_theta, intensity))
    return {
        "two_theta_deg": [round(x, 6) for x, _ in points],
        "intensity": [round(y, 6) for _, y in points],
        "points_count": len(points),
        "parser_status": "ok" if points else "empty",
    }


def parse_simple_peaks(text, wavelength_a=DEFAULT_WAVELENGTH_A):
    """Parse simple d/intensity or 2theta/intensity peak lists."""
    peaks = []
    for line in str(text or "").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";", "//")):
            continue
        parts = re.split(r"[\s,;\t]+", line)
        nums = []
        for part in parts[:4]:
            try:
                nums.append(float(part.replace(",", ".")))
            except ValueError:
                pass
        if len(nums) < 2:
            continue
        first, intensity = nums[0], nums[1]
        # Simple peak lists in this pipeline are primarily d/I. Treat values in
        # a typical angular range as 2theta only when they are clearly too high
        # to be basal/companion d-spacing values.
        if first >= 20.0:
            d_a = d_from_two_theta(first, wavelength_a)
            two_theta = first
        else:
            d_a = first
            two_theta = two_theta_from_d(d_a, wavelength_a)
        if d_a and two_theta:
            peaks.append({
                "d_A": round(d_a, 5),
                "two_theta_deg": round(two_theta, 5),
                "intensity": intensity,
                "relative_intensity": intensity,
                "hkl": None,
                "source_peak_id": None,
            })
    return peaks


def formula_tokens(formula):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        formula: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return sorted(set(re.findall(r"[A-Z][a-z]?", str(formula or ""))))


def formula_compatible(local_formula, external_formula):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        local_formula: Valor de entrada consumido por esta etapa do fluxo.
        external_formula: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    local = set(formula_tokens(local_formula))
    external = set(formula_tokens(external_formula))
    if not local or not external:
        return None
    overlap = len(local & external) / max(len(local), len(external))
    return overlap >= 0.6


def score_match(term, external):
    """Transparent match score between Argiloteca term and external record."""
    score = 0.0
    basis = []
    warnings = []
    local_name = normalize_mineral_name(term.get("mineral"))
    external_name = normalize_mineral_name(external.get("matched_name") or external.get("mineral") or "")
    category = str(term.get("category") or "").lower()

    if local_name and external_name and local_name == external_name:
        score += 0.50
        basis.append("exact_name")
    elif local_name and external_name and (local_name in external_name or external_name in local_name):
        score += 0.25
        score -= 0.25
        basis.append("partial_name")
        warnings.append("Nome parcial ou ambíguo.")

    compatible = formula_compatible(term.get("chemical_formula"), external.get("formula"))
    if compatible is True:
        score += 0.20
        basis.append("formula_compatible")
    elif compatible is False:
        score -= 0.40
        warnings.append("Formula potencialmente incompatível.")

    if term.get("family") and term.get("family") == external.get("family"):
        score += 0.15
        basis.append("family_compatible")

    if external.get("has_measured_xrd"):
        score += 0.10
        basis.append("has_powder_xrd")
    if external.get("has_dif"):
        score += 0.10
        basis.append("has_dif")
    if external.get("has_cif"):
        score += 0.05
        basis.append("has_cif")
    if external.get("is_theoretical") or external.get("has_error_flag"):
        score -= 0.30
        warnings.append("Registro teórico, duplicado ou marcado com erro.")
    if category in {"group", "clay_material"} and external_name and local_name != external_name:
        score -= 0.30
        warnings.append("Grupo/material não deve virar espécie confirmada.")

    score = min(1.0, max(0.0, score))
    if score >= 0.80:
        status = "accepted"
    elif score >= 0.60:
        status = "provisional"
    elif score >= 0.40:
        status = "needs_review"
    else:
        status = "rejected"
    return {"score": round(score, 4), "basis": basis, "warnings": warnings, "curation_status": status}


def normalized_pattern(term, source, source_record_id, matched_name, data_kind, pattern_kind, **kwargs):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        term: Valor de entrada consumido por esta etapa do fluxo.
        source: Valor de entrada consumido por esta etapa do fluxo.
        source_record_id: Valor de entrada consumido por esta etapa do fluxo.
        matched_name: Valor de entrada consumido por esta etapa do fluxo.
        data_kind: Valor de entrada consumido por esta etapa do fluxo.
        pattern_kind: Valor de entrada consumido por esta etapa do fluxo.
        **kwargs: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    match = score_match(term, {
        "matched_name": matched_name,
        "family": term.get("family"),
        "formula": kwargs.get("formula"),
        "has_measured_xrd": data_kind == "measured_powder_xrd",
        "has_dif": data_kind == "dif_reference",
        "has_cif": data_kind in {"cif_structure", "simulated_powder_xrd"},
        "is_theoretical": kwargs.get("is_theoretical"),
        "has_error_flag": kwargs.get("has_error_flag"),
    })
    warnings = list(kwargs.get("warnings") or []) + match["warnings"]
    return {
        "argiloteca_id": term.get("id"),
        "argiloteca_mineral": term.get("mineral"),
        "argiloteca_family": term.get("family"),
        "argiloteca_category": term.get("category"),
        "source": source,
        "source_record_id": source_record_id,
        "source_record_url": kwargs.get("source_record_url"),
        "source_file_url": kwargs.get("source_file_url"),
        "source_license": kwargs.get("source_license") or SOURCE_LICENSES.get(source, {}).get("license", "unknown_manual_review"),
        "source_citation": kwargs.get("source_citation"),
        "downloaded_at": kwargs.get("downloaded_at") or utc_now_iso(),
        "source_last_modified": kwargs.get("source_last_modified"),
        "checksum_sha256": kwargs.get("checksum_sha256"),
        "data_kind": data_kind,
        "pattern_kind": pattern_kind,
        "preparation": kwargs.get("preparation") or "unknown",
        "treatment": kwargs.get("treatment") or "unknown",
        "wavelength_A": kwargs.get("wavelength_A") or DEFAULT_WAVELENGTH_A,
        "radiation": kwargs.get("radiation") or "CuKa",
        "matched_name": matched_name,
        "match_confidence": match["score"],
        "match_basis": match["basis"],
        "peaks": kwargs.get("peaks") or [],
        "profile": kwargs.get("profile") or {"two_theta_deg": [], "intensity": []},
        "cif": kwargs.get("cif") or {},
        "warnings": warnings,
        "curation_status": kwargs.get("curation_status") or match["curation_status"],
    }


def write_jsonl(path, records):
    """
    Gera artefatos derivados, relatórios ou saídas serializadas com parâmetros e proveniência para auditoria posterior.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
        records: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        for record in records:
            fp.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    records = []
    path = Path(path)
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def build_panel_index(records, max_peaks=12):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        records: Valor de entrada consumido por esta etapa do fluxo.
        max_peaks: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    out = []
    for record in records:
        peaks = record.get("peaks") or []
        top_peaks = sorted(peaks, key=lambda peak: peak.get("relative_intensity") or peak.get("intensity") or 0, reverse=True)[:max_peaks]
        out.append({
            "argiloteca_id": record.get("argiloteca_id"),
            "source": record.get("source"),
            "source_record_id": record.get("source_record_id"),
            "data_kind": record.get("data_kind"),
            "pattern_kind": record.get("pattern_kind"),
            "top_peaks": top_peaks,
            "source_url": record.get("source_record_url") or record.get("source_file_url"),
            "local_path_relativo": record.get("local_path_relativo") or (record.get("cif") or {}).get("local_path"),
            "match_confidence": record.get("match_confidence"),
            "curation_status": record.get("curation_status"),
            "warnings": record.get("warnings") or [],
        })
    return out


def write_curation_queue(path, records):
    """
    Gera artefatos derivados, relatórios ou saídas serializadas com parâmetros e proveniência para auditoria posterior.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
        records: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "argiloteca_id", "mineral", "title_pt", "family", "category", "source",
        "source_record_id", "matched_name", "match_confidence", "reason",
        "warnings", "recommended_action", "source_url", "local_file",
    ]
    with open(path, "w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for record in records:
            if record.get("curation_status") not in {"needs_review", "rejected", "provisional"}:
                continue
            writer.writerow({
                "argiloteca_id": record.get("argiloteca_id"),
                "mineral": record.get("argiloteca_mineral"),
                "title_pt": record.get("title_pt", ""),
                "family": record.get("argiloteca_family"),
                "category": record.get("argiloteca_category"),
                "source": record.get("source"),
                "source_record_id": record.get("source_record_id"),
                "matched_name": record.get("matched_name"),
                "match_confidence": record.get("match_confidence"),
                "reason": record.get("curation_status"),
                "warnings": " | ".join(record.get("warnings") or []),
                "recommended_action": "Revisar nome, fórmula, família, picos e licença antes de expor como referência auxiliar.",
                "source_url": record.get("source_record_url") or record.get("source_file_url"),
                "local_file": record.get("local_path_relativo") or (record.get("cif") or {}).get("local_path"),
            })


def build_coverage(vocabulary, records):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        vocabulary: Valor de entrada consumido por esta etapa do fluxo.
        records: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    by_term = {term["id"]: [] for term in vocabulary}
    for record in records:
        by_term.setdefault(record.get("argiloteca_id"), []).append(record)

    def has(term_records, source=None, data_kind=None):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            term_records: Valor de entrada consumido por esta etapa do fluxo.
            source: Valor de entrada consumido por esta etapa do fluxo.
            data_kind: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        return any((source is None or r.get("source") == source) and (data_kind is None or r.get("data_kind") == data_kind) for r in term_records)

    by_family = {}
    for term in vocabulary:
        family = term.get("family") or "unknown"
        fam = by_family.setdefault(family, {"total_terms": 0, "with_external_match": 0, "needs_review": 0})
        term_records = by_term.get(term["id"], [])
        fam["total_terms"] += 1
        if term_records:
            fam["with_external_match"] += 1
        if any(r.get("curation_status") in {"needs_review", "rejected", "provisional"} for r in term_records):
            fam["needs_review"] += 1

    values = list(by_term.values())
    return {
        "total_terms": len(vocabulary),
        "with_rruff_measured_xrd": sum(1 for rs in values if has(rs, "RRUFF", "measured_powder_xrd")),
        "with_amcsd_cif": sum(1 for rs in values if has(rs, "AMCSD", "cif_structure")),
        "with_amcsd_dif": sum(1 for rs in values if has(rs, "AMCSD", "dif_reference")),
        "with_cod_cif": sum(1 for rs in values if has(rs, "COD", "cif_structure")),
        "with_simulated_pattern": sum(1 for rs in values if has(rs, None, "simulated_powder_xrd")),
        "needs_review": sum(1 for rs in values if any(r.get("curation_status") in {"needs_review", "rejected", "provisional"} for r in rs)),
        "without_external_match": sum(1 for rs in values if not rs),
        "by_family": by_family,
    }


def save_source_licenses(out_dir):
    """
    Gera artefatos derivados, relatórios ou saídas serializadas com parâmetros e proveniência para auditoria posterior.
    
    Args:
        out_dir: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    path = Path(out_dir) / "manifests" / "source_licenses.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(SOURCE_LICENSES, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path
