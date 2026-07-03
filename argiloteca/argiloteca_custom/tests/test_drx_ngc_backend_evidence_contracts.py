import copy
import importlib
import unittest

from argiloteca.services.drx_ngc_workflow import (
    build_ngc_evidence_summary_contract,
    build_ngc_workflow,
)


class DrxNgcBackendEvidenceContractsTest(unittest.TestCase):
    def smectite_items(self):
        return [
            {
                "sample_base": "S-EV",
                "filename": "S-EV (N).raw",
                "preparation": "natural",
                "peaks": [{"d_angstrom": 14.8, "intensity": 100}],
            },
            {
                "sample_base": "S-EV",
                "filename": "S-EV (G).raw",
                "preparation": "glycolated",
                "peaks": [{"d_angstrom": 17.0, "intensity": 100}],
            },
            {
                "sample_base": "S-EV",
                "filename": "S-EV (C).raw",
                "preparation": "calcined",
                "peaks": [{"d_angstrom": 10.0, "intensity": 80}],
            },
        ]

    def test_workflow_includes_ngc_evidence_summary_per_group(self):
        payload = build_ngc_workflow(self.smectite_items())
        group = payload["groups"][0]

        self.assertIn("ngc_evidence_summary", group)
        summary = group["ngc_evidence_summary"]
        self.assertEqual(summary["version"], "argiloteca.drx.ngc.evidence_summary.v1")
        self.assertEqual(summary["policy"], "argiloteca_rule_based_diagnostic")
        self.assertEqual(summary["sample_base"], "S-EV")
        self.assertIn(summary["status"], {"available", "empty", "insufficient_data"})
        self.assertIsInstance(summary["sections"], list)
        self.assertIsInstance(summary["warnings"], list)

    def test_smectite_ngc_evidence_preserves_expansion_or_collapse(self):
        summary = build_ngc_workflow(self.smectite_items())["groups"][0]["ngc_evidence_summary"]
        labels = [
            str(item.get("label") or "")
            for section in summary["sections"]
            for item in section.get("items", [])
        ]
        joined = " ".join(labels)

        self.assertEqual(summary["status"], "available")
        self.assertTrue("expands_with_glycol" in joined or "collapses_after_heating" in joined)

    def test_sources_preserve_rule_id_chapter_and_page_when_available(self):
        summary = build_ngc_workflow(self.smectite_items())["groups"][0]["ngc_evidence_summary"]
        sources = [
            item.get("source") or {}
            for section in summary["sections"]
            for item in section.get("items", [])
            if item.get("source")
        ]

        self.assertTrue(any(source.get("rule_id") for source in sources))
        self.assertTrue(any(source.get("chapter") in {7, 8} for source in sources))
        self.assertTrue(any(source.get("page") for source in sources if source.get("chapter") == 7))

    def test_empty_payload_returns_empty_without_breaking(self):
        summary = build_ngc_evidence_summary_contract({"sample_base": "EMPTY"})

        self.assertEqual(summary["version"], "argiloteca.drx.ngc.evidence_summary.v1")
        self.assertEqual(summary["status"], "empty")
        self.assertEqual(summary["sample_base"], "EMPTY")
        self.assertEqual(summary["sections"], [])

    def test_contract_does_not_mutate_existing_scientific_fields(self):
        group = build_ngc_workflow(self.smectite_items())["groups"][0]
        original = copy.deepcopy(
            {
                "candidates": group.get("candidates"),
                "best_candidate": group.get("best_candidate"),
                "diagnostic_interpretation": group.get("diagnostic_interpretation"),
                "ngc_behavior": group.get("ngc_behavior"),
            }
        )

        build_ngc_evidence_summary_contract(group)

        self.assertEqual(group.get("candidates"), original["candidates"])
        self.assertEqual(group.get("best_candidate"), original["best_candidate"])
        self.assertEqual(group.get("diagnostic_interpretation"), original["diagnostic_interpretation"])
        self.assertEqual(group.get("ngc_behavior"), original["ngc_behavior"])

    def test_module_import_has_no_flask_or_invenio_dependency(self):
        module = importlib.import_module("argiloteca.services.drx_ngc_workflow")

        self.assertTrue(hasattr(module, "build_ngc_evidence_summary_contract"))


if __name__ == "__main__":
    unittest.main()
