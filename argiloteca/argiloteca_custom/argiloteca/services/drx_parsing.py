"""Dependency-light DRX parsing boundary used by the web-service facade."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from argiloteca_drx_core.curves import (
    CurveParseError,
    parse_curve_bytes,
    parse_raw_bytes as parse_core_raw_bytes,
    parse_text_curve_bytes as parse_core_text_curve_bytes,
)


class RawParseError(ValueError):
    """Raised when a supported curve cannot be converted to a diffractogram."""


@dataclass
class DiffractogramData:
    two_theta: list[float]
    intensity: list[float]
    metadata: dict


def _adapt(operation, *args, **kwargs):
    try:
        parsed = operation(*args, **kwargs)
    except CurveParseError as exc:
        raise RawParseError(str(exc)) from exc
    return DiffractogramData(parsed.two_theta, parsed.intensity, parsed.metadata)


def parse_raw_bytes(content):
    return _adapt(parse_core_raw_bytes, content)


def parse_text_curve_bytes(content, filename=None):
    return _adapt(parse_core_text_curve_bytes, content, filename=filename)


def parse_diffractogram_bytes(content, filename=None):
    return _adapt(parse_curve_bytes, content, filename=filename)


def parse_raw_file(path):
    path = Path(path)
    return parse_raw_bytes(path.read_bytes())
