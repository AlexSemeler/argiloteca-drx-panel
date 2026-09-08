"""Stable processing boundary while legacy implementations are migrated."""

from __future__ import annotations

from argiloteca_drx_core.curves import normalize_area, normalize_max
from argiloteca_drx_core.processing import (
    advanced_als_summary,
    compact_advanced_als_curve,
    process_advanced_als_curve,
)

__all__ = [
    "advanced_als_summary",
    "compact_advanced_als_curve",
    "normalize_area",
    "normalize_max",
    "process_advanced_als_curve",
]
