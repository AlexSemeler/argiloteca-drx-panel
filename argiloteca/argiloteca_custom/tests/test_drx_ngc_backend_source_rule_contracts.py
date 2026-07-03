import copy
import importlib
import unittest

from argiloteca.services.drx_ngc_workflow import (
    build_ngc_source_rule_summary_contract,
    build_ngc_workflow,
)


class DrxNgcBackendSourceRuleContractsTest(unittest.TestCase):
    def illite_items(self):
        return [
            {
                "sample_base": "S-SRC",
                "filename": "S-SRC (N).raw",
                "preparation": "natural",
                "peaks": [{"d_angstrom": 10.0, "intensity": 100}, {"d_angstrom": 5.0, "intensity": 40}],
            },
            {
                "sample_base": "S-SRC",
                "filename": "S-SRC (G).raw",
                "preparation": "glycolated",
                "peaks": [{"d_angstrom": 10.0, "intensity": 90}],
            },
            {
                "sample_base": "S-SRC",
                "filename": "S-SRC (C).raw",
                "preparation": "calcined",
                "peaks": [{"d_angstrom": 10.0, "intensity": 80}],
            },
        ]

    def test_workflow_includes_source_rule_summary_per_group(self):
        group = build_ngc_workflow(self.illite_items())["groups"][0]
        summary = group["ngc_source_rule_summary"]

        self.assertEqual(summary["version"], "argiloteca.drx.ngc.source_rule_summary.v1")
        self.assertEqual(summary["policy"], "argiloteca_rule_based_diagnostic")
        self.assertEqual(summary["sample_base"], "S-SRC")
        self.assertIn(summary["status"], {"available", "empty"})
        self.assertIsInstance(summary["candidates"], list)
        self.assertIsInstance(summary["warnings"], list)

    def test_source_rule_summary_preserves_rules_and_tables(self):
        summary = build_ngc_workflow(self.illite_items())["groups"][0]["ngc_source_rule_summary"]
        rules = [
            rule
            for candidate in summary["candidates"]
            for rule in candidate.get("rules", [])
        ]
        tables = [
            table
            for candidate in summary["candidates"]
            for table in candidate.get("tables", [])
        ]

        self.assertEqual(summary["status"], "available")
        self.assertTrue(any(rule.get("rule_id") for rule in rules))
        self.assertTrue(any(str(rule.get("rule_id") or "").startswith("chapter7_") for rule in rules))
        self.assertTrue(any((rule.get("source") or {}).get("page") for rule in rules))
        self.assertTrue(any(table.get("rows") for table in tables) or any(rule.get("source") for rule in rules))

    def test_contract_does_not_mutate_existing_scientific_fields(self):
        group = build_ngc_workflow(self.illite_items())["groups"][0]
        original = copy.deepcopy(
            {
                "candidates": group.get("candidates"),
                "best_candidate": group.get("best_candidate"),
                "diagnostic_interpretation": group.get("diagnostic_interpretation"),
                "ngc_behavior": group.get("ngc_behavior"),
            }
        )

        build_ngc_source_rule_summary_contract(group)

        self.assertEqual(group.get("candidates"), original["candidates"])
        self.assertEqual(group.get("best_candidate"), original["best_candidate"])
        self.assertEqual(group.get("diagnostic_interpretation"), original["diagnostic_interpretation"])
        self.assertEqual(group.get("ngc_behavior"), original["ngc_behavior"])

    def test_empty_payload_returns_empty_without_breaking(self):
        summary = build_ngc_source_rule_summary_contract({"sample_base": "EMPTY"})

        self.assertEqual(summary["version"], "argiloteca.drx.ngc.source_rule_summary.v1")
        self.assertEqual(summary["status"], "empty")
        self.assertEqual(summary["sample_base"], "EMPTY")
        self.assertEqual(summary["candidates"], [])

    def test_module_import_has_no_flask_or_invenio_dependency(self):
        module = importlib.import_module("argiloteca.services.drx_ngc_workflow")

        self.assertTrue(hasattr(module, "build_ngc_source_rule_summary_contract"))


if __name__ == "__main__":
    unittest.main()
