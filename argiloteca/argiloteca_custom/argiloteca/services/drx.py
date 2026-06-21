"""
Projeto: Painel DRX Argiloteca

Descrição:
DRX import and comparison helpers for Argiloteca. The RAW extension is vendor-specific. This MVP supports the small Bruker/EVA layouts observed in the local corpus and simple two-column text curves (.csv/.txt/.xy/.dat), rejecting unknown layouts with an explicit import status. As rotinas tambem alinham eixo 2theta para comparacao N/G/C, anexam resultados avancados ALS/FWHM e enriquecem snapshots sem alterar os RAWs ou JSONs derivados usados pelo povoamento.

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
import hashlib
import math
import os
import re
import shutil
import struct
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from .geoquimica import (
    DEFAULT_SIZE,
    extract_mineral_entries,
    extract_primary_sample,
    record_custom_fields,
    record_title,
    safe_text,
    search_records,
)
from .raw_snapshot_links import raw_snapshot_link_for_item
from .drx_science_engine import detect_peaks_scipy, fit_peaks_lmfit
from argiloteca.drx_core.curves import (
    CurveParseError,
    parse_curve_bytes as core_parse_curve_bytes,
    parse_raw_bytes as core_parse_raw_bytes,
    parse_text_curve_bytes as core_parse_text_curve_bytes,
)


DEFAULT_INSTANCE_PATH = Path(
    os.environ.get(
        "INVENIO_INSTANCE_PATH",
        Path(__file__).resolve().parents[3] / "var" / "instance",
    )
)
DEFAULT_WORKSPACE_PATH = Path(__file__).resolve().parents[4]
DEFAULT_WORKSPACE_INSTANCE_PATH = DEFAULT_WORKSPACE_PATH / "var" / "instance"
DRX_INDEX_PATH = DEFAULT_INSTANCE_PATH / "argiloteca_drx_index.json"
DRX_DATA_DIR = DEFAULT_INSTANCE_PATH / "argiloteca_drx_data"
DRX_RAW_DIR = DRX_DATA_DIR / "raw"
ANALYTICAL_PACKAGES_DIR = Path(
    os.environ.get("ARGILOTECA_ANALYTICAL_PACKAGES_DIR")
    or Path(os.environ.get("INVENIO_INSTANCE_PATH", DEFAULT_WORKSPACE_INSTANCE_PATH)) / "argiloteca_analytical_packages"
)
STATIC_ANALYTICAL_PACKAGES_DIR = Path(__file__).resolve().parents[1] / "static" / "data" / "analytical_packages"
PACKAGE_ALIASES_PATH = Path(
    os.environ.get("ARGILOTECA_ANALYTICAL_PACKAGE_ALIASES", ANALYTICAL_PACKAGES_DIR / "aliases.json")
)
# Snapshots derivados pelo pipeline de povoamento. Eles sao lidos como fonte
# externa de evidencia e nao sao regravados por este modulo de servico.
DRX_RAW_SNAPSHOT_PATH = Path(
    os.environ.get(
        "ARGILOTECA_DRX_RAW_SNAPSHOT_PATH",
        DEFAULT_WORKSPACE_PATH
        / "povoamento"
        / "visualizacao-drx"
        / "saida_argiloteca_drx"
        / "classificacao_mineralogica_raw.json",
    )
)
DRX_TREATMENT_SNAPSHOT_PATH = Path(
    os.environ.get(
        "ARGILOTECA_DRX_TREATMENT_SNAPSHOT_PATH",
        DEFAULT_WORKSPACE_PATH
        / "povoamento"
        / "visualizacao-drx"
        / "saida_argiloteca_drx"
        / "classificacao_tratamento_raw.json",
    )
)
DRX_ADVANCED_MANIFEST_PATH = Path(
    os.environ.get(
        "ARGILOTECA_DRX_ADVANCED_MANIFEST_PATH",
        DEFAULT_WORKSPACE_PATH
        / "povoamento"
        / "visualizacao-drx"
        / "saida_argiloteca_drx"
        / "processamento_avancado_manifest.jsonl",
    )
)
DRX_ADVANCED_RESULTS_DIR = Path(
    os.environ.get(
        "ARGILOTECA_DRX_ADVANCED_RESULTS_DIR",
        DEFAULT_WORKSPACE_PATH
        / "povoamento"
        / "visualizacao-drx"
        / "saida_argiloteca_drx"
        / "curvas_avancadas",
    )
)
DRX_AXIS_CORRECTIONS_PATH = Path(
    os.environ.get(
        "ARGILOTECA_DRX_AXIS_CORRECTIONS_PATH",
        DEFAULT_WORKSPACE_PATH
        / "povoamento"
        / "visualizacao-drx"
        / "saida_argiloteca_drx"
        / "correcoes_eixo_2theta.json",
    )
)
try:
    DRX_AXIS_ALIGNMENT_MIN_OFFSET = float(os.environ.get("ARGILOTECA_DRX_AXIS_ALIGNMENT_MIN_OFFSET", "0.05"))
except ValueError:
    DRX_AXIS_ALIGNMENT_MIN_OFFSET = 0.05
DRX_MINERAL_CLASSIFICATION_PATH = Path(
    os.environ.get(
        "ARGILOTECA_DRX_MINERAL_CLASSIFICATION_PATH",
        DEFAULT_WORKSPACE_PATH
        / "povoamento"
        / "visualizacao-drx"
        / "saida_argiloteca_drx"
        / "classificacao_mineralogica_raw.json",
    )
)
DRX_NGC_GROUP_CLASSIFICATION_PATH = Path(
    os.environ.get(
        "ARGILOTECA_DRX_NGC_GROUP_CLASSIFICATION_PATH",
        DRX_MINERAL_CLASSIFICATION_PATH.parent / "classificacao_mineralogica_ngc_groups.json",
    )
)
DRX_NGC_GROUP_CLASSIFICATION_FALLBACK_PATH = (
    DEFAULT_WORKSPACE_PATH / "data" / "drx" / "saida_argiloteca_drx" / "classificacao_mineralogica_ngc_groups.json"
)
DRX_MANUAL_MINERAL_OVERRIDES_PATH = Path(
    os.environ.get(
        "ARGILOTECA_DRX_MANUAL_MINERAL_OVERRIDES_PATH",
        DRX_MINERAL_CLASSIFICATION_PATH.parent / "manual_mineral_overrides.json",
    )
)
SUPPORTED_LOCAL_IMPORT_ROOTS = (
    Path("/Users/visualizacao-drx/raw"),
    DEFAULT_WORKSPACE_PATH / "povoamento" / "visualizacao-drx" / "raw",
    DEFAULT_WORKSPACE_PATH / "povoamento" / "visualizacao-drx" / "raw-classificados",
    DEFAULT_WORKSPACE_PATH / "data" / "drx" / "raw",
    DEFAULT_WORKSPACE_PATH / "data" / "drx" / "raw-classificados",
    DRX_RAW_DIR,
)
MIN_POINTS = 10
MAX_RENDER_POINTS = 3000
SUPPORTED_TEXT_CURVE_EXTENSIONS = {".csv", ".txt", ".xy", ".dat"}
SUPPORTED_UPLOAD_CURVE_EXTENSIONS = {".raw", *SUPPORTED_TEXT_CURVE_EXTENSIONS}
RECORD_LEVEL_KEY = "__record__"
MAX_MINERAL_CANDIDATES_PER_DIFRACTOGRAM = 6
SNAPSHOT_ID_PREFIX = "snapshot:"
ADVANCED_ALS_SCHEMA = "argiloteca.drx.advanced_als.v1"
# Parametros fisicos usados em d-spacing e Scherrer; manter explicitos ajuda a
# rastrear que o painel assume radiacao Cu Kalpha nos calculos auxiliares.
ADVANCED_ALS_WAVELENGTH_CU = 1.5406
ADVANCED_ALS_SCHERRER_K = 0.9
# Faixas diagnosticas em d-spacing (Angstrom) usadas pelo painel para orientar
# argilominerais e calibracao por quartzo, nao para substituir curadoria.
DRX_DIAGNOSTIC_D_RANGES = {
    "illite10A": (9.7, 10.4),
    "kaolinite7A": (6.9, 7.8),
    "smectiteNatural": (13.0, 16.5),
    "smectiteGlycolated": (16.6, 18.6),
    "smectiteCalcined": (9.4, 10.4),
    "chlorite14A": (13.7, 14.6),
    "quartz101": (3.24, 3.44),
    "quartz100": (4.23, 4.35),
}
TARGETED_BASAL_PEAK_RANGES = (
    {"range_id": "smectite_n_12_15a", "mineral": "Esmectita", "label": "Esmectita N 12-15 A", "d_min": 12.0, "d_max": 15.5},
    {"range_id": "smectite_g_17a", "mineral": "Esmectita", "label": "Esmectita G ~17 A", "d_min": 16.6, "d_max": 18.6},
    {"range_id": "smectite_c_10a", "mineral": "Esmectita", "label": "Esmectita C ~10 A", "d_min": 9.4, "d_max": 10.4},
    {"range_id": "illite_10a", "mineral": "Ilita", "label": "Ilita/Mica 10 A", "d_min": 9.7, "d_max": 10.4},
    {"range_id": "illite_5a", "mineral": "Ilita", "label": "Ilita/Mica 5 A", "d_min": 4.85, "d_max": 5.15},
    {"range_id": "illite_3_33a", "mineral": "Ilita", "label": "Ilita/Mica 3.33 A", "d_min": 3.26, "d_max": 3.40},
    {"range_id": "kaolinite_7a", "mineral": "Caulinita", "label": "Caulinita 7 A", "d_min": 6.9, "d_max": 7.8},
    {"range_id": "kaolinite_3_57a", "mineral": "Caulinita", "label": "Caulinita 3.57 A", "d_min": 3.52, "d_max": 3.62},
    {"range_id": "chlorite_14a", "mineral": "Clorita", "label": "Clorita 14 A", "d_min": 13.7, "d_max": 15.3},
    {"range_id": "chlorite_7a", "mineral": "Clorita", "label": "Clorita 7 A", "d_min": 6.9, "d_max": 7.4},
    {"range_id": "chlorite_4_72a", "mineral": "Clorita", "label": "Clorita 4.72 A", "d_min": 4.60, "d_max": 4.85},
    {"range_id": "chlorite_3_53a", "mineral": "Clorita", "label": "Clorita 3.53 A", "d_min": 3.45, "d_max": 3.65},
    {"range_id": "quartz_101", "mineral": "Quartzo", "label": "Quartzo 101", "d_min": 3.24, "d_max": 3.44},
    {"range_id": "quartz_100", "mineral": "Quartzo", "label": "Quartzo 100", "d_min": 4.23, "d_max": 4.35},
)
DRX_QUARTZ_CALIBRATION_SEARCH_D_RANGE = (3.24, 3.44)
DRX_QUARTZ_CALIBRATION_TARGET_D = 3.34
DRX_QUARTZ_CALIBRATION_MIN_RELATIVE_INTENSITY = 2.0
DRX_QUARTZ_CALIBRATION_MIN_OFFSET = 0.02
ADVANCED_FIT_RESULT_KEYS = (
    "peak_id",
    "center_2theta",
    "center_2theta_stderr",
    "center_d_angstrom",
    "amplitude",
    "height",
    "area",
    "fwhm",
    "sigma",
    "gamma",
    "fraction",
    "baseline_local",
    "redchi",
    "aic",
    "bic",
    "r_squared",
    "model_name",
    "profile_model",
    "peak_location_method",
    "uncertainty_source",
    "fwhm_source",
    "fit_success",
    "fit_quality",
    "fit_message",
)


class RawParseError(ValueError):
    """Raised when a RAW file cannot be converted into a 1D diffractogram."""


@dataclass
class DiffractogramData:
    """In-memory 1D diffractogram parsed from RAW bytes.

    `two_theta` and `intensity` have the same length; `metadata` carries the
    parser format, axis limits, step and any later axis-alignment provenance.
    """

    two_theta: list[float]
    intensity: list[float]
    metadata: dict


def utc_now_iso():
    """Return a compact UTC timestamp for manifests and import records."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_float32_series(content, offset, count):
    """Read one little-endian float32 intensity vector from a RAW layout."""
    required = offset + (count * 4)
    if count < MIN_POINTS or required > len(content):
        raise RawParseError("Arquivo .raw incompleto ou sem pontos suficientes.")
    values = struct.unpack("<" + ("f" * count), content[offset:required])
    if not all(math.isfinite(value) for value in values):
        raise RawParseError("Intensidades contem valores nao finitos.")
    return [round(float(value), 6) for value in values]


def _build_axis(start, step, count):
    """Build the 2theta axis from header start/step metadata."""
    if not math.isfinite(start) or not math.isfinite(step) or step <= 0:
        raise RawParseError("Metadados de 2theta invalidos no cabecalho .raw.")
    return [round(float(start + (index * step)), 6) for index in range(count)]


def parse_raw_bytes(content):
    """Parse supported RAW byte layouts into 2theta/intensity arrays."""
    try:
        parsed = core_parse_raw_bytes(content)
    except CurveParseError as exc:
        raise RawParseError(str(exc)) from exc
    return DiffractogramData(parsed.two_theta, parsed.intensity, parsed.metadata)


def _parse_text_curve_number(value):
    """Parse one numeric cell from CSV/TXT/XY text without locale side effects."""
    text = safe_text(value).strip()
    if not text:
        return None
    text = text.replace("\ufeff", "").strip().strip('"').strip("'")
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    text = re.sub(r"[^0-9eE+\-.]", "", text)
    if not text or text in {"+", "-", ".", "+.", "-."}:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _text_curve_columns(line):
    """Return candidate numeric tokens from one delimited or whitespace row."""
    text = safe_text(line).strip()
    if not text or text.startswith(("#", "//", ";")):
        return []
    tokens = re.split(r"[;\t, ]+", text)
    return [_parse_text_curve_number(token) for token in tokens if safe_text(token).strip()]


def parse_text_curve_bytes(content, filename=None):
    """Parse a simple two-column 2theta/intensity text curve."""
    try:
        parsed = core_parse_text_curve_bytes(content, filename=filename)
    except CurveParseError as exc:
        raise RawParseError(str(exc)) from exc
    return DiffractogramData(parsed.two_theta, parsed.intensity, parsed.metadata)


def parse_diffractogram_bytes(content, filename=None):
    """Parse an uploaded diffractogram by extension, with RAW/text fallbacks."""
    try:
        parsed = core_parse_curve_bytes(content, filename=filename)
    except CurveParseError as exc:
        raise RawParseError(str(exc)) from exc
    return DiffractogramData(parsed.two_theta, parsed.intensity, parsed.metadata)


def parse_raw_file(path):
    """Parse a RAW file path into a diffractogram object."""
    path = Path(path)
    return parse_raw_bytes(path.read_bytes())


def infer_diffractogram_sample_base(*values):
    """Infer the N/G/C sample base by removing treatment suffixes from names."""
    raw = ""
    for value in values:
        text = safe_text(value)
        if not text:
            continue
        name = Path(text).name
        raw = re.sub(r"\.[A-Za-z0-9]+$", "", name).strip() or text.strip()
        if raw:
            break
    if not raw:
        return ""
    base = re.sub(
        r"[\s._-]*\(?\b(N|G|C|NAT|NATURAL|GLY|GLICOL|GLICOLADA|CAL|CALC|CALCINADA)\b\)?$",
        "",
        raw,
        flags=re.IGNORECASE,
    )
    base = re.sub(r"\s+", " ", base).strip()
    return base or raw


@lru_cache(maxsize=8)
def load_two_theta_axis_corrections(path=None):
    """Load optional manual 2theta offsets keyed by filename/path/sample code."""
    corrections_path = Path(path or DRX_AXIS_CORRECTIONS_PATH)
    try:
        with open(corrections_path, "r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}
    if isinstance(payload, dict) and isinstance(payload.get("corrections"), dict):
        payload = payload["corrections"]
    if not isinstance(payload, dict):
        return {}
    return {
        safe_text(key).casefold(): value
        for key, value in payload.items()
        if safe_text(key)
    }


def _axis_correction_keys(*values):
    """Generate lookup keys for manual 2theta corrections."""
    keys = []
    for value in values:
        text = safe_text(value)
        if not text:
            continue
        path = Path(text)
        for candidate in (text, path.name, path.stem):
            key = safe_text(candidate).casefold()
            if key and key not in keys:
                keys.append(key)
    return keys


def _axis_offset_from_corrections(corrections, *values):
    """Return a manual offset when any filename/path/sample key matches."""
    corrections = corrections or {}
    for key in _axis_correction_keys(*values):
        correction = corrections.get(key)
        if isinstance(correction, dict):
            correction = (
                correction.get("offset_2theta")
                or correction.get("two_theta_offset")
                or correction.get("offset")
            )
        try:
            offset = float(correction)
        except (TypeError, ValueError):
            continue
        if math.isfinite(offset):
            return offset
    return None


def apply_two_theta_axis_alignment(
    parsed,
    *,
    filename=None,
    path=None,
    sample_code=None,
    sample_base=None,
    treatment=None,
    target_start=None,
    absolute_offset=None,
    manual_corrections=None,
    min_offset=DRX_AXIS_ALIGNMENT_MIN_OFFSET,
    absolute_min_offset=DRX_QUARTZ_CALIBRATION_MIN_OFFSET,
):
    """Shift parsed 2theta values by manual, quartz or Natural-anchor offset.

    A ordem de preferencia e: correcao manual, deslocamento absoluto por quartzo
    101 e, para G/C, ancoragem no inicio do eixo da amostra Natural equivalente.
    """
    if not parsed or not parsed.two_theta:
        return parsed

    current_start = float(parsed.two_theta[0])
    current_end = float(parsed.two_theta[-1])
    offset = _axis_offset_from_corrections(manual_corrections, path, filename, sample_code)
    method = ""
    target = None
    calibration_payload = None
    if offset is not None:
        method = "manual_offset"
    else:
        if isinstance(absolute_offset, dict):
            calibration_payload = dict(absolute_offset)
            absolute_offset = (
                calibration_payload.get("offset_2theta")
                or calibration_payload.get("two_theta_offset")
                or calibration_payload.get("offset")
            )
        try:
            absolute_value = float(absolute_offset)
        except (TypeError, ValueError):
            absolute_value = None
        if absolute_value is not None and math.isfinite(absolute_value) and abs(absolute_value) > float(absolute_min_offset):
            offset = absolute_value
            method = (
                safe_text(calibration_payload.get("method"))
                if calibration_payload
                else "absolute_offset"
            ) or "absolute_offset"
        else:
            offset = None
        treatment_text = (safe_text(treatment) or "").casefold()
        try:
            target = float(target_start)
        except (TypeError, ValueError):
            target = None
        if offset is None and treatment_text in {"glicolado", "glicolada", "calcinado", "calcinada"} and target is not None and math.isfinite(target):
            offset = target - current_start
            if abs(offset) > float(min_offset):
                method = "ngc_natural_start_anchor"

    if offset is None or not math.isfinite(offset) or not method:
        return parsed
    method_min_offset = float(
        min_offset
        if method in {"ngc_natural_start_anchor", "manual_offset"}
        else absolute_min_offset
    )
    if abs(offset) <= method_min_offset and method != "manual_offset":
        return parsed

    parsed.two_theta = [round(float(value) + offset, 6) for value in parsed.two_theta]
    parsed.metadata.update(
        {
            "two_theta_original_start": round(current_start, 6),
            "two_theta_original_end": round(current_end, 6),
            "two_theta_start": round(float(parsed.two_theta[0]), 6),
            "two_theta_end": round(float(parsed.two_theta[-1]), 6),
            "two_theta_offset_applied": round(float(offset), 6),
            "two_theta_alignment_method": method,
            "two_theta_alignment_min_offset": method_min_offset,
            "two_theta_alignment_target_start": round(target, 6) if target is not None and math.isfinite(target) else None,
            "two_theta_alignment_sample_base": safe_text(sample_base),
        }
    )
    if calibration_payload:
        parsed.metadata.update(
            {
                "two_theta_quartz_calibration": calibration_payload,
                "two_theta_quartz_observed_2theta": calibration_payload.get("observed_two_theta"),
                "two_theta_quartz_observed_d": calibration_payload.get("observed_d"),
                "two_theta_quartz_target_2theta": calibration_payload.get("target_two_theta"),
                "two_theta_quartz_target_d": calibration_payload.get("target_d"),
            }
        )
    return parsed


def align_raw_curve_for_classified_display(
    parsed,
    *,
    filename=None,
    path=None,
    sample_code=None,
    sample_base=None,
    treatment=None,
    target_start=None,
    manual_corrections=None,
):
    """Apply the classifier N/G/C axis correction before a curve is displayed.

    Curvas glicoladas e calcinadas devem ser comparadas no mesmo referencial da
    Natural da amostra-base; quando essa ancora nao existe, usa-se quartzo 101.
    """
    inferred_treatment = infer_diffractogram_treatment(sample_code, filename, path)
    treatment_value = safe_text(treatment) or inferred_treatment.get("type")
    sample_base_value = (
        safe_text(sample_base)
        or infer_diffractogram_sample_base(sample_code, filename, path)
    )
    if target_start is None:
        target_start = _snapshot_natural_axis_start(
            sample_base_value,
            str(DRX_RAW_SNAPSHOT_PATH),
            str(DRX_TREATMENT_SNAPSHOT_PATH),
        )
    treatment_text = (safe_text(treatment_value) or "").casefold()
    has_ngc_anchor = (
        treatment_text in {"glicolado", "glicolada", "calcinado", "calcinada"}
        and target_start is not None
    )
    quartz_offset = None
    if not has_ngc_anchor:
        quartz_offset = calculate_quartz_axis_offset(parsed.two_theta, parsed.intensity)
    parsed = apply_two_theta_axis_alignment(
        parsed,
        filename=filename,
        path=path,
        sample_code=sample_code,
        sample_base=sample_base_value,
        treatment=treatment_value,
        target_start=target_start,
        absolute_offset=quartz_offset,
        manual_corrections=manual_corrections if manual_corrections is not None else load_two_theta_axis_corrections(),
    )
    parsed.metadata.setdefault("two_theta_alignment_sample_base", sample_base_value)
    parsed.metadata.setdefault("two_theta_alignment_treatment", treatment_value)
    parsed.metadata["curve_source"] = (
        "classificacao_mineralogica_raw_com_eixo_ajustado"
        if parsed.metadata.get("two_theta_offset_applied") is not None
        else "classificacao_mineralogica_raw"
    )
    return parsed


def _shift_numeric_value(value, offset, digits=6):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
        offset: Valor de entrada consumido por esta etapa do fluxo.
        digits: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    number = _finite_float(value)
    if number is None:
        return value
    return round(number + float(offset), digits)


def shift_observed_two_theta_fields(rows, offset):
    """Shift observed 2theta fields from processed metadata to the classified axis."""
    offset_value = _finite_float(offset)
    if offset_value is None or abs(offset_value) <= 1e-12:
        return rows
    shifted_rows = []
    axis_keys = (
        "two_theta",
        "twoTheta",
        "center_2theta",
        "observed_two_theta",
        "measured_two_theta",
        "measured_two_theta_min",
        "measured_two_theta_max",
        "fit_window_min_2theta",
        "fit_window_max_2theta",
    )
    d_keys = ("d", "d_spacing", "d_angstrom", "center_d_angstrom")
    for row in rows or []:
        if not isinstance(row, dict):
            shifted_rows.append(row)
            continue
        shifted = dict(row)
        for key in axis_keys:
            if key in shifted:
                shifted[key] = _shift_numeric_value(shifted.get(key), offset_value)
        theta_for_d = None
        for key in ("two_theta", "center_2theta", "observed_two_theta"):
            theta_for_d = _finite_float(shifted.get(key))
            if theta_for_d is not None:
                break
        if theta_for_d is not None:
            d_spacing = _two_theta_to_d_spacing(theta_for_d)
            if d_spacing is not None:
                for key in d_keys:
                    if key in shifted:
                        shifted[key] = round(float(d_spacing), 5)
        shifted_rows.append(shifted)
    return shifted_rows


def align_compact_advanced_curve_to_classified_axis(advanced_curve, classified_two_theta, offset=None):
    """Make an advanced compact curve use the same 2theta axis shown in the chart."""
    if not isinstance(advanced_curve, dict) or not advanced_curve:
        return advanced_curve
    current_axis = advanced_curve.get("two_theta") or []
    if not current_axis:
        return advanced_curve
    result = dict(advanced_curve)
    target_axis = []
    if classified_two_theta:
        target_axis, _unused = decimate_series(classified_two_theta, classified_two_theta, max_points=len(current_axis))
    if len(target_axis) == len(current_axis):
        result["two_theta"] = [round(float(value), 6) for value in target_axis]
        result["axis_source"] = "classificacao_mineralogica_raw"
        return result
    offset_value = _finite_float(offset)
    if offset_value is not None and abs(offset_value) > 1e-12:
        result["two_theta"] = [
            round(float(value) + offset_value, 6)
            if _finite_float(value) is not None
            else value
            for value in current_axis
        ]
        result["axis_source"] = "classificacao_mineralogica_raw_offset"
    return result


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
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _finite_curve_pairs(two_theta, intensity):
    """Return finite 2theta/intensity pairs sorted for numeric processing."""
    pairs = []
    for theta_raw, value_raw in zip(two_theta or [], intensity or []):
        theta = _finite_float(theta_raw)
        value = _finite_float(value_raw)
        if theta is not None and value is not None:
            pairs.append((theta, max(value, 0.0)))
    pairs.sort(key=lambda row: row[0])
    return pairs


def _round_series(values, digits=8):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        values: Valor de entrada consumido por esta etapa do fluxo.
        digits: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return [round(float(value), digits) for value in values]


def _moving_average(values, window):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        values: Valor de entrada consumido por esta etapa do fluxo.
        window: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if window <= 1 or len(values) <= 2:
        return [float(value) for value in values]
    half = max(1, window // 2)
    result = []
    for index in range(len(values)):
        start = max(0, index - half)
        end = min(len(values), index + half + 1)
        chunk = values[start:end]
        result.append(sum(chunk) / len(chunk))
    return result


def _smooth_savgol_compatible(values, window=5, polyorder=2):
    """Return Savitzky-Golay-like smoothing without making SciPy mandatory."""
    values = [float(value) for value in values]
    if len(values) < 3:
        return values
    window = max(3, int(window or 5))
    if window % 2 == 0:
        window += 1
    if len(values) < window:
        return _moving_average(values, min(len(values), window))
    try:
        from scipy.signal import savgol_filter  # type: ignore

        return [max(float(value), 0.0) for value in savgol_filter(values, window_length=window, polyorder=polyorder)]
    except Exception:
        pass
    if window == 5 and polyorder == 2:
        coeffs = (-3.0 / 35.0, 12.0 / 35.0, 17.0 / 35.0, 12.0 / 35.0, -3.0 / 35.0)
        smoothed = _moving_average(values, window)
        for index in range(2, len(values) - 2):
            smoothed[index] = max(sum(values[index + offset - 2] * coeffs[offset] for offset in range(5)), 0.0)
        return smoothed
    return _moving_average(values, window)


def _d_spacing_to_two_theta(d_spacing, wavelength=ADVANCED_ALS_WAVELENGTH_CU):
    """Convert d-spacing to 2theta with Bragg's law for the configured wavelength."""
    value = _finite_float(d_spacing)
    if value is None or value <= 0:
        return None
    ratio = float(wavelength) / (2.0 * value)
    if ratio <= 0 or ratio > 1:
        return None
    return math.degrees(2.0 * math.asin(ratio))


def calculate_quartz_axis_offset(
    two_theta,
    intensity,
    *,
    search_d_range=DRX_QUARTZ_CALIBRATION_SEARCH_D_RANGE,
    target_d=DRX_QUARTZ_CALIBRATION_TARGET_D,
    min_relative_intensity=DRX_QUARTZ_CALIBRATION_MIN_RELATIVE_INTENSITY,
    smooth_window=25,
    polyorder=2,
):
    """Find quartz 101 and return an absolute 2theta shift for axis calibration.

    O pico de quartzo e usado como ancora operacional quando nao ha par N/G/C
    com Natural confiavel; o resultado traz metadados para auditoria no painel.
    """
    pairs = _finite_curve_pairs(two_theta, intensity)
    if len(pairs) < MIN_POINTS:
        return None
    clean_two_theta = [row[0] for row in pairs]
    clean_intensity = [row[1] for row in pairs]
    smoothed = _smooth_savgol_compatible(clean_intensity, window=smooth_window, polyorder=polyorder)
    maximum = max(smoothed) if smoothed else 0.0
    if maximum <= 0:
        return None

    d_min, d_max = sorted((float(search_d_range[0]), float(search_d_range[1])))
    min_two_theta = _d_spacing_to_two_theta(d_max)
    max_two_theta = _d_spacing_to_two_theta(d_min)
    target_two_theta = _d_spacing_to_two_theta(target_d)
    if min_two_theta is None or max_two_theta is None or target_two_theta is None:
        return None

    threshold = maximum * (float(min_relative_intensity) / 100.0)
    range_indices = [
        index for index, theta in enumerate(clean_two_theta)
        if min_two_theta <= theta <= max_two_theta
    ]
    if not range_indices:
        return None

    candidate_indices = []
    for index in range_indices:
        value = smoothed[index]
        if value < threshold:
            continue
        left = smoothed[index - 1] if index > 0 else value
        right = smoothed[index + 1] if index < len(smoothed) - 1 else value
        if value >= left and value >= right:
            candidate_indices.append(index)
    if candidate_indices:
        best_index = max(candidate_indices, key=lambda idx: smoothed[idx])
    else:
        best_index = max(range_indices, key=lambda idx: smoothed[idx])
        if smoothed[best_index] < threshold:
            return None

    observed_two_theta = clean_two_theta[best_index]
    observed_d = _two_theta_to_d_spacing(observed_two_theta)
    offset = target_two_theta - observed_two_theta
    if not math.isfinite(offset):
        return None
    return {
        "offset": round(float(offset), 6),
        "method": "quartz_101_absolute_anchor",
        "observed_two_theta": round(float(observed_two_theta), 6),
        "observed_d": round(float(observed_d), 5) if observed_d is not None else None,
        "target_two_theta": round(float(target_two_theta), 6),
        "target_d": round(float(target_d), 5),
        "search_d_range": [round(d_min, 5), round(d_max, 5)],
        "min_relative_intensity_percent": float(min_relative_intensity),
    }


def _second_difference_penalty_diagonals(size):
    """Build the smoothness penalty diagonals used by the ALS fallback solver."""
    diagonal = [0.0 for _ in range(size)]
    upper_1 = [0.0 for _ in range(max(0, size - 1))]
    upper_2 = [0.0 for _ in range(max(0, size - 2))]
    for index in range(max(0, size - 2)):
        diagonal[index] += 1.0
        diagonal[index + 1] += 4.0
        diagonal[index + 2] += 1.0
        upper_1[index] += -2.0
        upper_1[index + 1] += -2.0
        upper_2[index] += 1.0
    return diagonal, upper_1, upper_2


def _solve_pentadiagonal(lower_2, lower_1, diagonal, upper_1, upper_2, rhs):
    """Solve a five-diagonal linear system produced by ALS baseline smoothing."""
    size = len(diagonal)
    lower_2 = list(lower_2)
    lower_1 = list(lower_1)
    diagonal = list(diagonal)
    upper_1 = list(upper_1)
    upper_2 = list(upper_2)
    rhs = list(rhs)
    for pivot_index in range(size):
        pivot = diagonal[pivot_index]
        if abs(pivot) < 1e-12:
            pivot = 1e-12 if pivot >= 0 else -1e-12
            diagonal[pivot_index] = pivot

        row = pivot_index + 1
        if row < size and abs(lower_1[row]) > 0:
            factor = lower_1[row] / pivot
            lower_1[row] = 0.0
            diagonal[row] -= factor * upper_1[pivot_index]
            if pivot_index < size - 2:
                upper_1[row] -= factor * upper_2[pivot_index]
            rhs[row] -= factor * rhs[pivot_index]

        row = pivot_index + 2
        if row < size and abs(lower_2[row]) > 0:
            factor = lower_2[row] / pivot
            lower_2[row] = 0.0
            lower_1[row] -= factor * upper_1[pivot_index]
            if pivot_index < size - 2:
                diagonal[row] -= factor * upper_2[pivot_index]
            rhs[row] -= factor * rhs[pivot_index]

    solution = [0.0 for _ in range(size)]
    for index in range(size - 1, -1, -1):
        value = rhs[index]
        if index + 1 < size:
            value -= upper_1[index] * solution[index + 1]
        if index + 2 < size:
            value -= upper_2[index] * solution[index + 2]
        pivot = diagonal[index]
        if abs(pivot) < 1e-12:
            pivot = 1e-12 if pivot >= 0 else -1e-12
        solution[index] = value / pivot
    return solution


def _als_baseline_stdlib(values, lam=1e6, p=0.01, iterations=10):
    """Compute ALS baseline without SciPy, using the pentadiagonal solver."""
    values = [float(value) for value in values]
    size = len(values)
    if size < 3:
        return [0.0 for _ in values]
    penalty_diagonal, penalty_upper_1, penalty_upper_2 = _second_difference_penalty_diagonals(size)
    weights = [1.0 for _ in values]
    baseline = [0.0 for _ in values]
    p = min(max(float(p), 0.001), 0.999)
    lam = max(float(lam), 0.0)
    for _iteration in range(max(1, int(iterations or 1))):
        diagonal = [weights[index] + (lam * penalty_diagonal[index]) for index in range(size)]
        upper_1 = [lam * value for value in penalty_upper_1]
        upper_2 = [lam * value for value in penalty_upper_2]
        lower_1 = [0.0] + upper_1[:]
        lower_2 = [0.0, 0.0] + upper_2[:]
        rhs = [weights[index] * values[index] for index in range(size)]
        baseline = _solve_pentadiagonal(lower_2, lower_1, diagonal, upper_1, upper_2, rhs)
        weights = [p if values[index] > baseline[index] else 1.0 - p for index in range(size)]
    return baseline


def _als_baseline(values, lam=1e6, p=0.01, iterations=10):
    """Compute ALS baseline, preferring SciPy and falling back to stdlib."""
    try:
        import numpy as np  # type: ignore
        from scipy import sparse  # type: ignore
        from scipy.sparse.linalg import spsolve  # type: ignore

        y = np.asarray(values, dtype=float)
        size = len(y)
        if size < 3:
            return [0.0 for _ in values], "none_too_few_points"
        difference = sparse.diags([1, -2, 1], [0, 1, 2], shape=(size - 2, size), format="csc")
        weights = np.ones(size)
        baseline = np.zeros(size)
        p = min(max(float(p), 0.001), 0.999)
        for _iteration in range(max(1, int(iterations or 1))):
            weight_matrix = sparse.spdiags(weights, 0, size, size)
            z_matrix = weight_matrix + float(lam) * difference.T.dot(difference)
            baseline = spsolve(z_matrix, weights * y)
            weights = np.where(y > baseline, p, 1.0 - p)
        return [float(value) for value in baseline], "als_scipy_sparse"
    except Exception:
        return _als_baseline_stdlib(values, lam=lam, p=p, iterations=iterations), "als_stdlib_pentadiagonal"


def _normalize_positive(values):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        values: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    maximum = max([value for value in values if math.isfinite(value)] or [0.0])
    if maximum <= 0:
        return [0.0 for _ in values], 0.0
    return [max(float(value), 0.0) / maximum for value in values], maximum


def _two_theta_to_d_spacing(two_theta, wavelength=ADVANCED_ALS_WAVELENGTH_CU):
    """Convert 2theta to d-spacing with Bragg's law."""
    theta = math.radians(float(two_theta) / 2.0)
    sine = math.sin(theta)
    if sine <= 0:
        return None
    return wavelength / (2.0 * sine)


def _interpolate_x(left_x, left_y, right_x, right_y, target_y):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        left_x: Valor de entrada consumido por esta etapa do fluxo.
        left_y: Valor de entrada consumido por esta etapa do fluxo.
        right_x: Valor de entrada consumido por esta etapa do fluxo.
        right_y: Valor de entrada consumido por esta etapa do fluxo.
        target_y: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    span = right_y - left_y
    if abs(span) < 1e-12:
        return left_x
    ratio = (target_y - left_y) / span
    return left_x + ((right_x - left_x) * ratio)


def _peak_fwhm(two_theta, values, peak_index):
    """Estimate peak FWHM directly from a corrected curve."""
    peak_value = values[peak_index]
    if peak_value <= 0:
        return None, None, None
    half_height = peak_value / 2.0
    left = peak_index
    while left > 0 and values[left] > half_height:
        left -= 1
    right = peak_index
    while right < len(values) - 1 and values[right] > half_height:
        right += 1
    if left == peak_index or right == peak_index:
        return None, None, None
    left_x = _interpolate_x(two_theta[left], values[left], two_theta[left + 1], values[left + 1], half_height)
    right_x = _interpolate_x(two_theta[right - 1], values[right - 1], two_theta[right], values[right], half_height)
    width = max(0.0, right_x - left_x)
    return width or None, left_x, right_x


def _integrated_peak_area(two_theta, values, peak_index, threshold_fraction=0.005):
    """Integrate a local peak window above a small baseline-relative threshold."""
    peak_value = values[peak_index]
    if peak_value <= 0:
        return 0.0, peak_index, peak_index
    threshold = peak_value * max(0.0, float(threshold_fraction))
    left = peak_index
    while left > 0 and values[left] > threshold:
        left -= 1
    right = peak_index
    while right < len(values) - 1 and values[right] > threshold:
        right += 1
    area = 0.0
    for index in range(left, right):
        dx = abs(two_theta[index + 1] - two_theta[index])
        area += ((values[index] + values[index + 1]) / 2.0) * dx
    return area, left, right


def _select_advanced_peaks(two_theta, corrected, normalized, max_peaks=40, start_two_theta=4.0, prominence=0.02, min_distance=0.18):
    """Pick local maxima for advanced ALS evidence, keeping peaks separated."""
    candidates = []
    for index in range(1, len(normalized) - 1):
        if two_theta[index] < start_two_theta:
            continue
        value = normalized[index]
        if value < prominence:
            continue
        if value >= normalized[index - 1] and value >= normalized[index + 1]:
            candidates.append(index)

    candidates.sort(key=lambda idx: normalized[idx], reverse=True)
    selected = []
    for index in candidates:
        if any(abs(two_theta[index] - two_theta[other]) < min_distance for other in selected):
            continue
        selected.append(index)
        if len(selected) >= max_peaks:
            break
    return selected


def _select_advanced_peaks_with_engine(two_theta, corrected, normalized, max_peaks=40, start_two_theta=4.0, prominence=0.02, min_distance=0.18):
    """Prefer scipy.signal.find_peaks from the isolated science engine."""
    engine_payload = detect_peaks_scipy(
        two_theta,
        normalized,
        start_two_theta=start_two_theta,
        prominence=prominence,
        min_distance=min_distance,
        max_peaks=max_peaks,
    )
    if engine_payload.get("success"):
        indices = []
        for row in engine_payload.get("peaks") or []:
            try:
                index = int(row.get("index"))
            except (TypeError, ValueError):
                continue
            if 0 <= index < len(normalized):
                indices.append(index)
        if indices:
            return indices[:max_peaks], engine_payload.get("method") or "scipy.signal.find_peaks", None
    fallback = _select_advanced_peaks(
        two_theta,
        corrected,
        normalized,
        max_peaks=max_peaks,
        start_two_theta=start_two_theta,
        prominence=prominence,
        min_distance=min_distance,
    )
    return fallback, "stdlib_local_maxima_fallback", engine_payload.get("error")


def _advanced_fit_rows(two_theta, corrected, normalized, peak_indices, *, wavelength_angstrom=ADVANCED_ALS_WAVELENGTH_CU, detection_method="local_maxima_after_als"):
    """Build peak and fit-result rows consumed by the package/similarity UI."""
    peaks = []
    fits = []
    for number, index in enumerate(peak_indices, start=1):
        center = two_theta[index]
        d_spacing = _two_theta_to_d_spacing(center, wavelength=wavelength_angstrom)
        fwhm, left_half, right_half = _peak_fwhm(two_theta, corrected, index)
        area, area_left, area_right = _integrated_peak_area(two_theta, corrected, index)
        theta_rad = math.radians(center / 2.0)
        crystallite_size_nm = None
        if fwhm and fwhm > 0 and math.cos(theta_rad) > 0:
            crystallite_size_nm = (
                ADVANCED_ALS_SCHERRER_K * (float(wavelength_angstrom) / 10.0)
            ) / (math.radians(fwhm) * math.cos(theta_rad))
        relative = normalized[index]
        peak = {
            "peak_index": number,
            "source_index": index,
            "two_theta": round(center, 5),
            "d": round(d_spacing, 5) if d_spacing else None,
            "d_angstrom": round(d_spacing, 5) if d_spacing else None,
            "intensity": round(corrected[index], 8),
            "relative_intensity": round(relative * 100.0, 2),
            "intensity_relative": round(relative, 8),
            "fwhm": round(fwhm, 6) if fwhm else None,
            "prominence": round(relative, 8),
            "status": "detected",
            "source": "advanced_als",
            "detection_method": detection_method,
        }
        peaks.append(peak)
        fits.append(
            {
                "peak_id": f"als:{number}",
                "center_2theta": round(center, 5),
                "center_2theta_stderr": None,
                "center_d_angstrom": round(d_spacing, 5) if d_spacing else None,
                "amplitude": round(corrected[index], 8),
                "height": round(relative, 8),
                "area": round(area, 8),
                "fwhm": round(fwhm, 6) if fwhm else None,
                "sigma": None,
                "gamma": None,
                "fraction": None,
                "baseline_local": 0.0,
                "scherrer_crystallite_size_nm": round(crystallite_size_nm, 4) if crystallite_size_nm else None,
                "scherrer_k": ADVANCED_ALS_SCHERRER_K,
                "wavelength_angstrom": wavelength_angstrom,
                "redchi": None,
                "aic": None,
                "bic": None,
                "r_squared": None,
                "model_name": "als_measured_peak",
                "profile_model": "measured_window",
                "peak_location_method": "local_maximum_after_als",
                "uncertainty_source": "not_estimated",
                "fwhm_source": "half_maximum_als_uncorrected",
                "fit_success": bool(fwhm),
                "fit_quality": "medium" if fwhm else "low",
                "fit_message": "Medidas diretas sobre curva corrigida por ALS; FWHM sem correção instrumental.",
                "fit_window_min_2theta": round(two_theta[area_left], 5),
                "fit_window_max_2theta": round(two_theta[area_right], 5),
                "half_max_left_2theta": round(left_half, 5) if left_half is not None else None,
                "half_max_right_2theta": round(right_half, 5) if right_half is not None else None,
                "source_peak": peak,
            }
        )
    engine_payload = fit_peaks_lmfit(
        two_theta,
        corrected,
        peak_indices,
        wavelength_angstrom=wavelength_angstrom,
    )
    if engine_payload.get("success") and engine_payload.get("fit_results"):
        by_peak = {
            int(row.get("peak_index")): row
            for row in engine_payload.get("fit_results") or []
            if row.get("peak_index") is not None
        }
        for fit in fits:
            try:
                peak_number = int(str(fit.get("peak_id") or "").split(":")[-1])
            except ValueError:
                continue
            engine_fit = by_peak.get(peak_number)
            if not engine_fit:
                continue
            fit.update(
                {
                    **{key: value for key, value in engine_fit.items() if key not in {"peak_index"}},
                    "peak_id": fit.get("peak_id"),
                    "wavelength_angstrom": wavelength_angstrom,
                    "peak_location_method": "lmfit_pseudo_voigt_after_als",
                    "uncertainty_source": "lmfit_covariance" if engine_fit.get("center_2theta_stderr") is not None else "lmfit_no_stderr",
                    "fwhm_source": "lmfit_pseudo_voigt",
                    "fit_quality": "high" if engine_fit.get("fit_success") else "low",
                    "fit_message": engine_fit.get("fit_message") or "Ajuste pseudo-Voigt via lmfit.",
                }
            )
            for peak in peaks:
                if peak.get("peak_index") == peak_number:
                    peak["two_theta"] = engine_fit.get("center_2theta") or peak.get("two_theta")
                    peak["d"] = engine_fit.get("center_d_angstrom") or peak.get("d")
                    peak["d_angstrom"] = engine_fit.get("center_d_angstrom") or peak.get("d_angstrom")
                    peak["fwhm"] = engine_fit.get("fwhm") or peak.get("fwhm")
                    peak["fit_model"] = "lmfit.PseudoVoigtModel"
                    break
    elif engine_payload.get("error"):
        for fit in fits:
            fit["fit_engine_warning"] = engine_payload.get("error")
    return peaks, fits


def _safe_slice(values, indices):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        values: Valor de entrada consumido por esta etapa do fluxo.
        indices: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return [values[index] for index in indices if 0 <= index < len(values)]


def _is_local_maximum(values, index):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        values: Valor de entrada consumido por esta etapa do fluxo.
        index: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if index <= 0 or index >= len(values) - 1:
        return False
    return values[index] >= values[index - 1] and values[index] >= values[index + 1]


def _targeted_quality(relative_height, local_contrast, is_local_max, fwhm):
    """Classify targeted basal evidence without treating it as confirmation."""
    if local_contrast < 0.003:
        return "not_found"
    if not is_local_max and (relative_height >= 0.008 or local_contrast >= 0.008):
        return "shoulder"
    if relative_height >= 0.05 and local_contrast >= 0.02 and is_local_max:
        return "strong"
    if local_contrast >= 0.006 or (relative_height >= 0.006 and is_local_max):
        return "weak"
    return "not_found"


def targeted_basal_peak_scan(
    two_theta,
    intensity_corrected,
    intensity_raw=None,
    wavelength=ADVANCED_ALS_WAVELENGTH_CU,
    ranges=None,
):
    """Scan diagnostic basal windows for weak clay-mineral peaks.

    This complements the global peak picking. Each row is auxiliary evidence and
    can be `weak` or `shoulder`; downstream code must not treat it as
    confirmatory mineral identification.
    """
    pairs = []
    raw_values = list(intensity_raw or [])
    for index, (theta_raw, value_raw) in enumerate(zip(two_theta or [], intensity_corrected or [])):
        theta = _finite_float(theta_raw)
        value = _finite_float(value_raw)
        if theta is None or value is None:
            continue
        raw_value = _finite_float(raw_values[index]) if index < len(raw_values) else None
        pairs.append((theta, max(value, 0.0), raw_value))
    pairs.sort(key=lambda row: row[0])
    if len(pairs) < MIN_POINTS:
        return []

    clean_two_theta = [row[0] for row in pairs]
    corrected = [row[1] for row in pairs]
    raw = [row[2] for row in pairs]
    maximum = max(corrected) if corrected else 0.0
    maximum = maximum if maximum > 0 else 1.0
    range_rows = list(ranges or TARGETED_BASAL_PEAK_RANGES)
    results = []

    for row in range_rows:
        d_min = _finite_float(row.get("d_min"))
        d_max = _finite_float(row.get("d_max"))
        if d_min is None or d_max is None or d_min <= 0 or d_max <= 0:
            continue
        d_low, d_high = sorted((d_min, d_max))
        theta_min = _d_spacing_to_two_theta(d_high, wavelength=wavelength)
        theta_max = _d_spacing_to_two_theta(d_low, wavelength=wavelength)
        center_d = (d_low + d_high) / 2.0
        center_two_theta = _d_spacing_to_two_theta(center_d, wavelength=wavelength)
        indices = [
            index for index, theta in enumerate(clean_two_theta)
            if theta_min is not None and theta_max is not None and theta_min <= theta <= theta_max
        ]
        base = {
            "range_id": safe_text(row.get("range_id")),
            "mineral": safe_text(row.get("mineral")),
            "label": safe_text(row.get("label")),
            "expected_d_min": round(d_low, 5),
            "expected_d_max": round(d_high, 5),
            "expected_d_center": round(center_d, 5),
            "expected_two_theta_min": round(theta_min, 5) if theta_min is not None else None,
            "expected_two_theta_max": round(theta_max, 5) if theta_max is not None else None,
            "expected_two_theta_center": round(center_two_theta, 5) if center_two_theta is not None else None,
            "source": "targeted_basal_peak_scan",
            "interpretation_policy": "pico basal direcionado auxiliar; nao confirma fase mineralogica",
        }
        if not indices:
            results.append({**base, "status": "not_found", "observed_peak": None})
            continue

        peak_index = max(indices, key=lambda idx: corrected[idx])
        window_values = _safe_slice(corrected, indices)
        peak_value = corrected[peak_index]
        floor = min(window_values) if window_values else 0.0
        local_range = max(window_values) - floor if window_values else 0.0
        relative_height = peak_value / maximum if maximum else 0.0
        local_contrast = local_range / maximum if maximum else 0.0
        fwhm, left_half, right_half = _peak_fwhm(clean_two_theta, corrected, peak_index)
        area, area_left, area_right = _integrated_peak_area(clean_two_theta, corrected, peak_index, threshold_fraction=0.01)
        d_observed = _two_theta_to_d_spacing(clean_two_theta[peak_index], wavelength=wavelength)
        is_local_max = _is_local_maximum(corrected, peak_index)
        quality = _targeted_quality(relative_height, local_contrast, is_local_max, fwhm)
        observed_peak = None
        if quality != "not_found" and d_observed is not None:
            observed_peak = {
                "peak_index": f"targeted:{safe_text(row.get('range_id'))}",
                "source_index": peak_index,
                "two_theta": round(clean_two_theta[peak_index], 5),
                "d": round(d_observed, 5),
                "d_angstrom": round(d_observed, 5),
                "intensity": round(peak_value, 8),
                "intensity_raw": round(raw[peak_index], 8) if raw[peak_index] is not None else None,
                "relative_intensity": round(relative_height * 100.0, 4),
                "intensity_relative": round(relative_height, 8),
                "local_contrast": round(local_contrast, 8),
                "fwhm": round(fwhm, 6) if fwhm else None,
                "area": round(area, 8),
                "status": quality,
                "source": "targeted_basal_peak_scan",
                "detection_method": "targeted_d_spacing_window",
            }
        results.append(
            {
                **base,
                "status": quality,
                "observed_d_angstrom": observed_peak.get("d_angstrom") if observed_peak else None,
                "observed_two_theta": observed_peak.get("two_theta") if observed_peak else None,
                "intensity": observed_peak.get("intensity") if observed_peak else None,
                "relative_intensity": observed_peak.get("relative_intensity") if observed_peak else None,
                "local_contrast": round(local_contrast, 8),
                "fwhm": observed_peak.get("fwhm") if observed_peak else None,
                "area": observed_peak.get("area") if observed_peak else None,
                "delta_d_from_center": round(abs(d_observed - center_d), 5) if observed_peak and d_observed is not None else None,
                "delta_two_theta_from_center": round(abs(clean_two_theta[peak_index] - center_two_theta), 5) if observed_peak and center_two_theta is not None else None,
                "window_point_count": len(indices),
                "area_window_min_2theta": round(clean_two_theta[area_left], 5) if observed_peak else None,
                "area_window_max_2theta": round(clean_two_theta[area_right], 5) if observed_peak else None,
                "half_max_left_2theta": round(left_half, 5) if observed_peak and left_half is not None else None,
                "half_max_right_2theta": round(right_half, 5) if observed_peak and right_half is not None else None,
                "observed_peak": observed_peak,
            }
        )
    return results


def process_advanced_als_curve(
    two_theta,
    intensity,
    *,
    sample_id=None,
    filename=None,
    metadata=None,
    window_length=5,
    polyorder=2,
    als_lambda=1e6,
    als_p=0.01,
    als_iterations=10,
    start_two_theta=4.0,
    peak_prominence=0.02,
    max_peaks=40,
    wavelength_angstrom=ADVANCED_ALS_WAVELENGTH_CU,
):
    """Build the advanced ALS processing payload used by the DRX comparator.

    A saida e evidencia auxiliar: picos, baseline, FWHM e metadados de metodo.
    Ela nao altera classificacao mineralogica derivada nem substitui curadoria.
    """
    pairs = _finite_curve_pairs(two_theta, intensity)
    if len(pairs) < MIN_POINTS:
        return {
            "success": False,
            "schema": ADVANCED_ALS_SCHEMA,
            "generated_at": utc_now_iso(),
            "filename": filename,
            "sample_id": sample_id,
            "metadata": metadata or {},
            "curve": {"two_theta": [], "intensity_raw": [], "baseline": [], "intensity_corrected": [], "intensity_normalized": []},
            "peaks": [],
            "fit_results": [],
            "qc_flags": [{"code": "too_few_points", "severity": "error", "message": "Curva com pontos insuficientes para ALS."}],
        }

    clean_two_theta = [row[0] for row in pairs]
    raw_intensity = [row[1] for row in pairs]
    filtered = _smooth_savgol_compatible(raw_intensity, window=window_length, polyorder=polyorder)
    baseline, baseline_method = _als_baseline(filtered, lam=als_lambda, p=als_p, iterations=als_iterations)
    corrected = [max(filtered[index] - baseline[index], 0.0) for index in range(len(filtered))]
    normalized, corrected_max = _normalize_positive(corrected)
    peak_indices, peak_detection_method, peak_detection_error = _select_advanced_peaks_with_engine(
        clean_two_theta,
        corrected,
        normalized,
        max_peaks=max_peaks,
        start_two_theta=start_two_theta,
        prominence=peak_prominence,
    )
    try:
        wavelength_angstrom = float(wavelength_angstrom or ADVANCED_ALS_WAVELENGTH_CU)
    except (TypeError, ValueError):
        wavelength_angstrom = ADVANCED_ALS_WAVELENGTH_CU
    peaks, fit_results = _advanced_fit_rows(
        clean_two_theta,
        corrected,
        normalized,
        peak_indices,
        wavelength_angstrom=wavelength_angstrom,
        detection_method=peak_detection_method,
    )
    targeted_basal_peaks = targeted_basal_peak_scan(
        clean_two_theta,
        corrected,
        intensity_raw=raw_intensity,
        wavelength=wavelength_angstrom,
    )
    qc_flags = []
    if baseline_method == "als_stdlib_pentadiagonal":
        qc_flags.append(
            {
                "code": "als_stdlib_fallback",
                "severity": "info",
                "message": "ALS executado com solver pentadiagonal da biblioteca padrao; SciPy nao e obrigatorio.",
            }
        )
    if not peaks:
        qc_flags.append({"code": "no_peaks_after_als", "severity": "warning", "message": "Nenhum pico acima do limiar apos ALS."})
    if corrected_max <= 0:
        qc_flags.append({"code": "flat_corrected_curve", "severity": "warning", "message": "Curva corrigida sem amplitude positiva."})
    if peak_detection_error:
        qc_flags.append(
            {
                "code": "scipy_peak_detection_unavailable",
                "severity": "info",
                "message": "Deteccao SciPy indisponivel; fallback local usado. " + str(peak_detection_error),
            }
        )

    return {
        "success": True,
        "schema": ADVANCED_ALS_SCHEMA,
        "generated_at": utc_now_iso(),
        "raw_path": None,
        "filename": filename,
        "sample_id": sample_id,
        "metadata": metadata or {},
        "preparation": None,
        "xrd_method": {
            "radiation": "Cu Kalpha",
            "wavelength_angstrom": wavelength_angstrom,
            "scherrer_k": ADVANCED_ALS_SCHERRER_K,
            "scherrer_note": "Tamanho de cristalito estimado sem correcao de alargamento instrumental.",
        },
        "peak_processing": {
            "phase": "processamento_avancado_als",
            "smoothing": "savgol_scipy_or_compatible",
            "window_length": window_length,
            "polyorder": polyorder,
            "baseline_method": baseline_method,
            "als_lambda": als_lambda,
            "als_p": als_p,
            "als_iterations": als_iterations,
            "start_two_theta": start_two_theta,
            "peak_prominence": peak_prominence,
            "max_peaks": max_peaks,
            "peak_detection_method": peak_detection_method,
            "targeted_basal_peak_scan": "enabled",
            "targeted_basal_peak_range_count": len(TARGETED_BASAL_PEAK_RANGES),
            "wavelength_angstrom": wavelength_angstrom,
        },
        "curve": {
            "two_theta": _round_series(clean_two_theta, 6),
            "intensity_raw": _round_series(raw_intensity, 8),
            "intensity_filtered": _round_series(filtered, 8),
            "baseline": _round_series(baseline, 8),
            "intensity_corrected": _round_series(corrected, 8),
            "intensity_normalized": _round_series(normalized, 8),
            "normalization": "max",
            "baseline_method": baseline_method,
            "processing_phase": "processamento_avancado_als",
        },
        "peaks": peaks,
        "targeted_basal_peaks": targeted_basal_peaks,
        "fit_results": fit_results,
        "mineral_evidence": [],
        "mineral_characterization": [],
        "basal_tracking": {},
        "qc_flags": qc_flags,
        "interpretation_policy": "Evidencia assistida para comparacao DRX; nao substitui curadoria mineralogica.",
    }


def advanced_als_summary(payload):
    """Return a compact count/status summary for an advanced ALS payload."""
    curve = (payload or {}).get("curve") or {}
    return {
        "success": bool((payload or {}).get("success")),
        "schema": (payload or {}).get("schema") or ADVANCED_ALS_SCHEMA,
        "generated_at": (payload or {}).get("generated_at"),
        "normalization": curve.get("normalization"),
        "baseline_method": curve.get("baseline_method"),
        "processing_phase": curve.get("processing_phase") or "processamento_avancado_als",
        "points": len(curve.get("two_theta") or []),
        "peaks": len((payload or {}).get("peaks") or []),
        "fit_results": len((payload or {}).get("fit_results") or []),
        "qc_flags": len((payload or {}).get("qc_flags") or []),
    }


def compact_advanced_als_curve(payload, max_points=MAX_RENDER_POINTS):
    """Return the curve channels needed by the browser, bounded by point count."""
    curve = (payload or {}).get("curve") or {}
    two_theta = curve.get("two_theta") or []
    if not two_theta:
        return {"available": False, "error": "Processamento avançado ALS sem curva 2θ."}
    result = {
        "available": bool((payload or {}).get("success")),
        "baseline_method": curve.get("baseline_method"),
        "normalization": curve.get("normalization"),
        "processing_phase": curve.get("processing_phase") or "processamento_avancado_als",
        "points": len(two_theta),
    }
    result["two_theta"], _unused = decimate_series(two_theta, two_theta, max_points=max_points)
    for key in ("intensity_raw", "intensity_filtered", "baseline", "intensity_corrected", "intensity_normalized"):
        values = curve.get(key) or []
        if len(values) == len(two_theta):
            _unused, result[key] = decimate_series(two_theta, values, max_points=max_points)
    return result


def _load_index(index_path=DRX_INDEX_PATH):
    """Load the local import index; invalid/missing files become an empty index."""
    try:
        with open(index_path, "r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except FileNotFoundError:
        return {"version": 1, "diffractograms": []}
    except json.JSONDecodeError:
        return {"version": 1, "diffractograms": []}
    if not isinstance(payload, dict):
        return {"version": 1, "diffractograms": []}
    payload.setdefault("version", 1)
    payload.setdefault("diffractograms", [])
    return payload


@lru_cache(maxsize=8)
def _load_json_payload(path):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    path = Path(path)
    try:
        with open(path, "r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None
    return payload


def _snapshot_id_for_path(path):
    """Create the same stable id used to expose RAW snapshot rows via the API."""
    digest = hashlib.sha256(str(path or "").encode("utf-8")).hexdigest()[:20]
    return f"{SNAPSHOT_ID_PREFIX}{digest}"


def _iter_raw_snapshot_rows(path=None):
    """Iterate classification rows from the module-wide RAW snapshot."""
    path = path or DRX_RAW_SNAPSHOT_PATH
    payload = _load_json_payload(path)
    if not isinstance(payload, dict):
        return []
    rows = payload.get("results") or payload.get("records") or []
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _load_treatment_snapshot_index(path=None):
    """Index N/G/C treatment snapshot rows by path, filename and sample code."""
    path = path or DRX_TREATMENT_SNAPSHOT_PATH
    payload = _load_json_payload(path)
    by_key = {}
    if not isinstance(payload, dict):
        return by_key
    for row in payload.get("results") or []:
        if not isinstance(row, dict):
            continue
        for key in _classification_lookup_keys(row.get("path"), row.get("filename"), row.get("sample_code")):
            by_key[key] = row
    return by_key


def _sha256_file(path):
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


def _package_alias_targets():
    """Return canonical package ids that should win duplicate enrichment ties."""
    try:
        with open(PACKAGE_ALIASES_PATH, "r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return set()
    aliases = payload.get("aliases") if isinstance(payload, dict) else {}
    targets = set()
    for target in (aliases or {}).values():
        if isinstance(target, dict):
            target = target.get("drx") or target.get("default") or target.get("record_id")
        if target:
            targets.add(str(target))
    return targets


def _has_fwhm(item):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        item: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    for row in item.get("fit_results") or []:
        if isinstance(row, dict) and row.get("fwhm") is not None:
            return True
    return False


def _has_package_fwhm(item):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        item: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return _has_fwhm(item)


def _package_candidate_sort_key(candidate, canonical_targets):
    """Prefer canonical packages, FWHM-rich entries and existing advanced output."""
    item = candidate.get("item") or {}
    advanced_path = item.get("advanced_result_path")
    advanced_exists = bool(advanced_path and Path(advanced_path).expanduser().exists())
    record_id = safe_text(candidate.get("record_id"))
    return (
        0 if record_id in canonical_targets else 1,
        0 if _has_package_fwhm(item) else 1,
        0 if advanced_exists else 1,
        record_id,
        safe_text(item.get("filename")),
    )


def _add_package_index_candidate(index, key, candidate):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        index: Valor de entrada consumido por esta etapa do fluxo.
        key: Valor de entrada consumido por esta etapa do fluxo.
        candidate: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    normalized = (safe_text(key) or "").casefold()
    if not normalized:
        return
    index.setdefault(normalized, []).append(candidate)


def _normalized_lookup_text(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return (safe_text(value) or "").casefold()


def _path_lookup_keys(*values):
    """Build raw and resolved path keys for cross-machine manifest matching."""
    keys = set()
    for value in values:
        text = safe_text(value)
        if not text:
            continue
        keys.add(text.casefold())
        try:
            keys.add(str(Path(text).expanduser().resolve()).casefold())
        except (OSError, RuntimeError):
            pass
    return {key for key in keys if key}


def _add_advanced_index_candidate(index, key, candidate):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        index: Valor de entrada consumido por esta etapa do fluxo.
        key: Valor de entrada consumido por esta etapa do fluxo.
        candidate: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    normalized = _normalized_lookup_text(key)
    if normalized:
        index.setdefault(normalized, []).append(candidate)


def _read_jsonl_rows(path):
    """Read JSONL rows while ignoring malformed lines from generated manifests."""
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as fp:
            for line in fp:
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    rows.append(payload)
    except OSError:
        return []
    return rows


@lru_cache(maxsize=12000)
def _read_advanced_result_payload(path_text):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        path_text: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    path = Path(path_text).expanduser()
    try:
        with open(path, "r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _compact_advanced_fit_results(rows, limit=20):
    """Keep only fit fields that the API contract exposes to the browser."""
    compact = []
    for row in (rows or [])[:limit]:
        if not isinstance(row, dict):
            continue
        compact.append({key: row.get(key) for key in ADVANCED_FIT_RESULT_KEYS if key in row})
    return compact


def _compact_advanced_peaks(rows, limit=20):
    """Trim advanced peak rows to the fields useful in DRX comparison."""
    compact = []
    for peak in (rows or [])[:limit]:
        if not isinstance(peak, dict):
            continue
        compact.append(
            {
                "peak_index": peak.get("peak_index") or peak.get("index"),
                "two_theta": peak.get("two_theta") or peak.get("twoTheta"),
                "d": peak.get("d") or peak.get("d_spacing") or peak.get("d_angstrom"),
                "d_angstrom": peak.get("d_angstrom") or peak.get("d") or peak.get("d_spacing"),
                "intensity": peak.get("intensity"),
                "relative_intensity": peak.get("relative_intensity") or peak.get("intensity_relative"),
                "intensity_relative": peak.get("intensity_relative") or peak.get("relative_intensity"),
                "prominence": peak.get("prominence"),
                "status": peak.get("status"),
                "source": peak.get("source") or peak.get("detection_method"),
            }
        )
    return compact


def _compact_targeted_basal_peaks(rows, limit=40):
    """Trim targeted basal scan rows for API/UI contracts."""
    compact = []
    for row in (rows or [])[:limit]:
        if not isinstance(row, dict):
            continue
        observed = row.get("observed_peak") if isinstance(row.get("observed_peak"), dict) else None
        compact.append(
            {
                "range_id": safe_text(row.get("range_id")),
                "mineral": safe_text(row.get("mineral")),
                "label": safe_text(row.get("label")),
                "status": safe_text(row.get("status")),
                "expected_d_min": row.get("expected_d_min"),
                "expected_d_max": row.get("expected_d_max"),
                "expected_d_center": row.get("expected_d_center"),
                "observed_d_angstrom": row.get("observed_d_angstrom"),
                "observed_two_theta": row.get("observed_two_theta"),
                "intensity": row.get("intensity"),
                "relative_intensity": row.get("relative_intensity"),
                "local_contrast": row.get("local_contrast"),
                "fwhm": row.get("fwhm"),
                "area": row.get("area"),
                "delta_d_from_center": row.get("delta_d_from_center"),
                "observed_peak": observed,
                "source": row.get("source"),
                "interpretation_policy": row.get("interpretation_policy"),
            }
        )
    return compact


def _advanced_summary_from_payload(payload, manifest_row, result_path):
    """Summarize an advanced processing payload plus manifest provenance."""
    curve = payload.get("curve") or {}
    return {
        "success": bool(payload.get("success", manifest_row.get("success", True))),
        "generated_at": payload.get("generated_at"),
        "normalization": curve.get("normalization"),
        "baseline_method": curve.get("baseline_method"),
        "points": len(curve.get("two_theta") or []) or manifest_row.get("points"),
        "peaks": len(payload.get("peaks") or []) or manifest_row.get("peaks"),
        "fit_results": len(payload.get("fit_results") or []) or manifest_row.get("fit_results"),
        "targeted_basal_peaks": len(payload.get("targeted_basal_peaks") or []),
        "targeted_basal_peaks_found": sum(
            1 for row in (payload.get("targeted_basal_peaks") or [])
            if isinstance(row, dict) and row.get("status") in {"strong", "weak", "shoulder"}
        ),
        "mineral_evidence": len(payload.get("mineral_evidence") or []) or manifest_row.get("mineral_evidence"),
        "mineral_characterization": len(payload.get("mineral_characterization") or []),
        "qc_flags": len(payload.get("qc_flags") or []) or manifest_row.get("qc_flags"),
        "parser": manifest_row.get("parser"),
        "parser_fallback": manifest_row.get("parser_fallback"),
        "powerxrd_status": manifest_row.get("powerxrd_status"),
        "result_path": str(result_path),
        "error": payload.get("error") or manifest_row.get("error") or manifest_row.get("error_message"),
    }


def _advanced_result_fields(candidate):
    """Load selected advanced ALS evidence for one enrichment candidate."""
    result_path = Path(candidate.get("result_path") or "")
    payload = _read_advanced_result_payload(str(result_path))
    manifest_row = candidate.get("manifest_row") or {}
    if not payload:
        return {}
    fields = {
        "advanced_result_path": str(result_path),
        "advanced_summary": _advanced_summary_from_payload(payload, manifest_row, result_path),
        "fit_results": _compact_advanced_fit_results(payload.get("fit_results") or []),
        "targeted_basal_peaks": _compact_targeted_basal_peaks(payload.get("targeted_basal_peaks") or []),
        "mineral_evidence": (payload.get("mineral_evidence") or [])[:20],
        "mineral_characterization": (payload.get("mineral_characterization") or [])[:20],
        "qc_flags": (payload.get("qc_flags") or [])[:20],
        "basal_tracking": payload.get("basal_tracking") or {},
        "peak_processing": payload.get("peak_processing") or {},
        "xrd_method": payload.get("xrd_method") or {},
    }
    peaks = _compact_advanced_peaks(payload.get("peaks") or [])
    if peaks:
        fields["advanced_peaks"] = peaks
    return fields


@lru_cache(maxsize=4)
def _load_advanced_drx_enrichment_index():
    """Index module-wide advanced DRX results for snapshot enrichment."""
    by_path = {}
    by_name = {}
    rows = _read_jsonl_rows(DRX_ADVANCED_MANIFEST_PATH)
    success_rows = 0
    with_output = 0
    for row in rows:
        if row.get("success") is not True:
            continue
        success_rows += 1
        result_path = Path(row.get("output") or "")
        if not result_path.exists():
            continue
        with_output += 1
        candidate = {
            "manifest_row": row,
            "result_path": str(result_path),
        }
        for key in _path_lookup_keys(row.get("raw_path")):
            _add_advanced_index_candidate(by_path, key, candidate)
        for key in _classification_lookup_keys(row.get("filename"), row.get("sample_id")):
            _add_advanced_index_candidate(by_name, key, candidate)
    return {
        "by_path": by_path,
        "by_name": by_name,
        "manifest_path": str(DRX_ADVANCED_MANIFEST_PATH),
        "results_dir": str(DRX_ADVANCED_RESULTS_DIR),
        "manifest_rows": len(rows),
        "success_rows": success_rows,
        "results_with_output": with_output,
    }


@lru_cache(maxsize=4)
def _load_package_drx_enrichment_index():
    """Index package DRX metadata used to enrich the module-wide RAW snapshot."""
    by_key = {}
    by_sha = {}
    manifest_paths = []
    for root in (ANALYTICAL_PACKAGES_DIR, STATIC_ANALYTICAL_PACKAGES_DIR):
        if root.exists():
            manifest_paths.extend(path for path in root.rglob("drx_manifest.json") if path.is_file())

    for manifest_path in sorted(set(manifest_paths)):
        try:
            with open(manifest_path, "r", encoding="utf-8") as fp:
                manifest = json.load(fp)
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(manifest, dict):
            continue
        record_id = safe_text(manifest.get("record_id")) or manifest_path.parent.name
        for item in manifest.get("items") or []:
            if not isinstance(item, dict):
                continue
            if not (item.get("advanced_result_path") or item.get("fit_results")):
                continue
            candidate = {
                "record_id": record_id,
                "manifest_path": str(manifest_path),
                "item": item,
            }
            for key in _classification_lookup_keys(
                item.get("raw_path"),
                item.get("filename"),
                item.get("sample_code"),
                item.get("sha256"),
            ):
                _add_package_index_candidate(by_key, key, candidate)
            digest = safe_text(item.get("sha256")).casefold()
            if digest:
                by_sha.setdefault(digest, []).append(candidate)
    return {
        "by_key": by_key,
        "by_sha": by_sha,
        "canonical_targets": _package_alias_targets(),
        "manifest_count": len(set(manifest_paths)),
    }


def _package_candidates_for_snapshot(row, item, package_index):
    """Find package manifest candidates that may describe one snapshot RAW."""
    by_key = package_index.get("by_key") or {}
    candidates = []
    seen = set()
    for key in _classification_lookup_keys(
        row.get("path"),
        row.get("raw_path"),
        row.get("filename"),
        row.get("sample_code"),
        item.get("raw_path"),
        item.get("filename"),
        item.get("sample_code"),
    ):
        for candidate in by_key.get(key, []):
            candidate_key = (candidate.get("manifest_path"), id(candidate.get("item")))
            if candidate_key not in seen:
                seen.add(candidate_key)
                candidates.append(candidate)
    return candidates


def _snapshot_raw_sha(row, item, candidates):
    """Resolve a SHA-256 for a snapshot RAW when safe local access exists."""
    explicit = (safe_text(row.get("sha256") or row.get("raw_sha256") or item.get("sha256")) or "").casefold()
    if explicit:
        return explicit
    if not candidates:
        return ""
    raw_path = _resolve_snapshot_raw_path(row.get("path") or row.get("raw_path") or item.get("raw_path"))
    try:
        if raw_path and raw_path.exists() and _is_safe_local_raw_path(raw_path):
            return _sha256_file(raw_path).casefold()
    except OSError:
        return ""
    return ""


def _select_package_match(row, item, package_index):
    """Choose the best package enrichment candidate for a snapshot item."""
    candidates = _package_candidates_for_snapshot(row, item, package_index)
    raw_sha = _snapshot_raw_sha(row, item, candidates)
    if raw_sha:
        sha_candidates = package_index.get("by_sha", {}).get(raw_sha, [])
        if sha_candidates:
            candidate_ids = {(candidate.get("manifest_path"), id(candidate.get("item"))) for candidate in candidates}
            candidates = [
                candidate
                for candidate in sha_candidates
                if not candidate_ids or (candidate.get("manifest_path"), id(candidate.get("item"))) in candidate_ids
            ] or sha_candidates
    if not candidates:
        return None
    return sorted(candidates, key=lambda candidate: _package_candidate_sort_key(candidate, package_index.get("canonical_targets") or set()))[0]


def _enrich_snapshot_item_from_package(row, item, package_index=None):
    """Attach package-level FWHM/ALS fields to a module-wide snapshot item."""
    package_index = package_index if package_index is not None else _load_package_drx_enrichment_index()
    match = _select_package_match(row, item, package_index)
    if not match:
        return item
    package_item = match.get("item") or {}
    fields = (
        "advanced_result_path",
        "advanced_summary",
        "fit_results",
        "targeted_basal_peaks",
        "mineral_evidence",
        "mineral_characterization",
        "qc_flags",
        "basal_tracking",
        "peak_processing",
        "xrd_method",
    )
    for field in fields:
        value = package_item.get(field)
        if value not in (None, "", [], {}):
            item[field] = value
    if package_item.get("peaks"):
        item["advanced_peaks"] = package_item.get("peaks")
    if package_item.get("sha256"):
        item["raw_sha256"] = package_item.get("sha256")

    package_record_id = safe_text(match.get("record_id"))
    item["package_record_id"] = package_record_id
    traceability = dict(item.get("traceability") or {})
    traceability.update(
        {
            "analytical_package_match": True,
            "analytical_package_record_id": package_record_id,
            "analytical_package_manifest_path": match.get("manifest_path"),
            "advanced_result_path": item.get("advanced_result_path"),
            "fit_results_count": len(item.get("fit_results") or []),
            "has_fwhm": _has_package_fwhm(item),
        }
    )
    item["traceability"] = traceability
    return item


def _enrich_snapshot_item_from_raw_link(item):
    """Attach public Argiloteca record links from the curated RAW link table."""
    link = raw_snapshot_link_for_item(item)
    if not link:
        return item
    item["record_id"] = link.get("record_id")
    item["package_record_id"] = link.get("package_record_id") or link.get("record_id")
    item["record_url"] = link.get("record_url")
    item["package_url"] = link.get("package_url")
    traceability = dict(item.get("traceability") or {})
    traceability.update(
        {
            "raw_snapshot_link": True,
            "raw_snapshot_link_record_id": link.get("record_id"),
            "raw_snapshot_link_package_record_id": link.get("package_record_id"),
            "raw_snapshot_link_path": link.get("raw_snapshot_link_path"),
        }
    )
    item["traceability"] = traceability
    return item


def _advanced_candidates_for_snapshot(row, item, advanced_index):
    """Find advanced processing outputs by path first, then filename/sample keys."""
    by_path = advanced_index.get("by_path") or {}
    for key in _path_lookup_keys(row.get("path"), row.get("raw_path"), item.get("raw_path")):
        candidates = by_path.get(key) or []
        if candidates:
            return candidates

    by_name = advanced_index.get("by_name") or {}
    candidates = []
    seen = set()
    for key in _classification_lookup_keys(
        row.get("filename"),
        row.get("sample_code"),
        item.get("filename"),
        item.get("sample_code"),
    ):
        for candidate in by_name.get(key, []):
            candidate_key = candidate.get("result_path")
            if candidate_key not in seen:
                seen.add(candidate_key)
                candidates.append(candidate)
    if len(candidates) == 1:
        return candidates
    return []


def _enrich_snapshot_item_from_advanced_processing(row, item, advanced_index=None):
    """Attach module-wide advanced ALS output when no package field already wins."""
    advanced_index = advanced_index if advanced_index is not None else _load_advanced_drx_enrichment_index()
    candidates = _advanced_candidates_for_snapshot(row, item, advanced_index)
    if not candidates:
        return item
    candidate = candidates[0]
    fields = _advanced_result_fields(candidate)
    if not fields:
        return item

    for field, value in fields.items():
        if value in (None, "", [], {}):
            continue
        if field in {"advanced_result_path", "advanced_summary", "fit_results"}:
            item.setdefault(field, value)
        elif field == "targeted_basal_peaks":
            item.setdefault(field, value)
        elif field == "advanced_peaks":
            item.setdefault(field, value)
        else:
            item.setdefault(field, value)

    traceability = dict(item.get("traceability") or {})
    fit_results = item.get("fit_results") or []
    traceability.update(
        {
            "advanced_processing_match": True,
            "advanced_processing_manifest_path": advanced_index.get("manifest_path"),
            "advanced_processing_result_path": fields.get("advanced_result_path"),
            "advanced_processing_fit_results_count": len(fit_results),
            "advanced_processing_has_fwhm": _has_fwhm(item),
        }
    )
    item["traceability"] = traceability
    return item


def _treatment_for_snapshot_row(row, treatment_index=None):
    """Resolve N/G/C treatment from snapshot, treatment index or filename rules."""
    treatment_index = treatment_index or {}
    for key in _classification_lookup_keys(row.get("path"), row.get("filename"), row.get("sample_code")):
        treatment_row = treatment_index.get(key)
        if treatment_row:
            treatment = safe_text(treatment_row.get("treatment")) or "indeterminado"
            inferred = infer_diffractogram_treatment(row.get("sample_code"), row.get("filename"), row.get("path"))
            if treatment == "indeterminado" and inferred.get("type") != "indeterminado":
                return {
                    "type": inferred["type"],
                    "label": inferred["label"],
                    "confidence": inferred["confidence"],
                    "evidence": inferred["evidence"],
                    "sample_base": infer_diffractogram_sample_base(row.get("sample_code"), row.get("filename"), row.get("path")),
                }
            return {
                "type": treatment,
                "label": safe_text(treatment_row.get("preparation_label"))
                or {
                    "natural": "Natural",
                    "glicolado": "Glicolado",
                    "calcinado": "Calcinado",
                    "indeterminado": "Indeterminado",
                }.get(treatment, treatment.title()),
                "confidence": safe_text(treatment_row.get("confidence")),
                "evidence": safe_text(treatment_row.get("name_evidence")),
                "sample_base": safe_text(treatment_row.get("sample_base"))
                or infer_diffractogram_sample_base(row.get("sample_code"), row.get("filename"), row.get("path")),
            }
    row_treatment = safe_text(row.get("treatment"))
    if row_treatment in {"natural", "glicolado", "calcinado", "indeterminado"}:
        return {
            "type": row_treatment,
            "label": {
                "natural": "Natural",
                "glicolado": "Glicolado",
                "calcinado": "Calcinado",
                "indeterminado": "Indeterminado",
            }.get(row_treatment, row_treatment.title()),
            "confidence": "media",
            "evidence": "campo treatment no snapshot mineralogico",
            "sample_base": safe_text(row.get("sample_base"))
            or infer_diffractogram_sample_base(row.get("sample_code"), row.get("filename"), row.get("path")),
        }
    treatment = infer_diffractogram_treatment(row.get("sample_code"), row.get("filename"), row.get("path"))
    return {
        "type": treatment["type"],
        "label": treatment["label"],
        "confidence": treatment["confidence"],
        "evidence": treatment["evidence"],
        "sample_base": infer_diffractogram_sample_base(row.get("sample_code"), row.get("filename"), row.get("path")),
    }


def _compact_webmineral_features(candidate):
    """Reduce WebMineral enrichment to scientific fields shown by the panel."""
    features = candidate.get("webmineral_features") or candidate.get("features") or {}
    if not isinstance(features, dict):
        return {}

    chemistry = features.get("chemistry") or features.get("chemical_composition") or {}
    crystallography = features.get("crystallography") or {}
    classification = features.get("classification") or {}
    auxiliary_qc = features.get("auxiliary_qc") or {}
    descriptive = features.get("descriptive_properties") or {}
    vocabulary = features.get("vocabulary_expansion") or candidate.get("vocabulary_expansion") or {}

    compact = {}
    if isinstance(chemistry, dict) and chemistry:
        composition = []
        for entry in (chemistry.get("composition") or [])[:12]:
            if not isinstance(entry, dict):
                continue
            composition.append(
                {
                    "element": safe_text(entry.get("element")),
                    "symbol": safe_text(entry.get("symbol")),
                    "element_percent": entry.get("element_percent"),
                    "oxide": safe_text(entry.get("oxide")),
                    "oxide_percent": entry.get("oxide_percent"),
                }
            )
        compact["chemistry"] = {
            "chemical_formula": safe_text(chemistry.get("chemical_formula")),
            "empirical_formula": safe_text(chemistry.get("empirical_formula")),
            "molecular_weight_g_mol": chemistry.get("molecular_weight_g_mol"),
            "total_oxide_percent": chemistry.get("total_oxide_percent"),
            "has_chemical_composition": bool(chemistry.get("has_chemical_composition")),
            "composition": composition,
        }

    if isinstance(crystallography, dict) and crystallography:
        compact["crystallography"] = {
            "cell_parameters": crystallography.get("cell_parameters") or {},
            "crystal_system": crystallography.get("crystal_system") or {},
            "xray_summary": safe_text(crystallography.get("xray_summary")),
            "has_crystallography": bool(crystallography.get("has_crystallography")),
        }

    if isinstance(classification, dict) and classification:
        compact["classification"] = {
            "dana": classification.get("dana") or {},
            "strunz": classification.get("strunz") or {},
            "has_structural_classification": bool(classification.get("has_structural_classification")),
        }

    if isinstance(auxiliary_qc, dict) and auxiliary_qc:
        compact["auxiliary_qc"] = {
            "density": auxiliary_qc.get("density") or {},
            "electron_density": auxiliary_qc.get("electron_density") or {},
            "radioactivity": auxiliary_qc.get("radioactivity") or {},
            "has_auxiliary_qc": bool(auxiliary_qc.get("has_auxiliary_qc")),
        }

    if isinstance(descriptive, dict) and descriptive:
        compact["descriptive_properties"] = {
            key: safe_text(descriptive.get(key))
            for key in (
                "synonym",
                "ima_status",
                "color",
                "cleavage",
                "habit",
                "hardness",
                "luster",
                "streak",
            )
            if descriptive.get(key)
        }

    if isinstance(vocabulary, dict) and vocabulary:
        compact["vocabulary_expansion"] = {
            "category": safe_text(vocabulary.get("category")),
            "family": safe_text(vocabulary.get("family")),
            "members_count": vocabulary.get("members_count"),
            "member_ids": vocabulary.get("member_ids") or [],
            "representative_lines_count": vocabulary.get("representative_lines_count"),
            "source_layers": vocabulary.get("source_layers") or [],
            "validation_status": safe_text(vocabulary.get("validation_status")),
        }

    return compact


def _candidate_feature_groups(candidate):
    """Return classifier feature group labels used for traceability chips."""
    groups = candidate.get("classifier_feature_groups") or []
    if not isinstance(groups, list):
        return []
    return [safe_text(group) for group in groups if safe_text(group)]


def _snapshot_candidates(row):
    """Normalize classifier mineral candidates from one RAW snapshot row."""
    candidates = []
    for candidate in (row.get("candidates") or [])[:MAX_MINERAL_CANDIDATES_PER_DIFRACTOGRAM]:
        if not isinstance(candidate, dict):
            continue
        candidates.append(
            {
                "mineral": safe_text(candidate.get("mineral")),
                "formula": safe_text(candidate.get("formula")),
                "group": safe_text(candidate.get("group")),
                "score": candidate.get("score"),
                "confidence": safe_text(candidate.get("confidence")),
                "matched_lines": candidate.get("matched_lines"),
                "reference_lines": candidate.get("reference_lines"),
                "coverage": candidate.get("coverage"),
                "source": safe_text(candidate.get("source")),
                "argilomineral_id": safe_text(candidate.get("argilomineral_id")),
                "category": safe_text(candidate.get("category")),
                "family": safe_text(candidate.get("family")),
                "classifier_feature_groups": _candidate_feature_groups(candidate),
                "webmineral_features": _compact_webmineral_features(candidate),
                "matches": candidate.get("matches") or [],
            }
        )
    return candidates


def _manual_override_candidate(candidate):
    """Normalize one curated candidate without making it look automatic."""
    if not isinstance(candidate, dict):
        return {}
    normalized = {
        "mineral": safe_text(candidate.get("mineral")),
        "formula": safe_text(candidate.get("formula")),
        "group": safe_text(candidate.get("group")),
        "score": candidate.get("score"),
        "confidence": safe_text(candidate.get("confidence")) or "curatorial",
        "matched_lines": candidate.get("matched_lines"),
        "reference_lines": candidate.get("reference_lines"),
        "coverage": candidate.get("coverage"),
        "source": safe_text(candidate.get("source")) or "curadoria_manual_argiloteca",
        "argilomineral_id": safe_text(candidate.get("argilomineral_id")),
        "category": safe_text(candidate.get("category")) or "manual_override",
        "family": safe_text(candidate.get("family")),
        "classifier_feature_groups": _candidate_feature_groups(candidate),
        "webmineral_features": _compact_webmineral_features(candidate),
        "matches": candidate.get("matches") or [],
        "override": True,
        "policy": "curatorial_auxiliary_not_confirmatory",
    }
    return normalized if normalized["mineral"] else {}


def _manual_override_match_keys(override):
    """
    Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
    
    Args:
        override: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    match = override.get("match") if isinstance(override.get("match"), dict) else {}
    keys = []
    for value in override.get("keys") or []:
        keys.extend(_classification_lookup_keys(value))
    for field in (
        "sample_code",
        "sample_base",
        "filename",
        "path",
        "raw_path",
        "sha256",
        "raw_sha256",
        "diffractogram_id",
    ):
        keys.extend(_classification_lookup_keys(match.get(field)))
    return {key for key in keys if key}


@lru_cache(maxsize=8)
def _load_manual_mineral_overrides(path=None):
    """Load optional curated mineral overrides keyed by sample/file/path/hash."""
    override_path = Path(path or DRX_MANUAL_MINERAL_OVERRIDES_PATH)
    payload = _load_json_payload(override_path)
    if not isinstance(payload, dict):
        return {"available": False, "path": str(override_path), "overrides": []}
    raw_overrides = payload.get("overrides") or payload.get("items") or []
    overrides = []
    for override in raw_overrides:
        if not isinstance(override, dict):
            continue
        candidates = [
            candidate
            for candidate in (
                [_manual_override_candidate(override.get("candidate"))]
                if isinstance(override.get("candidate"), dict)
                else [_manual_override_candidate(candidate) for candidate in (override.get("candidates") or [])]
            )
            if candidate
        ]
        keys = _manual_override_match_keys(override)
        contains = [
            safe_text(value).casefold()
            for value in (override.get("contains") or (override.get("match") or {}).get("contains") or [])
            if safe_text(value)
        ]
        if not candidates or (not keys and not contains):
            continue
        normalized = dict(override)
        normalized["candidates"] = candidates
        normalized["_keys"] = keys
        normalized["_contains"] = contains
        overrides.append(normalized)
    return {
        "available": True,
        "path": str(override_path),
        "schema_version": safe_text(payload.get("schema_version")),
        "overrides": overrides,
    }


def _manual_override_keys_for_item(row, item):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        row: Valor de entrada consumido por esta etapa do fluxo.
        item: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    keys = set()
    for value in (
        row.get("path"),
        row.get("raw_path"),
        row.get("filename"),
        row.get("sample_code"),
        row.get("sample_code_guess"),
        row.get("sha256"),
        row.get("raw_sha256"),
        item.get("raw_path"),
        item.get("filename"),
        item.get("sample_code"),
        item.get("sample_base"),
        item.get("id"),
        item.get("diffractogram_id"),
        item.get("raw_sha256"),
    ):
        keys.update(_classification_lookup_keys(value))
    return keys


def _manual_override_haystack(row, item):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        row: Valor de entrada consumido por esta etapa do fluxo.
        item: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return " ".join(
        safe_text(value)
        for value in (
            row.get("path"),
            row.get("raw_path"),
            row.get("filename"),
            row.get("sample_code"),
            row.get("sample_code_guess"),
            item.get("raw_path"),
            item.get("filename"),
            item.get("sample_code"),
            item.get("sample_base"),
        )
        if safe_text(value)
    ).casefold()


def _matching_manual_overrides(row, item, overrides_index=None):
    """
    Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
    
    Args:
        row: Valor de entrada consumido por esta etapa do fluxo.
        item: Valor de entrada consumido por esta etapa do fluxo.
        overrides_index: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    overrides_index = overrides_index if overrides_index is not None else _load_manual_mineral_overrides()
    matches = []
    if not overrides_index.get("available"):
        return matches
    item_keys = _manual_override_keys_for_item(row, item)
    haystack = _manual_override_haystack(row, item)
    for override in overrides_index.get("overrides") or []:
        if item_keys.intersection(override.get("_keys") or set()):
            matches.append(override)
            continue
        contains = override.get("_contains") or []
        if contains and any(value in haystack for value in contains):
            matches.append(override)
    return matches


def _apply_manual_mineral_overrides(row, item, overrides_index=None):
    """Prepend curated candidates and mark traceability/policy on the item."""
    matches = _matching_manual_overrides(row, item, overrides_index)
    if not matches:
        return item
    existing = list(item.get("mineral_candidates") or [])
    candidates = []
    seen = set()
    warnings = list(item.get("warnings") or [])
    override_ids = []
    for override in matches:
        override_id = safe_text(override.get("id")) or safe_text(override.get("name"))
        if override_id:
            override_ids.append(override_id)
        for warning in override.get("warnings") or []:
            warning_text = safe_text(warning)
            if warning_text and warning_text not in warnings:
                warnings.append(warning_text)
        for candidate in override.get("candidates") or []:
            key = _raw_snapshot_mineral_key(candidate.get("mineral"))
            if key and key not in seen:
                candidates.append(candidate)
                seen.add(key)
    for candidate in existing:
        key = _raw_snapshot_mineral_key(candidate.get("mineral"))
        if key and key in seen:
            continue
        candidates.append(candidate)
        if key:
            seen.add(key)
    item["mineral_candidates"] = candidates[:MAX_MINERAL_CANDIDATES_PER_DIFRACTOGRAM]
    item["argilominerais"] = _unique_texts(candidate.get("mineral") for candidate in item["mineral_candidates"])
    item["grupos_minerais"] = _unique_texts(candidate.get("group") for candidate in item["mineral_candidates"])
    item["warnings"] = warnings
    traceability = dict(item.get("traceability") or {})
    traceability.update(
        {
            "manual_mineral_override": True,
            "manual_mineral_override_ids": override_ids,
            "manual_mineral_override_path": (
                overrides_index or _load_manual_mineral_overrides()
            ).get("path"),
            "manual_mineral_override_policy": "curatorial_auxiliary_not_confirmatory",
        }
    )
    item["traceability"] = traceability
    return item


def _snapshot_item_from_row(row, treatment_index=None, package_index=None, advanced_index=None):
    """Build the public API item for one module-wide RAW snapshot row."""
    path = safe_text(row.get("path") or row.get("raw_path"))
    filename = safe_text(row.get("filename")) or Path(path).name
    sample_code = safe_text(row.get("sample_code") or row.get("sample_code_guess")) or Path(filename).stem
    treatment = _treatment_for_snapshot_row(row, treatment_index)
    candidates = _snapshot_candidates(row)
    peaks = (row.get("peaks") or row.get("detected_peaks") or [])[:16]
    diffractogram_id = _snapshot_id_for_path(path or filename)
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    item = {
        "id": diffractogram_id,
        "diffractogram_id": diffractogram_id,
        "record_id": None,
        "source": "snapshot_geral_raw",
        "sample_code": sample_code,
        "sample_base": treatment.get("sample_base") or sample_code,
        "filename": filename,
        "original_filename": filename,
        "raw_path": path,
        "status": safe_text(row.get("status")) or "ok",
        "error_message": safe_text(row.get("error_message")),
        "metadata": metadata,
        "preparation": treatment["type"],
        "preparation_label": treatment["label"],
        "preparation_confidence": treatment.get("confidence"),
        "preparation_evidence": treatment.get("evidence"),
        "treatment": treatment["type"],
        "treatment_label": treatment["label"],
        "mineral_candidates": candidates,
        "detected_peaks": peaks,
        "peaks": peaks,
        "argilominerais": _unique_texts(candidate.get("mineral") for candidate in candidates),
        "grupos_minerais": _unique_texts(candidate.get("group") for candidate in candidates),
        "traceability": {
            "record_associated": False,
            "source_snapshot": str(DRX_RAW_SNAPSHOT_PATH),
            "mineral_candidate_count": len(candidates),
        },
    }
    if package_index is not None:
        item = _enrich_snapshot_item_from_package(row, item, package_index)
    item = _apply_manual_mineral_overrides(row, item)
    item = _enrich_snapshot_item_from_raw_link(item)
    item = _attach_ngc_group_classification_to_snapshot_item(item)
    if advanced_index is not None:
        item = _enrich_snapshot_item_from_advanced_processing(row, item, advanced_index)
    return item


def _attach_ngc_group_classification_to_snapshot_item(item):
    """Attach group-level N/G/C classification to snapshot RAW items when available."""
    ngc_group_index = _load_ngc_group_classification_index()
    ngc_group_classification = _ngc_group_classification_for_item(item, ngc_group_index)
    if not ngc_group_classification:
        return item
    enriched = dict(item)
    mineral_candidates = []
    for candidate in enriched.get("mineral_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        mineral_candidates.append(
            {
                **candidate,
                "raw_candidate_score": candidate.get("score"),
                "score_role": "raw_individual_auxiliary",
                "interpretation_policy": "candidato individual fraco/auxiliar quando houver trio N/G/C",
            }
        )
    enriched["mineral_candidates"] = mineral_candidates
    enriched["ngc_group_classification"] = ngc_group_classification
    enriched["ngc_group_classification_available"] = True
    traceability = dict(enriched.get("traceability") or {})
    traceability.update(
        {
            "ngc_group_classification": True,
            "ngc_group_classification_path": ngc_group_index.get("path"),
            "raw_candidate_policy": (
                "candidatos por RAW isolado sao evidencias secundarias; classificacao N/G/C de grupo prevalece para argilominerais"
            ),
        }
    )
    enriched["traceability"] = traceability
    return enriched


def _normalized_raw_snapshot_filters(filters=None):
    """Normalize API filter inputs for snapshot list and suggestion endpoints."""
    filters = filters or {}
    status_filter = (filters.get("status") or "").strip().casefold()
    return {
        "query": (filters.get("q") or "").strip().casefold(),
        "preparation": (filters.get("preparation") or filters.get("treatment") or "").strip().casefold(),
        "argilomineral": (filters.get("argilomineral") or "").strip().casefold(),
        "mineral_group": (filters.get("mineral_group") or "").strip().casefold(),
        "sample_code": (filters.get("sample_code") or "").strip().casefold(),
        "status": status_filter,
        "include_all_statuses": status_filter in {"all", "todos", "tudo", "*"},
    }


def _raw_snapshot_mineral_key(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return re.sub(r"[^a-z0-9]+", "-", safe_text(value).casefold()).strip("-")


def _candidate_matches_mineral_filter(candidate, mineral_filter):
    """
    Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
    
    Args:
        candidate: Valor de entrada consumido por esta etapa do fluxo.
        mineral_filter: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    target = _raw_snapshot_mineral_key(mineral_filter)
    candidate_name = safe_text((candidate or {}).get("mineral")).casefold()
    candidate_key = _raw_snapshot_mineral_key(candidate_name)
    return bool(target and (target == candidate_key or target in candidate_name))


def _raw_snapshot_item_matches_argilomineral_filter(item, mineral_filter):
    """
    Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
    
    Args:
        item: Valor de entrada consumido por esta etapa do fluxo.
        mineral_filter: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    target = _raw_snapshot_mineral_key(mineral_filter)
    if any(
        _candidate_matches_mineral_filter(candidate, mineral_filter)
        for candidate in (item.get("mineral_candidates") or [])
    ):
        return True
    for mineral in item.get("argilominerais") or []:
        mineral_text = safe_text(mineral).casefold()
        mineral_key = _raw_snapshot_mineral_key(mineral_text)
        if mineral_filter in mineral_text or (target and target == mineral_key):
            return True
    return False


def _raw_snapshot_item_matches_filters(item, normalized_filters):
    """Apply query, status, preparation and mineral filters to a snapshot item."""
    item_status = safe_text(item.get("status")).casefold()
    status_filter = normalized_filters["status"]
    if not normalized_filters["include_all_statuses"] and item.get("status") not in {"ok", "importado"}:
        return False
    if status_filter and not normalized_filters["include_all_statuses"] and item_status != status_filter:
        return False

    haystack = " ".join(
        str(value or "")
        for value in [
            item.get("sample_code"),
            item.get("sample_base"),
            item.get("filename"),
            item.get("raw_path"),
            item.get("preparation_label"),
            " ".join(item.get("argilominerais") or []),
            " ".join(item.get("grupos_minerais") or []),
        ]
    ).casefold()
    if normalized_filters["query"] and normalized_filters["query"] not in haystack:
        return False
    if normalized_filters["preparation"] and normalized_filters["preparation"] != safe_text(item.get("preparation")).casefold():
        return False
    if normalized_filters["sample_code"] and normalized_filters["sample_code"] not in safe_text(item.get("sample_code")).casefold():
        return False
    if normalized_filters["argilomineral"] and not _raw_snapshot_item_matches_argilomineral_filter(
        item,
        normalized_filters["argilomineral"],
    ):
        return False
    if normalized_filters["mineral_group"] and normalized_filters["mineral_group"] not in " ".join(
        item.get("grupos_minerais") or []
    ).casefold():
        return False
    return True


def _candidate_score(candidate):
    """
    Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
    
    Args:
        candidate: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    try:
        return float((candidate or {}).get("score"))
    except (TypeError, ValueError):
        return float("-inf")


def _raw_snapshot_mineral_rank(item, mineral_filter):
    """Rank mineral-filtered rows by whether the target is the top candidate."""
    candidates = item.get("mineral_candidates") or []
    if not candidates:
        return (0, float("-inf"))
    target_scores = [
        _candidate_score(candidate)
        for candidate in candidates
        if _candidate_matches_mineral_filter(candidate, mineral_filter)
    ]
    if not target_scores:
        return (0, float("-inf"))
    best_target_score = max(target_scores)
    best_overall_score = max(_candidate_score(candidate) for candidate in candidates)
    target_is_top_candidate = best_target_score >= best_overall_score
    return (1 if target_is_top_candidate else 0, best_target_score)


def _filtered_raw_snapshot_pairs(filters=None):
    """Return raw rows plus enriched/filter-matching snapshot item pairs."""
    rows = _iter_raw_snapshot_rows()
    treatment_index = _load_treatment_snapshot_index()
    package_index = _load_package_drx_enrichment_index()
    normalized_filters = _normalized_raw_snapshot_filters(filters)
    filtered_pairs = []
    for row in rows:
        item = _snapshot_item_from_row(row, treatment_index, package_index, None)
        if _raw_snapshot_item_matches_filters(item, normalized_filters):
            filtered_pairs.append((item, row))
    if normalized_filters["argilomineral"]:
        filtered_pairs.sort(
            key=lambda pair: _raw_snapshot_mineral_rank(pair[0], normalized_filters["argilomineral"]),
            reverse=True,
        )
    return rows, filtered_pairs


def _snapshot_row_by_id(diffractogram_id):
    """Find the backing snapshot row for an API diffractogram id."""
    if not str(diffractogram_id or "").startswith(SNAPSHOT_ID_PREFIX):
        return None
    for row in _iter_raw_snapshot_rows():
        path = safe_text(row.get("path") or row.get("raw_path"))
        filename = safe_text(row.get("filename"))
        if _snapshot_id_for_path(path or filename) == diffractogram_id:
            return row
    return None


@lru_cache(maxsize=4096)
def _snapshot_natural_axis_start(sample_base, snapshot_path_text=None, treatment_path_text=None):
    """Find the natural curve start angle used to align G/C companions."""
    sample_base_key = safe_text(sample_base).casefold()
    if not sample_base_key:
        return None
    snapshot_path = Path(snapshot_path_text or DRX_RAW_SNAPSHOT_PATH)
    treatment_path = Path(treatment_path_text or DRX_TREATMENT_SNAPSHOT_PATH)
    treatment_index = _load_treatment_snapshot_index(treatment_path)
    for row in _iter_raw_snapshot_rows(snapshot_path):
        treatment = _treatment_for_snapshot_row(row, treatment_index)
        row_base = safe_text(treatment.get("sample_base")).casefold()
        if row_base != sample_base_key or treatment.get("type") != "natural":
            continue
        raw_path = safe_text(row.get("path") or row.get("raw_path"))
        resolved_raw_path = _resolve_snapshot_raw_path(raw_path)
        if not raw_path or not _is_safe_local_raw_path(resolved_raw_path) or not resolved_raw_path.exists():
            continue
        try:
            parsed = parse_raw_file(resolved_raw_path)
        except Exception:
            continue
        try:
            return float(parsed.metadata.get("two_theta_start"))
        except (TypeError, ValueError):
            return None
    return None


def _save_index(payload, index_path=DRX_INDEX_PATH):
    """Persist the local import index atomically."""
    index_path = Path(index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = index_path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
        fp.write("\n")
    tmp_path.replace(index_path)


def _relative_to_instance(path):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    try:
        return str(Path(path).resolve().relative_to(DEFAULT_INSTANCE_PATH.resolve()))
    except Exception:
        return str(path)


def _is_safe_local_raw_path(path):
    """Ensure local RAW access stays inside approved import/snapshot roots."""
    resolved = Path(path).expanduser().resolve()
    for root in SUPPORTED_LOCAL_IMPORT_ROOTS:
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def _resolve_snapshot_raw_path(path):
    """Resolve snapshot paths across original and current workspace layouts."""
    candidate = Path(path or "").expanduser()
    if candidate.exists():
        return candidate

    text = str(path or "")
    marker_targets = (
        (
            "povoamento/visualizacao-drx/raw-classificados/",
            (
                DEFAULT_WORKSPACE_PATH / "povoamento" / "visualizacao-drx" / "raw-classificados",
                DEFAULT_WORKSPACE_PATH / "data" / "drx" / "raw-classificados",
            ),
        ),
        (
            "povoamento/visualizacao-drx/raw/",
            (
                DEFAULT_WORKSPACE_PATH / "povoamento" / "visualizacao-drx" / "raw",
                DEFAULT_WORKSPACE_PATH / "data" / "drx" / "raw",
            ),
        ),
    )
    for marker, target_roots in marker_targets:
        if marker not in text:
            continue
        suffix = text.split(marker, 1)[1]
        for target_root in target_roots:
            remapped = target_root / suffix
            if remapped.exists():
                return remapped

    filename = candidate.name
    if filename:
        for root in SUPPORTED_LOCAL_IMPORT_ROOTS:
            for remapped in root.rglob(filename):
                if remapped.exists():
                    return remapped
    return candidate


def build_diffractogram_record(record_id, sample_code, original_name, raw_path, parsed, status="importado", error=None):
    """Create an index entry and sidecar curve JSON for an imported RAW."""
    diffractogram_id = uuid.uuid4().hex
    data_path = DRX_DATA_DIR / f"{diffractogram_id}.json"
    raw_ref = str(raw_path) if raw_path else None

    data_path.parent.mkdir(parents=True, exist_ok=True)
    with open(data_path, "w", encoding="utf-8") as fp:
        json.dump(
            {
                "id": diffractogram_id,
                "two_theta": parsed.two_theta,
                "intensity": parsed.intensity,
            },
            fp,
            ensure_ascii=False,
        )
        fp.write("\n")

    return {
        "id": diffractogram_id,
        "record_id": record_id,
        "sample_code": sample_code,
        "original_filename": original_name,
        "raw_path": raw_ref,
        "data_path": _relative_to_instance(data_path),
        "metadata": {
            **parsed.metadata,
            "imported_at": utc_now_iso(),
        },
        "status": status,
        "error_message": error,
    }


def import_raw_path(record_id, path, sample_code=None, copy_raw=True):
    """Import a local RAW file and associate it with an Argiloteca record id."""
    source_path = Path(path).expanduser().resolve()
    if not _is_safe_local_raw_path(source_path):
        raise RawParseError("Caminho local fora das pastas autorizadas para importacao DRX.")

    parsed = parse_raw_file(source_path)
    raw_path = source_path
    if copy_raw:
        DRX_RAW_DIR.mkdir(parents=True, exist_ok=True)
        raw_path = DRX_RAW_DIR / f"{uuid.uuid4().hex}_{source_path.name}"
        shutil.copy2(source_path, raw_path)

    item = build_diffractogram_record(
        record_id=str(record_id),
        sample_code=safe_text(sample_code),
        original_name=source_path.name,
        raw_path=raw_path,
        parsed=parsed,
    )
    payload = _load_index()
    payload["diffractograms"].append(item)
    _save_index(payload)
    return item


def import_raw_upload(record_id, storage, sample_code=None):
    """Import a Flask/Werkzeug upload object and associate it with a record id."""
    original_name = Path(storage.filename or "difratograma.raw").name
    DRX_RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = DRX_RAW_DIR / f"{uuid.uuid4().hex}_{original_name}"
    storage.save(raw_path)
    parsed = parse_raw_file(raw_path)
    item = build_diffractogram_record(
        record_id=str(record_id),
        sample_code=safe_text(sample_code),
        original_name=original_name,
        raw_path=raw_path,
        parsed=parsed,
    )
    payload = _load_index()
    payload["diffractograms"].append(item)
    _save_index(payload)
    return item


def record_exists(record_id, size=DEFAULT_SIZE):
    """Return True when the target record is visible in the published record service."""
    target = str(record_id or "")
    if not target:
        return False
    for record in search_records(size=size):
        if str(record.get("id") or "") == target or str(record.get("uuid") or "") == target:
            return True
    return False


def record_import_error(record_id, original_name, error_message, sample_code=None):
    """Record a failed import attempt so the API can report it consistently."""
    item = {
        "id": uuid.uuid4().hex,
        "record_id": str(record_id),
        "sample_code": safe_text(sample_code),
        "original_filename": original_name,
        "raw_path": None,
        "data_path": None,
        "metadata": {"imported_at": utc_now_iso()},
        "status": "erro",
        "error_message": str(error_message),
    }
    payload = _load_index()
    payload["diffractograms"].append(item)
    _save_index(payload)
    return item


def load_drx_index():
    """Expose the local DRX import index to routes/tests."""
    return _load_index()


def load_diffractogram_data(diffractogram_id):
    """Load curve data for either snapshot-backed or locally imported DRX ids."""
    snapshot_row = _snapshot_row_by_id(diffractogram_id)
    if snapshot_row:
        treatment_index = _load_treatment_snapshot_index()
        item = _snapshot_item_from_row(
            snapshot_row,
            treatment_index,
            _load_package_drx_enrichment_index(),
            _load_advanced_drx_enrichment_index(),
        )
        raw_path = item.get("raw_path")
        resolved_raw_path = _resolve_snapshot_raw_path(raw_path)
        if raw_path and _is_safe_local_raw_path(resolved_raw_path) and resolved_raw_path.exists():
            try:
                parsed = parse_raw_file(resolved_raw_path)
                parsed = align_raw_curve_for_classified_display(
                    parsed,
                    filename=item.get("filename"),
                    path=str(resolved_raw_path),
                    sample_code=item.get("sample_code"),
                    sample_base=item.get("sample_base"),
                    treatment=item.get("treatment"),
                    manual_corrections=load_two_theta_axis_corrections(),
                )
                offset = parsed.metadata.get("two_theta_offset_applied")
                advanced_curve = None
                if item.get("advanced_result_path"):
                    advanced_payload = _read_advanced_result_payload(item.get("advanced_result_path"))
                    advanced_curve = compact_advanced_als_curve(advanced_payload, max_points=MAX_RENDER_POINTS)
                    advanced_curve = align_compact_advanced_curve_to_classified_axis(
                        advanced_curve,
                        parsed.two_theta,
                        offset=offset,
                    )
                if offset is not None:
                    item["advanced_peaks"] = shift_observed_two_theta_fields(item.get("advanced_peaks") or [], offset)
                    item["fit_results"] = shift_observed_two_theta_fields(item.get("fit_results") or [], offset)
                metadata = {
                    **item,
                    "resolved_raw_path": str(resolved_raw_path),
                    **parsed.metadata,
                }
                if advanced_curve:
                    metadata["advanced_curve"] = advanced_curve
                return {
                    "metadata": metadata,
                    "two_theta": parsed.two_theta,
                    "intensity": parsed.intensity,
                }
            except Exception as exc:
                return {
                    "metadata": {**item, "error_message": str(exc)},
                    "two_theta": [],
                    "intensity": [],
                }
        return {
            "metadata": {**item, "error_message": "Arquivo RAW do snapshot nao encontrado no ambiente local."},
            "two_theta": [],
            "intensity": [],
        }

    index = _load_index()
    item = next(
        (entry for entry in index.get("diffractograms", []) if entry.get("id") == diffractogram_id),
        None,
    )
    if not item:
        return None
    classification_index = _load_mineral_classification_index()
    mineral_classification = _mineral_classification_for_item(item, classification_index)
    metadata = {
        **item,
        "mineral_classification": mineral_classification,
        "mineral_candidates": mineral_classification.get("candidates") or [],
        "detected_peaks": mineral_classification.get("peaks") or [],
    }
    if item.get("status") != "importado" or not item.get("data_path"):
        return {"metadata": metadata, "two_theta": [], "intensity": []}

    data_path = DEFAULT_INSTANCE_PATH / item["data_path"]
    try:
        with open(data_path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
    except Exception:
        data = {"two_theta": [], "intensity": []}

    raw_path = item.get("raw_path")
    resolved_raw_path = Path(raw_path).expanduser() if raw_path else None
    if resolved_raw_path and _is_safe_local_raw_path(resolved_raw_path) and resolved_raw_path.exists():
        try:
            parsed = parse_raw_file(resolved_raw_path)
            parsed = align_raw_curve_for_classified_display(
                parsed,
                filename=item.get("original_filename"),
                path=str(resolved_raw_path),
                sample_code=item.get("sample_code"),
                sample_base=infer_diffractogram_sample_base(
                    item.get("sample_code"),
                    item.get("original_filename"),
                    str(resolved_raw_path),
                ),
                treatment=infer_diffractogram_treatment(
                    item.get("sample_code"),
                    item.get("original_filename"),
                    str(resolved_raw_path),
                ).get("type"),
                manual_corrections=load_two_theta_axis_corrections(),
            )
            return {
                "metadata": {
                    **metadata,
                    "resolved_raw_path": str(resolved_raw_path),
                    **parsed.metadata,
                },
                "two_theta": parsed.two_theta,
                "intensity": parsed.intensity,
            }
        except Exception:
            pass

    return {
        "metadata": {**metadata, "curve_source": "data_path_pre_importado"},
        "two_theta": data.get("two_theta") or [],
        "intensity": data.get("intensity") or [],
    }


def list_raw_snapshot_items(filters=None, limit=80, offset=0):
    """Return RAW files from the module-wide DRX snapshot, not tied to records."""
    rows, filtered_pairs = _filtered_raw_snapshot_pairs(filters)
    package_index = _load_package_drx_enrichment_index()
    advanced_index = _load_advanced_drx_enrichment_index()

    items = [item for item, _row in filtered_pairs]
    total = len(items)
    package_record_counts = Counter(
        item.get("package_record_id")
        for item in items
        if (item.get("traceability") or {}).get("analytical_package_match") and item.get("package_record_id")
    )
    limit = max(1, min(int(limit or 80), 500))
    offset = max(0, int(offset or 0))
    page_pairs = filtered_pairs[offset : offset + limit]
    page = [
        _enrich_snapshot_item_from_advanced_processing(row, item, advanced_index)
        for item, row in page_pairs
    ]
    advanced_processing_enriched_items = sum(
        1 for item, row in filtered_pairs if _advanced_candidates_for_snapshot(row, item, advanced_index)
    )
    advanced_processing_returned_items = sum(
        1 for item in page if (item.get("traceability") or {}).get("advanced_processing_match")
    )
    advanced_processing_returned_with_fwhm = sum(
        1 for item in page if (item.get("traceability") or {}).get("advanced_processing_has_fwhm")
    )
    advanced_processing_fwhm_scope = "filtered_set" if total == len(page) else "returned_page"
    return {
        "success": True,
        "source": "snapshot_geral_raw",
        "snapshot_path": str(DRX_RAW_SNAPSHOT_PATH),
        "items": page,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "returned": len(page),
        },
        "filters": {
            "sample_code": sorted({item.get("sample_code") for item in items if item.get("sample_code")})[:500],
            "treatment": [
                value
                for value in ("natural", "glicolado", "calcinado", "indeterminado")
                if any(item.get("preparation") == value for item in items)
            ],
            "argilomineral": sorted({m for item in items for m in (item.get("argilominerais") or []) if m})[:500],
            "mineral_group": sorted({g for item in items for g in (item.get("grupos_minerais") or []) if g})[:500],
            "status": sorted({item.get("status") for item in items if item.get("status")}),
        },
        "meta": {
            "raw_files_total": len(rows),
            "snapshot_available": bool(rows),
            "package_manifest_count": package_index.get("manifest_count", 0),
            "package_enriched_items": sum(1 for item in items if (item.get("traceability") or {}).get("analytical_package_match")),
            "package_enriched_with_fwhm": sum(1 for item in items if (item.get("traceability") or {}).get("has_fwhm")),
            "package_enriched_record_counts": dict(sorted(package_record_counts.items())),
            "advanced_processing_manifest_rows": advanced_index.get("manifest_rows", 0),
            "advanced_processing_success_rows": advanced_index.get("success_rows", 0),
            "advanced_processing_results_with_output": advanced_index.get("results_with_output", 0),
            "advanced_processing_enriched_items": advanced_processing_enriched_items,
            "advanced_processing_returned_items": advanced_processing_returned_items,
            "advanced_processing_returned_with_fwhm": advanced_processing_returned_with_fwhm,
            "advanced_processing_enriched_with_fwhm": advanced_processing_returned_with_fwhm,
            "advanced_processing_enriched_with_fwhm_scope": advanced_processing_fwhm_scope,
        },
    }


def _comparison_candidate_match(match):
    """Trim a classifier match to comparison-suggestion fields."""
    return {
        "observed_d": match.get("observed_d"),
        "reference_d": match.get("reference_d"),
        "delta_d": match.get("delta_d"),
        "observed_two_theta": match.get("observed_two_theta"),
        "reference_two_theta": match.get("reference_two_theta"),
        "delta_two_theta": match.get("delta_two_theta"),
        "observed_relative_intensity": match.get("observed_relative_intensity"),
        "reference_relative_intensity": match.get("reference_relative_intensity"),
        "closeness": match.get("closeness"),
    }


def _comparison_candidate(candidate):
    """Trim one mineral candidate for the suggestion API."""
    return {
        "mineral": safe_text(candidate.get("mineral")),
        "formula": safe_text(candidate.get("formula")),
        "group": safe_text(candidate.get("group")),
        "score": candidate.get("score"),
        "confidence": safe_text(candidate.get("confidence")),
        "matched_lines": candidate.get("matched_lines"),
        "reference_lines": candidate.get("reference_lines"),
        "coverage": candidate.get("coverage"),
        "source": safe_text(candidate.get("source")),
        "argilomineral_id": safe_text(candidate.get("argilomineral_id")),
        "category": safe_text(candidate.get("category")),
        "family": safe_text(candidate.get("family")),
        "matches": [_comparison_candidate_match(match) for match in (candidate.get("matches") or [])[:3] if isinstance(match, dict)],
    }


def _comparison_suggestion_item(item):
    """Return the compact item payload used in comparison suggestions."""
    return {
        "id": item.get("id"),
        "diffractogram_id": item.get("diffractogram_id"),
        "record_id": item.get("record_id"),
        "package_record_id": item.get("package_record_id"),
        "record_url": item.get("record_url"),
        "package_url": item.get("package_url"),
        "source": item.get("source"),
        "sample_code": item.get("sample_code"),
        "sample_base": item.get("sample_base"),
        "filename": item.get("filename"),
        "original_filename": item.get("original_filename"),
        "preparation": item.get("preparation"),
        "preparation_label": item.get("preparation_label"),
        "treatment": item.get("treatment"),
        "treatment_label": item.get("treatment_label"),
        "status": item.get("status"),
        "mineral_candidates": [
            _comparison_candidate(candidate)
            for candidate in (item.get("mineral_candidates") or [])[:1]
            if isinstance(candidate, dict)
        ],
        "argilominerais": (item.get("argilominerais") or [])[:6],
        "grupos_minerais": (item.get("grupos_minerais") or [])[:6],
    }


def _add_comparison_suggestion(suggestions, suggestion_type, label, priority, group, suggestion_items):
    """Append a comparison suggestion when at least two unique items exist."""
    seen = set()
    unique_items = []
    for item in suggestion_items:
        if not item:
            continue
        key = item.get("diffractogram_id") or item.get("id") or item.get("sample_code") or item.get("filename")
        if not key or key in seen:
            continue
        seen.add(key)
        unique_items.append(item)
    if len(unique_items) < 2:
        return
    suggestions.append(
        {
            "type": suggestion_type,
            "label": label,
            "priority": priority,
            "group": group,
            "items": [_comparison_suggestion_item(item) for item in unique_items[:6]],
        }
    )


def build_raw_snapshot_comparison_suggestions(filters=None, limit=1000):
    """Build comparison groups over the full RAW snapshot without loading curves."""
    rows, filtered_pairs = _filtered_raw_snapshot_pairs(filters)
    items = [item for item, _row in filtered_pairs]
    grouped = {}
    by_preparation = {"natural": [], "glicolado": [], "calcinado": [], "indeterminado": []}
    by_mineral = {}
    for item in items:
        base = item.get("sample_base") or item.get("sample_code") or item.get("filename")
        group = grouped.setdefault(base, {"sampleBase": base, "items": {}, "allItems": []})
        preparation = item.get("preparation")
        if preparation and preparation not in group["items"]:
            group["items"][preparation] = item
        group["allItems"].append(item)
        if preparation in by_preparation:
            by_preparation[preparation].append(item)
        for candidate in (item.get("mineral_candidates") or [])[:3]:
            mineral = safe_text(candidate.get("mineral"))
            if mineral:
                by_mineral.setdefault(mineral, []).append(item)

    suggestions = []
    for group in grouped.values():
        natural = group["items"].get("natural")
        glicolado = group["items"].get("glicolado")
        calcinado = group["items"].get("calcinado")
        indeterminado = group["items"].get("indeterminado")
        visible_group = {"sampleBase": group["sampleBase"]}
        if natural and glicolado and calcinado:
            _add_comparison_suggestion(
                suggestions,
                "trio",
                "Natural x glicolado x calcinado",
                1,
                visible_group,
                [natural, glicolado, calcinado],
            )
        elif natural and glicolado:
            _add_comparison_suggestion(suggestions, "ng", "Natural x glicolado", 2, visible_group, [natural, glicolado])
        elif natural and calcinado:
            _add_comparison_suggestion(suggestions, "nc", "Natural x calcinado", 3, visible_group, [natural, calcinado])
        elif glicolado and calcinado:
            _add_comparison_suggestion(suggestions, "gc", "Glicolado x calcinado", 4, visible_group, [glicolado, calcinado])
        if indeterminado and (natural or glicolado or calcinado):
            _add_comparison_suggestion(
                suggestions,
                "indeterminado",
                "Arquivo indeterminado x preparação conhecida",
                5,
                visible_group,
                [indeterminado, natural, glicolado, calcinado],
            )
        if len(group["allItems"]) >= 3:
            _add_comparison_suggestion(
                suggestions,
                "replicatas",
                "Conjunto com múltiplos arquivos da mesma amostra-base",
                8,
                visible_group,
                group["allItems"],
            )

    for mineral, mineral_items in by_mineral.items():
        sample_bases = {item.get("sample_base") or item.get("sample_code") for item in mineral_items}
        if len(sample_bases) >= 2:
            _add_comparison_suggestion(
                suggestions,
                "mineral",
                "Mesmo candidato mineralógico: " + mineral,
                6,
                {"sampleBase": "Mineral: " + mineral},
                mineral_items,
            )

    preparation_labels = {
        "natural": "Natural",
        "glicolado": "Glicolado",
        "calcinado": "Calcinado",
        "indeterminado": "Indeterminado",
    }
    for preparation, preparation_items in by_preparation.items():
        if len(preparation_items) >= 3:
            _add_comparison_suggestion(
                suggestions,
                "preparo",
                "Comparar arquivos com preparo " + preparation_labels.get(preparation, preparation.title()),
                7,
                {"sampleBase": "Preparo: " + preparation_labels.get(preparation, preparation.title())},
                preparation_items,
            )

    suggestions.sort(
        key=lambda suggestion: (
            suggestion.get("priority") or 999,
            safe_text((suggestion.get("group") or {}).get("sampleBase")).casefold(),
        )
    )
    suggestions_total = len(suggestions)
    limit = max(1, min(int(limit or 1000), 5000))
    returned = suggestions[:limit]
    return {
        "success": True,
        "source": "snapshot_geral_raw",
        "snapshot_path": str(DRX_RAW_SNAPSHOT_PATH),
        "suggestions": returned,
        "pagination": {
            "total": suggestions_total,
            "limit": limit,
            "offset": 0,
            "returned": len(returned),
        },
        "meta": {
            "raw_files_total": len(rows),
            "items_total": len(items),
            "sample_bases_total": len({item.get("sample_base") for item in items if item.get("sample_base")}),
            "suggestions_total": suggestions_total,
            "suggestions_returned": len(returned),
        },
    }


def _unique_texts(values):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        values: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    values_by_key = {}
    for value in values or []:
        text = safe_text(value)
        if text:
            values_by_key[text.casefold()] = text
    return [values_by_key[key] for key in sorted(values_by_key)]


def _classification_lookup_keys(*values):
    """Generate robust lookup keys for filenames, stems and sample codes."""
    keys = []
    for value in values:
        text = safe_text(value)
        if not text:
            continue
        path = Path(text)
        variants = {text, path.name, path.stem}
        if path.suffix:
            variants.add(path.name[: -len(path.suffix)])
        for variant in variants:
            normalized = safe_text(variant)
            if normalized:
                keys.append(normalized.casefold())
    return keys


def _load_mineral_classification_index(path=DRX_MINERAL_CLASSIFICATION_PATH):
    """Load the derived classifier snapshot as an item lookup index."""
    path = Path(path)
    try:
        with open(path, "r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except FileNotFoundError:
        return {"available": False, "path": str(path), "by_key": {}}
    except json.JSONDecodeError:
        return {"available": False, "path": str(path), "by_key": {}, "error": "JSON de classificacao invalido."}

    by_key = {}
    for row in payload.get("results") or []:
        if not isinstance(row, dict) or row.get("status") != "ok":
            continue
        candidates = []
        for candidate in (row.get("candidates") or [])[:MAX_MINERAL_CANDIDATES_PER_DIFRACTOGRAM]:
            if not isinstance(candidate, dict):
                continue
            candidates.append(
                {
                    "mineral": safe_text(candidate.get("mineral")),
                    "formula": safe_text(candidate.get("formula")),
                    "group": safe_text(candidate.get("group")),
                    "score": candidate.get("score"),
                    "confidence": safe_text(candidate.get("confidence")),
                    "matched_lines": candidate.get("matched_lines"),
                    "reference_lines": candidate.get("reference_lines"),
                    "coverage": candidate.get("coverage"),
                    "source": safe_text(candidate.get("source")),
                    "argilomineral_id": safe_text(candidate.get("argilomineral_id")),
                    "category": safe_text(candidate.get("category")),
                    "family": safe_text(candidate.get("family")),
                    "classifier_feature_groups": _candidate_feature_groups(candidate),
                    "webmineral_features": _compact_webmineral_features(candidate),
                    "matches": candidate.get("matches") or [],
                }
            )
        classification = {
            "filename": row.get("filename"),
            "sample_code": row.get("sample_code"),
            "status": row.get("status"),
            "candidates": candidates,
            "peaks": (row.get("peaks") or [])[:16],
        }
        for key in _classification_lookup_keys(row.get("filename"), row.get("sample_code")):
            by_key[key] = classification

    return {
        "available": True,
        "path": str(path),
        "summary": payload.get("summary") or {},
        "by_key": by_key,
    }


@lru_cache(maxsize=4)
def _load_ngc_group_classification_index(path_text=None):
    """Load group-level N/G/C classification generated by the batch diagnostic script."""
    if path_text:
        path = Path(path_text)
    else:
        candidate_paths = [
            DRX_NGC_GROUP_CLASSIFICATION_PATH,
            DRX_NGC_GROUP_CLASSIFICATION_FALLBACK_PATH,
        ]
        path = next((candidate for candidate in candidate_paths if candidate.exists()), candidate_paths[0])
    try:
        with open(path, "r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except FileNotFoundError:
        return {"available": False, "path": str(path), "by_sample_base": {}}
    except json.JSONDecodeError:
        return {"available": False, "path": str(path), "by_sample_base": {}, "error": "JSON N/G/C invalido."}

    by_sample_base = {}
    for group in payload.get("groups") or []:
        if not isinstance(group, dict):
            continue
        sample_id = safe_text(group.get("sample_id"))
        keys = set(_classification_lookup_keys(sample_id))
        keys.update(_classification_lookup_keys(infer_diffractogram_sample_base(sample_id)))
        probable_minerals = [_normalize_ngc_group_candidate(row) for row in (group.get("probable_minerals") or [])]
        possible_minerals = [_normalize_ngc_group_candidate(row) for row in (group.get("possible_minerals") or [])]
        accessory_minerals = [_normalize_ngc_group_candidate(row) for row in (group.get("accessory_minerals") or [])]
        candidates = [_normalize_ngc_group_candidate(row) for row in (group.get("candidates") or [])]
        for key in keys:
            if key:
                by_sample_base[key] = {
                    "schema_version": payload.get("schema_version"),
                    "source_path": str(path),
                    "sample_id": sample_id,
                    "status": group.get("status"),
                    "available_treatments": group.get("available_treatments") or [],
                    "probable_minerals": probable_minerals,
                    "possible_minerals": possible_minerals,
                    "accessory_minerals": accessory_minerals,
                    "candidates": candidates,
                    "diagnoses": group.get("diagnoses") or [],
                    "best_treatment": group.get("best_treatment") or {},
                    "warnings": group.get("warnings") or [],
                    "policy": group.get("policy") or payload.get("interpretation_policy"),
                }

    return {
        "available": True,
        "path": str(path),
        "schema_version": payload.get("schema_version"),
        "by_sample_base": by_sample_base,
        "summary": {
            "groups": len(payload.get("groups") or []),
            "samples_processed": payload.get("samples_processed"),
        },
    }


def _normalize_ngc_group_candidate(candidate):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        candidate: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not isinstance(candidate, dict):
        return {}
    row = dict(candidate)
    if row.get("score") is None:
        for key in ("ngc_group_score", "basal_diagnostic_score", "similarity_score", "reference_match_score"):
            if row.get(key) is not None:
                row["score"] = row.get(key)
                break
    row.setdefault("score_role", "ngc_group_auxiliary")
    row.setdefault("interpretation_policy", "classificacao N/G/C auxiliar; nao confirma fase mineralogica")
    return row


def _ngc_group_classification_for_item(item, ngc_index):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        item: Valor de entrada consumido por esta etapa do fluxo.
        ngc_index: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    sample_base = infer_diffractogram_sample_base(
        item.get("sample_code"),
        item.get("original_filename"),
        item.get("raw_path"),
        item.get("filename"),
    )
    for key in _classification_lookup_keys(sample_base, item.get("sample_code"), item.get("original_filename")):
        group = (ngc_index.get("by_sample_base") or {}).get(key)
        if group:
            return group
    return None


def _mineral_classification_for_item(item, classification_index):
    """Return classifier peaks/candidates for one imported or snapshot item."""
    for key in _classification_lookup_keys(item.get("sample_code"), item.get("original_filename"), item.get("raw_path")):
        classification = classification_index.get("by_key", {}).get(key)
        if classification:
            return classification
    if classification_index.get("available"):
        return {"status": "nao_encontrado", "candidates": [], "peaks": []}
    return {
        "status": "indisponivel",
        "candidates": [],
        "peaks": [],
        "message": "Classificacao mineralogica ainda nao encontrada para este difratograma.",
    }


def infer_diffractogram_treatment(*values):
    """Infer the XRD preparation from common local RAW filename suffixes."""
    joined = " ".join(safe_text(value) or "" for value in values)
    text = joined.upper()
    rules = (
        (r"\(\s*N\s*\)(?:\.RAW)?(?:$|[\s._-])", "natural", "sufixo (N)"),
        (r"\(\s*G\s*\)(?:\.RAW)?(?:$|[\s._-])", "glicolado", "sufixo (G)"),
        (r"\(\s*C\s*\)(?:\.RAW)?(?:$|[\s._-])", "calcinado", "sufixo (C)"),
        (r"(?:^|[\s._-])N(?:\.RAW)?(?:$|[\s._-])", "natural", "sufixo N/-N"),
        (r"(?:^|[\s._-])G(?:\.RAW)?(?:$|[\s._-])", "glicolado", "sufixo G/-G"),
        (r"(?:^|[\s._-])C(?:\.RAW)?(?:$|[\s._-])", "calcinado", "sufixo C/-C"),
        (r"(?:CAL|CALC|CALCIN|AQUEC|HEAT|550|500|350|300)", "calcinado", "marcador textual/temperatura"),
        (r"N(?:\.RAW)?$", "natural", "sufixo N"),
        (r"G(?:\.RAW)?$", "glicolado", "sufixo G"),
        (r"C(?:\.RAW)?$", "calcinado", "sufixo C"),
    )
    for pattern, treatment, evidence in rules:
        if re.search(pattern, text):
            return {
                "type": treatment,
                "label": {
                    "natural": "Natural",
                    "glicolado": "Glicolado",
                    "calcinado": "Calcinado",
                }[treatment],
                "confidence": "alta",
                "evidence": evidence,
            }
    return {
        "type": "indeterminado",
        "label": "Indeterminado",
        "confidence": "baixa",
        "evidence": "sem marcador N/G/C no nome do arquivo ou codigo da amostra",
    }


def _sample_contexts(custom_fields):
    """Index record sample metadata by sample code for imported DRX rows."""
    samples = custom_fields.get("arg:amostras")
    contexts = {}
    if isinstance(samples, list):
        for index, sample in enumerate(samples):
            if not isinstance(sample, dict):
                continue
            code = safe_text(sample.get("codigo_amostra"))
            if not code:
                continue
            contexts[code] = {
                "sample_index": index,
                "sample_id": safe_text(sample.get("sample_id")) or safe_text(sample.get("id")) or code,
                "sample_code": code,
                "sample_label": safe_text(sample.get("descricao_amostra"))
                or safe_text(sample.get("local_coleta"))
                or code,
                "locality": safe_text(sample.get("local_coleta")),
                "sample_type": safe_text(sample.get("tipo_amostra"))
                or safe_text(sample.get("contexto_geologico")),
                "field_notes": safe_text(sample.get("observacoes_campo")),
            }

    if contexts:
        return contexts

    legacy_code = safe_text(custom_fields.get("arg:amostra_codigo"))
    if legacy_code:
        contexts[legacy_code] = {
            "sample_index": 0,
            "sample_id": legacy_code,
            "sample_code": legacy_code,
            "sample_label": safe_text(custom_fields.get("arg:amostra_descricao_local")) or legacy_code,
            "locality": safe_text(custom_fields.get("arg:amostra_local_coleta"))
            or safe_text(custom_fields.get("arg:pesquisa_local")),
            "sample_type": safe_text(custom_fields.get("arg:amostra_tipo_amostra")),
            "field_notes": None,
        }
    return contexts


def _analysis_contexts(custom_fields):
    """Index record analysis metadata by sample code."""
    analyses_by_code = {}
    analyses = custom_fields.get("arg:analises")
    if not isinstance(analyses, list):
        return analyses_by_code

    for analysis in analyses:
        if not isinstance(analysis, dict):
            continue
        code = safe_text(analysis.get("codigo_amostra"))
        if not code:
            continue
        analyses_by_code.setdefault(code, []).append(
            {
                "analysis_id": safe_text(analysis.get("analise_id")) or safe_text(analysis.get("id")),
                "sample_code": code,
                "method": safe_text(analysis.get("metodo")),
                "analysis_date": safe_text(analysis.get("data_analise")),
                "laboratory": safe_text(analysis.get("laboratorio")),
                "equipment": safe_text(analysis.get("equipamento")),
                "result_file": safe_text(analysis.get("arquivo_resultado")),
                "main_result": safe_text(analysis.get("resultado_principal")),
                "interpretation": safe_text(analysis.get("interpretacao")),
                "notes": safe_text(analysis.get("observacoes")),
            }
        )
    return analyses_by_code


def _mineral_contexts(custom_fields):
    """Index curated mineral context by sample code, with record-level fallback."""
    minerals_by_code = {}
    minerals = custom_fields.get("arg:argilominerais")
    if isinstance(minerals, list):
        for index, mineral in enumerate(minerals):
            if not isinstance(mineral, dict):
                continue
            code = safe_text(mineral.get("codigo_amostra")) or RECORD_LEVEL_KEY
            minerals_by_code.setdefault(code, []).append(
                {
                    "entry_id": index + 1,
                    "sample_code": None if code == RECORD_LEVEL_KEY else code,
                    "mineral_name": safe_text(mineral.get("nome"))
                    or safe_text(mineral.get("nome_cientifico_padronizado")),
                    "mineral_group": safe_text(mineral.get("grupo"))
                    or safe_text(mineral.get("grupo_mineralogico")),
                    "description": safe_text(mineral.get("descricao_curta")) or safe_text(mineral.get("descricao")),
                    "formation_geological": safe_text(mineral.get("formacao_geologica")),
                    "external_source": safe_text(mineral.get("external_source")),
                }
            )
    elif extract_mineral_entries(custom_fields):
        minerals_by_code[RECORD_LEVEL_KEY] = extract_mineral_entries(custom_fields)
    return minerals_by_code


def _record_description(record):
    """Collect record metadata used to contextualize DRX diffractograms."""
    custom_fields = record_custom_fields(record)
    sample = extract_primary_sample(custom_fields)
    minerals = extract_mineral_entries(custom_fields)
    samples_by_code = _sample_contexts(custom_fields)
    analyses_by_sample_code = _analysis_contexts(custom_fields)
    minerals_by_sample_code = _mineral_contexts(custom_fields)
    mineral_names = []
    mineral_groups = []
    descriptions = []
    for mineral in minerals:
        if mineral.get("mineral_name"):
            mineral_names.append(mineral["mineral_name"])
        if mineral.get("mineral_group"):
            mineral_groups.append(mineral["mineral_group"])
        if mineral.get("origin_summary"):
            descriptions.append(mineral["origin_summary"])
        if mineral.get("validation_notes"):
            descriptions.append(mineral["validation_notes"])

    return {
        "title": record_title(record),
        "sample_code": sample.get("sample_code"),
        "sample_label": sample.get("sample_label"),
        "sample_locality": sample.get("locality"),
        "sample_type": sample.get("sample_type"),
        "sample_count": len(samples_by_code),
        "sample_codes": sorted(samples_by_code),
        "samples_by_code": samples_by_code,
        "analyses_by_sample_code": analyses_by_sample_code,
        "minerals_by_sample_code": minerals_by_sample_code,
        "argilominerais": sorted(set(mineral_names)),
        "grupos_minerais": sorted(set(mineral_groups)),
        "ambiente_formacao": safe_text(custom_fields.get("arg:origem_ambiente_formacao")),
        "rocha_hospedeira": safe_text(custom_fields.get("arg:origem_tipo_rocha")),
        "formacao_geologica": safe_text(custom_fields.get("arg:origem_formacao_geologica")),
        "metodos": safe_text(custom_fields.get("arg:metodo_tecnicas_utilizadas"))
        or safe_text(custom_fields.get("arg:metodo_descricao")),
        "resumo": " | ".join(descriptions[:3]),
    }


def _enrich_diffractogram(item, description, classification_index=None):
    """Attach sample, analysis and classifier context to an imported DRX item."""
    sample_code = safe_text(item.get("sample_code"))
    samples_by_code = description.get("samples_by_code") or {}
    analyses_by_sample_code = description.get("analyses_by_sample_code") or {}
    minerals_by_sample_code = description.get("minerals_by_sample_code") or {}
    sample = samples_by_code.get(sample_code) or {
        "sample_id": sample_code,
        "sample_code": sample_code,
        "sample_label": sample_code,
        "locality": None,
        "sample_type": None,
        "field_notes": None,
    }
    sample_minerals = minerals_by_sample_code.get(sample_code) or []
    record_minerals = minerals_by_sample_code.get(RECORD_LEVEL_KEY) or []
    enriched = dict(item)
    treatment = infer_diffractogram_treatment(
        item.get("sample_code"),
        item.get("original_filename"),
    )
    enriched["sample_code"] = sample_code
    enriched["sample"] = sample
    enriched["treatment"] = treatment["type"]
    enriched["treatment_label"] = treatment["label"]
    enriched["treatment_confidence"] = treatment["confidence"]
    enriched["treatment_evidence"] = treatment["evidence"]
    enriched["analyses"] = analyses_by_sample_code.get(sample_code) or []
    enriched["argilominerais"] = _unique_texts(mineral.get("mineral_name") for mineral in sample_minerals)
    enriched["grupos_minerais"] = _unique_texts(mineral.get("mineral_group") for mineral in sample_minerals)
    enriched["record_level_argilominerais"] = _unique_texts(mineral.get("mineral_name") for mineral in record_minerals)
    classification_index = classification_index or {"available": False, "by_key": {}}
    ngc_group_index = _load_ngc_group_classification_index()
    mineral_classification = _mineral_classification_for_item(item, classification_index)
    ngc_group_classification = _ngc_group_classification_for_item(item, ngc_group_index)
    if ngc_group_classification:
        mineral_classification = dict(mineral_classification or {})
        mineral_classification["raw_candidate_policy"] = (
            "candidatos por RAW isolado sao evidencias secundarias; classificacao N/G/C de grupo prevalece para argilominerais"
        )
        mineral_classification["ngc_group_classification_available"] = True
    enriched["mineral_classification"] = mineral_classification
    mineral_candidates = mineral_classification.get("candidates") or []
    if ngc_group_classification:
        mineral_candidates = [
            {
                **candidate,
                "raw_candidate_score": candidate.get("score"),
                "score_role": "raw_individual_auxiliary",
                "interpretation_policy": "candidato individual fraco/auxiliar quando houver trio N/G/C",
            }
            for candidate in mineral_candidates
            if isinstance(candidate, dict)
        ]
    enriched["mineral_candidates"] = mineral_candidates
    if ngc_group_classification:
        enriched["ngc_group_classification"] = ngc_group_classification
    enriched["detected_peaks"] = mineral_classification.get("peaks") or []
    enriched["traceability"] = {
        "sample_found": bool(sample_code and sample_code in samples_by_code),
        "analysis_count": len(enriched["analyses"]),
        "mineral_count": len(sample_minerals),
        "record_level_mineral_count": len(record_minerals),
        "mineral_candidate_count": len(enriched["mineral_candidates"]),
        "mineral_classification_status": mineral_classification.get("status"),
        "ngc_group_classification": bool(ngc_group_classification),
        "ngc_group_classification_path": ngc_group_index.get("path"),
    }
    return enriched


def list_records_with_drx(filters=None, size=DEFAULT_SIZE):
    """Return records that have at least one imported DRX entry."""
    filters = filters or {}
    index = _load_index()
    classification_index = _load_mineral_classification_index()
    by_record = {}
    for item in index.get("diffractograms", []):
        by_record.setdefault(str(item.get("record_id")), []).append(item)

    records = []
    query = (filters.get("q") or "").strip().casefold()
    sample_filter = (filters.get("sample_code") or "").strip().casefold()
    treatment_filter = (filters.get("treatment") or "").strip().casefold()
    mineral_filter = (filters.get("argilomineral") or "").strip().casefold()
    group_filter = (filters.get("mineral_group") or "").strip().casefold()

    for record in search_records(size=size):
        record_id = str(record.get("id") or record.get("uuid") or "")
        diffractograms = by_record.get(record_id) or []
        imported = [item for item in diffractograms if item.get("status") == "importado"]
        if not imported:
            continue

        description = _record_description(record)
        valid_sample_codes = set(description.get("sample_codes") or [])
        if valid_sample_codes:
            imported = [
                item
                for item in imported
                if safe_text(item.get("sample_code")) in valid_sample_codes
            ]
        if not imported:
            continue
        imported = [_enrich_diffractogram(item, description, classification_index) for item in imported]
        if treatment_filter:
            imported = [
                item
                for item in imported
                if treatment_filter == safe_text(item.get("treatment")).casefold()
            ]
            if not imported:
                continue
        imported_sample_codes = _unique_texts(item.get("sample_code") for item in imported)
        imported_minerals = _unique_texts(
            mineral
            for item in imported
            for mineral in (item.get("argilominerais") or [])
            + [candidate.get("mineral") for candidate in (item.get("mineral_candidates") or [])]
        )
        imported_groups = _unique_texts(
            group
            for item in imported
            for group in (item.get("grupos_minerais") or [])
            + [candidate.get("group") for candidate in (item.get("mineral_candidates") or [])]
        )
        haystack = " ".join(
            str(value or "")
            for value in [
                record_id,
                description.get("title"),
                description.get("sample_code"),
                description.get("sample_label"),
                " ".join(imported_sample_codes),
                " ".join(item.get("original_filename") or "" for item in imported),
                " ".join(description.get("argilominerais") or []),
                " ".join(description.get("grupos_minerais") or []),
            ]
        ).casefold()
        if query and query not in haystack:
            continue
        if sample_filter and sample_filter not in " ".join(imported_sample_codes).casefold():
            continue
        if mineral_filter and mineral_filter not in " ".join(imported_minerals or description.get("argilominerais") or []).casefold():
            continue
        if group_filter and group_filter not in " ".join(imported_groups or description.get("grupos_minerais") or []).casefold():
            continue

        public_description = {
            key: value
            for key, value in description.items()
            if key not in {"samples_by_code", "analyses_by_sample_code", "minerals_by_sample_code"}
        }
        records.append(
            {
                "id": record_id,
                **public_description,
                "diffractograms": imported,
                "links": {
                    "record_html": f"/records/{record_id}",
                    "record_api": f"/api/records/{record_id}",
                },
            }
        )

    return {
        "success": True,
        "meta": {
            "total_records": len(records),
            "total_diffractograms": sum(len(record["diffractograms"]) for record in records),
            "mineral_classification_available": classification_index.get("available", False),
            "mineral_classification_path": classification_index.get("path"),
        },
        "records": records,
        "filters": {
            "argilomineral": sorted(
                {
                    m
                    for record in records
                    for item in (record.get("diffractograms") or [])
                    for m in (item.get("argilominerais") or [])
                    + [candidate.get("mineral") for candidate in (item.get("mineral_candidates") or [])]
                    if m
                }
            ),
            "mineral_group": sorted(
                {
                    g
                    for record in records
                    for item in (record.get("diffractograms") or [])
                    for g in (item.get("grupos_minerais") or [])
                    + [candidate.get("group") for candidate in (item.get("mineral_candidates") or [])]
                    if g
                }
            ),
            "sample_code": sorted(
                {
                    item.get("sample_code")
                    for record in records
                    for item in (record.get("diffractograms") or [])
                    if item.get("sample_code")
                }
            ),
            "treatment": [
                value
                for value in ("natural", "glicolado", "calcinado", "indeterminado")
                if any(
                    item.get("treatment") == value
                    for record in records
                    for item in (record.get("diffractograms") or [])
                )
            ],
        },
    }


def decimate_series(two_theta, intensity, max_points=MAX_RENDER_POINTS):
    """Keep browser payloads bounded while preserving the full converted file."""
    if len(two_theta) <= max_points:
        return two_theta, intensity
    step = max(1, math.ceil(len(two_theta) / max_points))
    return two_theta[::step], intensity[::step]
