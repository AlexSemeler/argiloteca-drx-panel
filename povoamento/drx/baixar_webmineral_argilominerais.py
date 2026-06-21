#!/usr/bin/env python3
"""Baixa/cacheia paginas WebMineral para os argilominerais da Argiloteca.

O objetivo e manter uma copia local e auditavel das paginas consultadas para os
81 termos do vocabulario controlado. Quando uma pagina nao estiver disponivel
ou a rede falhar, o termo ainda entra no manifesto com status de erro. O
classificador DRX pode usar esse JSON como referencia local preferencial e
completar linhas d/I conhecidas com a referencia embutida.
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VOCAB = REPO_ROOT / "povoamento" / "vocabularios" / "argilominerais.jsonl"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "povoamento" / "visualizacao-drx" / "webmineral"
DEFAULT_REFERENCE_JSON = (
    REPO_ROOT
    / "povoamento"
    / "visualizacao-drx"
    / "saida_argiloteca_drx"
    / "webmineral_argilominerais_vocabulario.json"
)
WEBMINERAL_DATA_BASE = "https://webmineral.com/data"
WEBMINERAL_XRAY_URL = "https://webmineral.com/MySQL/xray.php"
CACHED_HTML_MIN_BYTES = 1000
# Faixas de d-spacing que tambem aparecem no classificador e no painel. Aqui
# ficam no manifesto WebMineral para rastrear a origem das regras auxiliares.
DRX_DIAGNOSTIC_RANGES = {
    "illite_10a": {"d_min": 9.7, "d_max": 10.4, "preparation": "any", "label": "Ilita 10A"},
    "kaolinite_7a": {"d_min": 6.9, "d_max": 7.8, "preparation": "any", "label": "Caulinita 7A"},
    "smectite_natural": {"d_min": 13.0, "d_max": 16.5, "preparation": "natural", "label": "Esmectita natural"},
    "smectite_glycolated": {"d_min": 16.6, "d_max": 18.6, "preparation": "glicolado", "label": "Esmectita glicolada"},
    "smectite_calcined": {"d_min": 9.4, "d_max": 10.4, "preparation": "calcinado", "label": "Esmectita calcinada"},
    "chlorite_001_basal": {"d_min": 13.7, "d_max": 14.6, "preparation": "any", "label": "Clorita basal 001"},
    "quartz_101": {"d_min": 3.24, "d_max": 3.44, "preparation": "any", "label": "Quartzo 101"},
    "quartz_100": {"d_min": 4.23, "d_max": 4.35, "preparation": "any", "label": "Quartzo 100"},
}
CHLORITE_BASAL_RANGE = DRX_DIAGNOSTIC_RANGES["chlorite_001_basal"]
CHLORITE_DIAGNOSTIC_SOURCE = "diagnostic_rule_chlorite_13_7_14_6a"
CHLORITE_DIAGNOSTIC_FEATURE = "diagnostic_basal_chlorite_13_7_14_6a"
CHLORITE_TARGET_D = 14.2
# Padrao local para clorita basal: ajuda a triagem quando WebMineral nao traz
# uma linha 001 clara, mas continua exigindo curadoria N/G/C.
CHLORITE_REFERENCE_PATTERNS = [
    {
        "id": "chlorite_001_basal",
        "reflection": "001",
        "d_min": CHLORITE_BASAL_RANGE["d_min"],
        "d_max": CHLORITE_BASAL_RANGE["d_max"],
        "target_d": CHLORITE_TARGET_D,
        "relative_intensity_min": 18.0,
        "source": CHLORITE_DIAGNOSTIC_SOURCE,
        "note": "Pico basal da clorita; usar N/G/C, permanencia termica e harmonicos para curadoria.",
    }
]


def utc_now_iso() -> str:
    """Retorna timestamp UTC para manifestos derivados."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def safe_slug(value: str) -> str:
    """Cria slug simples compativel com URLs historicas do WebMineral."""
    return (
        value.strip()
        .replace("/", "-")
        .replace("\\", "-")
        .replace("'", "")
        .replace('"', "")
        .replace(" ", "_")
    )


def load_vocab(path: Path) -> list[dict]:
    """Carrega o vocabulario autorizado que guia a coleta WebMineral."""
    terms = []
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            title = item.get("title") or {}
            terms.append(
                {
                    "id": item.get("id"),
                    "title_en": title.get("en") or item.get("id"),
                    "title_pt": title.get("pt") or "",
                    "category": (item.get("props") or {}).get("category"),
                    "family": (item.get("props") or {}).get("family"),
                    "status": (item.get("props") or {}).get("status"),
                    "source": (item.get("props") or {}).get("source"),
                }
            )
    return terms


def candidate_urls(term: dict) -> list[str]:
    """Gera URLs plausiveis por nome ingles e id do vocabulario."""
    names = [
        term.get("title_en") or "",
        str(term.get("id") or "").replace("-", " "),
    ]
    urls = []
    for name in names:
        name = name.strip()
        if not name:
            continue
        data_slug = urllib.parse.quote(safe_slug(name))
        urls.append(f"{WEBMINERAL_DATA_BASE}/{data_slug}.shtml")
        urls.append(f"{WEBMINERAL_XRAY_URL}?mineral={urllib.parse.quote(name)}")
    seen = set()
    unique = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def fetch_url(url: str, timeout: int) -> tuple[str | None, str | None]:
    """Baixa uma URL com user-agent proprio, retornando erro textual se falhar."""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Argiloteca-DRX/1.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace"), None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, str(exc)


def extract_xray_lines(html: str) -> list[dict]:
    """Extrai pares d/I de paginas WebMineral quando presentes.

    O WebMineral pode mudar o HTML; por isso este parser e defensivo e usa
    apenas padroes claros. Se nada for reconhecido, retorna lista vazia.
    """
    lines = []

    # Paginas de especies do WebMineral costumam trazer:
    # "X Ray Diffraction: By Intensity(I/Io): 7.17(1), 1.49(0.9), ..."
    # O valor entre parenteses e intensidade relativa I/Io.
    for section in _xray_sections(html):
        section_text = _clean_html_text(section)
        section_lines = []
        for match in re.finditer(
            r"(?P<d>\d+(?:\.\d+)?)\s*\(\s*(?P<i>\d+(?:\.\d+)?|0?\.\d+)\s*\)",
            section_text,
        ):
            try:
                d_value = float(match.group("d"))
                i_value = float(match.group("i"))
            except ValueError:
                continue
            if 0.5 <= d_value <= 80 and i_value >= 0:
                section_lines.append({"d": d_value, "i": i_value})
        if section_lines:
            max_i = max((line["i"] for line in section_lines), default=0)
            if max_i <= 1.5:
                for line in section_lines:
                    line["i"] = round(line["i"] * 100.0, 3)
            lines.extend(section_lines)

    text = _clean_html_text(html)

    # Padrao comum na tabela xray.php: d(theta) intensidade.
    if not lines:
        for match in re.finditer(r"(?P<d>\d+\.\d+)\s*\(\s*(?P<t>\d+\.\d+)\s*\)\s+(?P<i>\d{1,3})", text):
            try:
                lines.append({"d": float(match.group("d")), "i": float(match.group("i"))})
            except ValueError:
                continue

    # Fallback para paginas de dados com labels d/I próximos.
    if not lines:
        for match in re.finditer(r"\bd\s*=\s*(?P<d>\d+\.\d+).{0,80}?\bI\s*=\s*(?P<i>\d{1,3})", text, re.I):
            try:
                lines.append({"d": float(match.group("d")), "i": float(match.group("i"))})
            except ValueError:
                continue

    dedup = []
    seen = set()
    for line in lines:
        key = (round(line["d"], 4), round(line["i"], 2))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(line)
    return dedup[:12]


def _html_fragment_to_formula(html: str) -> str:
    text = html_lib.unescape(html or "")
    text = re.sub(r"<\s*sub\s*>(.*?)<\s*/\s*sub\s*>", r"\1", text, flags=re.I | re.S)
    text = re.sub(r"<\s*sup\s*>(.*?)<\s*/\s*sup\s*>", r"^\1", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&#8226;", "·").replace("•", "·").replace("�", "·")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _labeled_table_value(html: str, label: str) -> str:
    pattern = (
        r"<b>\s*"
        + label
        + r"\s*:\s*</b>\s*</td>\s*<td[^>]*>(?P<value>.*?)</td>"
    )
    match = re.search(pattern, html or "", re.I | re.S)
    if not match:
        return ""
    return _html_fragment_to_formula(match.group("value"))


def _numeric_value(value: str | None) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def _regex_number(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text or "", re.I)
    if not match:
        return None
    return _numeric_value(match.group(1))


def _parse_axial_ratios(value: str) -> dict:
    ratios = {"raw": value}
    match = re.search(
        r"a:b:c\s*=\s*([0-9.,]+)\s*:\s*([0-9.,]+)\s*:\s*([0-9.,]+)",
        value or "",
        re.I,
    )
    if match:
        ratios.update(
            {
                "a_to_b": _numeric_value(match.group(1)),
                "b_to_b": _numeric_value(match.group(2)),
                "c_to_b": _numeric_value(match.group(3)),
            }
        )
    return ratios


def _parse_cell_parameters(value: str) -> dict:
    cell = {"raw": value}
    fields = {
        "a_angstrom": r"\ba\s*=\s*([0-9.,]+)",
        "b_angstrom": r"\bb\s*=\s*([0-9.,]+)",
        "c_angstrom": r"\bc\s*=\s*([0-9.,]+)",
        "alpha_deg": r"\balpha\s*=\s*([0-9.,]+)",
        "beta_deg": r"\bbeta\s*=\s*([0-9.,]+)",
        "gamma_deg": r"\bgamma\s*=\s*([0-9.,]+)",
        "volume_angstrom3": r"\bV\s*=\s*([0-9.,]+)",
        "calculated_density_g_cm3": r"Den\s*\(\s*Calc\s*\)\s*=\s*([0-9.,]+)",
    }
    for key, pattern in fields.items():
        cell[key] = _regex_number(pattern, value)
    z_value = _regex_number(r"\bZ\s*=\s*([0-9.,]+)", value)
    cell["z"] = int(z_value) if z_value is not None and z_value.is_integer() else z_value
    cell["has_cell_parameters"] = any(
        cell.get(key) is not None
        for key in ("a_angstrom", "b_angstrom", "c_angstrom", "volume_angstrom3")
    )
    return cell


def _parse_crystal_system(value: str) -> dict:
    parsed = {
        "raw": value,
        "crystal_system": value,
        "hm_symbol": "",
        "space_group": "",
    }
    match = re.search(
        r"^(?P<system>.*?)\s*H-M\s+Symbol\s*\((?P<hm>[^)]+)\)\s*Space\s+Group:\s*(?P<space>.+)$",
        value or "",
        re.I,
    )
    if match:
        parsed.update(
            {
                "crystal_system": match.group("system").strip(),
                "hm_symbol": match.group("hm").strip(),
                "space_group": match.group("space").strip(),
            }
        )
    return parsed


def extract_crystallography(html: str) -> dict:
    """Extrai cristalografia auxiliar para desempate de candidatos DRX."""
    axial_raw = _labeled_table_value(html, r"Axial\s+Ratios")
    cell_raw = _labeled_table_value(html, r"Cell\s+Dimensions")
    crystal_system_raw = _labeled_table_value(html, r"Crystal\s+System")
    xray_summary = _labeled_table_value(html, r"X\s+Ray\s+Diffraction")
    crystallography = {
        "axial_ratios": _parse_axial_ratios(axial_raw) if axial_raw else {"raw": ""},
        "cell_parameters": _parse_cell_parameters(cell_raw) if cell_raw else {"raw": "", "has_cell_parameters": False},
        "crystal_system": _parse_crystal_system(crystal_system_raw) if crystal_system_raw else {
            "raw": "",
            "crystal_system": "",
            "hm_symbol": "",
            "space_group": "",
        },
        "xray_summary": xray_summary,
    }
    crystallography["has_crystallography"] = bool(axial_raw or cell_raw or crystal_system_raw)
    return crystallography


def _parse_classification(value: str) -> dict:
    match = re.search(r"\b([0-9]{2}(?:\.[A-Za-z0-9]+)+)\b", value or "")
    return {
        "raw": value,
        "code": match.group(1) if match else "",
        "description": value,
    }


def extract_structural_classification(html: str) -> dict:
    """Extrai classes Dana/Strunz como filtros de familia estrutural."""
    dana_raw = _labeled_table_value(html, r"Dana\s+Class")
    strunz_raw = _labeled_table_value(html, r"Strunz\s+Class")
    classification = {
        "dana": _parse_classification(dana_raw) if dana_raw else {"raw": "", "code": "", "description": ""},
        "strunz": _parse_classification(strunz_raw) if strunz_raw else {"raw": "", "code": "", "description": ""},
    }
    classification["has_structural_classification"] = bool(dana_raw or strunz_raw)
    return classification


def extract_structure_reference(html: str) -> dict:
    """Extrai referencia/modelo jPOWD quando o WebMineral traz estrutura."""
    match = re.search(r"<b>\s*Crystal\s+Structure\s*:\s*</b>", html or "", re.I)
    chunk = html[match.end() : match.end() + 4500] if match else ""
    model_match = re.search(r'<param\s+name="d_Model"\s+value="([^"]+)"', chunk, re.I)
    ref_match = re.search(r"<br>\s*<small>(.*?)</small>", chunk, re.I | re.S)
    jpowd_model = html_lib.unescape(model_match.group(1)).strip() if model_match else ""
    structure_reference = _html_fragment_to_formula(ref_match.group(1)) if ref_match else ""
    return {
        "has_structure_reference": bool(jpowd_model or structure_reference),
        "jpowd_model": jpowd_model,
        "structure_reference": structure_reference,
    }


def _parse_density(value: str) -> dict:
    density = {"raw": value, "min_g_cm3": None, "max_g_cm3": None, "average_g_cm3": None}
    average = _regex_number(r"Average\s*=\s*([0-9.,]+)", value)
    range_match = re.search(r"([0-9.,]+)\s*-\s*([0-9.,]+)", value or "")
    if range_match:
        density["min_g_cm3"] = _numeric_value(range_match.group(1))
        density["max_g_cm3"] = _numeric_value(range_match.group(2))
        density["average_g_cm3"] = average
    else:
        numeric = _regex_number(r"([0-9.,]+)", value)
        density["average_g_cm3"] = average if average is not None else numeric
    return density


def _parse_electron_density(value: str) -> dict:
    return {
        "raw": value,
        "bulk_density_g_cm3": _regex_number(r"Bulk\s+Density\s*\(\s*Electron\s+Density\s*\)\s*=\s*([0-9.,]+)", value),
        "specific_gravity": _regex_number(r"Specific\s+Gravity\s+of.*?=\s*([0-9.,]+)", value),
    }


def _parse_photoelectric(value: str) -> dict:
    return {
        "raw": value,
        "pe_barns_per_electron": _regex_number(r"PE[^=]{0,120}=\s*([0-9.,]+)", value),
        "u_barns_per_cc": _regex_number(r"\bU\s*=.*?=\s*([0-9.,]+)", value),
    }


def _parse_radioactivity(value: str) -> dict:
    grapi = _regex_number(r"GRapi\s*=\s*([0-9.,]+)", value)
    return {
        "raw": value,
        "grapi": grapi,
        "is_radioactive": bool(grapi and grapi > 0) and "not radioactive" not in (value or "").casefold(),
    }


def extract_auxiliary_qc(html: str) -> dict:
    """Extrai atributos numericos auxiliares para QC/classificacao."""
    density_raw = _labeled_table_value(html, r"Density")
    electron_density_raw = _labeled_table_value(html, r"Electron\s+Density")
    photoelectric_raw = _labeled_table_value(html, r"Photoelectric")
    radioactivity_raw = _labeled_table_value(html, r"Radioactivity")
    auxiliary = {
        "density": _parse_density(density_raw) if density_raw else {"raw": ""},
        "electron_density": _parse_electron_density(electron_density_raw) if electron_density_raw else {"raw": ""},
        "photoelectric": _parse_photoelectric(photoelectric_raw) if photoelectric_raw else {"raw": ""},
        "radioactivity": _parse_radioactivity(radioactivity_raw) if radioactivity_raw else {"raw": ""},
    }
    auxiliary["has_auxiliary_qc"] = bool(density_raw or electron_density_raw or photoelectric_raw or radioactivity_raw)
    return auxiliary


def extract_descriptive_properties(html: str) -> dict:
    """Extrai textos mineralogicos que podem virar features auxiliares."""
    labels = {
        "environment": r"Environment",
        "ima_status": r"IMA\s+Status",
        "synonym": r"Synonym",
        "color": r"Color",
        "cleavage": r"Cleavage",
        "habit": r"Habit",
        "hardness": r"Hardness",
        "luster": r"Luster",
        "streak": r"Streak",
        "optical_data": r"Optical\s+Data",
        "gladstone_dale": r"Gladstone-Dale",
    }
    properties = {key: _labeled_table_value(html, label) for key, label in labels.items()}
    properties["has_descriptive_properties"] = any(properties.values())
    return properties


def extract_webmineral_features(html: str) -> dict:
    """Agrega blocos quimicos, cristalograficos e auxiliares de uma pagina."""
    return {
        "chemistry": extract_chemical_composition(html),
        "crystallography": extract_crystallography(html),
        "classification": extract_structural_classification(html),
        "structure_reference": extract_structure_reference(html),
        "auxiliary_qc": extract_auxiliary_qc(html),
        "descriptive_properties": extract_descriptive_properties(html),
    }


def _composition_entries(html: str) -> list[dict]:
    """Extrai composicao elementar/oxidos da tabela HTML do WebMineral."""
    entries = []
    for match in re.finditer(
        r'<a[^>]+/chem/Chem-(?P<symbol>[A-Za-z]+)\.shtml[^>]*>'
        r"(?P<element>[^<]+)</a>(?P<rest>.*?)</font>",
        html or "",
        re.I | re.S,
    ):
        element = _clean_html_text(match.group("element")).strip()
        symbol = match.group("symbol").strip()
        text = _html_fragment_to_formula(match.group("rest"))
        parsed = re.search(
            r"(?P<element_percent>\d+(?:\.\d+)?)\s*%\s*"
            + re.escape(symbol)
            + r"\s+(?P<oxide_percent>\d+(?:\.\d+)?)\s*%\s*(?P<oxide>[A-Za-z0-9().^+\-]+)",
            text,
        )
        if not parsed:
            continue
        entries.append(
            {
                "element": element,
                "symbol": symbol,
                "element_percent": float(parsed.group("element_percent")),
                "oxide": parsed.group("oxide"),
                "oxide_percent": float(parsed.group("oxide_percent")),
            }
        )
    return entries


def extract_chemical_composition(html: str) -> dict:
    """Extrai formula e composicao quimica das paginas locais WebMineral."""
    chemical_formula = _labeled_table_value(html, r"Chemical\s+Formula")
    empirical_formula = _labeled_table_value(html, r"Empirical\s+Formula")
    text = _clean_html_text(html or "")
    molecular_weight = None
    weight_match = re.search(r"Molecular\s+Weight\s*=\s*(\d+(?:\.\d+)?)\s*gm", text, re.I)
    if weight_match:
        molecular_weight = float(weight_match.group(1))
    total_oxide = None
    total_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*=\s*TOTAL\s+OXIDE", text, re.I)
    if total_match:
        total_oxide = float(total_match.group(1))
    entries = _composition_entries(html)
    return {
        "chemical_formula": chemical_formula,
        "empirical_formula": empirical_formula,
        "molecular_weight_g_mol": molecular_weight,
        "composition": entries,
        "total_oxide_percent": total_oxide,
        "has_chemical_composition": bool(chemical_formula or empirical_formula or entries),
    }


def _clean_html_text(html: str) -> str:
    """Remove tags HTML e compacta espacos para parsers regex."""
    text = html_lib.unescape(html)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def _xray_sections(html: str) -> list[str]:
    """Recorta trechos proximos a X-Ray Diffraction para parsing defensivo."""
    sections = []
    for match in re.finditer(r"X\s*-?\s*Ray\s+Diffraction\s*:?", html, re.I):
        start = max(0, match.start() - 120)
        end = html.find("</tr>", match.end())
        if end == -1:
            end = match.end() + 1400
        else:
            end += len("</tr>")
        sections.append(html[start:end])
    return sections


def save_json(path: Path, payload: dict) -> None:
    """Grava JSON derivado com codificacao UTF-8 e newline final."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
        fp.write("\n")


def enrich_diagnostic_patterns(record: dict) -> dict:
    """Anexa a regra local de clorita ao registro WebMineral de chlorite."""
    if record.get("id") != "chlorite":
        return record
    record["diagnostic_ranges"] = {"chlorite_001_basal": DRX_DIAGNOSTIC_RANGES["chlorite_001_basal"]}
    record["webmineral_reference_patterns"] = CHLORITE_REFERENCE_PATTERNS
    record["classifier_feature_groups"] = sorted(
        set((record.get("classifier_feature_groups") or []) + [CHLORITE_DIAGNOSTIC_FEATURE])
    )
    lines = record.get("lines") or []
    d_min = CHLORITE_BASAL_RANGE["d_min"]
    d_max = CHLORITE_BASAL_RANGE["d_max"]
    has_basal = any(d_min <= float(line.get("d") or 0) <= d_max for line in lines if isinstance(line, dict))
    if not has_basal:
        lines.insert(
            0,
            {
                "d": CHLORITE_TARGET_D,
                "i": 100,
                "source": CHLORITE_DIAGNOSTIC_SOURCE,
                "reflection": "001",
                "range_d": [d_min, d_max],
            },
        )
    record["lines"] = lines
    return record


def collect(vocab_path: Path, output_dir: Path, reference_json: Path, timeout: int, offline: bool = False) -> dict:
    """Coleta ou reaproveita HTML WebMineral e consolida o JSON de referencia."""
    terms = load_vocab(vocab_path)
    pages_dir = output_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    records = []

    for term in terms:
        urls = candidate_urls(term)
        errors = []
        html_path = None
        lines = []
        selected_url = None
        status = "download_error"
        cached_path = pages_dir / f"{term['id']}.html"
        if cached_path.exists() and (offline or cached_path.stat().st_size >= CACHED_HTML_MIN_BYTES):
            html = cached_path.read_text(encoding="utf-8", errors="replace")
            html_path = cached_path
            selected_url = urls[0] if urls else WEBMINERAL_DATA_BASE
            lines = extract_xray_lines(html)
            features = extract_webmineral_features(html)
            status = "cached"
        for url in urls:
            if html_path:
                break
            if offline:
                errors.append({"url": url, "error": "offline_cache_missing"})
                continue
            html, error = fetch_url(url, timeout=timeout)
            if error:
                errors.append({"url": url, "error": error})
                continue
            selected_url = url
            html_path = pages_dir / f"{term['id']}.html"
            html_path.write_text(html or "", encoding="utf-8")
            lines = extract_xray_lines(html or "")
            features = extract_webmineral_features(html or "")
            status = "downloaded"
            break
        if not html_path:
            features = extract_webmineral_features("")
        records.append(
            enrich_diagnostic_patterns(
                {
                "id": term["id"],
                "mineral": term["title_en"],
                "title_pt": term["title_pt"],
                "category": term["category"],
                "family": term["family"],
                "vocabulary_source": term["source"],
                "source": selected_url or WEBMINERAL_DATA_BASE,
                "webmineral_url": selected_url,
                "local_html": str(html_path) if html_path else None,
                "status": status if html_path else "download_error",
                "lines": lines,
                "chemistry": features["chemistry"],
                "crystallography": features["crystallography"],
                "classification": features["classification"],
                "structure_reference": features["structure_reference"],
                "auxiliary_qc": features["auxiliary_qc"],
                "descriptive_properties": features["descriptive_properties"],
                "errors": errors[:3],
                }
            )
        )

    payload = {
        "source": "WebMineral local copy for Argiloteca clay vocabulary",
        "source_url": WEBMINERAL_DATA_BASE,
        "xray_url": WEBMINERAL_XRAY_URL,
        "generated_at": utc_now_iso(),
        "vocabulary_path": str(vocab_path),
        "diagnostic_ranges": DRX_DIAGNOSTIC_RANGES,
        "records": records,
        "summary": {
            "terms_total": len(records),
            "downloaded": sum(1 for row in records if row["status"] in {"downloaded", "cached"}),
            "with_xray_lines": sum(1 for row in records if row.get("lines")),
            "with_chemical_composition": sum(
                1 for row in records if (row.get("chemistry") or {}).get("has_chemical_composition")
            ),
            "with_crystallography": sum(
                1 for row in records if (row.get("crystallography") or {}).get("has_crystallography")
            ),
            "with_cell_parameters": sum(
                1
                for row in records
                if ((row.get("crystallography") or {}).get("cell_parameters") or {}).get("has_cell_parameters")
            ),
            "with_structural_classification": sum(
                1 for row in records if (row.get("classification") or {}).get("has_structural_classification")
            ),
            "with_structure_reference": sum(
                1 for row in records if (row.get("structure_reference") or {}).get("has_structure_reference")
            ),
            "with_auxiliary_qc": sum(
                1 for row in records if (row.get("auxiliary_qc") or {}).get("has_auxiliary_qc")
            ),
            "download_errors": sum(1 for row in records if row["status"] == "download_error"),
        },
        "notes": [
            "Copia local criada para uso como referencia de triagem DRX.",
            "Nem todo termo do vocabulario da Argiloteca corresponde a uma especie com pagina WebMineral.",
            "Linhas d/I devem ser usadas como evidencia auxiliar, nao como confirmacao mineralogica.",
            "Faixas diagnosticas locais N/G/C sincronizadas em 2026-06-19; clorita 001 usa 13.70-14.60 A.",
        ],
    }
    save_json(reference_json, payload)
    save_json(output_dir / "webmineral_argilominerais_vocabulario_manifest.json", payload)
    return payload


def parse_args() -> argparse.Namespace:
    """Define parametros CLI para coleta online/offline."""
    parser = argparse.ArgumentParser(description="Baixa/cacheia WebMineral para os 81 argilominerais da Argiloteca.")
    parser.add_argument("--vocab", default=str(DEFAULT_VOCAB), help="Vocabulário JSONL de argilominerais.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Diretório da cópia local WebMineral.")
    parser.add_argument("--reference-json", default=str(DEFAULT_REFERENCE_JSON), help="JSON consolidado usado pelo classificador.")
    parser.add_argument("--timeout", type=int, default=25, help="Timeout de rede por URL em segundos.")
    parser.add_argument("--offline", action="store_true", help="Usa apenas paginas HTML ja cacheadas; nao tenta rede.")
    return parser.parse_args()


def main() -> None:
    """Executa coleta WebMineral e imprime resumo da referencia gerada."""
    args = parse_args()
    payload = collect(
        vocab_path=Path(args.vocab),
        output_dir=Path(args.output_dir),
        reference_json=Path(args.reference_json),
        timeout=args.timeout,
        offline=args.offline,
    )
    print(
        json.dumps(
            {
                "success": True,
                "reference_json": args.reference_json,
                "output_dir": args.output_dir,
                **payload["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
