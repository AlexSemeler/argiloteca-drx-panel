#!/usr/bin/env python3
"""Classifica candidatos mineralogicos a partir de arquivos RAW de DRX.

O classificador compara os picos principais observados em 2theta/d-spacing com
linhas de referencia d/I. A fonte primaria prevista e a tabela publica do
WebMineral; quando nao houver cache local, o script usa uma referencia minima
embutida com argilominerais e fases comuns em amostras argilosas.

Resultado esperado: candidatos para triagem/curadoria, nao laudo mineralogico.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ARGILOTECA_CUSTOM = REPO_ROOT / "argiloteca" / "argiloteca_custom"
if str(ARGILOTECA_CUSTOM) not in sys.path:
    sys.path.insert(0, str(ARGILOTECA_CUSTOM))

from argiloteca.services.drx import (  # noqa: E402
    DRX_AXIS_ALIGNMENT_MIN_OFFSET,
    DRX_AXIS_CORRECTIONS_PATH,
    DRX_DIAGNOSTIC_D_RANGES,
    RawParseError,
    apply_two_theta_axis_alignment,
    calculate_quartz_axis_offset,
    infer_diffractogram_sample_base,
    infer_diffractogram_treatment,
    load_two_theta_axis_corrections,
    parse_raw_file,
)


DEFAULT_RAW_DIR = Path("/Users/visualizacao-drx/raw")
DEFAULT_OUTPUT_DIR = Path("/Users/visualizacao-drx/saida_argiloteca_drx")
PROJECT_VISUALIZACAO_DRX_DIR = REPO_ROOT / "povoamento" / "visualizacao-drx"
PROJECT_WEBMINERAL_REFERENCE = PROJECT_VISUALIZACAO_DRX_DIR / "saida_argiloteca_drx" / "webmineral_argilominerais_vocabulario.json"
PROJECT_WEBMINERAL_COPY_DIR = PROJECT_VISUALIZACAO_DRX_DIR / "webmineral"
ARGILOTECA_CLAY_VOCAB = REPO_ROOT / "povoamento" / "vocabularios" / "argilominerais.jsonl"
ARGILOTECA_VOCABULARY_EXPANSIONS = REPO_ROOT / "outputs" / "vocabularios" / "argilominerais_expansoes_classificacao.jsonl"
DEFAULT_REFERENCE_CACHE = PROJECT_WEBMINERAL_REFERENCE
WEBMINERAL_XRAY_URL = "https://webmineral.com/MySQL/xray.php"
CU_KA1 = 1.54056
# Faixas diagnosticas compartilhadas com o painel. Elas entram no classificador
# como evidencias auxiliares em d-spacing, especialmente para N/G/C e quartzo.
RANGE_ILITA_10A = DRX_DIAGNOSTIC_D_RANGES["illite10A"]
RANGE_CAULINITA_7A = DRX_DIAGNOSTIC_D_RANGES["kaolinite7A"]
RANGE_ESMECTITA_N = DRX_DIAGNOSTIC_D_RANGES["smectiteNatural"]
RANGE_ESMECTITA_G = DRX_DIAGNOSTIC_D_RANGES["smectiteGlycolated"]
RANGE_ESMECTITA_C = DRX_DIAGNOSTIC_D_RANGES["smectiteCalcined"]
RANGE_CLORITA_14A = DRX_DIAGNOSTIC_D_RANGES["chlorite14A"]
RANGE_QUARTZO_101 = DRX_DIAGNOSTIC_D_RANGES["quartz101"]
RANGE_QUARTZO_100 = DRX_DIAGNOSTIC_D_RANGES["quartz100"]
CHLORITE_BASAL_D_RANGE = RANGE_CLORITA_14A
CHLORITE_DIAGNOSTIC_SOURCE = "diagnostic_rule_chlorite_13_7_14_6a"
CHLORITE_MIN_RELATIVE_INTENSITY = 18.0


# Referencia minima para manter a triagem operacional quando o WebMineral ou o
# cache local nao estao disponiveis. Nao substitui padroes curatoriais completos.
EMBEDDED_REFERENCE = [
    {
        "mineral": "Kaolinite",
        "formula": "Al2Si2O5(OH)4",
        "group": "Grupo caulinita-serpentina",
        "source": "embedded WebMineral-compatible d/I reference",
        "lines": [{"d": 7.15, "i": 100}, {"d": 3.58, "i": 80}, {"d": 2.56, "i": 60}],
    },
    {
        "mineral": "Halloysite",
        "formula": "Al2Si2O5(OH)4",
        "group": "Grupo caulinita-serpentina",
        "source": "embedded WebMineral-compatible d/I reference",
        "lines": [{"d": 7.35, "i": 100}, {"d": 4.43, "i": 55}, {"d": 3.63, "i": 70}],
    },
    {
        "mineral": "Illite",
        "formula": "K0.65Al2.0[Al0.65Si3.35O10](OH)2",
        "group": "Grupo ilita e micas relacionadas",
        "source": "embedded WebMineral-compatible d/I reference",
        "lines": [{"d": 10.0, "i": 100}, {"d": 5.0, "i": 40}, {"d": 3.33, "i": 75}],
    },
    {
        "mineral": "Muscovite",
        "formula": "KAl2(AlSi3O10)(OH)2",
        "group": "Grupo das micas",
        "source": "embedded WebMineral-compatible d/I reference",
        "lines": [{"d": 9.95, "i": 100}, {"d": 4.48, "i": 60}, {"d": 3.34, "i": 80}],
    },
    {
        "mineral": "Brammallite",
        "formula": "(Na,H3O)(Al,Mg,Fe)2(Si,Al)4O10[(OH)2,(H2O)]",
        "group": "Grupo ilita e micas relacionadas",
        "source": "embedded WebMineral-compatible d/I reference",
        "lines": [{"d": 9.77, "i": 100}, {"d": 3.17, "i": 100}, {"d": 1.485, "i": 100}],
    },
    {
        "mineral": "Chlorite",
        "formula": "(Mg,Fe,Al)6(Si,Al)4O10(OH)8",
        "group": "Grupo das cloritas",
        "source": "embedded WebMineral-compatible d/I reference",
        "lines": [{"d": 14.2, "i": 100}, {"d": 7.1, "i": 60}, {"d": 3.54, "i": 80}],
    },
    {
        "mineral": "Montmorillonite",
        "formula": "(Na,Ca)0.33(Al,Mg)2Si4O10(OH)2.nH2O",
        "group": "Grupo esmectita",
        "source": "embedded WebMineral-compatible d/I reference",
        "lines": [{"d": 15.0, "i": 100}, {"d": 4.50, "i": 55}, {"d": 2.56, "i": 45}],
    },
    {
        "mineral": "Nontronite",
        "formula": "Na0.3Fe2(Si,Al)4O10(OH)2.nH2O",
        "group": "Grupo esmectita",
        "source": "embedded WebMineral-compatible d/I reference",
        "lines": [{"d": 15.4, "i": 100}, {"d": 4.56, "i": 100}, {"d": 1.52, "i": 100}],
    },
    {
        "mineral": "Hectorite",
        "formula": "Na0.3(Mg,Li)3Si4O10(OH)2",
        "group": "Grupo esmectita",
        "source": "embedded WebMineral-compatible d/I reference",
        "lines": [{"d": 15.8, "i": 80}, {"d": 4.58, "i": 100}, {"d": 1.53, "i": 100}],
    },
    {
        "mineral": "Quartz",
        "formula": "SiO2",
        "group": "Silicatos - tectossilicatos",
        "source": "embedded WebMineral-compatible d/I reference",
        "lines": [{"d": 3.34, "i": 100}, {"d": 4.26, "i": 35}, {"d": 1.82, "i": 25}],
    },
    {
        "mineral": "Albite",
        "formula": "NaAlSi3O8",
        "group": "Feldspatos",
        "source": "embedded WebMineral-compatible d/I reference",
        "lines": [{"d": 3.19, "i": 100}, {"d": 3.78, "i": 45}, {"d": 4.03, "i": 40}],
    },
    {
        "mineral": "Calcite",
        "formula": "CaCO3",
        "group": "Carbonatos",
        "source": "embedded WebMineral-compatible d/I reference",
        "lines": [{"d": 3.03, "i": 100}, {"d": 2.28, "i": 18}, {"d": 2.09, "i": 18}],
    },
    {
        "mineral": "Goethite",
        "formula": "FeO(OH)",
        "group": "Oxidos/hidroxidos de ferro",
        "source": "embedded WebMineral-compatible d/I reference",
        "lines": [{"d": 4.18, "i": 100}, {"d": 2.69, "i": 70}, {"d": 2.45, "i": 50}],
    },
    {
        "mineral": "Hematite",
        "formula": "Fe2O3",
        "group": "Oxidos de ferro",
        "source": "embedded WebMineral-compatible d/I reference",
        "lines": [{"d": 2.70, "i": 100}, {"d": 2.52, "i": 50}, {"d": 3.68, "i": 40}],
    },
]


def utc_now_iso():
    """Retorna timestamp UTC para rastrear execucoes derivadas."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
        fp.write("\n")


def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as fp:
            return json.load(fp)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default


def safe_text(value):
    return str(value or "").strip()


def two_theta_to_d(two_theta, wavelength=CU_KA1):
    """Converte 2theta em d-spacing pela lei de Bragg."""
    theta = math.radians(two_theta / 2.0)
    sine = math.sin(theta)
    if sine <= 0:
        return None
    return wavelength / (2.0 * sine)


def d_to_two_theta(d_spacing, wavelength=CU_KA1):
    """Converte d-spacing em 2theta pela lei de Bragg."""
    if not d_spacing or d_spacing <= 0:
        return None
    value = wavelength / (2.0 * d_spacing)
    if value <= 0 or value > 1:
        return None
    return math.degrees(2.0 * math.asin(value))


def moving_average(values, window):
    if window <= 1 or len(values) < window:
        return [float(value) for value in values]
    half = window // 2
    smoothed = []
    for index in range(len(values)):
        start = max(0, index - half)
        end = min(len(values), index + half + 1)
        chunk = values[start:end]
        smoothed.append(sum(chunk) / len(chunk))
    return smoothed


def percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return float(ordered[index])


def extract_peaks(two_theta, intensity, max_peaks=12, smooth_window=5, min_distance_deg=0.18, min_prominence_ratio=0.04):
    """Detecta picos locais principais em uma curva DRX ja parseada."""
    if len(two_theta) < 3 or len(two_theta) != len(intensity):
        return []
    smoothed = moving_average([float(value) for value in intensity], smooth_window)
    baseline = percentile(smoothed, 0.10)
    maximum = max(smoothed) if smoothed else 0.0
    amplitude = max(maximum - baseline, 1.0)
    threshold = baseline + amplitude * min_prominence_ratio
    candidates = []

    for index in range(1, len(smoothed) - 1):
        value = smoothed[index]
        if value < threshold:
            continue
        if value >= smoothed[index - 1] and value >= smoothed[index + 1]:
            d_spacing = two_theta_to_d(two_theta[index])
            if d_spacing:
                candidates.append(
                    {
                        "two_theta": round(float(two_theta[index]), 5),
                        "d": round(float(d_spacing), 5),
                        "intensity": round(float(intensity[index]), 5),
                        "relative_intensity": round(100.0 * max(value - baseline, 0.0) / amplitude, 2),
                        "index": index,
                    }
                )

    candidates.sort(key=lambda item: item["relative_intensity"], reverse=True)
    selected = []
    for peak in candidates:
        if any(abs(peak["two_theta"] - other["two_theta"]) < min_distance_deg for other in selected):
            continue
        selected.append(peak)
        if len(selected) >= max_peaks:
            break
    return selected


def ensure_chlorite_basal_peak(peaks, two_theta, intensity, smooth_window=5, min_prominence_ratio=0.04):
    """Reinsere pico basal de clorita quando ele aparece forte mas nao ficou no top."""
    if strongest_peak_in_d_range(peaks, *CHLORITE_BASAL_D_RANGE):
        return peaks
    if len(two_theta) < 3 or len(two_theta) != len(intensity):
        return peaks

    smoothed = moving_average([float(value) for value in intensity], smooth_window)
    baseline = percentile(smoothed, 0.10)
    maximum = max(smoothed) if smoothed else 0.0
    amplitude = max(maximum - baseline, 1.0)
    threshold = baseline + amplitude * (min_prominence_ratio / 2.0)
    range_indices = []
    for index in range(1, len(smoothed) - 1):
        d_spacing = two_theta_to_d(two_theta[index])
        if d_spacing and CHLORITE_BASAL_D_RANGE[0] <= d_spacing <= CHLORITE_BASAL_D_RANGE[1]:
            range_indices.append(index)
    if not range_indices:
        return peaks
    best_index = max(range_indices, key=lambda index: smoothed[index])
    if smoothed[best_index] < threshold:
        return peaks
    d_spacing = two_theta_to_d(two_theta[best_index])
    if not d_spacing:
        return peaks
    diagnostic_peak = {
        "two_theta": round(float(two_theta[best_index]), 5),
        "d": round(float(d_spacing), 5),
        "intensity": round(float(intensity[best_index]), 5),
        "relative_intensity": round(100.0 * max(smoothed[best_index] - baseline, 0.0) / amplitude, 2),
        "index": best_index,
        "source": CHLORITE_DIAGNOSTIC_SOURCE,
    }
    if diagnostic_peak["relative_intensity"] < CHLORITE_MIN_RELATIVE_INTENSITY:
        return peaks
    merged = list(peaks or []) + [diagnostic_peak]
    merged.sort(key=lambda item: item["relative_intensity"], reverse=True)
    return merged


def parse_webmineral_rows(text):
    """Extrai linhas d/I da tabela geral WebMineral quando o HTML permitir."""
    rows = []
    clean = html.unescape(re.sub(r"<[^>]+>", " ", text))
    pattern = re.compile(
        r"(?P<d1>\d+\.\d+)\(\s*(?P<t1>\d+\.\d+)\)\s+(?P<i1>[-\d]+)\s+"
        r"(?P<d2>\d+\.\d+)\(\s*(?P<t2>\d+\.\d+)\)\s+(?P<i2>[-\d]+)\s+"
        r"(?P<d3>\d+\.\d+)\(\s*(?P<t3>\d+\.\d+)\)\s+(?P<i3>[-\d]+)\s+"
        r"(?P<mineral>[A-Za-z][A-Za-z0-9 ._+'/()-]{1,80})\s+(?P<formula>[A-Z][^\n\r]{0,120})"
    )
    seen = set()
    for match in pattern.finditer(clean):
        mineral = " ".join(match.group("mineral").split()).strip()
        formula = " ".join(match.group("formula").split()).strip()
        key = (mineral.casefold(), formula)
        if key in seen:
            continue
        seen.add(key)
        lines = []
        for idx in ("1", "2", "3"):
            try:
                intensity = float(match.group(f"i{idx}"))
            except ValueError:
                intensity = 0.0
            lines.append({"d": float(match.group(f"d{idx}")), "i": intensity})
        rows.append(
            {
                "mineral": mineral,
                "formula": formula,
                "group": None,
                "source": WEBMINERAL_XRAY_URL,
                "lines": lines,
            }
        )
    return rows


def download_webmineral_reference(cache_path, pages=65, timeout=30):
    """Baixa a tabela do WebMineral quando a pagina permitir acesso direto."""
    rows_by_key = {}
    attempted = []
    page_urls = [WEBMINERAL_XRAY_URL]
    page_urls.extend(f"{WEBMINERAL_XRAY_URL}?st={page}" for page in range(1, pages + 1))

    for url in page_urls:
        attempted.append(url)
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Argiloteca-DRX/1.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                text = response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
        for row in parse_webmineral_rows(text):
            key = (row["mineral"].casefold(), row.get("formula") or "")
            rows_by_key[key] = row

    payload = {
        "source": WEBMINERAL_XRAY_URL,
        "downloaded_at": utc_now_iso(),
        "attempted_urls": attempted,
        "records": list(rows_by_key.values()),
        "notes": [
            "WebMineral lista os tres picos mais intensos por mineral.",
            "Use este cache como triagem; confirme interpretacoes por curadoria mineralogica.",
        ],
    }
    save_json(cache_path, payload)
    return payload


def load_reference(cache_path=None, update=False, pages=65):
    """Carrega referencia WebMineral local, atualiza opcionalmente ou usa fallback."""
    cache_path = Path(cache_path or DEFAULT_REFERENCE_CACHE)
    if update:
        if cache_path == PROJECT_WEBMINERAL_REFERENCE:
            try:
                from baixar_webmineral_argilominerais import collect
            except ImportError:  # pragma: no cover - usado quando importado como pacote em testes/scripts.
                from povoamento.drx.baixar_webmineral_argilominerais import collect

            payload = collect(
                vocab_path=ARGILOTECA_CLAY_VOCAB,
                output_dir=PROJECT_WEBMINERAL_COPY_DIR,
                reference_json=PROJECT_WEBMINERAL_REFERENCE,
                timeout=25,
            )
        else:
            payload = download_webmineral_reference(cache_path, pages=pages)
        if payload.get("records"):
            return normalize_reference_payload(payload, cache_path)

    payload = load_json(cache_path, default=None)
    if payload and payload.get("records"):
        return normalize_reference_payload(payload, cache_path)

    legacy_cache = DEFAULT_OUTPUT_DIR / "webmineral_xray_referencia.json"
    if cache_path != legacy_cache:
        payload = load_json(legacy_cache, default=None)
        if payload and payload.get("records"):
            return normalize_reference_payload(payload, legacy_cache)

    return {
        "source": "embedded",
        "downloaded_at": None,
        "records": EMBEDDED_REFERENCE,
        "notes": [
            "Referencia embutida usada porque o cache do WebMineral nao foi encontrado.",
            f"Para tentar atualizar: --atualizar-webmineral --cache-referencia {cache_path}",
        ],
    }


def normalize_reference_payload(payload, cache_path):
    """Normaliza cache local WebMineral e completa linhas conhecidas embutidas.

    O cache dos 81 termos pode conter entradas de vocabulário sem linhas d/I
    reconhecidas. Para nao perder a classificação já existente, esta função
    preserva as 81 entradas e injeta linhas embutidas quando o nome coincide.
    """
    embedded_by_name = {
        str(item.get("mineral") or "").casefold(): item
        for item in EMBEDDED_REFERENCE
    }
    records = []
    for row in payload.get("records") or []:
        item = dict(row)
        name = str(item.get("mineral") or item.get("title_en") or item.get("id") or "").strip()
        chemistry = item.get("chemistry") or item.get("chemical_composition") or {}
        if isinstance(chemistry, dict) and not item.get("formula"):
            item["formula"] = chemistry.get("chemical_formula") or chemistry.get("empirical_formula")
        if not item.get("group"):
            item["group"] = item.get("family") or item.get("category")
        item["classifier_feature_groups"] = reference_feature_groups(item)
        embedded = embedded_by_name.get(name.casefold())
        if embedded and not item.get("lines"):
            item["lines"] = embedded.get("lines") or []
            item.setdefault("formula", embedded.get("formula"))
            item.setdefault("group", embedded.get("group"))
            item["source"] = item.get("source") or embedded.get("source")
            item["line_source"] = "embedded WebMineral-compatible d/I reference merged into local vocabulary cache"
            item["classifier_feature_groups"] = reference_feature_groups(item)
        records.append(item)

    apply_vocabulary_expansions(records)

    existing = {str(item.get("mineral") or "").casefold() for item in records}
    for embedded in EMBEDDED_REFERENCE:
        if str(embedded.get("mineral") or "").casefold() not in existing:
            extra = dict(embedded)
            extra["status"] = "embedded_extra"
            records.append(extra)

    normalized = dict(payload)
    normalized["records"] = records
    normalized["source"] = payload.get("source") or "local_webmineral_cache"
    normalized["cache_path"] = str(cache_path)
    normalized["notes"] = (payload.get("notes") or []) + [
        "Cache local normalizado pelo classificador da Argiloteca.",
        "Entradas sem linhas d/I podem ser complementadas pela referencia embutida quando houver correspondencia nominal.",
    ]
    return normalized


def load_jsonl_rows(path):
    """Le um JSONL derivado, ignorando quando o arquivo ainda nao existe."""
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_vocabulary_expansions(path=ARGILOTECA_VOCABULARY_EXPANSIONS):
    """Carrega expansoes do vocabulario autorizadas para termos nao-especie."""
    expansions = {}
    for row in load_jsonl_rows(path):
        item_id = str(row.get("argilomineral_id") or row.get("id") or "").strip()
        if item_id:
            expansions[item_id] = row
    return expansions


def expansion_lines_for_classifier(expansion, limit=3):
    """Converte linhas representativas de expansao para o formato d/I."""
    lines = []
    for line in (expansion.get("representative_lines") or [])[:limit]:
        try:
            d_value = float(line.get("d_angstrom"))
            intensity = float(line.get("relative_intensity"))
        except (TypeError, ValueError):
            continue
        if d_value > 0 and intensity >= 0:
            lines.append({"d": d_value, "i": intensity})
    return lines


def apply_vocabulary_expansions(records, path=ARGILOTECA_VOCABULARY_EXPANSIONS):
    """Anexa expansoes locais ao cache de referencia sem remover entradas."""
    expansions = load_vocabulary_expansions(path)
    if not expansions:
        return
    by_id = {
        str(item.get("id") or item.get("argilomineral_id") or "").strip(): item
        for item in records
    }
    for item_id, expansion in expansions.items():
        item = by_id.get(item_id)
        if not item:
            item = {
                "id": item_id,
                "mineral": expansion.get("label_en") or item_id,
                "title_pt": expansion.get("label_pt") or "",
                "category": expansion.get("category") or "",
                "family": expansion.get("family") or "",
                "status": "derived_expansion",
            }
            records.append(item)
            by_id[item_id] = item

        lines = expansion_lines_for_classifier(expansion)
        if lines and not item.get("lines"):
            item["lines"] = lines
            item["line_source"] = "Argiloteca vocabulary expansion for group/material/mixed-layer term"
        item["vocabulary_expansion"] = {
            "expansion_kind": expansion.get("expansion_kind"),
            "component_terms": expansion.get("component_terms") or [],
            "member_ids": expansion.get("member_ids") or [],
            "members_count": expansion.get("members_count") or 0,
            "representative_lines_count": expansion.get("representative_lines_count") or len(lines),
            "mindat": expansion.get("mindat") or {},
            "source_layers": expansion.get("source_layers") or [],
            "validation_status": expansion.get("validation_status") or "auxiliary_not_confirmatory",
        }
        item.setdefault("category", expansion.get("category") or "")
        item.setdefault("family", expansion.get("family") or "")
        if not item.get("formula"):
            formula = (expansion.get("mindat") or {}).get("formula_ideal") or ""
            if formula and "inline" not in formula:
                item["formula"] = formula
        if not item.get("group"):
            item["group"] = item.get("family") or expansion.get("family")
        item["classifier_feature_groups"] = reference_feature_groups(item)


def reference_feature_groups(entry):
    """Resume quais camadas de evidencia existem para uma referencia."""
    groups = []
    chemistry = entry.get("chemistry") or entry.get("chemical_composition") or {}
    crystallography = entry.get("crystallography") or entry.get("webmineral_crystallography") or {}
    classification = entry.get("classification") or entry.get("webmineral_classification") or {}
    structure_reference = entry.get("structure_reference") or entry.get("webmineral_structure_reference") or {}
    auxiliary_qc = entry.get("auxiliary_qc") or entry.get("webmineral_auxiliary_qc") or {}
    descriptive = entry.get("descriptive_properties") or entry.get("webmineral_descriptive_properties") or {}
    vocabulary_expansion = entry.get("vocabulary_expansion") or {}
    if entry.get("lines"):
        groups.append("xray_lines")
    if isinstance(chemistry, dict) and chemistry.get("has_chemical_composition"):
        groups.append("chemical_composition")
    if isinstance(crystallography, dict) and crystallography.get("has_crystallography"):
        groups.append("crystallography")
    if isinstance(crystallography, dict) and (crystallography.get("cell_parameters") or {}).get("has_cell_parameters"):
        groups.append("unit_cell_parameters")
    if isinstance(classification, dict) and classification.get("has_structural_classification"):
        groups.append("dana_strunz_classification")
    if isinstance(structure_reference, dict) and structure_reference.get("has_structure_reference"):
        groups.append("jpowd_structure_reference")
    if isinstance(auxiliary_qc, dict) and auxiliary_qc.get("has_auxiliary_qc"):
        groups.append("auxiliary_qc")
    if isinstance(descriptive, dict) and descriptive.get("has_descriptive_properties"):
        groups.append("descriptive_mineralogy")
    if isinstance(vocabulary_expansion, dict) and vocabulary_expansion:
        groups.append("vocabulary_expansion")
    return groups


def compact_reference_features(entry):
    """Mantem os blocos WebMineral/vocabulario que o painel precisa exibir."""
    chemistry = entry.get("chemistry") or entry.get("chemical_composition") or {}
    crystallography = entry.get("crystallography") or entry.get("webmineral_crystallography") or {}
    classification = entry.get("classification") or entry.get("webmineral_classification") or {}
    structure_reference = entry.get("structure_reference") or entry.get("webmineral_structure_reference") or {}
    auxiliary_qc = entry.get("auxiliary_qc") or entry.get("webmineral_auxiliary_qc") or {}
    descriptive = entry.get("descriptive_properties") or entry.get("webmineral_descriptive_properties") or {}
    vocabulary_expansion = entry.get("vocabulary_expansion") or {}
    return {
        "chemistry": chemistry if isinstance(chemistry, dict) else {},
        "crystallography": crystallography if isinstance(crystallography, dict) else {},
        "classification": classification if isinstance(classification, dict) else {},
        "structure_reference": structure_reference if isinstance(structure_reference, dict) else {},
        "auxiliary_qc": auxiliary_qc if isinstance(auxiliary_qc, dict) else {},
        "descriptive_properties": descriptive if isinstance(descriptive, dict) else {},
        "vocabulary_expansion": vocabulary_expansion if isinstance(vocabulary_expansion, dict) else {},
    }


def strongest_peak_in_d_range(peaks, d_min, d_max):
    """Seleciona o pico mais intenso dentro de uma faixa diagnostica d."""
    candidates = [
        peak for peak in peaks or []
        if d_min <= float(peak.get("d") or 0) <= d_max
    ]
    candidates.sort(key=lambda item: float(item.get("relative_intensity") or 0), reverse=True)
    return candidates[0] if candidates else None


def is_chlorite_reference(entry):
    """Identifica entradas de referencia que representam cloritas."""
    text = " ".join(
        safe_text(value)
        for value in (
            entry.get("mineral"),
            entry.get("group"),
            entry.get("category"),
            entry.get("family"),
            entry.get("id"),
            entry.get("argilomineral_id"),
        )
    ).casefold()
    return "chlorite" in text or "clorit" in text


def preferred_chlorite_reference(reference):
    """Escolhe a melhor entrada de clorita para receber evidencia basal."""
    chlorites = [entry for entry in reference or [] if isinstance(entry, dict) and is_chlorite_reference(entry)]
    if not chlorites:
        chlorites = [entry for entry in EMBEDDED_REFERENCE if is_chlorite_reference(entry)]
    chlorites.sort(
        key=lambda entry: (
            0 if safe_text(entry.get("mineral")).casefold() == "chlorite" else 1,
            safe_text(entry.get("mineral")).casefold(),
        )
    )
    return chlorites[0] if chlorites else {
        "mineral": "Chlorite",
        "formula": "(Mg,Fe,Al)6(Si,Al)4O10(OH)8",
        "group": "chlorite_group",
        "source": CHLORITE_DIAGNOSTIC_SOURCE,
        "lines": [],
    }


def chlorite_basal_diagnostic_candidate(peaks, reference):
    """Cria candidato auxiliar quando ha pico basal de clorita em 13,58-14,87 A."""
    peak = strongest_peak_in_d_range(peaks, *CHLORITE_BASAL_D_RANGE)
    if not peak:
        return None
    reference_entry = preferred_chlorite_reference(reference)
    observed_d = float(peak.get("d") or 0)
    observed_two_theta = float(peak.get("two_theta") or 0)
    relative = float(peak.get("relative_intensity") or 0)
    if relative < CHLORITE_MIN_RELATIVE_INTENSITY:
        return None
    center_d = sum(CHLORITE_BASAL_D_RANGE) / 2.0
    diagnostic_match = {
        "reference_d": round(center_d, 5),
        "reference_two_theta": round(d_to_two_theta(center_d), 5),
        "reference_intensity": 100.0,
        "observed_d": round(observed_d, 5),
        "observed_two_theta": round(observed_two_theta, 5),
        "observed_relative_intensity": round(relative, 2),
        "delta_d": round(abs(observed_d - center_d), 5),
        "delta_two_theta": round(abs(observed_two_theta - d_to_two_theta(center_d)), 5),
        "closeness": round(max(0.0, 1.0 - abs(observed_d - center_d) / 0.3), 4),
        "diagnostic_range_d": [CHLORITE_BASAL_D_RANGE[0], CHLORITE_BASAL_D_RANGE[1]],
        "source": CHLORITE_DIAGNOSTIC_SOURCE,
    }
    score = round(min(0.82, max(0.58, 0.58 + (0.35 * min(relative, 100.0) / 100.0))), 4)
    return {
        "argilomineral_id": reference_entry.get("id") or reference_entry.get("argilomineral_id") or "chlorite",
        "mineral": reference_entry.get("mineral") or "Chlorite",
        "formula": reference_entry.get("formula") or "(Mg,Fe,Al)6(Si,Al)4O10(OH)8",
        "group": reference_entry.get("group") or "chlorite_group",
        "category": reference_entry.get("category"),
        "family": reference_entry.get("family"),
        "source": CHLORITE_DIAGNOSTIC_SOURCE,
        "classifier_feature_groups": sorted(set((reference_entry.get("classifier_feature_groups") or reference_feature_groups(reference_entry)) + ["diagnostic_basal_chlorite_13_7_14_6a"])),
        "webmineral_features": compact_reference_features(reference_entry),
        "score": score,
        "confidence": "media" if relative >= 15 else "baixa",
        "matched_lines": 1,
        "reference_lines": max(len(reference_entry.get("lines") or []), 1),
        "coverage": round(1 / max(len(reference_entry.get("lines") or []), 1), 4),
        "matches": [diagnostic_match],
        "diagnostic_note": "Pico basal de clorita observado entre 13,7 e 14,6 Å; usar N/G/C e harmônicos para curadoria.",
    }


def merge_diagnostic_chlorite(matches, peaks, reference, top):
    """Mescla a regra da clorita basal aos matches existentes sem duplicar demais."""
    diagnostic = chlorite_basal_diagnostic_candidate(peaks, reference)
    if not diagnostic:
        return matches[:top]
    merged = []
    applied = False
    generic_applied = False
    for match in matches:
        if is_chlorite_reference(match):
            updated = dict(match)
            updated["score"] = max(float(updated.get("score") or 0), diagnostic["score"])
            updated["confidence"] = "media" if updated["score"] >= 0.45 else updated.get("confidence") or "baixa"
            updated["source"] = updated.get("source") or diagnostic["source"]
            updated["classifier_feature_groups"] = sorted(set((updated.get("classifier_feature_groups") or []) + ["diagnostic_basal_chlorite_13_7_14_6a"]))
            updated["matches"] = (updated.get("matches") or []) + [
                row for row in diagnostic["matches"]
                if row not in (updated.get("matches") or [])
            ]
            updated["matched_lines"] = max(int(updated.get("matched_lines") or 0), 1)
            updated["diagnostic_note"] = diagnostic["diagnostic_note"]
            merged.append(updated)
            applied = True
            if safe_text(updated.get("mineral")).casefold() == "chlorite":
                generic_applied = True
        else:
            merged.append(match)
    if not applied or not generic_applied:
        merged.append(diagnostic)
    merged.sort(key=lambda item: (float(item.get("score") or 0), int(item.get("matched_lines") or 0)), reverse=True)
    return merged[:top]


def match_reference(peaks, reference, tolerance_d=0.08, tolerance_two_theta=0.35, top=8):
    """Compara picos observados contra linhas d/I de referencia."""
    matches = []
    if not peaks:
        return matches

    peak_by_strength = sorted(peaks, key=lambda item: item["relative_intensity"], reverse=True)
    for entry in reference:
        line_matches = []
        weighted_score = 0.0
        total_weight = 0.0
        for line in entry.get("lines") or []:
            d_ref = float(line.get("d") or 0)
            i_ref = max(float(line.get("i") or 0), 1.0)
            two_theta_ref = d_to_two_theta(d_ref)
            if not d_ref or not two_theta_ref:
                continue
            total_weight += i_ref
            best = None
            for peak in peak_by_strength:
                delta_d = abs(float(peak["d"]) - d_ref)
                delta_two_theta = abs(float(peak["two_theta"]) - two_theta_ref)
                if delta_d <= tolerance_d or delta_two_theta <= tolerance_two_theta:
                    closeness_d = max(0.0, 1.0 - (delta_d / max(tolerance_d, 0.0001)))
                    closeness_t = max(0.0, 1.0 - (delta_two_theta / max(tolerance_two_theta, 0.0001)))
                    closeness = max(closeness_d, closeness_t)
                    candidate = {
                        "reference_d": round(d_ref, 5),
                        "reference_two_theta": round(two_theta_ref, 5),
                        "reference_intensity": i_ref,
                        "observed_d": peak["d"],
                        "observed_two_theta": peak["two_theta"],
                        "observed_relative_intensity": peak["relative_intensity"],
                        "delta_d": round(delta_d, 5),
                        "delta_two_theta": round(delta_two_theta, 5),
                        "closeness": round(closeness, 4),
                    }
                    if not best or candidate["closeness"] > best["closeness"]:
                        best = candidate
            if best:
                line_matches.append(best)
                weighted_score += i_ref * best["closeness"]

        if not total_weight:
            continue
        coverage = len(line_matches) / max(len(entry.get("lines") or []), 1)
        score = (weighted_score / total_weight) * (0.55 + 0.45 * coverage)
        if line_matches:
            matches.append(
                {
                    "argilomineral_id": entry.get("id") or entry.get("argilomineral_id"),
                    "mineral": entry.get("mineral"),
                    "formula": entry.get("formula"),
                    "group": entry.get("group"),
                    "category": entry.get("category"),
                    "family": entry.get("family"),
                    "source": entry.get("source"),
                    "classifier_feature_groups": entry.get("classifier_feature_groups") or reference_feature_groups(entry),
                    "webmineral_features": compact_reference_features(entry),
                    "score": round(score, 4),
                    "confidence": confidence_label(score, coverage, len(line_matches)),
                    "matched_lines": len(line_matches),
                    "reference_lines": len(entry.get("lines") or []),
                    "coverage": round(coverage, 4),
                    "matches": line_matches,
                }
            )

    matches.sort(key=lambda item: (item["score"], item["matched_lines"]), reverse=True)
    return merge_diagnostic_chlorite(matches, peaks, reference, top)


def confidence_label(score, coverage, matched_lines):
    if score >= 0.72 and coverage >= 0.66 and matched_lines >= 2:
        return "alta"
    if score >= 0.45 and matched_lines >= 2:
        return "media"
    return "baixa"


def classify_raw(path, reference, args):
    """Classifica um RAW e devolve picos, candidatos e metadados de alinhamento."""
    alignment = getattr(args, "axis_alignment_plan", {}).get(str(path), {})
    base = {
        "filename": path.name,
        "path": str(path),
        "sample_code": path.stem,
        "sample_base": alignment.get("sample_base") or infer_diffractogram_sample_base(path.stem, path.name, str(path)),
        "treatment": alignment.get("treatment") or infer_diffractogram_treatment(path.stem, path.name, str(path))["type"],
        "classified_at": utc_now_iso(),
    }
    try:
        parsed = parse_raw_file(path)
    except RawParseError as exc:
        return {
            **base,
            "status": "erro",
            "error_message": str(exc),
            "metadata": {},
            "peaks": [],
            "candidates": [],
        }

    parsed = apply_two_theta_axis_alignment(
        parsed,
        filename=path.name,
        path=str(path),
        sample_code=path.stem,
        sample_base=alignment.get("sample_base"),
        treatment=alignment.get("treatment"),
        target_start=alignment.get("target_start"),
        absolute_offset=alignment.get("absolute_offset"),
        manual_corrections=getattr(args, "axis_corrections", {}),
        min_offset=args.limiar_autoalinhamento_eixo,
    )
    peaks = extract_peaks(
        parsed.two_theta,
        parsed.intensity,
        max_peaks=args.max_peaks,
        smooth_window=args.smooth_window,
        min_distance_deg=args.min_distance,
        min_prominence_ratio=args.min_prominence,
    )
    peaks = ensure_chlorite_basal_peak(
        peaks,
        parsed.two_theta,
        parsed.intensity,
        smooth_window=args.smooth_window,
        min_prominence_ratio=args.min_prominence,
    )
    return {
        **base,
        "status": "ok",
        "error_message": None,
        "metadata": parsed.metadata,
        "peaks": peaks,
        "candidates": match_reference(
            peaks,
            reference,
            tolerance_d=args.tolerance_d,
            tolerance_two_theta=args.tolerance_two_theta,
            top=args.top_candidates,
        ),
    }


def collect_raw_files(input_path):
    """Lista arquivos .raw/.RAW a partir de arquivo unico ou pasta."""
    input_path = Path(input_path)
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() == ".raw" else []
    return sorted(path for path in input_path.rglob("*") if path.is_file() and path.suffix.lower() == ".raw")


def raw_axis_context(path):
    """Inferir preparo N/G/C e base da amostra a partir do nome do RAW."""
    treatment = infer_diffractogram_treatment(path.stem, path.name, str(path))
    return {
        "treatment": treatment["type"],
        "sample_base": infer_diffractogram_sample_base(path.stem, path.name, str(path)),
    }


def build_axis_alignment_plan(files, disabled=False):
    """Planeja alinhamento de eixo por Natural pareada ou quartzo 101."""
    contexts = {str(path): raw_axis_context(path) for path in files}
    natural_starts = {}
    raw_starts = {}
    quartz_offsets = {}
    if not disabled:
        for path in files:
            context = contexts[str(path)]
            try:
                parsed = parse_raw_file(path)
            except RawParseError:
                continue
            raw_starts[str(path)] = parsed.metadata.get("two_theta_start")
            quartz_offset = calculate_quartz_axis_offset(parsed.two_theta, parsed.intensity)
            if quartz_offset:
                quartz_offsets[str(path)] = quartz_offset
            if context["treatment"] != "natural" or not context["sample_base"]:
                continue
            offset_value = float((quartz_offset or {}).get("offset") or 0.0)
            corrected_start = (parsed.metadata.get("two_theta_start") or 0.0) + offset_value
            natural_starts.setdefault(context["sample_base"].casefold(), corrected_start)
    plan = {}
    for path in files:
        context = contexts[str(path)]
        target_start = natural_starts.get(context["sample_base"].casefold()) if context["sample_base"] else None
        absolute_offset = None
        if not disabled and (context["treatment"] == "natural" or target_start is None):
            absolute_offset = quartz_offsets.get(str(path))
        plan[str(path)] = {
            **context,
            "target_start": target_start,
            "absolute_offset": absolute_offset,
            "raw_start": raw_starts.get(str(path)),
        }
    return plan


def write_csv(path, rows):
    """Exporta um resumo tabular para revisao rapida fora do painel."""
    fields = [
        "filename",
        "sample_code",
        "status",
        "top_mineral",
        "top_group",
        "top_score",
        "top_confidence",
        "matched_lines",
        "peaks_two_theta",
        "peaks_d",
        "error_message",
        "path",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            top = (row.get("candidates") or [{}])[0]
            writer.writerow(
                {
                    "filename": row.get("filename"),
                    "sample_code": row.get("sample_code"),
                    "status": row.get("status"),
                    "top_mineral": top.get("mineral"),
                    "top_group": top.get("group"),
                    "top_score": top.get("score"),
                    "top_confidence": top.get("confidence"),
                    "matched_lines": top.get("matched_lines"),
                    "peaks_two_theta": ";".join(str(peak.get("two_theta")) for peak in row.get("peaks") or []),
                    "peaks_d": ";".join(str(peak.get("d")) for peak in row.get("peaks") or []),
                    "error_message": row.get("error_message"),
                    "path": row.get("path"),
                }
            )


def build_summary(rows, reference_payload):
    """Monta resumo JSON da classificacao para manifestos e publicacao."""
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    errors = [row for row in rows if row.get("status") != "ok"]
    minerals = {}
    for row in ok_rows:
        for index, candidate in enumerate(row.get("candidates") or []):
            if index > 2:
                break
            name = candidate.get("mineral")
            if not name:
                continue
            bucket = minerals.setdefault(
                name,
                {
                    "mineral": name,
                    "group": candidate.get("group"),
                    "count_top3": 0,
                    "best_score": 0,
                    "samples": [],
                },
            )
            bucket["count_top3"] += 1
            bucket["best_score"] = max(bucket["best_score"], candidate.get("score") or 0)
            bucket["samples"].append(row.get("sample_code"))

    return {
        "success": True,
        "generated_at": utc_now_iso(),
        "reference_source": reference_payload.get("source"),
        "reference_records": len(reference_payload.get("records") or []),
        "files_total": len(rows),
        "files_ok": len(ok_rows),
        "files_error": len(errors),
        "candidate_minerals_top3": sorted(
            minerals.values(),
            key=lambda item: (item["count_top3"], item["best_score"]),
            reverse=True,
        ),
        "errors": [
            {"filename": row.get("filename"), "error_message": row.get("error_message")}
            for row in errors
        ],
        "notes": reference_payload.get("notes") or [],
    }


def parse_args():
    """Define parametros CLI do classificador derivado."""
    parser = argparse.ArgumentParser(
        description="Classifica candidatos mineralogicos em arquivos .RAW de DRX."
    )
    parser.add_argument("--input", default=str(DEFAULT_RAW_DIR), help="Arquivo .raw ou pasta com .raw/.RAW.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Pasta de saida JSON/CSV.")
    parser.add_argument("--cache-referencia", default=str(DEFAULT_REFERENCE_CACHE), help="Cache local WebMineral em JSON.")
    parser.add_argument("--atualizar-webmineral", action="store_true", help="Tenta baixar/atualizar a referencia do WebMineral.")
    parser.add_argument("--paginas-webmineral", type=int, default=65, help="Numero maximo de paginas WebMineral a tentar.")
    parser.add_argument("--max-files", type=int, default=0, help="Limita o numero de arquivos processados; 0 processa todos.")
    parser.add_argument("--max-peaks", type=int, default=15, help="Quantidade maxima de picos observados por RAW.")
    parser.add_argument("--top-candidates", type=int, default=8, help="Quantidade de candidatos por arquivo.")
    parser.add_argument("--smooth-window", type=int, default=5, help="Janela de suavizacao para detectar picos.")
    parser.add_argument("--min-distance", type=float, default=0.18, help="Distancia minima entre picos em graus 2theta.")
    parser.add_argument("--min-prominence", type=float, default=0.01, help="Prominencia minima relativa para aceitar pico.")
    parser.add_argument("--tolerance-d", type=float, default=0.08, help="Tolerancia de casamento em Angstrom.")
    parser.add_argument("--tolerance-two-theta", type=float, default=0.35, help="Tolerancia de casamento em graus 2theta.")
    parser.add_argument("--correcoes-eixo-json", default=str(DRX_AXIS_CORRECTIONS_PATH), help="JSON opcional com offsets manuais de 2theta por arquivo/caminho/amostra.")
    parser.add_argument("--desativar-autoalinhamento-eixo", action="store_true", help="Nao ancora G/C pelo inicio da curva Natural do mesmo grupo.")
    parser.add_argument("--limiar-autoalinhamento-eixo", type=float, default=DRX_AXIS_ALIGNMENT_MIN_OFFSET, help="Offset minimo em graus 2theta para aplicar autoalinhamento N/G/C.")
    return parser.parse_args()


def main():
    """Executa classificacao derivada e grava JSON/CSV/resumo."""
    args = parse_args()
    output_dir = Path(args.output_dir)
    reference_payload = load_reference(
        cache_path=args.cache_referencia,
        update=args.atualizar_webmineral,
        pages=args.paginas_webmineral,
    )
    reference = reference_payload.get("records") or EMBEDDED_REFERENCE
    files = collect_raw_files(args.input)
    if args.max_files and args.max_files > 0:
        files = files[: args.max_files]

    args.axis_corrections = load_two_theta_axis_corrections(args.correcoes_eixo_json)
    args.axis_alignment_plan = build_axis_alignment_plan(files, disabled=args.desativar_autoalinhamento_eixo)
    rows = [classify_raw(path, reference, args) for path in files]
    payload = {
        "summary": build_summary(rows, reference_payload),
        "parameters": {
            "input": str(args.input),
            "max_peaks": args.max_peaks,
            "top_candidates": args.top_candidates,
            "tolerance_d": args.tolerance_d,
            "tolerance_two_theta": args.tolerance_two_theta,
            "smooth_window": args.smooth_window,
            "min_distance": args.min_distance,
            "min_prominence": args.min_prominence,
            "axis_alignment": {
                "enabled": not args.desativar_autoalinhamento_eixo,
                "manual_corrections_path": str(args.correcoes_eixo_json),
                "manual_corrections_count": len(args.axis_corrections),
                "min_offset": args.limiar_autoalinhamento_eixo,
                "quartz_101_absolute_anchor": not args.desativar_autoalinhamento_eixo,
                "diagnostic_d_ranges": {
                    "RANGE_ILITA_10A": list(RANGE_ILITA_10A),
                    "RANGE_CAULINITA_7A": list(RANGE_CAULINITA_7A),
                    "RANGE_ESMECTITA_N": list(RANGE_ESMECTITA_N),
                    "RANGE_ESMECTITA_G": list(RANGE_ESMECTITA_G),
                    "RANGE_ESMECTITA_C": list(RANGE_ESMECTITA_C),
                    "RANGE_CLORITA_14A": list(RANGE_CLORITA_14A),
                    "RANGE_QUARTZO_101": list(RANGE_QUARTZO_101),
                    "RANGE_QUARTZO_100": list(RANGE_QUARTZO_100),
                },
            },
        },
        "results": rows,
    }

    json_path = output_dir / "classificacao_mineralogica_raw.json"
    csv_path = output_dir / "classificacao_mineralogica_raw.csv"
    summary_path = output_dir / "classificacao_mineralogica_resumo.json"
    save_json(json_path, payload)
    save_json(summary_path, payload["summary"])
    write_csv(csv_path, rows)

    print(
        json.dumps(
            {
                "success": True,
                "files_total": len(rows),
                "files_ok": payload["summary"]["files_ok"],
                "files_error": payload["summary"]["files_error"],
                "reference_source": payload["summary"]["reference_source"],
                "reference_records": payload["summary"]["reference_records"],
                "json": str(json_path),
                "csv": str(csv_path),
                "summary": str(summary_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
