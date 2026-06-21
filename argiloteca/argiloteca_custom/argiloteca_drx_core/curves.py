"""
Projeto: Painel DRX Argiloteca

Descrição:
Dependency-light curve parsing and XRD numeric helpers.

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

import math
import re
import struct
from dataclasses import dataclass
from pathlib import Path


MIN_POINTS = 10
SUPPORTED_TEXT_CURVE_EXTENSIONS = {".csv", ".txt", ".xy", ".dat"}
SUPPORTED_UPLOAD_CURVE_EXTENSIONS = {".raw", *SUPPORTED_TEXT_CURVE_EXTENSIONS}
CU_K_ALPHA_WAVELENGTH = 1.5406


class CurveParseError(ValueError):
    """Raised when a diffractogram curve cannot be parsed."""


@dataclass
class CurveData:
    """In-memory 1D diffractogram curve."""

    two_theta: list[float]
    intensity: list[float]
    metadata: dict


def _read_float32_series(content, offset, count):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        content: Valor de entrada consumido por esta etapa do fluxo.
        offset: Valor de entrada consumido por esta etapa do fluxo.
        count: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    required = offset + (count * 4)
    if count < MIN_POINTS or required > len(content):
        raise CurveParseError("Arquivo .raw incompleto ou sem pontos suficientes.")
    values = struct.unpack("<" + ("f" * count), content[offset:required])
    if not all(math.isfinite(value) for value in values):
        raise CurveParseError("Intensidades contem valores nao finitos.")
    return [round(float(value), 6) for value in values]


def _build_axis(start, step, count):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        start: Valor de entrada consumido por esta etapa do fluxo.
        step: Valor de entrada consumido por esta etapa do fluxo.
        count: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not math.isfinite(start) or not math.isfinite(step) or step <= 0:
        raise CurveParseError("Metadados de 2theta invalidos no cabecalho .raw.")
    return [round(float(start + (index * step)), 6) for index in range(count)]


def parse_raw_bytes(content):
    """Parse supported Bruker/EVA-like RAW byte layouts."""
    if len(content) < 320:
        raise CurveParseError("Arquivo .raw muito pequeno para conter um difratograma.")
    magic = content[:4]
    if magic == b"RAW ":
        count = struct.unpack("<I", content[4:8])[0]
        start = struct.unpack("<f", content[8:12])[0]
        step = struct.unpack("<f", content[12:16])[0]
        data_offset = 156
        detected_format = "RAW legacy float32"
    elif content[:7] == b"RAW1.01":
        start = struct.unpack("<f", content[0x388:0x38C])[0]
        step = struct.unpack("<d", content[0x378:0x380])[0]
        data_offset = 0x3F8
        count = (len(content) - data_offset) // 4
        detected_format = "RAW1.01 float32"
    elif magic == b"RAW2":
        count = struct.unpack("<H", content[0x102:0x104])[0]
        start = struct.unpack("<f", content[0x108:0x10C])[0]
        step = struct.unpack("<f", content[0x10C:0x110])[0]
        data_offset = 0x13C
        detected_format = "RAW2 EVA float32"
    else:
        raise CurveParseError("Formato .raw nao reconhecido pela assinatura do arquivo.")
    intensity = _read_float32_series(content, data_offset, count)
    two_theta = _build_axis(start, step, count)
    return CurveData(
        two_theta=two_theta,
        intensity=intensity,
        metadata={
            "two_theta_start": round(float(two_theta[0]), 6),
            "two_theta_end": round(float(two_theta[-1]), 6),
            "step": round(float(step), 8),
            "points": count,
            "detected_format": detected_format,
            "data_offset": data_offset,
        },
    )


def _parse_number(value):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = str(value or "").strip().replace("\ufeff", "").strip('"').strip("'")
    if not text:
        return None
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    text = re.sub(r"[^0-9eE+\-.]", "", text)
    if not text or text in {"+", "-", ".", "+.", "-."}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _text_curve_columns(line):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        line: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = str(line or "").strip()
    if not text or text.startswith(("#", "//", ";")):
        return []
    tokens = re.split(r"[;\t, ]+", text)
    return [_parse_number(token) for token in tokens if str(token or "").strip()]


def parse_text_curve_bytes(content, filename=None):
    """Parse a simple two-column 2theta/intensity text curve."""
    try:
        text = content.decode("utf-8-sig")
        encoding = "utf-8-sig"
    except UnicodeDecodeError:
        text = content.decode("latin-1")
        encoding = "latin-1"
    rows = []
    skipped_rows = 0
    for line in text.splitlines():
        values = [value for value in _text_curve_columns(line) if value is not None]
        if len(values) < 2:
            skipped_rows += 1
            continue
        rows.append((float(values[0]), float(values[1])))
    rows = [(x, y) for x, y in rows if math.isfinite(x) and math.isfinite(y)]
    if len(rows) < MIN_POINTS:
        raise CurveParseError("Arquivo tabular sem pontos suficientes de 2theta/intensidade.")
    if not all(rows[index][0] < rows[index + 1][0] for index in range(len(rows) - 1)):
        raise CurveParseError("Eixo 2theta do arquivo tabular precisa estar em ordem crescente.")
    two_theta = [round(row[0], 6) for row in rows]
    intensity = [round(row[1], 6) for row in rows]
    steps = [two_theta[index + 1] - two_theta[index] for index in range(len(two_theta) - 1)]
    step = sorted(steps)[len(steps) // 2] if steps else None
    return CurveData(
        two_theta=two_theta,
        intensity=intensity,
        metadata={
            "two_theta_start": round(float(two_theta[0]), 6),
            "two_theta_end": round(float(two_theta[-1]), 6),
            "step": round(float(step), 8) if step else None,
            "points": len(two_theta),
            "detected_format": "text two-column diffractogram",
            "parser_format": "text_curve",
            "text_encoding": encoding,
            "skipped_text_rows": skipped_rows,
            "original_filename": Path(filename).name if filename else None,
        },
    )


def parse_curve_bytes(content, filename=None):
    """Parse an uploaded diffractogram by extension, with RAW/text fallbacks."""
    suffix = Path(filename or "").suffix.lower()
    if suffix == ".raw":
        parsed = parse_raw_bytes(content)
        parsed.metadata["parser_format"] = "raw"
        return parsed
    if suffix in SUPPORTED_TEXT_CURVE_EXTENSIONS:
        return parse_text_curve_bytes(content, filename=filename)
    try:
        parsed = parse_raw_bytes(content)
        parsed.metadata["parser_format"] = "raw"
        return parsed
    except CurveParseError:
        return parse_text_curve_bytes(content, filename=filename)


def normalize_max(values):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        values: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    maximum = max([float(value) for value in values or [] if math.isfinite(float(value))] or [0.0])
    if maximum <= 0:
        return [0.0 for _ in values or []], 0.0
    return [max(float(value), 0.0) / maximum for value in values or []], maximum


def normalize_area(x_values, y_values):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        x_values: Valor de entrada consumido por esta etapa do fluxo.
        y_values: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    values = [max(float(value), 0.0) for value in y_values or []]
    if len(values) < 2:
        return values, 0.0
    area = 0.0
    xs = [float(value) for value in x_values or []]
    for index in range(min(len(xs), len(values)) - 1):
        area += abs(xs[index + 1] - xs[index]) * ((values[index] + values[index + 1]) / 2.0)
    if area <= 0:
        return [0.0 for _ in values], 0.0
    return [value / area for value in values], area


def calculate_d_spacing(two_theta, wavelength=CU_K_ALPHA_WAVELENGTH):
    """Convert 2theta to d-spacing with Bragg's law."""
    theta = math.radians(float(two_theta) / 2.0)
    sine = math.sin(theta)
    if sine <= 0:
        return None
    return float(wavelength) / (2.0 * sine)


def calculate_two_theta(d_spacing, wavelength=CU_K_ALPHA_WAVELENGTH):
    """Convert d-spacing to 2theta with Bragg's law."""
    value = float(d_spacing)
    if value <= 0:
        return None
    ratio = float(wavelength) / (2.0 * value)
    if ratio <= 0 or ratio > 1:
        return None
    return math.degrees(2.0 * math.asin(ratio))
