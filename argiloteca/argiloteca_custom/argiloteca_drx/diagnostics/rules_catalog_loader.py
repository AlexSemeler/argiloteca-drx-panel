"""Strict runtime loader for the versioned DRX rules catalog."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any


class RulesCatalogError(RuntimeError):
    """Raised when the canonical rules catalog cannot be trusted."""


_REQUIRED_TOP_LEVEL = {
    "version",
    "policy",
    "catalog_status",
    "source_scope",
    "units",
    "global_policy",
    "preparations",
    "named_ranges",
    "peak_sets",
    "rules",
}


def _yaml_module():
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - deployment dependency
        raise RulesCatalogError(
            "PyYAML>=6.0 is required to load rules_catalog.yaml; no fallback rules are allowed."
        ) from exc
    return yaml


def validate_rules_catalog(catalog: Any) -> dict:
    """Validate the executable subset used by the N/G/C workflow."""
    if not isinstance(catalog, dict):
        raise RulesCatalogError("rules catalog root must be a mapping")
    missing = sorted(_REQUIRED_TOP_LEVEL - set(catalog))
    if missing:
        raise RulesCatalogError(f"rules catalog is missing required keys: {missing}")
    if catalog.get("catalog_status") != "executable_canonical_catalog":
        raise RulesCatalogError("rules catalog is not marked executable_canonical_catalog")
    if not isinstance(catalog.get("named_ranges"), dict) or not catalog["named_ranges"]:
        raise RulesCatalogError("named_ranges must be a non-empty mapping")
    if not isinstance(catalog.get("peak_sets"), dict) or not catalog["peak_sets"]:
        raise RulesCatalogError("peak_sets must be a non-empty mapping")
    for name, row in catalog["named_ranges"].items():
        if not isinstance(row, dict):
            raise RulesCatalogError(f"named range {name!r} must be a mapping")
        try:
            d_min, d_max = float(row["d_min"]), float(row["d_max"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RulesCatalogError(f"named range {name!r} needs numeric d_min/d_max") from exc
        if d_min > d_max:
            raise RulesCatalogError(f"named range {name!r} has d_min > d_max")
    for name, peak_set in catalog["peak_sets"].items():
        ranges = peak_set.get("ranges") if isinstance(peak_set, dict) else None
        if not isinstance(ranges, list) or not ranges:
            raise RulesCatalogError(f"peak set {name!r} needs a non-empty ranges list")
        unknown = [item for item in ranges if item not in catalog["named_ranges"]]
        if unknown:
            raise RulesCatalogError(f"peak set {name!r} references unknown ranges: {unknown}")
    return catalog


@lru_cache(maxsize=4)
def load_rules_catalog(path: str | Path) -> dict:
    """Safely load and validate the canonical YAML; never silently fall back."""
    catalog_path = Path(path)
    try:
        raw = catalog_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RulesCatalogError(f"cannot read rules catalog: {catalog_path}") from exc
    try:
        catalog = _yaml_module().safe_load(raw)
    except Exception as exc:
        raise RulesCatalogError(f"invalid YAML rules catalog: {catalog_path}: {exc}") from exc
    return validate_rules_catalog(catalog)


def candidate_peak_windows(catalog: dict) -> dict[str, list[dict]]:
    """Build runtime windows from named ranges without parsing YAML text."""
    source_by_rule = {}
    for rule in catalog.get("rules", []):
        if not isinstance(rule, dict):
            continue
        rule_id = rule.get("id") or rule.get("rule_id")
        locators = rule.get("source_locator") or rule.get("source_locators") or []
        if isinstance(locators, dict):
            locators = [locators]
        if rule_id and locators:
            source_by_rule[rule_id] = dict(locators[0])
        for locator in locators:
            source_rule = locator.get("source_rule") if isinstance(locator, dict) else None
            if source_rule:
                source_by_rule[source_rule] = dict(locator)
    result = {}
    for candidate, peak_set in catalog["peak_sets"].items():
        rows = []
        for range_name in peak_set["ranges"]:
            source_range = catalog["named_ranges"][range_name]
            rule_id = source_range.get("source_rule")
            source = dict(source_by_rule.get(rule_id, {}))
            source["rule_id"] = rule_id
            row = {
                "d_min": float(source_range["d_min"]),
                "d_max": float(source_range["d_max"]),
                "label": range_name.replace("_", " "),
                "source": source,
            }
            for key in ("source_value_angstrom", "operational_tolerance_angstrom", "tolerance_basis"):
                if key in source_range:
                    row[key] = source_range[key]
            rows.append(row)
        result[candidate] = rows
    return result
