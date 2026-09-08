from pathlib import Path

import pytest

from argiloteca_drx.diagnostics.chapter7_knowledge import REFLECTION_TABLES
from argiloteca_drx.diagnostics.chapter7_rule_executor import execute_chapter7_rules
from argiloteca_drx.diagnostics.chapter8_mixed_layer.ordering_classifier import classify_ordering
from argiloteca_drx.diagnostics.chapter8_mixed_layer.superstructure_detector import detect_superstructures
from argiloteca_drx.diagnostics.octahedral_classifier import classify_octahedral
from argiloteca_drx.diagnostics.rules_catalog_loader import RulesCatalogError, load_rules_catalog


CATALOG = Path(__file__).parents[1] / "argiloteca_drx" / "diagnostics" / "rules_catalog.yaml"


def _peak(d, intensity=100):
    return {"d": d, "d_A": d, "intensity": intensity}


def test_table_7_3_preserves_source_values_and_separate_tolerance():
    rows = REFLECTION_TABLES["table_7_3_sepiolite_palygorskite"]["rows"]
    sepiolite = [row for row in rows if row["mineral"] == "sepiolite"]
    assert [row["source_value_angstrom"] for row in sepiolite] == [12.8, 7.6, 5.1, 4.4, 3.77, 3.35]
    assert sepiolite[0]["operational_tolerance_angstrom"] == 0.5


def test_table_7_6_is_non_basal_random_powder_data():
    table = REFLECTION_TABLES["table_7_6_kaolin_polytypes"]
    assert table["preparation"] == "random_powder"
    assert {row["mineral"] for row in table["rows"]} == {"kaolinite", "dickite", "nacrite", "metahalloysite"}
    assert not any(row.get("reflection") in {"001", "002"} for row in table["rows"])
    assert not any(row["source_value_angstrom"] in {7.15, 3.57} for row in table["rows"])


def test_table_7_4_keeps_source_points_distinct_from_operational_tolerance():
    table = REFLECTION_TABLES["table_7_4_d060"]
    saponite = next(row for row in table["rows"] if row["mineral"] == "saponite")
    assert saponite["source_value_angstrom"] == 1.520
    assert saponite["source_range_angstrom"] is None
    assert table["operational_tolerance_angstrom"] == 0.015


def test_d060_returns_nonexclusive_saponite_nontronite_compatibilities():
    result = classify_octahedral(1.5205, tolerance=0.002)
    names = {row["mineral"] for row in result["compatibilities"]}
    assert {"saponite", "nontronite"} <= names
    assert result["octahedral_type"] == "ambiguous"


def test_d060_warns_about_quartz_interference():
    result = classify_octahedral(1.542)
    assert any("quartz" in warning.lower() and "1.82" in warning for warning in result["warnings"])


def test_rules_never_emit_automatic_confirmation():
    result = execute_chapter7_rules(
        {"N": [_peak(14.2), _peak(7.1), _peak(4.74), _peak(3.55)], "G": [_peak(14.2)], "C": [_peak(14.2)]},
        behavior={"behaviors": []},
    )
    assert result["candidates"]
    assert all(row["confidence"] != "confirmed_by_rules" for row in result["candidates"])
    assert result["candidates"][0]["confidence"] == "strong_candidate_by_rules"


def test_single_long_period_peak_does_not_assign_ordering():
    superstructures = detect_superstructures({"N": [_peak(24.0)]})
    result = classify_ordering({}, superstructures)
    assert result["ordering_state"] == "unknown"
    assert "at_least_three_00l_reflections" in result["missing_requirements"]


def test_invalid_yaml_fails_explicitly(tmp_path):
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("version: [", encoding="utf-8")
    load_rules_catalog.cache_clear()
    with pytest.raises(RulesCatalogError):
        load_rules_catalog(invalid)


def test_canonical_yaml_is_executable_and_has_corrected_sepiolite():
    load_rules_catalog.cache_clear()
    catalog = load_rules_catalog(CATALOG)
    assert catalog["catalog_status"] == "executable_canonical_catalog"
    assert catalog["named_ranges"]["sepiolite_12a"]["source_value_angstrom"] == 12.8
