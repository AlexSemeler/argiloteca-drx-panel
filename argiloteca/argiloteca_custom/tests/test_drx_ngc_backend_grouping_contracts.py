"""Testes do contrato backend de agrupamento N/G/C."""

from __future__ import annotations

import importlib
import sys
import unittest

from argiloteca.services.drx_ngc_workflow import build_ngc_backend_grouping_contract, build_ngc_workflow


def _item(sample_base, preparation, filename, peak_count=1, source="test_fixture"):
    """Cria item sintetico compativel com o workflow N/G/C."""

    return {
        "id": filename,
        "sample_base": sample_base,
        "preparation": preparation,
        "filename": filename,
        "peaks": [{"d": 10.0 + index, "intensity": 100 - index} for index in range(peak_count)],
        "metadata": {"source": source},
    }


class DrxNgcBackendGroupingContractsTest(unittest.TestCase):
    """Valida agrupamento estrutural sem alterar interpretacao mineralogica."""

    def test_complete_ngc_items_generate_complete_group(self):
        payload = build_ngc_backend_grouping_contract(
            [
                _item("VERDE", "natural", "VERDE (N).raw"),
                _item("VERDE", "glicolado", "VERDE (G).raw"),
                _item("VERDE", "calcinado", "VERDE (C).raw"),
            ]
        )

        self.assertEqual(payload["status"], "available")
        self.assertEqual(len(payload["groups"]), 1)
        group = payload["groups"][0]
        self.assertEqual(group["sample_base"], "VERDE")
        self.assertTrue(group["is_complete_ngc"])
        self.assertEqual(group["available_treatments"], ["natural", "glycolated", "calcined"])

    def test_incomplete_ng_without_calcined_generates_incomplete_group(self):
        group = build_ngc_backend_grouping_contract(
            [_item("AZUL", "natural", "AZUL (N).raw"), _item("AZUL", "glicolado", "AZUL (G).raw")]
        )["groups"][0]

        self.assertFalse(group["is_complete_ngc"])
        self.assertEqual(group["available_treatments"], ["natural", "glycolated"])

    def test_preparations_appear_in_available_treatments(self):
        group = build_ngc_backend_grouping_contract(
            [
                _item("A", "natural", "A_N.raw"),
                _item("A", "glycolated", "A_G.raw"),
                _item("A", "heated", "A_C.raw"),
            ]
        )["groups"][0]

        self.assertEqual(group["available_treatments"], ["natural", "glycolated", "calcined"])

    def test_items_preserve_file_preparation_sample_peak_count_and_source(self):
        item = build_ngc_backend_grouping_contract([_item("S1", "natural", "S1 (N).raw", peak_count=3)])["groups"][0]["items"][0]

        self.assertEqual(item["filename"], "S1 (N).raw")
        self.assertEqual(item["preparation"], "natural")
        self.assertEqual(item["sample_base"], "S1")
        self.assertEqual(item["peak_count"], 3)
        self.assertEqual(item["metadata_source"], "test_fixture")

    def test_build_ngc_workflow_includes_backend_grouping(self):
        workflow = build_ngc_workflow(
            [
                _item("VERDE", "natural", "VERDE (N).raw"),
                _item("VERDE", "glicolado", "VERDE (G).raw"),
                _item("VERDE", "calcinado", "VERDE (C).raw"),
            ]
        )

        self.assertIn("backend_grouping", workflow)
        self.assertEqual(workflow["backend_grouping"]["version"], "argiloteca.drx.ngc.backend_grouping.v1")

    def test_backend_grouping_does_not_replace_mineralogical_interpretation(self):
        workflow = build_ngc_workflow(
            [
                _item("VERDE", "natural", "VERDE (N).raw"),
                _item("VERDE", "glicolado", "VERDE (G).raw"),
                _item("VERDE", "calcinado", "VERDE (C).raw"),
            ]
        )

        group = workflow["groups"][0]
        self.assertIn("candidates", group)
        self.assertIn("clay_interpretation", group)
        self.assertIn("diagnostic_interpretation", group)
        self.assertNotIn("candidates", workflow["backend_grouping"]["groups"][0])

    def test_item_without_sample_base_uses_conservative_key_and_warning(self):
        payload = build_ngc_backend_grouping_contract(
            [{"id": "orphan", "filename": "ORFA (N).raw", "preparation": "natural", "peaks": []}]
        )

        group = payload["groups"][0]
        self.assertEqual(group["sample_base"], "ORFA (N)")
        self.assertIn("sample_base ausente", group["warnings"][0])

    def test_import_does_not_load_flask_or_invenio_modules(self):
        before = set(sys.modules)
        module = importlib.import_module("argiloteca.services.drx_ngc_workflow")
        after = set(sys.modules)
        newly_loaded = after - before

        self.assertTrue(hasattr(module, "build_ngc_backend_grouping_contract"))
        forbidden_roots = {"flask", "invenio_app", "invenio_records", "invenio_rdm_records"}
        self.assertFalse(forbidden_roots.intersection(newly_loaded))

    def test_tests_do_not_depend_on_javascript(self):
        payload = build_ngc_backend_grouping_contract([_item("S", "natural", "S_N.raw")])

        self.assertEqual(payload["version"], "argiloteca.drx.ngc.backend_grouping.v1")
        self.assertNotIn("buildNgcGroups", str(payload))

    def test_contract_does_not_touch_instance_state(self):
        payload = build_ngc_backend_grouping_contract([_item("S", "natural", "S_N.raw")])

        self.assertNotIn("instance", str(payload).lower())


if __name__ == "__main__":
    unittest.main()
