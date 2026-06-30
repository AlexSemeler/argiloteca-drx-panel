import unittest
import json
import subprocess
from pathlib import Path

from argiloteca.services.drx_ngc_workflow import build_ngc_workflow
from argiloteca_drx.diagnostics.ambiguity_rules import evaluate_ambiguities
from argiloteca_drx.diagnostics.chapter7_knowledge import get_chapter7_knowledge
from argiloteca_drx.diagnostics.diagnostic_decision_tree import interpret_ngc
from argiloteca_drx.diagnostics.empirical_builder import build_empirical_ranges
from argiloteca_drx.diagnostics.matcher import match_peak
from argiloteca_drx.diagnostics.octahedral_classifier import classify_octahedral
from argiloteca_drx.diagnostics.serializers import serialize_for_invenio


class DrxV3EngineTest(unittest.TestCase):
    @property
    def repo_root(self):
        return Path(__file__).resolve().parents[3]

    def read_project_file(self, relative_path):
        return (self.repo_root / relative_path).read_text(encoding="utf-8")

    def labels(self, payload):
        return [row["label"] for row in payload["diagnostic_interpretation"]["combined_candidates"]]

    def test_classic_kaolinite_ngc(self):
        payload = interpret_ngc({"N": [(7.16, 100), (3.57, 50)], "G": [(7.15, 90)], "C": []}, {"d060": 1.49})
        self.assertEqual(payload["diagnostic_interpretation"]["policy"], "argiloteca_rule_based_diagnostic")
        self.assertIn("kaolin_group", self.labels(payload))

    def test_kaolinite_strong_thermal_reduction_is_accepted(self):
        payload = interpret_ngc(
            {"N": [(7.16, 100), (3.57, 50)], "G": [(7.15, 90)], "C": [(7.14, 10)]},
            {"d060": 1.49},
        )
        self.assertIn("kaolin_group", self.labels(payload))
        behaviors = payload["diagnostic_interpretation"]["behavior_interpretation"]["behaviors"]
        self.assertIn("strongly_reduced_after_heating", behaviors)

    def test_halloysite_and_serpentine_ambiguity_at_7a(self):
        payload = interpret_ngc({"N": [(7.25, 100)], "G": [(7.24, 95)], "C": [(7.23, 80)]}, {"d060": 1.54})
        self.assertIn("serpentine", self.labels(payload))
        windows = [row["window"] for row in payload["diagnostic_interpretation"]["ambiguities"]]
        self.assertIn("7 A", windows)

    def test_illite_mica_and_biotite_competitor(self):
        payload = interpret_ngc(
            {"N": [(10.0, 100), (5.0, 35), (3.34, 20)], "G": [(10.0, 95)], "C": [(10.0, 90)]},
            {"d060": 1.54},
        )
        labels = self.labels(payload)
        self.assertIn("illite_mica", labels)
        self.assertIn("biotite", labels)

    def test_chlorite_trioctahedral_and_dioctahedral(self):
        tri = interpret_ngc(
            {"N": [(14.2, 100), (7.1, 60), (4.72, 40), (3.53, 35)], "G": [(14.2, 80)], "C": [(14.1, 90)]},
            {"d060": 1.54},
        )
        dio = interpret_ngc({"N": [(14.2, 100), (7.1, 60)], "G": [(14.2, 80)], "C": [(14.1, 90)]}, {"d060": 1.50})
        self.assertIn("chlorite", self.labels(tri))
        self.assertIn("dioctahedral_chlorite", self.labels(dio))

    def test_smectite_montmorillonite_saponite_stevensite(self):
        dio = interpret_ngc({"N": [(14.8, 100)], "G": [(17.0, 100)], "C": [(10.0, 80)]}, {"d060": 1.50})
        tri = interpret_ngc(
            {"N": [(14.8, 100)], "G": [(17.0, 100)], "C": [(10.0, 80)]},
            {"d060": 1.54, "context": ["presalt"], "chemistry": {"Mg": "high"}},
        )
        self.assertIn("montmorillonite_or_nontronite", self.labels(dio))
        self.assertIn("stevensite", self.labels(tri))

    def test_kerolite_sepiolite_palygorskite(self):
        kerolite = interpret_ngc({"N": [(9.42, 100)], "G": [(9.44, 90)], "C": [(9.40, 80)]}, {"d060": 1.54, "context": ["presalt"]})
        sepiolite = interpret_ngc({"N": [(12.2, 100)], "G": [(12.2, 90)], "C": []}, {"morphology": ["fibrous"]})
        palygorskite = interpret_ngc({"N": [(10.4, 100)], "G": [(10.4, 90)], "C": []}, {"morphology": ["fibrous"]})
        self.assertIn("kerolite", self.labels(kerolite))
        self.assertIn("sepiolite", self.labels(sepiolite))
        self.assertIn("palygorskite", self.labels(palygorskite))

    def test_corrensite_and_ks_mixed_layers(self):
        corrensite = interpret_ngc({"N": [(29.0, 100), (14.5, 80)], "G": [(31.5, 90)], "C": [(24.0, 60)]}, {"d060": 1.54})
        ks = interpret_ngc(
            {"N": [(9.45, 100)], "G": [(9.45, 40), (17.0, 80)], "C": [(10.0, 60)]},
            {"context": ["presalt"], "chemistry": {"Mg": "high"}, "d060": 1.54},
        )
        self.assertIn("corrensite", self.labels(corrensite))
        self.assertIn("kerolite_stevensite_mixed_layer", self.labels(ks))

    def test_ambiguity_rules(self):
        ambiguities = evaluate_ambiguities({"N": [{"d": 3.34}, {"d": 14.2}, {"d": 12.2}, {"d": 10.0}, {"d": 7.1}]})
        self.assertEqual({"3.33-3.34 A", "14 A", "12 A", "10 A", "7 A"}, {row["window"] for row in ambiguities})

    def test_invalid_and_incomplete_data_blocks_high_confidence(self):
        payload = interpret_ngc({"N": [(14.8, 100)]})
        scores = payload["diagnostic_interpretation"]["confidence_scores"]
        for value in scores.values():
            self.assertNotEqual(value["confidence"], "high")

    def test_empirical_builder(self):
        rows = [
            {"sample_id": "A", "mineral_id": "kerolite", "family": "talc_kerolite_group", "preparation": "natural", "peak_id": "001", "d_spacing": 9.42, "source_record_id": "rec1", "validated_by": "spec", "validation_status": "accepted"},
            {"sample_id": "B", "mineral_id": "kerolite", "family": "talc_kerolite_group", "preparation": "natural", "peak_id": "001", "d_spacing": 9.44, "source_record_id": "rec2", "validated_by": "spec", "validation_status": "accepted"},
            {"sample_id": "C", "mineral_id": "kerolite", "family": "talc_kerolite_group", "preparation": "natural", "peak_id": "001", "d_spacing": 99, "source_record_id": "rec3", "validated_by": "spec", "validation_status": "rejected"},
        ]
        built = build_empirical_ranges(rows, min_samples=5)
        stats = built["ranges"]["kerolite"]["001"]["natural"]
        self.assertEqual(stats["n"], 2)
        self.assertEqual(stats["confidence"], "low")
        self.assertIn("provenance_hash", stats)

    def test_matcher_serializer_and_workflow_integration(self):
        match = match_peak({"d": 9.42, "intensity": 100}, source="all")
        self.assertIn("kerolite", match["combined_candidates"])
        payload = interpret_ngc({"N": [(14.8, 100)], "G": [(17.0, 100)], "C": [(10.0, 80)]}, {"d060": 1.54})
        exported = serialize_for_invenio(payload["diagnostic_interpretation"])
        self.assertIn("argiloteca:d_rx_diagnostic", exported)
        self.assertIn("source_rule_index", exported["argiloteca:d_rx_diagnostic"])
        workflow = build_ngc_workflow([
            {"sample_base": "S1", "preparation": "natural", "peaks": [{"d_spacing": 14.8, "intensity": 100}]},
            {"sample_base": "S1", "preparation": "glycolated", "peaks": [{"d_spacing": 17.0, "intensity": 100}]},
            {"sample_base": "S1", "preparation": "calcined", "peaks": [{"d_spacing": 10.0, "intensity": 80}]},
        ])
        self.assertEqual(workflow["groups"][0]["diagnostic_interpretation"]["policy"], "argiloteca_rule_based_diagnostic")

    def test_chapter7_knowledge_base_is_traceable(self):
        knowledge = get_chapter7_knowledge()
        self.assertEqual(knowledge["source"]["policy"], "argiloteca_rule_based_diagnostic")
        self.assertIn("chapter7_chlorite_ool", {row["rule_id"] for row in knowledge["diagnostic_rules"]})
        for rule in knowledge["diagnostic_rules"]:
            self.assertIn("source", rule)
            self.assertIn("page", rule["source"])
        self.assertIn("chlorite", knowledge["mineral_profiles"])
        required_tables = {
            "table_7_8a_silica_minerals",
            "table_7_8b_low_quartz",
            "table_7_9_feldspars",
            "table_7_10_zeolites",
            "table_7_11a_rhombohedral_carbonates",
            "table_7_11b_orthorhombic_carbonates_vaterite",
            "table_7_12_apatite_pyrite_jarosite",
            "table_7_13_sulfates",
            "table_7_14_oxides_hydroxides_anatase",
            "table_7_15_heat_treated_oxides",
        }
        self.assertTrue(required_tables.issubset(set(knowledge["tables"])))
        for table_id in required_tables:
            self.assertGreater(len(knowledge["tables"][table_id]["rows"]), 0)

    def test_interpretation_exposes_source_tables_for_panel(self):
        payload = interpret_ngc({"N": [(12.0, 100)], "G": [(12.0, 95)], "C": [(12.0, 90)]}, {})
        interpretation = payload["diagnostic_interpretation"]
        self.assertIn("source_reflection_tables", interpretation)
        self.assertIn("table_7_3_sepiolite_palygorskite", interpretation["source_reflection_tables"])
        serialized = serialize_for_invenio(interpretation)["argiloteca:d_rx_diagnostic"]
        self.assertIn("source_reflection_tables", serialized)
        self.assertGreater(len(serialized["source_reflection_tables"]["table_7_3_sepiolite_palygorskite"]["rows"]), 0)

    def test_panel_source_rule_can_render_table_rows(self):
        source = self.read_project_file("argiloteca/argiloteca_custom/argiloteca/static/js/drx-comparacao.js")
        self.assertIn("source_reflection_tables", source)
        self.assertIn("Dados das tabelas", source)
        self.assertIn("renderSourceTablePreview", source)
        self.assertIn("d inicial Å", source)

    def test_external_curve_preclassification_group_preserves_d060(self):
        items = [
            {
                "filename": "AM-01 (N).raw",
                "sample_code": "AM-01 (N)",
                "sample_base": "AM-01",
                "preparation": "natural",
                "peaks": [{"d_angstrom": 10.0, "two_theta": 8.84, "relative_intensity": 80}],
                "metadata": {"source": "external_curve_preclassification"},
            },
            {
                "filename": "AM-01 (G).raw",
                "sample_code": "AM-01 (G)",
                "sample_base": "AM-01",
                "preparation": "glicolado",
                "peaks": [{"d_angstrom": 17.0, "two_theta": 5.2, "relative_intensity": 95}],
                "metadata": {"source": "external_curve_preclassification"},
            },
            {
                "filename": "AM-01 (C).raw",
                "sample_code": "AM-01 (C)",
                "sample_base": "AM-01",
                "preparation": "calcinado",
                "peaks": [
                    {"d_angstrom": 10.0, "two_theta": 8.84, "relative_intensity": 90},
                    {"d_angstrom": 1.541, "two_theta": 60.0, "relative_intensity": 22},
                ],
                "metadata": {
                    "source": "external_curve_preclassification",
                    "d060": 1.541,
                    "d060_status": "inferred_auxiliary",
                    "d060_warning": "d060 inferido de RAW externo",
                },
            },
        ]
        payload = build_ngc_workflow(items)
        group = payload["groups"][0]
        self.assertEqual(group["status"], "trio completo")
        self.assertTrue(group["external_curve_preclassification"]["available"])
        self.assertTrue(group["external_raw_preclassification"]["available"])
        self.assertEqual(group["external_raw_preclassification"]["status"], "trio_completo")
        self.assertEqual(group["diagnostic_interpretation"]["policy"], "argiloteca_rule_based_diagnostic")
        self.assertEqual(group["diagnostic_interpretation"]["octahedral_classification"]["octahedral_type"], "trioctahedral")

    def test_external_curve_without_060_keeps_unknown_octahedral(self):
        payload = build_ngc_workflow([
            {
                "filename": "AM-02 (N).raw",
                "sample_code": "AM-02 (N)",
                "sample_base": "AM-02",
                "preparation": "natural",
                "peaks": [{"d_angstrom": 10.0, "two_theta": 8.84, "relative_intensity": 80}],
                "metadata": {"source": "external_curve_preclassification"},
            }
        ])
        group = payload["groups"][0]
        self.assertTrue(group["external_curve_preclassification"]["available"])
        self.assertTrue(group["external_raw_preclassification"]["available"])
        self.assertEqual(group["diagnostic_interpretation"]["octahedral_classification"]["octahedral_type"], "unknown")

    def test_external_curve_preclassification_panel_contract(self):
        source = self.read_project_file("argiloteca/argiloteca_custom/argiloteca/static/js/drx-comparacao.js")
        views = self.read_project_file("argiloteca/argiloteca_custom/argiloteca/views.py")
        self.assertIn("Pré-classificação de amostras externas N/G/C", source)
        self.assertIn("externalCurvePreclassification", source)
        self.assertIn("externalRawPreclassification", source)
        self.assertIn("external_curve_preclassification", source)
        self.assertIn("external_raw_preclassification", source)
        self.assertIn("Classificação 060 preliminar", source)
        self.assertIn("Processo de pré-classificação", source)
        self.assertIn("A classificação usa o conjunto temporário; a curva plotada permanece a curva lida.", source)
        self.assertIn("pré-classificação N/G/C acionada no painel", source)
        self.assertIn("_external_curve_preclassification_item", views)
        self.assertIn("_external_raw_preclassification_item", views)
        self.assertIn("_infer_external_curve_d060", views)
        self.assertIn("_infer_external_raw_d060", views)

    def test_panel_bragg_requires_explicit_wavelength(self):
        source = self.read_project_file("argiloteca/argiloteca_custom/argiloteca/static/js/drx-comparacao.js")
        bragg_start = source.index("function braggDSpacing(twoTheta, wavelength)")
        bragg_end = source.index("function braggTwoTheta", bragg_start)
        bragg_source = source[bragg_start:bragg_end]
        self.assertIn("const lambda = Number(wavelength);", bragg_source)
        self.assertIn("return null", bragg_source)
        self.assertNotIn("wavelength || CU_K_ALPHA_WAVELENGTH", bragg_source)
        self.assertIn("d: indisponível — λ não informado", source)
        result = subprocess.run(
            [
                "node",
                "-e",
                bragg_source
                + "\nconsole.log(JSON.stringify([braggDSpacing(10), braggDSpacing(10, 1.54056)]));",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        without_lambda, with_lambda = json.loads(result.stdout)
        self.assertIsNone(without_lambda)
        self.assertAlmostEqual(with_lambda, 8.84, delta=0.02)

    def test_panel_preserves_gaps_and_stacked_offset_in_chart_contract(self):
        source = self.read_project_file("argiloteca/argiloteca_custom/argiloteca/static/js/drx-comparacao.js")
        self.assertIn("function finiteNumber", source)
        self.assertIn("function chartSeriesPoints", source)
        self.assertIn("Math.max(xValues.length, yValues.length)", source)
        self.assertIn("connectgaps: false", source)
        self.assertIn("function svgLineSegments", source)
        self.assertIn("offset aplicado", source)
        self.assertIn("Intensidade normalizada + deslocamento artificial", source)
        self.assertIn("axis_mode", source)

    def test_panel_ngc_summary_uses_ranked_structured_candidates(self):
        source = self.read_project_file("argiloteca/argiloteca_custom/argiloteca/static/js/drx-comparacao.js")
        ranking_start = source.index("function renderNgcPrincipalRanking")
        ranking_end = source.index("function renderNgcCompactRanking", ranking_start)
        ranking_source = source[ranking_start:ranking_end]
        self.assertIn("function rankedNgcCandidates", source)
        self.assertIn("function ngcCandidateRulePeaks", source)
        self.assertIn("Ranking mineralógico N/G/C desta seleção", source)
        self.assertIn("Ranking auxiliar N/G/C", source)
        self.assertIn("Não representa fase única", source)
        self.assertIn("Cap. 7", source)
        self.assertIn("Cap. 8", source)
        self.assertIn("Picos diagnósticos não vinculados", source)
        self.assertNotIn("score ", ranking_source)
        self.assertNotIn("Argilomineral encontrado nos picos N/G/C", source)

    def test_drx_endpoint_reports_unambiguous_point_counts(self):
        source = self.read_project_file("argiloteca/argiloteca_custom/argiloteca/views.py")
        endpoint_start = source.index("def api_drx_difratograma")
        endpoint_end = source.index("@blueprint.route", endpoint_start + 1)
        endpoint_source = source[endpoint_start:endpoint_end]
        self.assertIn('"source_points": source_points', endpoint_source)
        self.assertIn('"payload_points": payload_points', endpoint_source)
        self.assertIn('"backend_points": backend_points', endpoint_source)
        self.assertIn('"rendered_points": rendered_points', endpoint_source)
        self.assertIn("rendered_points = None", endpoint_source)
        self.assertIn('"decimated": decimated', endpoint_source)
        self.assertNotIn('"total_points"', endpoint_source)


if __name__ == "__main__":
    unittest.main()
