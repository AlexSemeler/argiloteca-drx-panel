"""Testes dos adaptadores de contrato DRX."""

from __future__ import annotations

import importlib
import sys
import unittest

from argiloteca_drx_core import Diffractogram, Peak, Sample
from argiloteca_drx_core.adapters import (
    diffractogram_from_payload,
    evidence_from_payload,
    mineral_hypothesis_from_payload,
    ngc_comparison_from_payload,
    peak_from_payload,
    peaks_from_payload,
    sample_from_payload,
    treatment_from_payload,
    xrd_file_from_payload,
)


class DrxModelAdaptersTest(unittest.TestCase):
    """Valida conversores puros sem acionar regras cientificas."""

    def test_treatment_from_payload_recognizes_root_values(self):
        self.assertEqual(treatment_from_payload({"preparation": "natural"}).to_dict(), {"code": "N", "label": "natural", "inference": "payload"})
        self.assertEqual(treatment_from_payload({"treatment": "glicolada"}).code, "G")
        self.assertEqual(treatment_from_payload({"treatment_label": "calcined"}).label, "calcined")

    def test_treatment_from_payload_recognizes_metadata_values(self):
        treatment = treatment_from_payload({"metadata": {"treatment": "G"}})

        self.assertEqual(treatment.code, "G")
        self.assertEqual(treatment.label, "glycolated")
        self.assertEqual(treatment.inference, "metadata")

    def test_sample_from_payload_uses_explicit_sample_base_and_record_id(self):
        sample = sample_from_payload({"metadata": {"sample_base": "VERDE", "record_id": "rec-1", "title": "Amostra"}})

        self.assertEqual(sample.sample_base, "VERDE")
        self.assertEqual(sample.record_id, "rec-1")
        self.assertEqual(sample.title, "Amostra")

    def test_xrd_file_from_payload_uses_original_filename_and_source_sha256(self):
        xrd_file = xrd_file_from_payload({"id": "file-1", "original_filename": "VERDE (N).raw", "source_sha256": "abc"})

        self.assertEqual(xrd_file.filename, "VERDE (N).raw")
        self.assertEqual(xrd_file.file_id, "file-1")
        self.assertEqual(xrd_file.sha256, "abc")

    def test_peak_from_payload_normalizes_aliases(self):
        peak = peak_from_payload(
            {
                "peak_index": 2,
                "center_2theta": "8,84",
                "d_spacing": "10.0",
                "intensity_abs": "120.5",
                "intensity_relative": "88",
                "fwhm": "0.2",
                "integrated_intensity": "22.4",
                "attribution_method": "advanced_als",
            }
        )

        self.assertEqual(peak.peak_id, 2)
        self.assertEqual(peak.two_theta_deg, 8.84)
        self.assertEqual(peak.d_angstrom, 10.0)
        self.assertEqual(peak.intensity, 120.5)
        self.assertEqual(peak.relative_intensity, 88.0)
        self.assertEqual(peak.fwhm_deg, 0.2)
        self.assertEqual(peak.area, 22.4)
        self.assertEqual(peak.method, "advanced_als")

    def test_peak_from_payload_does_not_calculate_d_from_two_theta(self):
        peak = peak_from_payload({"two_theta": 8.84})

        self.assertEqual(peak.two_theta_deg, 8.84)
        self.assertIsNone(peak.d_angstrom)

    def test_peaks_from_payload_prefers_peaks_before_advanced_peaks(self):
        payload = {
            "peaks": [{"peak_id": "p0", "two_theta": 1.0}],
            "advanced_peaks": [{"peak_id": "p1", "two_theta": 2.0}],
            "detected_peaks": [{"peak_id": "p2", "two_theta": 3.0}],
        }

        peaks = peaks_from_payload(payload)

        self.assertEqual([peak.peak_id for peak in peaks], ["p0"])

    def test_peaks_from_payload_uses_advanced_peaks_before_detected_peaks_when_peaks_absent(self):
        payload = {
            "advanced_peaks": [{"peak_id": "p1", "two_theta": 2.0}, "invalid"],
            "detected_peaks": [{"peak_id": "p2", "two_theta": 3.0}],
        }

        peaks = peaks_from_payload(payload)

        self.assertEqual([peak.peak_id for peak in peaks], ["p1"])

    def test_diffractogram_from_payload_preserves_arrays_with_none(self):
        curve = diffractogram_from_payload({"id": "d1", "twoTheta": [5.0, None, 5.04], "intensity": [10.0, None, 12.0]})

        self.assertEqual(curve.diffractogram_id, "d1")
        self.assertEqual(curve.two_theta, [5.0, None, 5.04])
        self.assertEqual(curve.intensity, [10.0, None, 12.0])

    def test_diffractogram_from_payload_reads_axis_mode_from_metadata_visualization(self):
        curve = diffractogram_from_payload(
            {
                "two_theta": [1.0],
                "intensity": [2.0],
                "metadata": {"visualization": {"axis_mode": "aligned", "source_points": 100, "payload_points": 1}},
            }
        )

        self.assertEqual(curve.axis_mode, "aligned")
        self.assertEqual(curve.source_points, 100)
        self.assertEqual(curve.payload_points, 1)

    def test_diffractogram_from_payload_does_not_assume_wavelength(self):
        curve = diffractogram_from_payload({"two_theta": [8.84], "intensity": [100.0]})

        self.assertIsNone(curve.wavelength_angstrom)

    def test_evidence_from_payload_accepts_source_as_source_rule(self):
        evidence = evidence_from_payload({"id": "ev-1", "type": "behavior", "explanation": "10 A persistente", "source": {"rule_id": "r1"}})

        self.assertEqual(evidence.evidence_id, "ev-1")
        self.assertEqual(evidence.kind, "behavior")
        self.assertEqual(evidence.message, "10 A persistente")
        self.assertEqual(evidence.source_rule["rule_id"], "r1")

    def test_mineral_hypothesis_from_payload_serializes_nested_evidence(self):
        hypothesis = mineral_hypothesis_from_payload(
            {
                "label": "illite_mica",
                "diagnostic_status": "detected",
                "evidences": [{"message": "10 A estavel", "source": {"rule_id": "chapter7_illite"}}],
            }
        )

        payload = hypothesis.to_dict()

        self.assertEqual(payload["mineral"], "illite_mica")
        self.assertEqual(payload["status"], "detected")
        self.assertEqual(payload["evidence_for"][0]["message"], "10 A estavel")
        self.assertTrue(payload["requires_specialist_validation"])

    def test_ngc_comparison_from_payload_serializes_candidates_as_hypotheses(self):
        comparison = ngc_comparison_from_payload(
            {
                "sample_base": "VERDE",
                "available_treatments": ["natural", "glycolated"],
                "evidence": [{"message": "trio incompleto"}],
                "candidates": [{"target": "smectite_group", "status": "possible"}],
            }
        )

        payload = comparison.to_dict()

        self.assertEqual(payload["sample_base"], "VERDE")
        self.assertEqual(payload["hypotheses"][0]["mineral"], "smectite_group")
        self.assertEqual(payload["evidence"][0]["message"], "trio incompleto")

    def test_adapters_import_without_scientific_or_web_dependencies(self):
        before = set(sys.modules)
        module = importlib.import_module("argiloteca_drx_core.adapters")
        after = set(sys.modules)
        newly_loaded = after - before

        self.assertTrue(hasattr(module, "peak_from_payload"))
        forbidden_roots = {"flask", "invenio_app", "invenio_records", "numpy", "scipy", "pandas"}
        self.assertFalse(forbidden_roots.intersection(newly_loaded))

    def test_package_exports_models_without_breaking_core_import(self):
        self.assertIs(Sample, importlib.import_module("argiloteca_drx_core.models").Sample)
        self.assertIs(Peak, importlib.import_module("argiloteca_drx_core.models").Peak)
        self.assertIs(Diffractogram, importlib.import_module("argiloteca_drx_core.models").Diffractogram)


if __name__ == "__main__":
    unittest.main()
