"""Testes de contrato para os modelos internos do pipeline DRX."""

from __future__ import annotations

import importlib
import sys
import unittest

from argiloteca_drx_core.models import (
    Diffractogram,
    Evidence,
    MineralHypothesis,
    NgcComparison,
    Peak,
    Sample,
    validate_axis_lengths,
)


class DrxPipelineContractsTest(unittest.TestCase):
    """Valida contratos serializaveis sem acionar regras cientificas."""

    def test_sample_to_dict_preserves_expected_fields(self):
        sample = Sample(sample_id="S1", sample_base="AM-01", record_id="rec-1", title=None)

        self.assertEqual(
            sample.to_dict(),
            {
                "sample_id": "S1",
                "sample_base": "AM-01",
                "record_id": "rec-1",
                "title": None,
            },
        )

    def test_peak_to_dict_preserves_none_and_floats(self):
        peak = Peak(
            peak_id=1,
            two_theta_deg=8.84,
            d_angstrom=None,
            intensity=120.5,
            relative_intensity=88.2,
            fwhm_deg=0.18,
            area=None,
            source="synthetic",
            method="contract_test",
        )

        payload = peak.to_dict()

        self.assertEqual(payload["peak_id"], 1)
        self.assertEqual(payload["two_theta_deg"], 8.84)
        self.assertIsNone(payload["d_angstrom"])
        self.assertIsNone(payload["area"])
        self.assertEqual(payload["fwhm_deg"], 0.18)

    def test_diffractogram_to_dict_preserves_arrays_with_none(self):
        curve = Diffractogram(
            diffractogram_id="drx-1",
            two_theta=[5.0, None, 5.04],
            intensity=[10.0, None, 12.0],
            axis_mode="raw",
            metadata={"source": "test"},
        )

        payload = curve.to_dict()

        self.assertEqual(payload["two_theta"], [5.0, None, 5.04])
        self.assertEqual(payload["intensity"], [10.0, None, 12.0])
        self.assertEqual(payload["axis_mode"], "raw")
        self.assertIsNone(payload["wavelength_angstrom"])

    def test_validate_axis_lengths_returns_valid_for_aligned_arrays(self):
        result = validate_axis_lengths([1.0, 2.0], [10.0, 20.0])

        self.assertTrue(result["valid"])
        self.assertEqual(result["two_theta_points"], 2)
        self.assertEqual(result["intensity_points"], 2)

    def test_validate_axis_lengths_returns_invalid_for_misaligned_arrays(self):
        result = validate_axis_lengths([1.0, 2.0, 3.0], [10.0])

        self.assertFalse(result["valid"])
        self.assertEqual(result["two_theta_points"], 3)
        self.assertEqual(result["intensity_points"], 1)
        self.assertIn("tamanhos diferentes", result["message"])

    def test_mineral_hypothesis_serializes_nested_evidence(self):
        evidence = Evidence(
            evidence_id="ev-1",
            kind="behavior",
            message="Pico basal expandiu apos glicolacao.",
            observed={"N": 14.2, "G": 17.0},
            source_rule={"rule_id": "chapter7_smectite_ngc"},
            limitations=["Hipotese auxiliar."],
        )
        hypothesis = MineralHypothesis(
            mineral="smectite_group",
            status="possible",
            confidence="medium",
            evidence_for=[evidence],
            source_rules=[{"rule_id": "chapter7_smectite_ngc"}],
        )

        payload = hypothesis.to_dict()

        self.assertEqual(payload["mineral"], "smectite_group")
        self.assertEqual(payload["evidence_for"][0]["message"], "Pico basal expandiu apos glicolacao.")
        self.assertTrue(payload["requires_specialist_validation"])

    def test_ngc_comparison_serializes_hypotheses_and_evidence(self):
        evidence = Evidence(message="10 A persistente.", source_rule={"rule_id": "chapter7_illite_glauconite_mica"})
        hypothesis = MineralHypothesis(mineral="illite_mica", status="detected", evidence_for=[evidence])
        comparison = NgcComparison(
            sample_base="AM-01",
            available_treatments=["natural", "glycolated", "calcined"],
            basal_trajectories=[{"from": "N", "to": "G", "delta_d": 0.0}],
            evidence=[evidence],
            hypotheses=[hypothesis],
        )

        payload = comparison.to_dict()

        self.assertEqual(payload["sample_base"], "AM-01")
        self.assertEqual(payload["hypotheses"][0]["mineral"], "illite_mica")
        self.assertEqual(payload["evidence"][0]["source_rule"]["rule_id"], "chapter7_illite_glauconite_mica")

    def test_models_do_not_assume_wavelength(self):
        curve = Diffractogram(two_theta=[8.84], intensity=[100.0])
        peak = Peak(two_theta_deg=8.84)

        self.assertIsNone(curve.wavelength_angstrom)
        self.assertIsNone(curve.to_dict()["wavelength_angstrom"])
        self.assertIsNone(peak.d_angstrom)

    def test_from_dict_recreates_peak_diffractogram_and_hypothesis(self):
        peak = Peak.from_dict({"peak_id": "p1", "two_theta_deg": "8.84", "d_angstrom": None})
        curve = Diffractogram.from_dict({"diffractogram_id": "d1", "two_theta": [1, None], "intensity": [2, None]})
        hypothesis = MineralHypothesis.from_dict(
            {
                "mineral": "kaolin_group",
                "status": "possible",
                "evidence_for": [{"message": "7 A observado."}],
            }
        )

        self.assertEqual(peak.two_theta_deg, 8.84)
        self.assertIsNone(peak.d_angstrom)
        self.assertEqual(curve.two_theta, [1, None])
        self.assertEqual(hypothesis.evidence_for[0].message, "7 A observado.")

    def test_module_imports_without_scientific_or_web_dependencies(self):
        before = set(sys.modules)
        module = importlib.import_module("argiloteca_drx_core.models")
        after = set(sys.modules)
        newly_loaded = after - before

        self.assertTrue(hasattr(module, "Diffractogram"))
        forbidden_roots = {"flask", "invenio_app", "invenio_records", "numpy", "scipy", "pandas"}
        self.assertFalse(forbidden_roots.intersection(newly_loaded))


if __name__ == "__main__":
    unittest.main()
