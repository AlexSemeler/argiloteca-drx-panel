"""Contratos de modularização, radiação explícita e acessibilidade DRX."""

from __future__ import annotations

import math
import unittest
from pathlib import Path

from argiloteca.services import drx as legacy_drx
from argiloteca.services.drx_ngc import (
    build_ngc_backend_grouping_contract as modular_grouping,
    build_ngc_workflow as modular_workflow,
)
from argiloteca.services.drx_ngc_workflow import (
    build_ngc_backend_grouping_contract as legacy_grouping,
    build_ngc_workflow as legacy_workflow,
)
from argiloteca.services.drx_parsing import parse_diffractogram_bytes as modular_parse
from argiloteca.services.drx_routes import DRX_PUBLIC_ENDPOINTS
from argiloteca_drx_core.radiation import RadiationSpec, resolve_radiation


ROOT = Path(__file__).resolve().parents[1]


class RadiationSpecContractsTest(unittest.TestCase):
    def test_missing_or_unknown_radiation_stays_unavailable(self):
        self.assertFalse(resolve_radiation().available)
        self.assertFalse(resolve_radiation("").available)
        unknown = resolve_radiation("desconhecida")
        self.assertFalse(unknown.available)
        self.assertTrue(unknown.warnings)

    def test_explicit_cuka_and_numeric_wavelength_are_auditable(self):
        cuka = resolve_radiation("CuKa", source="user_param")
        numeric = resolve_radiation(1.5418, source="metadata", provenance={"file": "a.raw"})

        self.assertAlmostEqual(cuka.wavelength_angstrom, 1.5406)
        self.assertEqual(cuka.source, "user_param")
        self.assertEqual(numeric.wavelength_angstrom, 1.5418)
        self.assertEqual(numeric.provenance["file"], "a.raw")

    def test_invalid_numeric_wavelength_is_unavailable(self):
        for value in (0, -1, math.nan, math.inf):
            with self.subTest(value=value):
                self.assertFalse(resolve_radiation(value).available)

    def test_spec_is_immutable_and_serializable(self):
        spec = RadiationSpec(label="CuKa", wavelength_angstrom=1.5406, source="configuration")
        self.assertEqual(spec.to_dict()["unit"], "angstrom")
        with self.assertRaises((AttributeError, TypeError)):
            spec.label = "MoKa"


class ModularAccessibilitySourceContractsTest(unittest.TestCase):
    def read(self, relative):
        return ROOT.joinpath(relative).read_text(encoding="utf-8")

    def test_public_cif_paths_do_not_default_to_cuka(self):
        views = self.read("argiloteca/views.py")
        simulation = self.read("argiloteca/services/drx_cif_simulation.py")
        engine = self.read("argiloteca/services/drx_science_engine.py")

        self.assertNotIn('or "CuKa"', views)
        self.assertNotIn('value or "CuKa"', simulation)
        self.assertNotIn('wavelength="CuKa"', engine)

    def test_public_json_responses_do_not_embed_tracebacks(self):
        views = self.read("argiloteca/views.py")
        self.assertNotIn('"traceback": traceback.format_exc()', views)

    def test_accessible_labels_dialogs_live_regions_and_chart_contract(self):
        template = self.read("argiloteca/templates/semantic-ui/argiloteca/drx_comparacao.html")
        css = self.read("argiloteca/static/css/drx-comparacao.css")
        script = self.read("argiloteca/static/js/drx-comparacao.js")

        for token in (
            'for="argilo-drx-raw-search"',
            'for="argilo-drx-preparation"',
            'role="dialog"',
            'aria-modal="true"',
            'aria-labelledby="argilo-drx-raw-picker-title"',
            'data-role="chart-description"',
            'data-role="chart-table"',
            'aria-live="polite"',
        ):
            self.assertIn(token, template)
        self.assertIn(":focus-visible", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn('event.key === "Escape"', script)
        self.assertIn('event.key === "ArrowLeft"', script)
        self.assertIn("restoreDialogFocus", script)

    def test_modular_facades_exist(self):
        for relative in (
            "argiloteca/services/drx_parsing.py",
            "argiloteca/services/drx_processing.py",
            "argiloteca/services/drx_ngc/grouping.py",
            "argiloteca/services/drx_ngc/interpretation.py",
            "argiloteca/services/drx_ngc/evidence.py",
            "argiloteca/services/drx_ngc/source_rules.py",
            "argiloteca/services/drx_routes.py",
        ):
            self.assertTrue(ROOT.joinpath(relative).is_file(), relative)

    def test_legacy_and_modular_parser_are_equivalent(self):
        rows = "\n".join(f"{5 + index * 0.1:.1f} {100 + index}" for index in range(12)).encode()
        legacy = legacy_drx.parse_diffractogram_bytes(rows, filename="sample.xy")
        modular = modular_parse(rows, filename="sample.xy")

        self.assertEqual(legacy.two_theta, modular.two_theta)
        self.assertEqual(legacy.intensity, modular.intensity)
        self.assertEqual(legacy.metadata, modular.metadata)

    def test_legacy_and_modular_ngc_facades_are_equivalent(self):
        items = [
            {"sample_base": "A", "sample_code": "A N", "preparation": "natural", "peaks": [{"d_angstrom": 14.2}]},
            {"sample_base": "A", "sample_code": "A G", "preparation": "glicolado", "peaks": [{"d_angstrom": 17.0}]},
            {"sample_base": "A", "sample_code": "A C", "preparation": "calcinado", "peaks": [{"d_angstrom": 10.0}]},
        ]
        self.assertEqual(modular_grouping(items), legacy_grouping(items))
        self.assertEqual(modular_workflow(items), legacy_workflow(items))

    def test_route_inventory_covers_public_drx_handlers(self):
        views = self.read("argiloteca/views.py")
        for endpoint in DRX_PUBLIC_ENDPOINTS:
            self.assertIn(f"def {endpoint}", views)


if __name__ == "__main__":
    unittest.main()
