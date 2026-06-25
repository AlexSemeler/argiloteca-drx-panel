"""
Projeto: Painel DRX Argiloteca

Descrição:
Valida contratos e fluxos do painel DRX Argiloteca, cobrindo processamento científico, classificação auxiliar e integração com dados de referência.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br



Projeto:
Argiloteca / CPAA

Licença:
Preservar licença existente no repositório.

Última revisão:
2026-06-21

Observação:
Este arquivo integra o sistema de análise, comparação e interpretação de difratogramas de raios X para argilominerais.
"""

import json
import math
import os
import struct
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest import mock

from flask import Flask

from argiloteca.services import drx
from argiloteca.services import analytical_packages
from argiloteca.services import drx_reference_index
from argiloteca.services import neural_evidence
from argiloteca.services.drx_cif_simulation import build_cif_simulation_payload
from argiloteca.services.drx_external_jobs import claim_next_external_job, get_external_job, run_external_job_adapter, submit_external_job
from argiloteca.services.drx_ngc_workflow import build_ngc_workflow
from argiloteca.services.drx_runs import get_drx_run, list_drx_runs, persist_drx_run
from argiloteca.services.drx_selection_report import build_drx_selection_report
from argiloteca.services.drx_analysis import build_drx_analysis_run
from argiloteca.services.drx_report import build_drx_technical_report
from argiloteca.services.drx_references import compare_reference_pattern, parse_reference_pattern_bytes
import argiloteca.views as views


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def instance_deposit_asset(name):
    """Return a repository-local deposit asset path for legacy static tests."""
    return PROJECT_ROOT / "instance" / "assets" / "js" / "invenio_app_rdm" / "deposit" / name


def raw_legacy_bytes(points, start=3.0, step=0.02):
    """
    Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
    
    Args:
        points: Valor de entrada consumido por esta etapa do fluxo.
        start: Valor de entrada consumido por esta etapa do fluxo.
        step: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    header = bytearray(156)
    header[0:4] = b"RAW "
    header[4:8] = struct.pack("<I", len(points))
    header[8:12] = struct.pack("<f", start)
    header[12:16] = struct.pack("<f", step)
    return bytes(header) + struct.pack("<" + ("f" * len(points)), *points)


def raw2_bytes(points, start=3.0, step=0.02):
    """
    Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
    
    Args:
        points: Valor de entrada consumido por esta etapa do fluxo.
        start: Valor de entrada consumido por esta etapa do fluxo.
        step: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    header = bytearray(0x13C)
    header[0:4] = b"RAW2"
    header[0x102:0x104] = struct.pack("<H", len(points))
    header[0x108:0x10C] = struct.pack("<f", start)
    header[0x10C:0x110] = struct.pack("<f", step)
    return bytes(header) + struct.pack("<" + ("f" * len(points)), *points)


def raw101_bytes(points, start=2.0, step=0.02):
    """
    Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
    
    Args:
        points: Valor de entrada consumido por esta etapa do fluxo.
        start: Valor de entrada consumido por esta etapa do fluxo.
        step: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    header = bytearray(0x3F8)
    header[0:8] = b"RAW1.01\x00"
    header[0x378:0x380] = struct.pack("<d", step)
    header[0x388:0x38C] = struct.pack("<f", start)
    return bytes(header) + struct.pack("<" + ("f" * len(points)), *points)


class DrxParserTest(unittest.TestCase):
    """Representa a estrutura `DrxParserTest` dentro do fluxo técnico do painel Argiloteca, mantendo dados e operações relacionados ao módulo."""
    def test_parse_raw_legacy_layout(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        parsed = drx.parse_raw_bytes(raw_legacy_bytes(tuple(range(10, 60))))

        self.assertEqual(parsed.metadata["detected_format"], "RAW legacy float32")
        self.assertEqual(parsed.metadata["points"], 50)
        self.assertEqual(parsed.two_theta[0], 3.0)
        self.assertAlmostEqual(parsed.two_theta[-1], 3.98)
        self.assertEqual(parsed.intensity[:3], [10.0, 11.0, 12.0])

    def test_parse_raw2_eva_layout(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        parsed = drx.parse_raw_bytes(raw2_bytes(tuple(range(20, 35))))

        self.assertEqual(parsed.metadata["detected_format"], "RAW2 EVA float32")
        self.assertEqual(parsed.metadata["points"], 15)
        self.assertAlmostEqual(parsed.two_theta[1], 3.02)
        self.assertEqual(parsed.intensity[-1], 34.0)

    def test_parse_raw101_layout(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        parsed = drx.parse_raw_bytes(raw101_bytes(tuple(range(100, 130)), start=2.0, step=0.02))

        self.assertEqual(parsed.metadata["detected_format"], "RAW1.01 float32")
        self.assertEqual(parsed.metadata["points"], 30)
        self.assertEqual(parsed.metadata["data_offset"], 0x3F8)
        self.assertEqual(parsed.two_theta[0], 2.0)
        self.assertAlmostEqual(parsed.two_theta[-1], 2.58)
        self.assertEqual(parsed.intensity[:3], [100.0, 101.0, 102.0])

    def test_build_drx_analysis_run_exposes_versioned_contract(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        two_theta = [4.0 + index * 0.05 for index in range(160)]
        intensity = [10.0 for _ in two_theta]
        peak_index = min(range(len(two_theta)), key=lambda index: abs(two_theta[index] - 8.84))
        intensity[peak_index] = 500.0
        parsed = drx.DiffractogramData(
            two_theta=two_theta,
            intensity=intensity,
            metadata={
                "parser_format": "text_curve",
                "detected_format": "text two-column diffractogram",
                "points": len(two_theta),
                "two_theta_start": two_theta[0],
                "two_theta_end": two_theta[-1],
            },
        )

        payload = build_drx_analysis_run(
            filename="illite.csv",
            sample_code="illite",
            source_sha256="abc123",
            parsed=parsed,
            identification={"peaks": [], "candidates": []},
            preparation="natural",
            max_points=500,
        )

        self.assertEqual(payload["analysis_run"]["schema_version"], "argiloteca.drx.analysis_run.v1")
        self.assertIn("methods_hash", payload["analysis_run"]["reproducibility"])
        self.assertIn("input_hash", payload["analysis_run"]["reproducibility"])
        self.assertTrue(payload["advanced_processing"]["success"])
        self.assertIsInstance(payload["diagnostic_evidence"], list)

        report = build_drx_technical_report(
            analysis_run=payload["analysis_run"],
            advanced_processing=payload["advanced_processing"],
            identification={"peaks": [], "candidates": []},
            diagnostic_evidence=payload["diagnostic_evidence"],
        )
        self.assertEqual(report["schema_version"], "argiloteca.drx.technical_report.v1")
        self.assertEqual(report["analysis_schema_version"], "argiloteca.drx.analysis_run.v1")
        self.assertIn("methods_hash", report["reproducibility"])
        self.assertIn("peak_count", report["summary"])

    def test_targeted_basal_peak_scan_finds_weak_chlorite_peak_outside_global_top(self):
        """
        Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        two_theta = [2.0 + index * 0.02 for index in range(1500)]
        intensity = [0.05 for _ in two_theta]
        for center in [8.0, 9.2, 11.0, 13.0, 15.0, 17.0, 19.0, 21.0, 23.0, 25.0, 27.0, 29.0]:
            for index, theta in enumerate(two_theta):
                intensity[index] += 35.0 * math.exp(-((theta - center) ** 2) / (2 * 0.025 ** 2))
        chlorite_theta = drx._d_spacing_to_two_theta(14.2)
        for index, theta in enumerate(two_theta):
            intensity[index] += 1.4 * math.exp(-((theta - chlorite_theta) ** 2) / (2 * 0.035 ** 2))

        rows = drx.targeted_basal_peak_scan(two_theta, intensity)
        chlorite = next(row for row in rows if row["range_id"] == "chlorite_14a")

        self.assertIn(chlorite["status"], {"weak", "shoulder", "strong"})
        self.assertAlmostEqual(chlorite["observed_d_angstrom"], 14.2, delta=0.18)
        self.assertEqual(chlorite["observed_peak"]["source"], "targeted_basal_peak_scan")

    def test_targeted_basal_peak_scan_finds_weak_kaolinite_companion_and_marks_empty_range(self):
        """
        Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        two_theta = [2.0 + index * 0.02 for index in range(1500)]
        intensity = [0.03 for _ in two_theta]
        kaolinite_theta = drx._d_spacing_to_two_theta(3.57)
        for index, theta in enumerate(two_theta):
            intensity[index] += 0.9 * math.exp(-((theta - kaolinite_theta) ** 2) / (2 * 0.035 ** 2))

        rows = drx.targeted_basal_peak_scan(two_theta, intensity)
        kaolinite = next(row for row in rows if row["range_id"] == "kaolinite_3_57a")
        smectite = next(row for row in rows if row["range_id"] == "smectite_g_17a")

        self.assertIn(kaolinite["status"], {"weak", "shoulder", "strong"})
        self.assertAlmostEqual(kaolinite["observed_d_angstrom"], 3.57, delta=0.05)
        self.assertEqual(smectite["status"], "not_found")

    def test_process_advanced_als_curve_includes_targeted_basal_peaks(self):
        """
        Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        two_theta = [2.0 + index * 0.02 for index in range(1500)]
        intensity = [1.0 for _ in two_theta]
        chlorite_theta = drx._d_spacing_to_two_theta(14.2)
        for index, theta in enumerate(two_theta):
            intensity[index] += 3.0 * math.exp(-((theta - chlorite_theta) ** 2) / (2 * 0.04 ** 2))

        payload = drx.process_advanced_als_curve(two_theta, intensity, sample_id="CL-weak", filename="CL-weak.raw")

        self.assertIn("targeted_basal_peaks", payload)
        self.assertIn("targeted_basal_peak_scan", payload["peak_processing"])
        self.assertTrue(any(row["range_id"] == "chlorite_14a" for row in payload["targeted_basal_peaks"]))

    def test_parse_text_curve_csv_layout(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        content = "two_theta;intensity\n" + "\n".join(
            f"{3 + index * 0.02:.2f};{100 + index}" for index in range(12)
        )

        parsed = drx.parse_diffractogram_bytes(content.encode("utf-8"), filename="amostra.csv")

        self.assertEqual(parsed.metadata["parser_format"], "text_curve")
        self.assertEqual(parsed.metadata["points"], 12)
        self.assertEqual(parsed.two_theta[0], 3.0)
        self.assertAlmostEqual(parsed.two_theta[-1], 3.22)
        self.assertEqual(parsed.intensity[:3], [100.0, 101.0, 102.0])

    def test_reference_pattern_parser_and_matcher(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        reference = parse_reference_pattern_bytes(
            b"8.84,100\n12.35,40\n20.0,15\n",
            filename="illite.xy",
        )
        observed = [
            {"peak_index": 1, "two_theta": 8.86, "relative_intensity": 100},
            {"peak_index": 2, "two_theta": 12.30, "relative_intensity": 35},
        ]

        comparison = compare_reference_pattern(observed, reference, tolerance_two_theta=0.1)

        self.assertEqual(reference["schema_version"], "argiloteca.drx.reference_pattern.v1")
        self.assertEqual(reference["peak_count"], 3)
        self.assertEqual(comparison["schema_version"], "argiloteca.drx.reference_comparison.v1")
        self.assertEqual(comparison["matched_peak_count"], 2)
        self.assertGreater(comparison["score"], 0.7)

    def test_reference_index_search_uses_curated_manifest_with_provenance(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "rruff_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    [
                        {
                            "argilomineral_id": "kaolinite",
                            "mineral_name": "Kaolinite",
                            "sample_id": "R050099",
                            "file_type": "xy",
                            "local_path": "/curated/kaolinite.xy",
                            "points": [[12.35, 100.0], [24.9, 50.0]],
                            "peaks": [
                                {"two_theta": 12.35, "intensity": 100.0},
                                {"two_theta": 24.9, "intensity": 50.0},
                            ],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            try:
                with mock.patch.object(drx_reference_index, "DEFAULT_RRUFF_ODR_MANIFEST", manifest_path):
                    drx_reference_index.load_reference_index.cache_clear()
                    payload = drx_reference_index.search_reference_index(query="kaolinite", source="RRUFF_ODR")
            finally:
                drx_reference_index.load_reference_index.cache_clear()

        self.assertTrue(payload["success"])
        self.assertEqual(payload["schema_version"], "argiloteca.drx.reference_index.v1")
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["references"][0]["source"], "RRUFF_ODR")
        self.assertIn("provenance", payload["references"][0])
        self.assertEqual(payload["references"][0]["peaks"][0]["two_theta"], 12.35)
        self.assertEqual(payload["references"][0]["peaks"][0]["relative_intensity"], 100.0)
        self.assertEqual(payload["references"][0]["peaks"][1]["relative_intensity"], 50.0)

    def test_reference_pattern_from_index_returns_comparison_payload(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "rruff_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    [
                        {
                            "argilomineral_id": "kaolinite",
                            "mineral_name": "Kaolinite",
                            "sample_id": "R050099",
                            "file_type": "xy",
                            "local_path": "/curated/kaolinite.xy",
                            "peaks": [{"two_theta": 12.35, "intensity": 100.0}],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            try:
                with mock.patch.object(drx_reference_index, "DEFAULT_RRUFF_ODR_MANIFEST", manifest_path):
                    drx_reference_index.load_reference_index.cache_clear()
                    reference = drx_reference_index.reference_pattern_from_index("rruff_odr:kaolinite:R050099:xy")
            finally:
                drx_reference_index.load_reference_index.cache_clear()

        self.assertTrue(reference["success"])
        self.assertEqual(reference["schema_version"], "argiloteca.drx.indexed_reference_pattern.v1")
        self.assertEqual(reference["source"], "RRUFF_ODR")
        self.assertEqual(reference["peak_count"], 1)
        self.assertIn("provenance", reference["metadata"])

    def test_reference_index_loads_cif_cod_manifest_with_provenance(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            rruff_path = tmp_path / "rruff_manifest.json"
            cod_path = tmp_path / "cif_cod_reference_index.json"
            rruff_path.write_text("[]", encoding="utf-8")
            cod_path.write_text(
                json.dumps(
                    {
                        "references": [
                            {
                                "reference_id": "cod:9004218",
                                "source": "COD",
                                "cod_id": "9004218",
                                "mineral_name": "Cobaltite",
                                "formula": "CoAsS",
                                "local_path": "/curated/cod_9004218.cif",
                                "source_sha256": "abc",
                                "peaks": [{"two_theta": 35.97, "relative_intensity": 100}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            try:
                with mock.patch.object(drx_reference_index, "DEFAULT_RRUFF_ODR_MANIFEST", rruff_path), mock.patch.object(
                    drx_reference_index, "DEFAULT_CIF_COD_REFERENCE_MANIFEST", cod_path
                ):
                    drx_reference_index.load_reference_index.cache_clear()
                    payload = drx_reference_index.search_reference_index(query="cobaltite", source="COD")
                    reference = drx_reference_index.reference_pattern_from_index("cod:9004218")
            finally:
                drx_reference_index.load_reference_index.cache_clear()

        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["references"][0]["source"], "COD")
        self.assertEqual(reference["metadata"]["cod_id"], "9004218")
        self.assertEqual(reference["metadata"]["provenance"]["source_format"], "cif")

    def test_reference_pattern_cif_uses_science_engine_bridge(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with mock.patch(
            "argiloteca.services.drx_references.simulate_cif_pattern",
            return_value={
                "success": True,
                "engine": "pymatgen.XRDCalculator",
                "formula": "Si",
                "sites": 2,
                "peaks": [
                    {"peak_index": 1, "two_theta": 28.44, "relative_intensity": 100, "d_angstrom": 3.135},
                ],
            },
        ):
            reference = parse_reference_pattern_bytes(
                b"data_Si\n_chemical_formula_sum 'Si'\n",
                filename="si.cif",
            )

        self.assertEqual(reference["metadata"]["simulation_status"], "ok")
        self.assertEqual(reference["metadata"]["simulation_engine"], "pymatgen.XRDCalculator")
        self.assertEqual(reference["peak_count"], 1)

    def test_cif_simulation_contract_exposes_provenance(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        content = b"data_Si\n_chemical_formula_sum 'Si'\n"
        with mock.patch(
            "argiloteca.services.drx_cif_simulation.simulate_cif_pattern",
            return_value={
                "success": True,
                "engine": "pymatgen.XRDCalculator",
                "formula": "Si",
                "sites": 2,
                "peaks": [
                    {"peak_index": 1, "two_theta": 28.44, "relative_intensity": 100, "d_angstrom": 3.135},
                    {"peak_index": 2, "two_theta": 47.3, "relative_intensity": 42, "d_angstrom": 1.921},
                ],
            },
        ):
            payload = build_cif_simulation_payload(content, filename="si.cif", wavelength="CuKa")

        self.assertTrue(payload["success"])
        self.assertEqual(payload["schema_version"], "argiloteca.drx.cif_simulation.v1")
        self.assertEqual(payload["engine"], "pymatgen.XRDCalculator")
        self.assertEqual(payload["formula"], "Si")
        self.assertEqual(payload["peak_count"], 2)
        self.assertEqual(payload["peaks"][0]["relative_intensity"], 100.0)
        self.assertIn("source_sha256", payload)
        self.assertEqual(payload["provenance"]["source_format"], "cif")
        self.assertIn("auxiliar", payload["interpretation_policy"])

    def _ngc_items(self, sample, natural=None, glycolated=None, calcined=None):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            sample: Valor de entrada consumido por esta etapa do fluxo.
            natural: Valor de entrada consumido por esta etapa do fluxo.
            glycolated: Valor de entrada consumido por esta etapa do fluxo.
            calcined: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        rows = []
        for prep, suffix, peaks in (
            ("natural", "N", natural),
            ("glicolado", "G", glycolated),
            ("calcinado", "C", calcined),
        ):
            if peaks is None:
                continue
            rows.append({
                "filename": f"{sample} ({suffix}).raw",
                "sample_base": sample,
                "preparation": prep,
                "peaks": peaks,
            })
        return rows

    def _clay_candidate(self, payload, candidate_id):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            payload: Valor de entrada consumido por esta etapa do fluxo.
            candidate_id: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        group = payload["groups"][0]
        candidates = {
            row["candidateId"]: row
            for row in group["clay_interpretation"]["candidates"]
        }
        return candidates[candidate_id]

    def test_ngc_clay_interpretation_detects_probable_kaolin_group(self):
        """
        Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        payload = build_ngc_workflow(self._ngc_items(
            "KAO-01",
            natural=[{"d": 7.15, "i_abs": 100}, {"d": 3.57, "i_abs": 45}],
            glycolated=[{"d": 7.14, "i_abs": 95}, {"d": 3.57, "i_abs": 44}],
            calcined=[{"d": 7.15, "i_abs": 5}],
        ))

        kaolin = self._clay_candidate(payload, "kaolin_group")
        chlorite = self._clay_candidate(payload, "chlorite_group")

        self.assertEqual(kaolin["status"], "provável")
        self.assertGreaterEqual(kaolin["score"], 0.8)
        self.assertGreater(kaolin["score"], chlorite["score"])
        self.assertTrue(any("7 Å" in row for row in kaolin["evidenceFor"]))
        self.assertEqual(kaolin["level"], "group")

    def test_ngc_clay_interpretation_detects_probable_chlorite_group(self):
        """
        Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        peaks = [{"d": 14.7, "i_abs": 90}, {"d": 7.1, "i_abs": 60}, {"d": 4.72, "i_abs": 40}, {"d": 3.53, "i_abs": 35}]
        payload = build_ngc_workflow(self._ngc_items("CHL-01", natural=peaks, glycolated=peaks, calcined=peaks))

        chlorite = self._clay_candidate(payload, "chlorite_group")
        kaolin = self._clay_candidate(payload, "kaolin_group")

        self.assertEqual(chlorite["status"], "provável")
        self.assertGreaterEqual(chlorite["score"], 0.8)
        self.assertGreater(chlorite["score"], kaolin["score"])
        self.assertTrue(any("14" in row for row in chlorite["evidenceFor"]))
        self.assertTrue(any("clinochlore" in row.lower() or "chamosite" in row.lower() for row in chlorite["warnings"]))

    def test_ngc_clay_interpretation_detects_smectite_group(self):
        """
        Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        payload = build_ngc_workflow(self._ngc_items(
            "SME-01",
            natural=[{"d": 15.0, "i_abs": 80}],
            glycolated=[{"d": 17.0, "i_abs": 100}],
            calcined=[{"d": 10.0, "i_abs": 70}],
        ))

        smectite = self._clay_candidate(payload, "smectite_group")

        self.assertEqual(smectite["status"], "provável")
        self.assertGreaterEqual(smectite["score"], 0.8)
        self.assertTrue(any("Expansão" in row for row in smectite["evidenceFor"]))
        self.assertEqual(smectite["level"], "group")

    def test_ngc_clay_interpretation_detects_illite_mica_with_quartz_warning(self):
        """
        Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        payload = build_ngc_workflow(self._ngc_items(
            "ILL-01",
            natural=[{"d": 10.02, "i_abs": 90}, {"d": 5.0, "i_abs": 35}, {"d": 3.33, "i_abs": 45}, {"d": 3.34, "i_abs": 120}],
            glycolated=[{"d": 10.01, "i_abs": 88}],
            calcined=[{"d": 10.03, "i_abs": 92}],
        ))

        illite = self._clay_candidate(payload, "illite_mica")

        self.assertEqual(illite["status"], "provável")
        self.assertGreaterEqual(illite["score"], 0.75)
        self.assertTrue(any("10 Å" in row for row in illite["evidenceFor"]))
        self.assertTrue(any("Quartzo" in row or "quartzo" in row for row in illite["overlaps"]))
        self.assertEqual(illite["level"], "series")

    def test_ngc_clay_interpretation_flags_kaolin_chlorite_mixture(self):
        """
        Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        payload = build_ngc_workflow(self._ngc_items(
            "MIX-01",
            natural=[{"d": 14.4, "i_abs": 70}, {"d": 7.1, "i_abs": 100}, {"d": 4.72, "i_abs": 30}, {"d": 3.53, "i_abs": 28}],
            glycolated=[{"d": 14.4, "i_abs": 65}, {"d": 7.1, "i_abs": 95}],
            calcined=[{"d": 14.4, "i_abs": 80}, {"d": 7.1, "i_abs": 35}],
        ))

        kaolin = self._clay_candidate(payload, "kaolin_group")
        chlorite = self._clay_candidate(payload, "chlorite_group")
        mixed = self._clay_candidate(payload, "mixed_layer")

        self.assertGreaterEqual(chlorite["score"], 0.6)
        self.assertGreaterEqual(kaolin["score"], 0.4)
        self.assertIn(mixed["status"], {"ambíguo", "possível"})
        self.assertTrue(any("mistura" in row.lower() for row in mixed["evidenceFor"]))

    def test_ngc_clay_interpretation_marks_vermiculite_as_provisional(self):
        """
        Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        payload = build_ngc_workflow(self._ngc_items(
            "VER-01",
            natural=[{"d": 14.2, "i_abs": 85}],
            glycolated=[{"d": 14.1, "i_abs": 80}],
            calcined=[{"d": 10.4, "i_abs": 45}],
        ))

        vermiculite = self._clay_candidate(payload, "vermiculite_group")

        self.assertIn(vermiculite["status"], {"provisório", "possível"})
        self.assertTrue(any("K/Mg" in row or "glicerol" in row for row in vermiculite["recommendedAdditionalTests"]))
        self.assertLess(vermiculite["score"], 0.8)

    def test_ngc_clay_interpretation_flags_mixed_layer_from_broad_partial_response(self):
        """
        Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        payload = build_ngc_workflow(self._ngc_items(
            "ML-01",
            natural=[{"d": 14.5, "i_abs": 80, "fwhm": 1.2}],
            glycolated=[{"d": 16.0, "i_abs": 65, "fwhm": 1.1}],
            calcined=[{"d": 10.2, "i_abs": 40}],
        ))

        mixed = self._clay_candidate(payload, "mixed_layer")
        smectite = self._clay_candidate(payload, "smectite_group")

        self.assertEqual(mixed["status"], "ambíguo")
        self.assertTrue(any("Pico largo" in row for row in mixed["evidenceFor"]))
        self.assertLess(smectite["score"], 0.8)

    def test_ngc_clay_interpretation_degrades_with_only_natural_7a(self):
        """
        Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        payload = build_ngc_workflow(self._ngc_items(
            "ONLY-N",
            natural=[{"d": 7.12, "i_abs": 100}],
            glycolated=None,
            calcined=None,
        ))

        group = payload["groups"][0]
        kaolin = self._clay_candidate(payload, "kaolin_group")

        self.assertIn("glycolated", group["clay_interpretation"]["missingPreparations"])
        self.assertIn("calcined", group["clay_interpretation"]["missingPreparations"])
        self.assertIn(kaolin["status"], {"possível", "descartado"})
        self.assertLess(kaolin["score"], 0.8)
        self.assertTrue(any("Preparações ausentes" in row for row in group["clay_interpretation"]["globalWarnings"]))

    def test_ngc_workflow_contract_detects_smectite_expansion(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        payload = build_ngc_workflow(
            [
                {
                    "filename": "AM-01-N.raw",
                    "sample_base": "AM-01",
                    "preparation": "natural",
                    "peaks": [{"d_angstrom": 14.8, "two_theta": 5.96, "relative_intensity": 80}],
                },
                {
                    "filename": "AM-01-G.raw",
                    "sample_base": "AM-01",
                    "preparation": "glicolado",
                    "peaks": [{"d_angstrom": 17.1, "two_theta": 5.16, "relative_intensity": 100}],
                },
                {
                    "filename": "AM-01-C.raw",
                    "sample_base": "AM-01",
                    "preparation": "calcinado",
                    "peaks": [{"d_angstrom": 10.0, "two_theta": 8.84, "relative_intensity": 75}],
                },
            ]
        )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["schema_version"], "argiloteca.drx.ngc_workflow.v1")
        self.assertEqual(payload["group_count"], 1)
        group = payload["groups"][0]
        self.assertEqual(group["status"], "trio completo")
        self.assertEqual(group["best_candidate"]["mineral_candidate"], "esmectita expansiva")
        self.assertGreater(group["best_candidate"]["score"], 0.7)
        self.assertIn("companion_peaks", group)
        self.assertIn("ngc_behavior", group)
        self.assertIn("mixed_layer_warnings", group)
        screening = {row["mineral"]: row for row in group["target_screening"]}
        self.assertEqual(screening["Esmectita"]["status"], "detected")
        self.assertIn("glycolated_17a", screening["Esmectita"]["companion_peaks"])
        self.assertIn("script_interval_ranges", payload)
        self.assertTrue(any(row["mineral"] == "Esmectita" for row in group["interval_diagnostics"]))
        self.assertTrue(
            any(
                "ESMECTITA Detectada: Expansao p/ 16.1-18.3 A no Glicol e colapso na Calcinada."
                in row["message"]
                for row in group["interval_diagnostics"]
            )
        )
        self.assertIn("auxiliar", payload["interpretation_policy"])

    def test_ngc_workflow_interval_rules_detect_script_ranges(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        payload = build_ngc_workflow(
            [
                {
                    "filename": "AM-02-N.raw",
                    "sample_base": "AM-02",
                    "preparation": "natural",
                    "peaks": [
                        {"d": 10.0, "i_abs": 120, "two_theta": 8.84},
                        {"d": 7.2, "i_abs": 90, "two_theta": 12.28},
                        {"d": 3.34, "i_abs": 500, "two_theta": 26.66},
                        {"d": 4.30, "i_abs": 80, "two_theta": 20.64},
                    ],
                },
                {
                    "filename": "AM-02-G.raw",
                    "sample_base": "AM-02",
                    "preparation": "glicolado",
                    "peaks": [
                        {"d": 10.1, "i_abs": 110, "two_theta": 8.74},
                        {"d": 7.2, "i_abs": 85, "two_theta": 12.28},
                        {"d": 3.34, "i_abs": 480, "two_theta": 26.66},
                    ],
                },
                {
                    "filename": "AM-02-C.raw",
                    "sample_base": "AM-02",
                    "preparation": "calcinado",
                    "peaks": [
                        {"d": 10.2, "i_abs": 100, "two_theta": 8.66},
                        {"d": 7.2, "i_abs": 5, "two_theta": 12.28},
                        {"d": 3.34, "i_abs": 470, "two_theta": 26.66},
                    ],
                },
            ]
        )

        group = payload["groups"][0]
        minerals = {row["mineral"] for row in group["interval_diagnostics"]}
        self.assertIn("Ilita", minerals)
        self.assertIn("Caulinita", minerals)
        self.assertIn("Quartzo", minerals)
        messages = [row["message"] for row in group["interval_diagnostics"]]
        self.assertTrue(any("ILITA Detectada: Pico estavel entre 9.7-10.4 A" in message for message in messages))
        self.assertTrue(any("CAULINITA Detectada: Pico entre 7.0-7.4 A destruido na Calcinacao." in message for message in messages))
        self.assertTrue(any("QUARTZO Detectado: Pico principal da ordem 101 imutavel" in message for message in messages))
        self.assertTrue(any("Confirmado por pico secundario (100)" in message for message in messages))
        self.assertIn("illite", group["companion_peaks"])
        self.assertIn("companion_5a", group["companion_peaks"]["illite"])
        self.assertIn("quartz_auxiliary", group["companion_peaks"])
        self.assertTrue(
            any("quartzo" in warning.casefold() for warning in group["mixed_layer_warnings"])
        )

    def test_ngc_workflow_target_screening_prioritizes_chlorite_kaolinite_illite(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        payload = build_ngc_workflow(
            [
                {
                    "filename": "CL-01-N.raw",
                    "sample_base": "CL-01",
                    "preparation": "natural",
                    "peaks": [
                        {"d": 14.2, "i_abs": 90, "two_theta": 6.22},
                        {"d": 10.0, "i_abs": 50, "two_theta": 8.84},
                        {"d": 7.1, "i_abs": 40, "two_theta": 12.45},
                    ],
                },
                {
                    "filename": "CL-01-G.raw",
                    "sample_base": "CL-01",
                    "preparation": "glicolado",
                    "peaks": [{"d": 10.1, "i_abs": 45, "two_theta": 8.75}],
                },
                {
                    "filename": "CL-01-C.raw",
                    "sample_base": "CL-01",
                    "preparation": "calcinado",
                    "peaks": [
                        {"d": 14.25, "i_abs": 120, "two_theta": 6.19},
                        {"d": 10.2, "i_abs": 42, "two_theta": 8.66},
                        {"d": 7.1, "i_abs": 35, "two_theta": 12.45},
                    ],
                },
            ]
        )

        group = payload["groups"][0]
        screening = {row["mineral"]: row for row in group["target_screening"]}
        interval_messages = [row["message"] for row in group["interval_diagnostics"]]
        self.assertEqual(screening["Clorita"]["status"], "detected")
        self.assertEqual(screening["Ilita"]["status"], "detected")
        self.assertEqual(screening["Caulinita"]["status"], "possible")
        self.assertIn("companion_4_72a", screening["Clorita"]["companion_peaks"])
        self.assertEqual(screening["Clorita"]["ngc_behavior"]["status"], "preserved")
        self.assertTrue(any("CLORITA Detectada: Pico ~14.2 A intensificado na Calcinada" in message for message in interval_messages))
        self.assertIn("auxiliar", screening["Clorita"]["interpretation_policy"])

    def test_ngc_workflow_flags_mixed_layer_or_vermiculite_like_partial_response(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        payload = build_ngc_workflow(
            [
                {
                    "filename": "MX-01-N.raw",
                    "sample_base": "MX-01",
                    "preparation": "natural",
                    "peaks": [
                        {"d": 14.4, "i_abs": 85, "two_theta": 6.14},
                        {"d": 7.1, "i_abs": 60, "two_theta": 12.45},
                    ],
                },
                {
                    "filename": "MX-01-G.raw",
                    "sample_base": "MX-01",
                    "preparation": "glicolado",
                    "peaks": [{"d": 16.9, "i_abs": 45, "two_theta": 5.23}],
                },
                {
                    "filename": "MX-01-C.raw",
                    "sample_base": "MX-01",
                    "preparation": "calcinado",
                    "peaks": [{"d": 7.1, "i_abs": 35, "two_theta": 12.45}],
                },
            ]
        )

        group = payload["groups"][0]
        screening = {row["mineral"]: row for row in group["target_screening"]}
        self.assertEqual(screening["Esmectita"]["status"], "mixed_layer_suspected")
        self.assertTrue(group["mixed_layer_warnings"])
        self.assertTrue(any("interestratificado" in warning for warning in group["mixed_layer_warnings"]))

    def test_ngc_workflow_target_screening_uses_manual_chlorite_hint_as_possible(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        payload = build_ngc_workflow(
            [
                {
                    "filename": "AND-06B (N).raw",
                    "sample_base": "AND-06B",
                    "preparation": "natural",
                    "mineral_candidates": [
                        {"mineral": "Chlorite", "argilomineral_id": "chlorite", "override": True}
                    ],
                    "peaks": [{"d": 3.55, "i_abs": 55, "two_theta": 25.08}],
                },
                {
                    "filename": "AND-06B (G).raw",
                    "sample_base": "AND-06B",
                    "preparation": "glicolado",
                    "mineral_candidates": [
                        {"mineral": "Chlorite", "argilomineral_id": "chlorite", "override": True}
                    ],
                    "peaks": [],
                },
                {
                    "filename": "AND-06B (C).raw",
                    "sample_base": "AND-06B",
                    "preparation": "calcinado",
                    "mineral_candidates": [
                        {"mineral": "Chlorite", "argilomineral_id": "chlorite", "override": True}
                    ],
                    "peaks": [],
                },
            ]
        )

        group = payload["groups"][0]
        screening = {row["mineral"]: row for row in group["target_screening"]}
        self.assertEqual(screening["Clorita"]["status"], "possible")
        self.assertEqual(group["best_candidate"]["mineral_candidate"], "clorita")
        self.assertIn("nao confirma", group["best_candidate"]["interpretation_policy"])

    def test_ngc_workflow_consumes_targeted_basal_peaks(self):
        """
        Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        payload = build_ngc_workflow(
            [
                {
                    "filename": "CL-target-N.raw",
                    "sample_base": "CL-target",
                    "preparation": "natural",
                    "peaks": [],
                    "targeted_basal_peaks": [
                        {
                            "range_id": "chlorite_14a",
                            "mineral": "Clorita",
                            "label": "Clorita 14 A",
                            "status": "weak",
                            "observed_d_angstrom": 14.18,
                            "observed_two_theta": 6.23,
                            "intensity": 1.2,
                            "relative_intensity": 1.1,
                            "observed_peak": {"d_angstrom": 14.18, "two_theta": 6.23, "intensity": 1.2},
                        }
                    ],
                },
                {
                    "filename": "CL-target-C.raw",
                    "sample_base": "CL-target",
                    "preparation": "calcinado",
                    "peaks": [],
                    "targeted_basal_peaks": [
                        {
                            "range_id": "chlorite_14a",
                            "mineral": "Clorita",
                            "label": "Clorita 14 A",
                            "status": "weak",
                            "observed_d_angstrom": 14.25,
                            "observed_two_theta": 6.19,
                            "intensity": 1.5,
                            "relative_intensity": 1.4,
                            "observed_peak": {"d_angstrom": 14.25, "two_theta": 6.19, "intensity": 1.5},
                        }
                    ],
                },
            ]
        )

        group = payload["groups"][0]
        screening = {row["mineral"]: row for row in group["target_screening"]}
        self.assertEqual(screening["Clorita"]["status"], "detected")
        self.assertEqual(len(group["targeted_basal_peaks"]), 2)

    def test_ngc_workflow_exposes_script_like_report_for_panel(self):
        """
        Gera artefatos derivados, relatórios ou saídas serializadas com parâmetros e proveniência para auditoria posterior.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        payload = build_ngc_workflow(
            [
                {
                    "filename": "22-25 (N).raw",
                    "sample_base": "22-25",
                    "preparation": "natural",
                    "peaks": [
                        {"d": 14.31, "i_abs": 94.3, "two_theta": 6.16, "fwhm": 0.38, "area": 278},
                        {"d": 10.03, "i_abs": 229.4, "two_theta": 8.80, "fwhm": 0.46, "area": 278},
                        {"d": 7.11, "i_abs": 145.5, "two_theta": 12.42, "fwhm": 0.41, "area": 94},
                        {"d": 3.34, "i_abs": 384.6, "two_theta": 26.66, "fwhm": 0.31, "area": 174},
                    ],
                },
                {
                    "filename": "22-25 (G).raw",
                    "sample_base": "22-25",
                    "preparation": "glicolado",
                    "peaks": [
                        {"d": 10.00, "i_abs": 190.0, "two_theta": 8.82},
                        {"d": 7.11, "i_abs": 134.6, "two_theta": 12.42},
                        {"d": 3.34, "i_abs": 508.0, "two_theta": 26.66},
                    ],
                },
                {
                    "filename": "22-25 (C).raw",
                    "sample_base": "22-25",
                    "preparation": "calcinado",
                    "peaks": [
                        {"d": 14.17, "i_abs": 131.5, "two_theta": 6.22},
                        {"d": 10.00, "i_abs": 283.3, "two_theta": 8.82},
                        {"d": 3.34, "i_abs": 318.5, "two_theta": 26.66},
                    ],
                },
            ]
        )

        group = payload["groups"][0]
        script_report = group["script_report"]
        self.assertEqual(script_report["title"], "Diagnostico comparativo N/G/C")
        self.assertIn("Ilita", script_report["detected_minerals"])
        self.assertIn("Clorita", script_report["detected_minerals"])
        self.assertTrue(any("ILITA Detectada" in row["message"] for row in script_report["diagnostics"]))
        self.assertEqual(len(script_report["peak_tables"]), 3)
        self.assertEqual(script_report["peak_tables"][0]["preparation"], "natural")
        self.assertGreaterEqual(script_report["peak_tables"][0]["peak_count"], 3)

    def test_ngc_group_classification_index_marks_raw_candidates_auxiliary(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "classificacao_mineralogica_ngc_groups.json"
            index_path.write_text(
                json.dumps(
                    {
                        "schema_version": "argiloteca.drx.ngc_group_classification.v1",
                        "groups": [
                            {
                                "sample_id": "22-25",
                                "status": "trio completo",
                                "available_treatments": ["C", "G", "N"],
                                "probable_minerals": [
                                    {"mineral": "Clorita", "ngc_group_score": 0.9}
                                ],
                                "possible_minerals": [],
                                "accessory_minerals": [{"mineral": "Quartzo", "ngc_group_score": 0.65}],
                                "candidates": [{"mineral": "Clorita", "role": "probable", "ngc_group_score": 0.9}],
                                "diagnoses": [],
                                "best_treatment": {"treatment": "N"},
                                "policy": "triagem auxiliar",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            drx._load_ngc_group_classification_index.cache_clear()
            index = drx._load_ngc_group_classification_index(str(index_path))
            item = {"sample_code": "22-25 (N)", "original_filename": "22-25 (N).raw"}
            group = drx._ngc_group_classification_for_item(item, index)

            self.assertTrue(index["available"])
            self.assertEqual(group["sample_id"], "22-25")
            self.assertEqual(group["probable_minerals"][0]["mineral"], "Clorita")

    def test_selection_report_contract_includes_ngc_and_hashes(self):
        """
        Gera artefatos derivados, relatórios ou saídas serializadas com parâmetros e proveniência para auditoria posterior.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        items = [
            {
                "id": "drx-1",
                "filename": "AM-01-G.raw",
                "sample_code": "AM-01-G",
                "sample_base": "AM-01",
                "preparation": "glicolado",
                "peaks": [{"d_angstrom": 17.1, "two_theta": 5.16, "relative_intensity": 100}],
            }
        ]
        ngc = build_ngc_workflow(items)
        report = build_drx_selection_report(items=items, ngc_workflow=ngc, view_parameters={"mode": "normalized"})

        self.assertTrue(report["success"])
        self.assertEqual(report["schema_version"], "argiloteca.drx.selection_report.v1")
        self.assertEqual(report["ngc_workflow"]["schema_version"], "argiloteca.drx.ngc_workflow.v1")
        self.assertEqual(report["summary"]["item_count"], 1)
        self.assertIn("input_hash", report["reproducibility"])
        self.assertIn("methods_hash", report["reproducibility"])
        self.assertIn("auxiliar", report["interpretation_policy"])

    def test_drx_run_artifact_persists_versioned_json(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("argiloteca.services.drx_runs.DEFAULT_RUNS_DIR", Path(tmpdir)):
                payload = persist_drx_run(
                    run_id="run-test-1",
                    analysis_run={"schema_version": "argiloteca.drx.analysis_run.v1", "input": {"sample_code": "AM-01"}},
                    technical_report={"schema_version": "argiloteca.drx.technical_report.v1", "summary": {"peak_count": 2}},
                    inputs={"source_sha256": "abc"},
                    parameters={"wavelength_angstrom": 1.5406},
                    record_id="rec-1",
                    sample_code="AM-01",
                )
                loaded = get_drx_run("run-test-1")
                listed = list_drx_runs(record_id="rec-1")

        self.assertTrue(payload["success"])
        self.assertEqual(payload["schema_version"], "argiloteca.drx.run_artifact.v1")
        self.assertEqual(loaded["run_id"], "run-test-1")
        self.assertEqual(listed["total"], 1)
        self.assertIn("artifact_hash", payload["reproducibility"])

    def test_external_job_worker_contract_marks_unconfigured_outside_request(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("argiloteca.services.drx_external_jobs.DEFAULT_JOBS_DIR", Path(tmpdir)), mock.patch.dict(os.environ, {}, clear=True):
                submitted = submit_external_job("gsas2", payload={"input": "curve.xy"})
                claimed = claim_next_external_job()
                completed = run_external_job_adapter(claimed)
                loaded = get_external_job(submitted["job"]["job_id"])

        self.assertTrue(submitted["success"])
        self.assertEqual(claimed["status"], "running")
        self.assertEqual(completed["job"]["status"], "failed")
        self.assertFalse(loaded["job"]["result"]["implemented"])
        self.assertEqual(loaded["job"]["result"]["reason"], "adapter_not_configured")

    def test_external_job_worker_runs_configured_adapter(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = Path(tmpdir) / "adapter.py"
            adapter.write_text(
                "import json, os\n"
                "path = os.environ['ARGILOTECA_DRX_JOB_RESULT_JSON']\n"
                "payload = {'ok': True, 'engine': os.environ['ARGILOTECA_DRX_JOB_ENGINE']}\n"
                "open(path, 'w', encoding='utf-8').write(json.dumps(payload))\n",
                encoding="utf-8",
            )
            env = {"ARGILOTECA_DRX_GSAS2_COMMAND": "%s %s" % (sys.executable, adapter)}
            with mock.patch("argiloteca.services.drx_external_jobs.DEFAULT_JOBS_DIR", Path(tmpdir)), mock.patch.dict(os.environ, env, clear=True):
                submitted = submit_external_job("gsas2", payload={"input": "curve.xy"})
                claimed = claim_next_external_job()
                completed = run_external_job_adapter(claimed)
                loaded = get_external_job(submitted["job"]["job_id"])

        self.assertEqual(completed["job"]["status"], "succeeded")
        self.assertTrue(loaded["job"]["result"]["implemented"])
        self.assertEqual(loaded["job"]["result"]["adapter_result"]["engine"], "gsas2")

    def test_neural_evidence_matching_and_missing_index(self):
        """
        Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "neural_evidence_index.json"
            index_path.write_text(
                json.dumps(
                    {
                        "schema_version": "argiloteca.drx.neural_evidence_index.v1",
                        "generated_at": "2026-06-20T00:00:00Z",
                        "source": {"path": "/home/invenio/difract/outputs/precomputed"},
                        "entries": [
                            {
                                "diffractogram_id": "snapshot:abc",
                                "sample_id": "AM-01",
                                "filename": "AM-01-N.RAW",
                                "source_curve": "/data/raw/AM-01-N.RAW",
                                "source_sha256": "sha123",
                                "record_id": "rec-1",
                                "candidates": [{"mineral": "caulinita", "score": 0.8}],
                                "warnings": [],
                                "status": "auxiliary_not_confirmatory",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            neural_evidence._load_index_cached.cache_clear()
            by_id = neural_evidence.neural_evidence_for_diffractogram("snapshot:abc", path=index_path)
            by_raw = neural_evidence.neural_evidence_for_diffractogram("missing", metadata={"original_filename": "AM-01-N.raw"}, path=index_path)
            by_curve = neural_evidence.neural_evidence_for_diffractogram("missing", metadata={"source_curve": "/data/raw/AM-01-N.raw"}, path=index_path)
            by_sample = neural_evidence.neural_evidence_for_diffractogram("missing", metadata={"sample_code": "AM-01"}, path=index_path)
            missing = neural_evidence.neural_evidence_for_diffractogram("snapshot:abc", path=Path(tmpdir) / "missing.json")
            neural_evidence._load_index_cached.cache_clear()

        self.assertTrue(by_id["success"])
        self.assertTrue(by_raw["success"])
        self.assertTrue(by_curve["success"])
        self.assertTrue(by_sample["success"])
        self.assertEqual(by_id["usage_policy"], "auxiliary_not_confirmatory")
        self.assertFalse(missing["available"])

    def test_drx_frontend_prefers_plotly_before_svg_fallback(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        js_path = Path(__file__).resolve().parents[1] / "argiloteca" / "static" / "js" / "drx-comparacao.js"
        source = js_path.read_text(encoding="utf-8")
        render_start = source.index("  function renderChart()")
        plotly_call = source.index("if (renderPlotlyMainChart(items)) return;", render_start)
        advanced_svg = source.index("const advancedChart = advancedScriptChartData(items);", render_start)
        self.assertLess(plotly_call, advanced_svg)

    def test_analysis_run_uses_scipy_peak_bridge_when_available(self):
        """
        Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        two_theta = [4.0 + index * 0.05 for index in range(160)]
        intensity = [10.0 for _ in two_theta]
        peak_index = min(range(len(two_theta)), key=lambda index: abs(two_theta[index] - 8.84))
        intensity[peak_index] = 500.0
        parsed = drx.DiffractogramData(
            two_theta=two_theta,
            intensity=intensity,
            metadata={"parser_format": "text_curve", "detected_format": "text", "points": len(two_theta)},
        )

        with mock.patch(
            "argiloteca.services.drx.detect_peaks_scipy",
            return_value={
                "success": True,
                "method": "scipy.signal.find_peaks",
                "peaks": [{"index": peak_index}],
            },
        ):
            payload = build_drx_analysis_run(
                filename="amostra.csv",
                sample_code="AM",
                source_sha256="sha",
                parsed=parsed,
                identification={"peaks": [], "candidates": []},
            )

        self.assertEqual(
            payload["analysis_run"]["methods"]["preprocessing"]["peak_detection_method"],
            "scipy.signal.find_peaks",
        )
        self.assertGreaterEqual(payload["analysis_run"]["artifacts"]["peak_count"], 1)

    def test_analysis_run_uses_lmfit_pseudo_voigt_when_available(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        two_theta = [4.0 + index * 0.05 for index in range(160)]
        intensity = [10.0 for _ in two_theta]
        peak_index = min(range(len(two_theta)), key=lambda index: abs(two_theta[index] - 8.84))
        intensity[peak_index] = 500.0
        parsed = drx.DiffractogramData(
            two_theta=two_theta,
            intensity=intensity,
            metadata={"parser_format": "text_curve", "detected_format": "text", "points": len(two_theta)},
        )

        with mock.patch(
            "argiloteca.services.drx.detect_peaks_scipy",
            return_value={"success": True, "method": "scipy.signal.find_peaks", "peaks": [{"index": peak_index}]},
        ), mock.patch(
            "argiloteca.services.drx.fit_peaks_lmfit",
            return_value={
                "success": True,
                "method": "lmfit.PseudoVoigtModel",
                "fit_results": [
                    {
                        "peak_index": 1,
                        "fit_success": True,
                        "center_2theta": 8.841,
                        "center_d_angstrom": 9.991,
                        "fwhm": 0.12,
                        "model_name": "lmfit.PseudoVoigtModel",
                        "profile_model": "pseudo_voigt",
                    }
                ],
            },
        ):
            payload = build_drx_analysis_run(
                filename="amostra.csv",
                sample_code="AM",
                source_sha256="sha",
                parsed=parsed,
                identification={"peaks": [], "candidates": []},
                wavelength_angstrom=1.5418,
            )

        fit = payload["advanced_processing"]["fit_results"][0]
        self.assertEqual(fit["model_name"], "lmfit.PseudoVoigtModel")
        self.assertEqual(fit["profile_model"], "pseudo_voigt")
        self.assertEqual(fit["wavelength_angstrom"], 1.5418)
        self.assertEqual(payload["analysis_run"]["input"]["wavelength_angstrom"], 1.5418)

    def test_parse_rejects_unknown_raw_layout(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with self.assertRaises(drx.RawParseError):
            drx.parse_raw_bytes(b"NOPE" + (b"\x00" * 400))

    def test_record_exists_checks_record_ids(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with mock.patch.object(
            drx,
            "search_records",
            return_value=[{"id": "rec-1"}, {"uuid": "uuid-2"}],
        ):
            self.assertTrue(drx.record_exists("rec-1"))
            self.assertTrue(drx.record_exists("uuid-2"))
            self.assertFalse(drx.record_exists("SEU_RECORD_ID"))

    def test_infer_diffractogram_treatment_from_filename(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        self.assertEqual(drx.infer_diffractogram_treatment("AM-01-N", "AM-01-N.RAW")["type"], "natural")
        self.assertEqual(drx.infer_diffractogram_treatment("AM-01-G", "AM-01-G.RAW")["type"], "glicolado")
        self.assertEqual(drx.infer_diffractogram_treatment("AM-01-C", "AM-01-C.RAW")["type"], "calcinado")
        self.assertEqual(drx.infer_diffractogram_treatment("AM-01", "AM-01.RAW")["type"], "indeterminado")


class DrxAssociationTest(unittest.TestCase):
    """Representa a estrutura `DrxAssociationTest` dentro do fluxo técnico do painel Argiloteca, mantendo dados e operações relacionados ao módulo."""
    def test_list_records_with_drx_associates_description(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with mock.patch.object(
            drx,
            "_load_index",
            return_value={
                "version": 1,
                "diffractograms": [
                    {
                        "id": "drx-1",
                        "record_id": "rec-1",
                        "sample_code": "AM-01",
                        "original_filename": "AM-01-N.raw",
                        "status": "importado",
                        "metadata": {"points": 15},
                    },
                    {
                        "id": "drx-orphan",
                        "record_id": "rec-1",
                        "sample_code": "AM-99",
                        "original_filename": "orfao.raw",
                        "status": "importado",
                        "metadata": {"points": 15},
                    }
                ],
            },
        ), mock.patch.object(
            drx,
            "_load_mineral_classification_index",
            return_value={
                "available": True,
                "path": "/tmp/classificacao.json",
                "by_key": {
                    "am-01": {
                        "status": "ok",
                        "candidates": [
                            {
                                "mineral": "Kaolinite",
                                "group": "Grupo caulinita-serpentina",
                                "score": 0.82,
                                "confidence": "alta",
                                "matches": [{"reference_d": 7.15, "observed_d": 7.13}],
                            }
                        ],
                        "peaks": [{"two_theta": 12.4, "d": 7.13}],
                    }
                },
            },
        ), mock.patch.object(
            drx,
            "search_records",
            return_value=[
                {
                    "id": "rec-1",
                    "metadata": {"title": "Argila caulinitica"},
                    "custom_fields": {
                        "arg:amostras": [
                            {"codigo_amostra": "AM-01", "local_coleta": "Pelotas"},
                            {"codigo_amostra": "AM-02", "local_coleta": "Camaqua"},
                        ],
                        "arg:analises": [
                            {"analise_id": "AN-01", "codigo_amostra": "AM-01", "metodo": "DRX"}
                        ],
                        "arg:argilominerais": [
                            {"codigo_amostra": "AM-01", "nome": "Caulinita", "grupo": "Caulim-serpentina"}
                        ],
                        "arg:origem_formacao_geologica": "Formacao teste",
                        "arg:metodo_tecnicas_utilizadas": "DRX",
                    },
                }
            ],
        ):
            payload = drx.list_records_with_drx()

        self.assertEqual(payload["meta"]["total_records"], 1)
        self.assertEqual(payload["records"][0]["id"], "rec-1")
        self.assertEqual(payload["records"][0]["sample_code"], "AM-01")
        self.assertEqual(payload["records"][0]["argilominerais"], ["Caulinita"])
        self.assertEqual(payload["filters"]["sample_code"], ["AM-01"])
        self.assertEqual(len(payload["records"][0]["diffractograms"]), 1)
        self.assertEqual(payload["records"][0]["diffractograms"][0]["id"], "drx-1")
        self.assertEqual(payload["records"][0]["diffractograms"][0]["sample"]["locality"], "Pelotas")
        self.assertEqual(payload["records"][0]["diffractograms"][0]["analyses"][0]["analysis_id"], "AN-01")
        self.assertEqual(payload["records"][0]["diffractograms"][0]["treatment"], "natural")
        self.assertEqual(payload["records"][0]["diffractograms"][0]["mineral_candidates"][0]["mineral"], "Kaolinite")
        self.assertEqual(payload["records"][0]["diffractograms"][0]["detected_peaks"][0]["d"], 7.13)
        self.assertIn("Kaolinite", payload["filters"]["argilomineral"])
        self.assertEqual(payload["filters"]["treatment"], ["natural"])
        self.assertTrue(payload["records"][0]["diffractograms"][0]["traceability"]["sample_found"])

    def test_raw_snapshot_items_are_available_without_record(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            raw_path = tmp_path / "AM-01-N.RAW"
            raw_path.write_bytes(raw_legacy_bytes(tuple(range(10, 60))))
            snapshot_path = tmp_path / "classificacao_mineralogica_raw.json"
            treatment_path = tmp_path / "classificacao_tratamento_raw.json"
            snapshot_path.write_text(
                json.dumps(
                    {
                        "summary": {"files_total": 1},
                        "results": [
                            {
                                "filename": raw_path.name,
                                "path": str(raw_path),
                                "sample_code": "AM-01-N",
                                "status": "ok",
                                "metadata": {"points": 50},
                                "peaks": [{"two_theta": 12.4, "d": 7.13}],
                                "candidates": [{"mineral": "Kaolinite", "group": "Caulim-serpentina"}],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            treatment_path.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "filename": raw_path.name,
                                "path": str(raw_path),
                                "sample_code": "AM-01-N",
                                "sample_base": "AM-01",
                                "treatment": "natural",
                                "confidence": "alta",
                                "name_evidence": "sufixo N",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            drx._load_json_payload.cache_clear()
            drx._load_package_drx_enrichment_index.cache_clear()
            drx._load_advanced_drx_enrichment_index.cache_clear()
            drx._read_advanced_result_payload.cache_clear()
            with mock.patch.object(drx, "DRX_RAW_SNAPSHOT_PATH", snapshot_path), mock.patch.object(
                drx, "DRX_TREATMENT_SNAPSHOT_PATH", treatment_path
            ), mock.patch.object(drx, "SUPPORTED_LOCAL_IMPORT_ROOTS", (tmp_path,)):
                payload = drx.list_raw_snapshot_items(filters={"q": "AM-01"}, limit=10)
                item = payload["items"][0]
                curve = drx.load_diffractogram_data(item["diffractogram_id"])

        self.assertTrue(payload["success"])
        self.assertEqual(payload["pagination"]["total"], 1)
        self.assertEqual(item["preparation"], "natural")
        self.assertEqual(item["mineral_candidates"][0]["mineral"], "Kaolinite")
        self.assertEqual(len(curve["two_theta"]), 50)
        self.assertEqual(curve["metadata"]["sample_code"], "AM-01-N")

    def test_raw_snapshot_manual_mineral_override_marks_auxiliary_candidate(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            raw_path = tmp_path / "AND-06B (N).raw"
            raw_path.write_bytes(raw_legacy_bytes(tuple(range(10, 60))))
            snapshot_path = tmp_path / "classificacao_mineralogica_raw.json"
            treatment_path = tmp_path / "classificacao_tratamento_raw.json"
            overrides_path = tmp_path / "manual_mineral_overrides.json"
            snapshot_path.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "filename": raw_path.name,
                                "path": str(raw_path),
                                "sample_code": "AND-06B (N)",
                                "status": "ok",
                                "candidates": [{"mineral": "Allophane", "group": "amorphous"}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            treatment_path.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "filename": raw_path.name,
                                "path": str(raw_path),
                                "sample_code": "AND-06B (N)",
                                "sample_base": "AND-06B",
                                "treatment": "indeterminado",
                                "name_evidence": "sem marcador N/G/C no nome",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            overrides_path.write_text(
                json.dumps(
                    {
                        "schema_version": "argiloteca.drx.manual_mineral_overrides.v1",
                        "items": [
                            {
                                "id": "manual-and-06b-chlorite",
                                "match": {"sample_base": "AND-06B"},
                                "candidate": {
                                    "mineral": "Chlorite",
                                    "group": "chlorite_group",
                                    "score": 0.95,
                                    "confidence": "curatorial",
                                    "argilomineral_id": "chlorite",
                                },
                                "warnings": ["curadoria manual auxiliar"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            drx._load_json_payload.cache_clear()
            drx._load_manual_mineral_overrides.cache_clear()
            drx._load_package_drx_enrichment_index.cache_clear()
            drx._load_advanced_drx_enrichment_index.cache_clear()
            drx._read_advanced_result_payload.cache_clear()
            with mock.patch.object(drx, "DRX_RAW_SNAPSHOT_PATH", snapshot_path), mock.patch.object(
                drx, "DRX_TREATMENT_SNAPSHOT_PATH", treatment_path
            ), mock.patch.object(drx, "DRX_MANUAL_MINERAL_OVERRIDES_PATH", overrides_path), mock.patch.object(
                drx, "SUPPORTED_LOCAL_IMPORT_ROOTS", (tmp_path,)
            ):
                payload = drx.list_raw_snapshot_items(filters={"q": "AND-06B"}, limit=10)
                item = payload["items"][0]

        self.assertEqual(item["mineral_candidates"][0]["mineral"], "Chlorite")
        self.assertEqual(item["preparation"], "natural")
        self.assertEqual(item["sample_base"], "AND-06B")
        self.assertTrue(item["mineral_candidates"][0]["override"])
        self.assertEqual(item["mineral_candidates"][0]["policy"], "curatorial_auxiliary_not_confirmatory")
        self.assertEqual(item["mineral_candidates"][1]["mineral"], "Allophane")
        self.assertIn("Chlorite", item["argilominerais"])
        self.assertTrue(item["traceability"]["manual_mineral_override"])
        self.assertEqual(item["traceability"]["manual_mineral_override_policy"], "curatorial_auxiliary_not_confirmatory")
        self.assertEqual(item["warnings"], ["curadoria manual auxiliar"])

    def test_raw_snapshot_items_include_package_advanced_results(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_path = tmp_path / "AM-01-N.RAW"
            raw_path.write_bytes(raw_legacy_bytes(tuple(range(10, 60))))
            digest = drx._sha256_file(raw_path)
            snapshot_path = tmp_path / "classificacao_mineralogica_raw.json"
            treatment_path = tmp_path / "classificacao_tratamento_raw.json"
            packages_dir = tmp_path / "packages"
            static_packages_dir = tmp_path / "static-packages"
            advanced_path = tmp_path / "advanced" / "AM-01-N.RAW.json"
            advanced_path.parent.mkdir()
            advanced_path.write_text(json.dumps({"curve": {"two_theta": [1, 2, 3]}}), encoding="utf-8")
            packages_dir.joinpath("rec-1").mkdir(parents=True)
            packages_dir.joinpath("rec-1", "drx_manifest.json").write_text(
                json.dumps(
                    {
                        "record_id": "rec-1",
                        "items": [
                            {
                                "id": "drx:AM-01-N",
                                "filename": raw_path.name,
                                "sample_code": "AM-01-N",
                                "raw_path": str(raw_path),
                                "sha256": digest,
                                "advanced_result_path": str(advanced_path),
                                "advanced_summary": {"fit_results": 1},
                                "fit_results": [{"peak_id": "peak:1", "fwhm": 0.18}],
                                "mineral_evidence": [{"status": "candidate"}],
                                "qc_flags": [{"code": "ok"}],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            snapshot_path.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "filename": raw_path.name,
                                "path": str(raw_path),
                                "sample_code": "AM-01-N",
                                "status": "ok",
                                "peaks": [{"two_theta": 12.4, "d": 7.13}],
                                "candidates": [{"mineral": "Kaolinite"}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            treatment_path.write_text(json.dumps({"results": []}), encoding="utf-8")

            drx._load_json_payload.cache_clear()
            drx._load_package_drx_enrichment_index.cache_clear()
            drx._load_advanced_drx_enrichment_index.cache_clear()
            drx._read_advanced_result_payload.cache_clear()
            with mock.patch.object(drx, "DRX_RAW_SNAPSHOT_PATH", snapshot_path), mock.patch.object(
                drx, "DRX_TREATMENT_SNAPSHOT_PATH", treatment_path
            ), mock.patch.object(drx, "SUPPORTED_LOCAL_IMPORT_ROOTS", (tmp_path,)), mock.patch.object(
                drx, "ANALYTICAL_PACKAGES_DIR", packages_dir
            ), mock.patch.object(drx, "STATIC_ANALYTICAL_PACKAGES_DIR", static_packages_dir), mock.patch.object(
                drx, "PACKAGE_ALIASES_PATH", packages_dir / "aliases.json"
            ):
                payload = drx.list_raw_snapshot_items(limit=10)
                item = payload["items"][0]
                curve = drx.load_diffractogram_data(item["diffractogram_id"])

        self.assertEqual(str(advanced_path), item["advanced_result_path"])
        self.assertEqual(0.18, item["fit_results"][0]["fwhm"])
        self.assertEqual("rec-1", item["package_record_id"])
        self.assertTrue(item["traceability"]["analytical_package_match"])
        self.assertEqual(1, payload["meta"]["package_enriched_items"])
        self.assertEqual(1, payload["meta"]["package_enriched_with_fwhm"])
        self.assertEqual({"rec-1": 1}, payload["meta"]["package_enriched_record_counts"])
        self.assertEqual(str(advanced_path), curve["metadata"]["advanced_result_path"])
        self.assertEqual(0.18, curve["metadata"]["fit_results"][0]["fwhm"])

    def test_raw_snapshot_package_alias_prefers_canonical_record_id(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_path = tmp_path / "AM-01-N.RAW"
            raw_path.write_bytes(raw_legacy_bytes(tuple(range(10, 60))))
            digest = drx._sha256_file(raw_path)
            snapshot_path = tmp_path / "classificacao_mineralogica_raw.json"
            treatment_path = tmp_path / "classificacao_tratamento_raw.json"
            packages_dir = tmp_path / "packages"
            static_packages_dir = tmp_path / "static-packages"
            aliases_path = packages_dir / "aliases.json"
            advanced_path = tmp_path / "advanced" / "AM-01-N.RAW.json"
            advanced_path.parent.mkdir()
            advanced_path.write_text(json.dumps({"curve": {"two_theta": [1, 2, 3]}}), encoding="utf-8")
            manifest_item = {
                "id": "drx:AM-01-N",
                "filename": raw_path.name,
                "sample_code": "AM-01-N",
                "raw_path": str(raw_path),
                "sha256": digest,
                "advanced_result_path": str(advanced_path),
                "advanced_summary": {"fit_results": 1},
                "fit_results": [{"peak_id": "peak:1", "fwhm": 0.18}],
            }
            for record_id in ("p3mpr-4y63", "p3mpr-4y638"):
                record_dir = packages_dir / record_id
                record_dir.mkdir(parents=True)
                record_dir.joinpath("drx_manifest.json").write_text(
                    json.dumps({"record_id": record_id, "items": [manifest_item]}),
                    encoding="utf-8",
                )
            aliases_path.write_text(
                json.dumps({"aliases": {"p3mpr-4y63": {"drx": "p3mpr-4y638"}}}),
                encoding="utf-8",
            )
            snapshot_path.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "filename": raw_path.name,
                                "path": str(raw_path),
                                "sample_code": "AM-01-N",
                                "status": "ok",
                                "peaks": [{"two_theta": 12.4, "d": 7.13}],
                                "candidates": [{"mineral": "Kaolinite"}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            treatment_path.write_text(json.dumps({"results": []}), encoding="utf-8")

            drx._load_json_payload.cache_clear()
            drx._load_package_drx_enrichment_index.cache_clear()
            drx._load_advanced_drx_enrichment_index.cache_clear()
            drx._read_advanced_result_payload.cache_clear()
            with mock.patch.object(drx, "DRX_RAW_SNAPSHOT_PATH", snapshot_path), mock.patch.object(
                drx, "DRX_TREATMENT_SNAPSHOT_PATH", treatment_path
            ), mock.patch.object(drx, "SUPPORTED_LOCAL_IMPORT_ROOTS", (tmp_path,)), mock.patch.object(
                drx, "ANALYTICAL_PACKAGES_DIR", packages_dir
            ), mock.patch.object(drx, "STATIC_ANALYTICAL_PACKAGES_DIR", static_packages_dir), mock.patch.object(
                drx, "PACKAGE_ALIASES_PATH", aliases_path
            ):
                payload = drx.list_raw_snapshot_items(limit=10)
                item = payload["items"][0]

        self.assertEqual("p3mpr-4y638", item["package_record_id"])
        self.assertEqual("p3mpr-4y638", item["traceability"]["analytical_package_record_id"])
        self.assertEqual({"p3mpr-4y638": 1}, payload["meta"]["package_enriched_record_counts"])

    def test_raw_snapshot_items_include_general_advanced_results_without_package(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_path = tmp_path / "AM-02-G.RAW"
            raw_path.write_bytes(raw_legacy_bytes(tuple(range(20, 70))))
            snapshot_path = tmp_path / "classificacao_mineralogica_raw.json"
            treatment_path = tmp_path / "classificacao_tratamento_raw.json"
            packages_dir = tmp_path / "packages"
            static_packages_dir = tmp_path / "static-packages"
            advanced_manifest = tmp_path / "processamento_avancado_manifest.jsonl"
            advanced_results = tmp_path / "curvas_avancadas"
            advanced_path = advanced_results / "AM-02-G.RAW.json"
            advanced_results.mkdir()
            advanced_path.write_text(
                json.dumps(
                    {
                        "success": True,
                        "filename": raw_path.name,
                        "sample_id": "AM-02-G",
                        "raw_path": str(raw_path),
                        "curve": {"two_theta": [3.0, 3.02, 3.04], "normalization": "max"},
                        "peaks": [{"peak_index": 1, "two_theta": 12.2, "d_angstrom": 7.25}],
                        "fit_results": [{"peak_id": "peak:1", "center_2theta": 12.2, "fwhm": 0.31}],
                        "mineral_evidence": [{"mineral_candidate": "Smectite"}],
                        "qc_flags": [{"code": "ok"}],
                    }
                ),
                encoding="utf-8",
            )
            advanced_manifest.write_text(
                json.dumps(
                    {
                        "success": True,
                        "output": str(advanced_path),
                        "raw_path": str(raw_path),
                        "filename": raw_path.name,
                        "sample_id": "AM-02-G",
                        "points": 50,
                        "peaks": 1,
                        "fit_results": 1,
                        "mineral_evidence": 1,
                        "qc_flags": 1,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            snapshot_path.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "filename": raw_path.name,
                                "path": str(raw_path),
                                "sample_code": "AM-02-G",
                                "status": "ok",
                                "peaks": [{"two_theta": 12.2, "d": 7.25}],
                                "candidates": [{"mineral": "Smectite"}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            treatment_path.write_text(json.dumps({"results": []}), encoding="utf-8")

            drx._load_json_payload.cache_clear()
            drx._load_package_drx_enrichment_index.cache_clear()
            drx._load_advanced_drx_enrichment_index.cache_clear()
            drx._read_advanced_result_payload.cache_clear()
            with mock.patch.object(drx, "DRX_RAW_SNAPSHOT_PATH", snapshot_path), mock.patch.object(
                drx, "DRX_TREATMENT_SNAPSHOT_PATH", treatment_path
            ), mock.patch.object(drx, "SUPPORTED_LOCAL_IMPORT_ROOTS", (tmp_path,)), mock.patch.object(
                drx, "ANALYTICAL_PACKAGES_DIR", packages_dir
            ), mock.patch.object(drx, "STATIC_ANALYTICAL_PACKAGES_DIR", static_packages_dir), mock.patch.object(
                drx, "PACKAGE_ALIASES_PATH", packages_dir / "aliases.json"
            ), mock.patch.object(drx, "DRX_ADVANCED_MANIFEST_PATH", advanced_manifest), mock.patch.object(
                drx, "DRX_ADVANCED_RESULTS_DIR", advanced_results
            ):
                payload = drx.list_raw_snapshot_items(limit=10)
                item = payload["items"][0]
                curve = drx.load_diffractogram_data(item["diffractogram_id"])

        self.assertEqual(str(advanced_path), item["advanced_result_path"])
        self.assertEqual(0.31, item["fit_results"][0]["fwhm"])
        self.assertNotIn("package_record_id", item)
        self.assertTrue(item["traceability"]["advanced_processing_match"])
        self.assertEqual(1, payload["meta"]["advanced_processing_enriched_items"])
        self.assertEqual(1, payload["meta"]["advanced_processing_enriched_with_fwhm"])
        self.assertEqual(str(advanced_path), curve["metadata"]["advanced_result_path"])
        self.assertEqual(0.31, curve["metadata"]["fit_results"][0]["fwhm"])

    def test_raw_snapshot_advanced_processing_is_applied_after_pagination(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_one = tmp_path / "AM-03-N.RAW"
            raw_two = tmp_path / "AM-04-N.RAW"
            raw_one.write_bytes(raw_legacy_bytes(tuple(range(10, 60))))
            raw_two.write_bytes(raw_legacy_bytes(tuple(range(20, 70))))
            snapshot_path = tmp_path / "classificacao_mineralogica_raw.json"
            treatment_path = tmp_path / "classificacao_tratamento_raw.json"
            packages_dir = tmp_path / "packages"
            static_packages_dir = tmp_path / "static-packages"
            advanced_manifest = tmp_path / "processamento_avancado_manifest.jsonl"
            advanced_results = tmp_path / "curvas_avancadas"
            advanced_results.mkdir()
            advanced_one = advanced_results / "AM-03-N.RAW.json"
            advanced_two = advanced_results / "AM-04-N.RAW.json"
            advanced_one.write_text(
                json.dumps({"success": True, "fit_results": [{"peak_id": "p1", "fwhm": 0.2}]}),
                encoding="utf-8",
            )
            advanced_two.write_text(
                json.dumps({"success": True, "fit_results": [{"peak_id": "p2", "fwhm": 0.4}]}),
                encoding="utf-8",
            )
            advanced_manifest.write_text(
                json.dumps(
                    {
                        "success": True,
                        "raw_path": str(raw_one),
                        "filename": raw_one.name,
                        "output": str(advanced_one),
                        "sample_id": "AM-03-N",
                    }
                )
                + "\n"
                + json.dumps(
                    {
                        "success": True,
                        "raw_path": str(raw_two),
                        "filename": raw_two.name,
                        "output": str(advanced_two),
                        "sample_id": "AM-04-N",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            snapshot_path.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "filename": raw_one.name,
                                "path": str(raw_one),
                                "sample_code": "AM-03-N",
                                "status": "ok",
                                "candidates": [{"mineral": "Kaolinite"}],
                            },
                            {
                                "filename": raw_two.name,
                                "path": str(raw_two),
                                "sample_code": "AM-04-N",
                                "status": "ok",
                                "candidates": [{"mineral": "Illite"}],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            treatment_path.write_text(json.dumps({"results": []}), encoding="utf-8")

            drx._load_json_payload.cache_clear()
            drx._load_package_drx_enrichment_index.cache_clear()
            drx._load_advanced_drx_enrichment_index.cache_clear()
            drx._read_advanced_result_payload.cache_clear()
            with mock.patch.object(drx, "DRX_RAW_SNAPSHOT_PATH", snapshot_path), mock.patch.object(
                drx, "DRX_TREATMENT_SNAPSHOT_PATH", treatment_path
            ), mock.patch.object(drx, "SUPPORTED_LOCAL_IMPORT_ROOTS", (tmp_path,)), mock.patch.object(
                drx, "ANALYTICAL_PACKAGES_DIR", packages_dir
            ), mock.patch.object(drx, "STATIC_ANALYTICAL_PACKAGES_DIR", static_packages_dir), mock.patch.object(
                drx, "PACKAGE_ALIASES_PATH", packages_dir / "aliases.json"
            ), mock.patch.object(drx, "DRX_ADVANCED_MANIFEST_PATH", advanced_manifest), mock.patch.object(
                drx, "DRX_ADVANCED_RESULTS_DIR", advanced_results
            ), mock.patch.object(
                drx, "_read_advanced_result_payload", wraps=drx._read_advanced_result_payload
            ) as read_advanced_result:
                payload = drx.list_raw_snapshot_items(limit=1)

        self.assertEqual(2, payload["pagination"]["total"])
        self.assertEqual(1, payload["pagination"]["returned"])
        self.assertEqual(2, payload["meta"]["advanced_processing_enriched_items"])
        self.assertEqual(1, payload["meta"]["advanced_processing_returned_items"])
        self.assertEqual(1, payload["meta"]["advanced_processing_returned_with_fwhm"])
        self.assertEqual("returned_page", payload["meta"]["advanced_processing_enriched_with_fwhm_scope"])
        self.assertEqual(1, read_advanced_result.call_count)

    def test_raw_snapshot_comparison_suggestions_use_full_filtered_set(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_paths = [
                tmp_path / "AM-10-N.RAW",
                tmp_path / "AM-10-G.RAW",
                tmp_path / "AM-10-C.RAW",
                tmp_path / "AM-11-N.RAW",
                tmp_path / "AM-11-G.RAW",
            ]
            for raw_path in raw_paths:
                raw_path.write_bytes(raw_legacy_bytes(tuple(range(10, 60))))
            snapshot_path = tmp_path / "classificacao_mineralogica_raw.json"
            treatment_path = tmp_path / "classificacao_tratamento_raw.json"
            packages_dir = tmp_path / "packages"
            static_packages_dir = tmp_path / "static-packages"
            snapshot_path.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "filename": raw_path.name,
                                "path": str(raw_path),
                                "sample_code": raw_path.stem,
                                "status": "ok",
                                "candidates": [{"mineral": "Kaolinite", "group": "Caulim-serpentina"}],
                            }
                            for raw_path in raw_paths
                        ]
                    }
                ),
                encoding="utf-8",
            )
            treatment_path.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "filename": raw_path.name,
                                "path": str(raw_path),
                                "sample_code": raw_path.stem,
                                "sample_base": raw_path.stem.rsplit("-", 1)[0],
                                "treatment": {
                                    "N": "natural",
                                    "G": "glicolado",
                                    "C": "calcinado",
                                }[raw_path.stem.rsplit("-", 1)[1]],
                            }
                            for raw_path in raw_paths
                        ]
                    }
                ),
                encoding="utf-8",
            )

            drx._load_json_payload.cache_clear()
            drx._load_package_drx_enrichment_index.cache_clear()
            drx._load_advanced_drx_enrichment_index.cache_clear()
            drx._read_advanced_result_payload.cache_clear()
            with mock.patch.object(drx, "DRX_RAW_SNAPSHOT_PATH", snapshot_path), mock.patch.object(
                drx, "DRX_TREATMENT_SNAPSHOT_PATH", treatment_path
            ), mock.patch.object(drx, "SUPPORTED_LOCAL_IMPORT_ROOTS", (tmp_path,)), mock.patch.object(
                drx, "ANALYTICAL_PACKAGES_DIR", packages_dir
            ), mock.patch.object(drx, "STATIC_ANALYTICAL_PACKAGES_DIR", static_packages_dir), mock.patch.object(
                drx, "PACKAGE_ALIASES_PATH", packages_dir / "aliases.json"
            ):
                payload = drx.build_raw_snapshot_comparison_suggestions(limit=10)

        suggestion_types = {suggestion["type"] for suggestion in payload["suggestions"]}
        trio = next(suggestion for suggestion in payload["suggestions"] if suggestion["type"] == "trio")
        self.assertEqual(5, payload["meta"]["items_total"])
        self.assertEqual(2, payload["meta"]["sample_bases_total"])
        self.assertIn("trio", suggestion_types)
        self.assertIn("ng", suggestion_types)
        self.assertEqual("AM-10", trio["group"]["sampleBase"])
        self.assertEqual(3, len(trio["items"]))


class DrxFrontendStaticTest(unittest.TestCase):
    """Representa a estrutura `DrxFrontendStaticTest` dentro do fluxo técnico do painel Argiloteca, mantendo dados e operações relacionados ao módulo."""
    def test_comparison_suggestions_use_server_snapshot_suggestions(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        script_path = (
            Path(__file__).resolve().parents[1]
            / "argiloteca"
            / "static"
            / "js"
            / "drx-comparacao.js"
        )
        script = script_path.read_text(encoding="utf-8")

        self.assertIn("rawSnapshotSuggestionsUrl", script)
        self.assertIn("function loadSuggestionPayload(recordId)", script)
        self.assertIn('query.set("limit", "5000")', script)
        self.assertIn("payload.suggestions || buildComparisonSuggestions", script)
        self.assertNotIn("suggestions.slice(0, 60)", script)

    def test_drx_panel_uses_backend_ngc_workflow_contract(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        base_path = Path(__file__).resolve().parents[1] / "argiloteca"
        template = base_path.joinpath("templates", "semantic-ui", "argiloteca", "drx_comparacao.html").read_text(
            encoding="utf-8"
        )
        script = base_path.joinpath("static", "js", "drx-comparacao.js").read_text(encoding="utf-8")

        self.assertIn("data-ngc-workflow-url", template)
        self.assertIn("data-selection-report-url", template)
        self.assertIn("api_drx_ngc_workflow", template)
        self.assertIn("api_drx_selection_report", template)
        self.assertIn("const ngcWorkflowUrl", script)
        self.assertIn("const selectionReportUrl", script)
        self.assertIn("function refreshNgcWorkflow", script)
        self.assertIn("Workflow N/G/C backend", script)
        self.assertIn("Picos companheiros", script)
        self.assertIn("Comportamento N/G/C", script)
        self.assertIn("Avisos de mistura/interestratificação", script)
        self.assertIn("mixed_layer_suspected", script)
        self.assertIn("i_abs", script)
        self.assertIn("i_norm", script)
        self.assertIn("fwhm", script)
        self.assertIn("area", script)
        self.assertIn("tau", script)


class DrxEndpointTest(unittest.TestCase):
    """Representa a estrutura `DrxEndpointTest` dentro do fluxo técnico do painel Argiloteca, mantendo dados e operações relacionados ao módulo."""
    def test_drx_records_endpoint_lists_payload(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))

        with mock.patch.object(
            views,
            "list_records_with_drx",
            return_value={"success": True, "records": [], "meta": {"total_records": 0}},
        ):
            response = app.test_client().get("/api/argiloteca/drx/registros")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])

    def test_raw_snapshot_suggestions_endpoint_returns_payload(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))

        with mock.patch.object(
            views,
            "build_raw_snapshot_comparison_suggestions",
            return_value={
                "success": True,
                "suggestions": [{"type": "trio", "items": []}],
                "meta": {"items_total": 9910},
                "pagination": {"total": 1, "returned": 1},
            },
        ) as build_suggestions:
            response = app.test_client().get("/api/argiloteca/drx/raw-snapshot/sugestoes?limit=25")

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(9910, payload["meta"]["items_total"])
        build_suggestions.assert_called_once()
        self.assertEqual(25, build_suggestions.call_args.kwargs["limit"])

    def test_import_endpoint_rejects_unknown_record(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))

        with mock.patch.object(views, "record_exists", return_value=False):
            response = app.test_client().post(
                "/api/argiloteca/drx/importar",
                json={
                    "record_id": "SEU_RECORD_ID",
                    "sample_code": "AM-01",
                    "path": "/Users/visualizacao-drx/raw/PORV33G.RAW",
                },
            )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()["success"])

    def test_external_raw_endpoint_returns_curve_without_record_association(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))

        response = app.test_client().post(
            "/api/argiloteca/drx/externo/curva",
            data={"file": (BytesIO(raw_legacy_bytes(tuple(range(10, 60)))), "externo.RAW")},
            content_type="multipart/form-data",
        )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sample_code"], "externo")
        self.assertFalse(payload["metadata"]["stored"])
        self.assertIn("detected_peaks", payload)
        self.assertIn("mineral_candidates", payload)

    def test_external_raw_endpoint_accepts_raw101_layout(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))

        response = app.test_client().post(
            "/api/argiloteca/drx/externo/curva",
            data={"file": (BytesIO(raw101_bytes(tuple(range(100, 160)))), "NP02C (G).raw")},
            content_type="multipart/form-data",
        )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sample_code"], "NP02C (G)")
        self.assertEqual(payload["metadata"]["detected_format"], "RAW1.01 float32")

    def test_external_curve_endpoint_accepts_csv_layout(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))
        content = "two_theta,intensity\n" + "\n".join(
            f"{4 + index * 0.05:.2f},{10 + index}" for index in range(20)
        )

        response = app.test_client().post(
            "/api/argiloteca/drx/externo/curva",
            data={"file": (BytesIO(content.encode("utf-8")), "externo.csv"), "wavelength_angstrom": "1.5418"},
            content_type="multipart/form-data",
        )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["sample_code"], "externo")
        self.assertEqual(payload["metadata"]["parser_format"], "text_curve")
        self.assertEqual(payload["analysis_run"]["schema_version"], "argiloteca.drx.analysis_run.v1")
        self.assertEqual(payload["analysis_run"]["input"]["parser_format"], "text_curve")
        self.assertEqual(payload["analysis_run"]["input"]["wavelength_angstrom"], 1.5418)
        self.assertFalse(payload["analysis_run"]["input"]["stored"])
        self.assertIn("reproducibility", payload["analysis_run"])
        self.assertIn("diagnostic_evidence", payload)
        self.assertEqual(payload["technical_report"]["schema_version"], "argiloteca.drx.technical_report.v1")
        self.assertEqual(payload["technical_report"]["analysis_schema_version"], "argiloteca.drx.analysis_run.v1")
        self.assertEqual(payload["total_points"], 20)

    def test_external_curve_endpoint_rejects_large_upload(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))
        with mock.patch.object(views, "DRX_TEMP_UPLOAD_MAX_BYTES", 32):
            response = app.test_client().post(
                "/api/argiloteca/drx/externo/curva",
                data={"file": (BytesIO(b"x" * 64), "grande.csv")},
                content_type="multipart/form-data",
            )

        payload = response.get_json()
        self.assertEqual(response.status_code, 413)
        self.assertFalse(payload["success"])
        self.assertIn("limite", payload["error"])

    def test_technical_report_endpoint_returns_json_and_html(self):
        """
        Gera artefatos derivados, relatórios ou saídas serializadas com parâmetros e proveniência para auditoria posterior.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))
        curve_payload = {
            "metadata": {
                "sample_code": "AM-01",
                "original_filename": "AM-01.csv",
                "parser_format": "text_curve",
                "detected_format": "text two-column diffractogram",
                "preparation": "natural",
            },
            "two_theta": [4.0 + index * 0.05 for index in range(40)],
            "intensity": [10.0 + index for index in range(40)],
        }

        with mock.patch.object(views, "load_diffractogram_data", return_value=curve_payload):
            json_response = app.test_client().get("/api/argiloteca/drx/technical-report/drx-1")
            html_response = app.test_client().get("/argiloteca/drx/reports/technical/drx-1")

        payload = json_response.get_json()
        self.assertEqual(json_response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["technical_report"]["schema_version"], "argiloteca.drx.technical_report.v1")
        self.assertEqual(html_response.status_code, 200)
        self.assertIn("Relatório técnico DRX", html_response.get_data(as_text=True))

    def test_reference_compare_endpoint_returns_versioned_payload(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))
        two_theta = [4.0 + index * 0.05 for index in range(160)]
        intensity = [10.0 for _ in two_theta]
        intensity[min(range(len(two_theta)), key=lambda index: abs(two_theta[index] - 8.84))] = 500.0
        curve_payload = {
            "metadata": {
                "sample_code": "AM-REF",
                "original_filename": "AM-REF.csv",
                "parser_format": "text_curve",
                "detected_format": "text two-column diffractogram",
            },
            "two_theta": two_theta,
            "intensity": intensity,
        }

        with mock.patch.object(views, "load_diffractogram_data", return_value=curve_payload):
            response = app.test_client().post(
                "/api/argiloteca/drx/references/compare/drx-ref",
                data={"reference_file": (BytesIO(b"8.84,100\n12.30,40\n"), "ref.xy")},
                content_type="multipart/form-data",
            )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["reference_pattern"]["schema_version"], "argiloteca.drx.reference_pattern.v1")
        self.assertEqual(payload["reference_comparison"]["schema_version"], "argiloteca.drx.reference_comparison.v1")
        self.assertIn("reference_comparison", payload["technical_report"])

    def test_reference_compare_indexed_endpoint_returns_report(self):
        """
        Gera artefatos derivados, relatórios ou saídas serializadas com parâmetros e proveniência para auditoria posterior.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))
        curve_payload = {
            "metadata": {
                "sample_code": "AM-IDX",
                "original_filename": "AM-IDX.csv",
                "parser_format": "text_curve",
                "detected_format": "text two-column diffractogram",
            },
            "two_theta": [4.0 + index * 0.05 for index in range(160)],
            "intensity": [10.0 for _ in range(160)],
        }
        curve_payload["intensity"][min(range(160), key=lambda index: abs(curve_payload["two_theta"][index] - 8.84))] = 500.0

        with mock.patch.object(views, "load_diffractogram_data", return_value=curve_payload), mock.patch.object(
            views,
            "reference_pattern_from_index",
            return_value={
                "success": True,
                "schema_version": "argiloteca.drx.indexed_reference_pattern.v1",
                "reference_id": "rruff_odr:illite:R1:xy",
                "filename": "illite.xy",
                "source": "RRUFF_ODR",
                "peaks": [{"peak_index": 1, "two_theta": 8.84, "d_angstrom": 9.99, "relative_intensity": 100}],
                "peak_count": 1,
                "warnings": [],
                "interpretation_policy": "Referencia indexada auxiliar.",
            },
        ):
            response = app.test_client().post(
                "/api/argiloteca/drx/references/compare-indexed/drx-indexed",
                json={"reference_id": "rruff_odr:illite:R1:xy"},
            )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["reference_pattern"]["schema_version"], "argiloteca.drx.indexed_reference_pattern.v1")
        self.assertEqual(payload["reference_comparison"]["reference_id"], "rruff_odr:illite:R1:xy")
        self.assertEqual(payload["technical_report"]["summary"]["reference_match_count"], 1)

    def test_science_engine_status_endpoint_returns_contract(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))
        with mock.patch.object(
            views,
            "science_engine_status",
            return_value={
                "schema_version": "argiloteca.drx.science_engine.v1",
                "available": True,
                "packages": {"pymatgen": "2025.10.7"},
            },
        ):
            response = app.test_client().get("/api/argiloteca/drx/science-engine/status")

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["engine"]["schema_version"], "argiloteca.drx.science_engine.v1")
        self.assertEqual(payload["engine"]["packages"]["pymatgen"], "2025.10.7")

    def test_cif_simulation_endpoint_returns_versioned_payload(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))
        expected = {
            "success": True,
            "schema_version": "argiloteca.drx.cif_simulation.v1",
            "filename": "si.cif",
            "engine": "pymatgen.XRDCalculator",
            "peak_count": 1,
            "peaks": [{"two_theta": 28.44, "relative_intensity": 100.0}],
        }

        with mock.patch.object(views, "build_cif_simulation_payload", return_value=expected) as mocked_simulation:
            response = app.test_client().post(
                "/api/argiloteca/drx/cif/simulate?max_peaks=25",
                data={"file": (BytesIO(b"data_Si\n_chemical_formula_sum 'Si'\n"), "si.cif"), "wavelength": "CuKa"},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["schema_version"], "argiloteca.drx.cif_simulation.v1")
        call_kwargs = mocked_simulation.call_args.kwargs
        self.assertEqual(call_kwargs["filename"], "si.cif")
        self.assertEqual(call_kwargs["wavelength"], "CuKa")
        self.assertEqual(call_kwargs["max_peaks"], 25)

    def test_ngc_workflow_endpoint_returns_versioned_payload(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))
        expected = {
            "success": True,
            "schema_version": "argiloteca.drx.ngc_workflow.v1",
            "group_count": 1,
            "groups": [{"sample_base": "AM-01", "best_candidate": {"mineral_candidate": "esmectita expansiva"}}],
        }

        with mock.patch.object(views, "build_ngc_workflow", return_value=expected) as mocked_workflow:
            response = app.test_client().post(
                "/api/argiloteca/drx/workflows/ngc",
                json={
                    "items": [
                        {
                            "sample_base": "AM-01",
                            "preparation": "glicolado",
                            "peaks": [{"d_angstrom": 17.1, "relative_intensity": 100}],
                        }
                    ]
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["schema_version"], "argiloteca.drx.ngc_workflow.v1")
        self.assertEqual(mocked_workflow.call_args.args[0][0]["sample_base"], "AM-01")

    def test_selection_report_endpoint_returns_reproducible_contract(self):
        """
        Gera artefatos derivados, relatórios ou saídas serializadas com parâmetros e proveniência para auditoria posterior.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))

        response = app.test_client().post(
            "/api/argiloteca/drx/reports/selection",
            json={
                "view_parameters": {"mode": "normalized"},
                "items": [
                    {
                        "id": "drx-1",
                        "filename": "AM-01-G.raw",
                        "sample_base": "AM-01",
                        "preparation": "glicolado",
                        "peaks": [{"d_angstrom": 17.1, "two_theta": 5.16, "relative_intensity": 100}],
                    }
                ],
            },
        )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["schema_version"], "argiloteca.drx.selection_report.v1")
        self.assertEqual(payload["ngc_workflow"]["schema_version"], "argiloteca.drx.ngc_workflow.v1")
        self.assertIn("input_hash", payload["reproducibility"])

    def test_reference_index_endpoint_returns_compact_payload(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))
        expected = {
            "success": True,
            "schema_version": "argiloteca.drx.reference_index.v1",
            "total": 1,
            "references": [{"reference_id": "rruff_odr:kaolinite:R1:xy"}],
        }

        with mock.patch.object(views, "search_reference_index", return_value=expected) as mocked_search:
            response = app.test_client().get("/api/argiloteca/drx/references?q=kaolinite&source=RRUFF_ODR&limit=5")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["schema_version"], "argiloteca.drx.reference_index.v1")
        mocked_search.assert_called_once_with(query="kaolinite", source="RRUFF_ODR", limit=5)

    def test_external_job_endpoint_registers_out_of_request_job(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.dict(os.environ, {"ARGILOTECA_DRX_JOBS_DIR": tmpdir}):
            response = app.test_client().post(
                "/api/argiloteca/drx/jobs/external",
                json={"engine": "gsas2", "diffractogram_id": "drx-1"},
            )
            created = response.get_json()
            status = app.test_client().get(
                "/api/argiloteca/drx/jobs/external/%s" % created["job"]["job_id"]
            )

        self.assertEqual(response.status_code, 202)
        self.assertTrue(created["success"])
        self.assertEqual(created["job"]["engine"], "gsas2")
        self.assertEqual(created["job"]["status"], "queued")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.get_json()["job"]["status"], "queued")

    def test_mineral_report_endpoint_exposes_curatorial_sources(self):
        """
        Gera artefatos derivados, relatórios ou saídas serializadas com parâmetros e proveniência para auditoria posterior.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))

        with mock.patch.object(
            views,
            "build_mineral_profile",
            return_value={
                "slug": "illite",
                "nome": "Illite",
                "nome_pt": "Ilita",
                "nome_cientifico_padronizado": "Illite",
                "classic_description": "Filossilicato usado como exemplo.",
                "quimica_mindat": "K0.65Al2.0[Al0.65Si3.35O10](OH)2",
                "difracao_raios_x_po_mindat": "Picos principais em torno de 10 A.",
                "petrologia_mindat": "Comum em rochas sedimentares e alteração.",
                "referencias_mindat_itens": ["Referencia Mindat exemplo"],
                "curatorial_facts": [
                    {"label": "Fonte externa", "value": "Mindat", "href": "https://www.mindat.org/"},
                ],
                "scientific_source_blocks": [
                    {
                        "key": "handbook_mineralogy",
                        "title": "Handbook of Mineralogy",
                        "href": "https://www.handbookofmineralogy.org/pdfs/illite.pdf",
                        "href_label": "Abrir ficha do Handbook",
                        "summary": "Ficha complementar com dados cristalográficos.",
                        "facts": [{"label": "Difração de raios X", "value": "10 A"}],
                    },
                    {
                        "key": "cms_source_clays",
                        "title": "Clay Minerals Society - Source Clays",
                        "href": "https://www.clays.org/sourceclays_data/",
                        "summary": "Materiais de referência comparativos.",
                        "samples": [{"code": "IMt-1", "label": "Silver Hill illite"}],
                    },
                ],
            },
        ):
            response = app.test_client().get("/argiloteca/argilominerais/illite/relatorio")

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["slug"], "illite")
        self.assertGreaterEqual(len(payload["technical_blocks"]), 4)
        self.assertEqual(payload["curatorial_facts"][0]["label"], "Fonte externa")
        self.assertEqual(payload["scientific_source_blocks"][0]["title"], "Handbook of Mineralogy")
        self.assertEqual(payload["scientific_source_blocks"][1]["title"], "Clay Minerals Society - Source Clays")


class AnalyticalPackageTest(unittest.TestCase):
    """Representa a estrutura `AnalyticalPackageTest` dentro do fluxo técnico do painel Argiloteca, mantendo dados e operações relacionados ao módulo."""
    def test_record_upload_manifest_uses_drx_analyses_and_record_files(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        record = {
            "id": "rec-1",
            "files": {
                "entries": {
                    "AM-01-N.RAW": {
                        "key": "AM-01-N.RAW",
                        "size": 1234,
                        "checksum": "sha256:abc",
                    }
                }
            },
            "custom_fields": {
                "arg:amostras": [
                    {
                        "codigo_amostra": "AM-01-N",
                        "local_coleta": "Lavras do Sul",
                        "contexto_geologico": "Alteracao hidrotermal",
                    }
                ],
                "arg:analises": [
                    {
                        "analise_id": "DRX-1",
                        "codigo_amostra": "AM-01-N",
                        "metodo": "drx",
                        "arquivo_resultado": "AM-01-N.RAW",
                        "resultado_principal": "DRX natural",
                    },
                    {
                        "analise_id": "FRX-1",
                        "codigo_amostra": "AM-01-N",
                        "metodo": "frx",
                        "arquivo_resultado": "quimica.csv",
                    },
                ],
            },
        }

        with mock.patch.object(analytical_packages, "_read_record", return_value=record):
            manifest = analytical_packages._build_record_upload_manifest("rec-1")

        self.assertIsNotNone(manifest)
        self.assertEqual(manifest["summary"]["total_files"], 1)
        self.assertEqual(manifest["source"]["kind"], "invenio_record_analyses")
        self.assertEqual(manifest["items"][0]["file_key"], "AM-01-N.RAW")
        self.assertEqual(manifest["items"][0]["preparation"], "natural")
        self.assertEqual(manifest["items"][0]["sample"]["locality"], "Lavras do Sul")

    def test_package_curve_reads_invenio_record_file_when_manifest_item_has_file_key(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with mock.patch.object(
            analytical_packages,
            "load_manifest",
            return_value={
                "_resolved_record_id": "rec-1",
                "items": [
                    {
                        "sample_code": "AM-01-N",
                        "filename": "AM-01-N.RAW",
                        "file_key": "AM-01-N.RAW",
                    }
                ],
            },
        ), mock.patch.object(
            analytical_packages,
            "_parse_record_file_curve",
            return_value=(
                {"points": 3, "detected_format": "RAW legacy float32"},
                [3.0, 3.02, 3.04],
                [10.0, 11.0, 12.0],
                3,
            ),
        ):
            payload = analytical_packages.load_package_curve("rec-1", sample_code="AM-01-N")

        self.assertTrue(payload["success"])
        self.assertEqual(payload["filename"], "AM-01-N.RAW")
        self.assertEqual(payload["metadata"]["points"], 3)

    def test_deposit_traceability_field_mentions_drx_package(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        asset_path = instance_deposit_asset("TraceabilityDepositField.js")
        if not asset_path.exists():
            self.skipTest(f"Asset local nao encontrado: {asset_path}")
        source = asset_path.read_text(encoding="utf-8")

        self.assertIn("Pacote analítico de DRX", source)
        self.assertIn("Vincular RAW pendentes como DRX", source)

    def test_scientific_context_panel_shows_title_before_fieldwork(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        asset_path = instance_deposit_asset("ScientificContextPanel.js")
        if not asset_path.exists():
            self.skipTest(f"Asset local nao encontrado: {asset_path}")
        source = asset_path.read_text(encoding="utf-8")
        lifecycle_list = source.index('<List relaxed divided className="mb-0">')
        title_position = source.index("<List.Header>Título do registro</List.Header>", lifecycle_list)
        fieldwork_position = source.index("<List.Header>Trabalho de Campo</List.Header>", lifecycle_list)

        self.assertIn("metadata.title", source)
        self.assertLess(title_position, fieldwork_position)

    def test_deposit_form_orders_invenio_metadata_after_scientific_blocks(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        asset_path = instance_deposit_asset("RDMDepositForm.js")
        if not asset_path.exists():
            self.skipTest(f"Asset local nao encontrado: {asset_path}")
        source = asset_path.read_text(encoding="utf-8")
        required_markers = (
            "<ScientificContextPanel />",
            "InvenioAppRdm.Deposit.TraceabilityCampaigns.container",
            "InvenioAppRdm.Deposit.SupportingScientificFields.container",
        )
        if not all(marker in source for marker in required_markers):
            self.skipTest(f"Asset local nao contem os blocos cientificos customizados: {asset_path}")

        context_position = source.index("<ScientificContextPanel />")
        files_position = source.index("InvenioAppRdm.Deposit.AccordionFieldFiles.container")
        scientific_positions = [
            source.index("InvenioAppRdm.Deposit.TraceabilityCampaigns.container"),
            source.index("InvenioAppRdm.Deposit.TraceabilitySamples.container"),
            source.index("InvenioAppRdm.Deposit.TraceabilityAnalyses.container"),
            source.index("InvenioAppRdm.Deposit.TraceabilityComposition.container"),
            source.index("InvenioAppRdm.Deposit.CustomFields.Argilominerais.container"),
            source.index("InvenioAppRdm.Deposit.TraceabilityPublications.container"),
            source.index("InvenioAppRdm.Deposit.SupportingScientificFields.container"),
        ]
        metadata_positions = [
            source.index("InvenioAppRdm.Deposit.AccordionFieldBasicInformation.container"),
            source.index("InvenioAppRdm.Deposit.AccordionFieldRecommendedInformation.container"),
            source.index("InvenioAppRdm.Deposit.AccordionFieldFunding.container"),
            source.index("InvenioAppRdm.Deposit.AccordionFieldAlternateIdentifiers.container"),
            source.index("InvenioAppRdm.Deposit.AccordionFieldRelatedWorks.container"),
            source.index("InvenioAppRdm.Deposit.AccordionFieldReferences.container"),
        ]

        self.assertLess(context_position, files_position)
        self.assertLess(files_position, min(scientific_positions))
        self.assertEqual(scientific_positions, sorted(scientific_positions))
        self.assertEqual(metadata_positions, sorted(metadata_positions))
        self.assertLess(max(scientific_positions), min(metadata_positions))

    def test_package_payload_filters_and_paginates_manifest(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with mock.patch.object(
            analytical_packages,
            "load_manifest",
            return_value={
                "summary": {"total_files": 2},
                "items": [
                    {
                        "sample_code": "AM-01-N",
                        "filename": "AM-01-N.RAW",
                        "preparation": "natural",
                        "mineral_candidates": [{"mineral": "Kaolinite"}],
                    },
                    {
                        "sample_code": "AM-01-G",
                        "filename": "AM-01-G.RAW",
                        "preparation": "glicolado",
                        "mineral_candidates": [{"mineral": "Smectite"}],
                    },
                ],
            },
        ):
            payload = analytical_packages.build_package_payload(
                "rec-1",
                preparation="natural",
                mineral="kaol",
                limit=1,
            )

        self.assertTrue(payload["exists"])
        self.assertEqual(payload["pagination"]["total"], 1)
        self.assertEqual(payload["items"][0]["sample_code"], "AM-01-N")

    def test_package_payload_uses_alias_when_new_version_has_no_manifest(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        def fake_exists(path):
            """
            Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
            
            Args:
                path: Valor de entrada consumido por esta etapa do fluxo.
            Returns:
                Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
            Raises:
                Exception: Propaga erros das dependências quando a validação ou o processamento falha.
            """
            return str(path).endswith("a8v7p-n9959/drx_manifest.json")

        manifest = {
            "summary": {"total_files": 1},
            "items": [{"sample_code": "AM-01-N", "filename": "AM-01-N.RAW"}],
        }

        with mock.patch.object(
            analytical_packages,
            "_load_aliases",
            return_value={"4rxma-end93": {"drx": "a8v7p-n9959"}},
        ), mock.patch.object(
            analytical_packages.Path,
            "exists",
            lambda path: fake_exists(path),
        ), mock.patch.object(
            analytical_packages.Path,
            "open",
            mock.mock_open(read_data=json.dumps(manifest)),
        ):
            payload = analytical_packages.build_package_payload("4rxma-end93")

        self.assertTrue(payload["exists"])
        self.assertEqual(payload["record_id"], "4rxma-end93")
        self.assertEqual(payload["package_record_id"], "a8v7p-n9959")
        self.assertEqual(payload["package_alias_from"], "4rxma-end93")
        self.assertEqual(payload["summary"]["total_files"], 1)

    def test_alias_file_accepts_metadata_wrapper(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with mock.patch.object(
            analytical_packages.Path,
            "open",
            mock.mock_open(read_data=json.dumps({"aliases": {"v2": {"drx": "v1"}}})),
        ):
            aliases = analytical_packages._load_aliases()

        self.assertEqual(aliases["v2"]["drx"], "v1")

    def test_external_curve_comparison_finds_existing_interpretation(self):
        """
        Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with mock.patch.object(
            analytical_packages,
            "load_manifest",
            return_value={
                "items": [
                    {
                        "sample_code": "AM-01-N",
                        "filename": "AM-01-N.RAW",
                        "sha256": "abc123",
                        "preparation": "natural",
                        "preparation_label": "Natural",
                        "metadata": {
                            "two_theta_start": 3.0,
                            "two_theta_end": 30.0,
                            "step": 0.02,
                            "points": 1351,
                        },
                        "detected_peaks": [
                            {"two_theta": 6.12, "d": 14.43},
                            {"two_theta": 12.4, "d": 7.13},
                        ],
                        "mineral_candidates": [{"mineral": "Kaolinite"}],
                    }
                ],
            },
        ):
            payload = analytical_packages.compare_external_curve_to_package(
                "rec-1",
                original_filename="AM-01-N.RAW",
                raw_sha256="abc123",
                metadata={
                    "two_theta_start": 3.0,
                    "two_theta_end": 30.0,
                    "step": 0.02,
                    "points": 1351,
                },
                detected_peaks=[{"two_theta": 6.121}, {"two_theta": 12.39}],
                mineral_candidates=[{"mineral": "Kaolinite"}],
            )

        self.assertTrue(payload["available"])
        self.assertEqual(payload["status"], "igual")
        self.assertTrue(payload["best_match"]["has_interpretation"])
        self.assertIn("interpretação", payload["message"])

    def test_external_curve_without_record_matches_global_raw_snapshot(self):
        """
        Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with mock.patch.object(
            drx,
            "list_raw_snapshot_items",
            return_value={
                "items": [
                    {
                        "id": "snapshot:abc",
                        "diffractogram_id": "snapshot:abc",
                        "sample_code": "HA + Nb",
                        "filename": "HA + Nb.raw",
                        "preparation": "indeterminado",
                        "preparation_label": "Indeterminado",
                        "detected_peaks": [{"two_theta": 6.1}],
                        "mineral_candidates": [{"mineral": "Kaolinite"}],
                    }
                ],
                "pagination": {"total": 1, "returned": 1},
            },
        ):
            payload = analytical_packages.compare_external_curve_to_package(
                None,
                original_filename="HA + Nb.raw",
                raw_sha256="abc123",
                metadata={"points": 3501},
            )

        self.assertTrue(payload["available"])
        self.assertEqual(payload["status"], "igual")
        self.assertEqual(payload["source"], "snapshot_geral_raw")
        self.assertEqual(payload["best_match"]["diffractogram_id"], "snapshot:abc")

    def test_external_curve_similarity_uses_peak_position_intensity_and_width(self):
        """
        Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with mock.patch.object(
            analytical_packages,
            "load_manifest",
            return_value={
                "items": [
                    {
                        "sample_code": "AM-01-N",
                        "filename": "AM-01-N.RAW",
                        "preparation": "natural",
                        "preparation_label": "Natural",
                        "metadata": {"two_theta_start": 2.0, "step": 0.02},
                        "detected_peaks": [
                            {
                                "peak_index": 1,
                                "two_theta": 4.30,
                                "relative_intensity": 82.0,
                            }
                        ],
                        "fit_results": [
                            {
                                "peak_id": "peak:1",
                                "fwhm": 0.18,
                                "fit_quality": "low",
                                "model_name": "measured_fallback",
                            }
                        ],
                        "mineral_candidates": [{"mineral": "Smectite"}],
                    }
                ],
            },
        ):
            payload = analytical_packages.compare_external_curve_to_package(
                "rec-1",
                original_filename="externo.RAW",
                metadata={"two_theta_start": 2.0, "step": 0.02},
                detected_peaks=[
                    {
                        "two_theta": 4.34,
                        "relative_intensity": 80.0,
                        "fwhm": 0.19,
                    }
                ],
                mineral_candidates=[],
            )

        self.assertTrue(payload["available"])
        self.assertGreater(payload["best_match"]["peak_score"], 0.5)
        self.assertGreater(payload["best_match"]["matched_peaks"][0]["score"], 0.5)
        self.assertIn("delta_two_theta", payload["best_match"]["matched_peaks"][0])
        self.assertIn("fwhm_delta_percent", payload["best_match"]["matched_peaks"][0])
        self.assertEqual(payload["best_match"]["matched_peaks"][0]["fwhm_weight"], 0.05)
        evidence = " ".join(payload["best_match"]["evidence"])
        self.assertIn("intensidade relativa", evidence)
        self.assertIn("largura/FWHM", evidence)
        self.assertIn("peso baixo", evidence)

    def test_external_curve_similarity_uses_full_curve_shape(self):
        """
        Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            advanced_path = Path(tmpdir) / "advanced.json"
            advanced_path.write_text(
                json.dumps(
                    {
                        "curve": {
                            "two_theta": [2.0, 3.0, 4.0, 5.0],
                            "intensity_normalized": [0.0, 1.0, 0.0, 0.0],
                        }
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(
                analytical_packages,
                "load_manifest",
                return_value={
                    "items": [
                        {
                            "sample_code": "AM-01-G",
                            "filename": "AM-01-G.RAW",
                            "preparation": "glicolado",
                            "preparation_label": "Glicolado",
                            "advanced_result_path": str(advanced_path),
                            "metadata": {"two_theta_start": 2.0, "step": 1.0},
                            "detected_peaks": [],
                            "mineral_candidates": [],
                        }
                    ],
                },
            ):
                payload = analytical_packages.compare_external_curve_to_package(
                    "rec-1",
                    original_filename="externo.RAW",
                    metadata={"two_theta_start": 2.0, "step": 1.0},
                    two_theta=[2.0, 3.0, 4.0, 5.0],
                    intensity=[0.0, 10.0, 0.0, 0.0],
                    detected_peaks=[],
                    mineral_candidates=[],
                )

        self.assertTrue(payload["available"])
        self.assertGreater(payload["best_match"]["curve_score"], 0.9)
        self.assertGreater(payload["best_match"]["score_components"]["curve"], 0.9)
        self.assertIn("curva completa", " ".join(payload["best_match"]["evidence"]))

    def test_analytical_package_endpoint_returns_payload(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))

        with mock.patch.object(
            views,
            "build_package_payload",
            return_value={
                "success": True,
                "exists": True,
                "record_id": "rec-1",
                "summary": {"total_files": 1},
                "items": [],
                "pagination": {"total": 0, "limit": 100, "offset": 0, "returned": 0},
            },
        ):
            response = app.test_client().get("/api/argiloteca/analises/rec-1")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])

    def test_drx_comparison_route_passes_package_context(self):
        """
        Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))

        def fake_render_template(template_name, **context):
            """
            Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
            
            Args:
                template_name: Valor de entrada consumido por esta etapa do fluxo.
                **context: Valor de entrada consumido por esta etapa do fluxo.
            Returns:
                Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
            Raises:
                Exception: Propaga erros das dependências quando a validação ou o processamento falha.
            """
            return (
                template_name
                + "|"
                + context.get("context_record_id", "")
                + "|"
                + context.get("context_record_title", "")
                + "|"
                + context.get("context_source", "")
                + "|"
                + json.dumps(context.get("authorized_mineral_aliases") or {}, sort_keys=True)
            )

        with mock.patch.object(
            views,
            "find_record_detail",
            return_value={"id": "4rxma-end93", "metadata": {"title": "Titulo analitico"}},
        ), mock.patch.object(
            views,
            "build_authorized_mineral_catalog",
            return_value=[
                {"slug": "illite", "nome_pt": "Ilita", "nome_en": "Illite"},
                {"slug": "chlorite", "nome_pt": "Clorita", "nome_en": "Chlorite"},
            ],
        ), mock.patch.object(
            views,
            "render_template",
            side_effect=fake_render_template,
        ):
            response = app.test_client().get("/drx/comparacao?record_id=4rxma-end93&source=package")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("semantic-ui/argiloteca/drx_comparacao.html", body)
        self.assertIn("4rxma-end93", body)
        self.assertIn("Titulo analitico", body)
        self.assertIn("package", body)
        self.assertIn('"ilita": "illite"', body)
        self.assertIn('"clorita": "chlorite"', body)

    def test_analises_index_route_renders_without_record_id(self):
        """
        Atende uma chamada da interface ou API, convertendo dados internos em resposta estável para o painel web.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))

        with mock.patch.object(
            views,
            "render_template",
            return_value="semantic-ui/argiloteca/analises_index.html",
        ) as mocked_render:
            response = app.test_client().get("/analises/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("analises_index.html", response.get_data(as_text=True))
        mocked_render.assert_called_once()
        template_name, = mocked_render.call_args.args
        self.assertEqual(template_name, "semantic-ui/argiloteca/analises_index.html")
        self.assertIn("authorized_mineral_slugs", mocked_render.call_args.kwargs)
        self.assertIn("authorized_mineral_aliases", mocked_render.call_args.kwargs)

    def test_authorized_mineral_alias_map_links_portuguese_labels_to_vocab_slugs(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        aliases = views._authorized_mineral_alias_map(
            [
                {
                    "id": "illite",
                    "slug": "illite",
                    "nome_pt": "Ilita",
                    "nome_en": "Illite",
                    "nome_cientifico_padronizado": "Illite",
                },
                {
                    "id": "chlorite",
                    "slug": "chlorite",
                    "nome_pt": "Clorita",
                    "nome_en": "Chlorite",
                    "nome_cientifico_padronizado": "Chlorite",
                },
            ]
        )

        self.assertEqual(aliases["ilita"], "illite")
        self.assertEqual(aliases["illite"], "illite")
        self.assertEqual(aliases["clorita"], "chlorite")
        self.assertEqual(aliases["chlorite"], "chlorite")

    def test_drx_context_title_falls_back_to_alias_snapshot(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        expected_title = (
            "INTEGRAÇÃO DE DADOS MINERALÓGICOS, ISÓTOPOS ESTÁVEIS (O, H) E POROSIDADE "
            "DE ROCHAS (14C-PMMA) NO RECONHECIMENTO DA EVOLUÇÃO DA ALTERAÇÃO NO SISTEMA "
            "HIDROTERMAL DE LAVRAS DO SUL/RS, BRASIL"
        )
        with mock.patch.object(
            views,
            "find_record_detail",
            return_value=None,
        ), mock.patch.object(
            views,
            "resolve_package_record_id",
            return_value=("a8v7p-n9959", "4rxma-end93"),
        ), mock.patch.object(
            views,
            "_read_json_snapshot",
            return_value={
                "records": [
                    {
                        "record_id": "a8v7p-n9959",
                        "record_title": expected_title,
                    }
                ]
            },
        ):
            self.assertEqual(views._record_title_for_context("4rxma-end93"), expected_title)

    def test_drx_context_title_reads_record_by_pid_when_search_misses(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with mock.patch.object(
            views,
            "find_record_detail",
            return_value=None,
        ), mock.patch.object(
            views,
            "_read_record_detail_by_pid",
            return_value={"id": "rxbj1-8mj74", "metadata": {"title": "Titulo direto do metadata.title"}},
        ):
            self.assertEqual(views._record_title_for_context("rxbj1-8mj74"), "Titulo direto do metadata.title")

    def test_drx_context_title_reads_publish_report_when_record_service_misses(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with mock.patch.object(
            views,
            "find_record_detail",
            return_value=None,
        ), mock.patch.object(
            views,
            "_read_record_detail_by_pid",
            return_value=None,
        ), mock.patch.object(
            views,
            "_record_title_from_publish_reports",
            return_value="REMOÇÃO DE METAIS PESADOS EM EFLUENTES SINTÉTICOS UTILIZANDO VERMICULITA COMO ADSORVENTE",
        ):
            self.assertEqual(
                views._record_title_for_context("rxbj1-8mj74"),
                "REMOÇÃO DE METAIS PESADOS EM EFLUENTES SINTÉTICOS UTILIZANDO VERMICULITA COMO ADSORVENTE",
            )

    def test_publish_report_title_accepts_id_column(self):
        """
        Gera artefatos derivados, relatórios ou saídas serializadas com parâmetros e proveniência para auditoria posterior.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        report_path = Path("/tmp/argiloteca-test-publish-report.tsv")
        report_path.write_text(
            "slug\tid\ttitle\n"
            "amostra\trxbj1-8mj74\tREMOÇÃO DE METAIS PESADOS EM EFLUENTES SINTÉTICOS UTILIZANDO VERMICULITA COMO ADSORVENTE\n",
            encoding="utf-8",
        )
        with mock.patch.object(views, "_PUBLISH_REPORT_PATHS", (report_path,)):
            self.assertEqual(
                views._record_title_from_publish_reports("rxbj1-8mj74"),
                "REMOÇÃO DE METAIS PESADOS EM EFLUENTES SINTÉTICOS UTILIZANDO VERMICULITA COMO ADSORVENTE",
            )

    def test_analytical_package_curve_endpoint_returns_payload(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        app = Flask(__name__)
        app.register_blueprint(views.create_blueprint(app))

        with mock.patch.object(
            views,
            "load_package_curve",
            return_value={
                "success": True,
                "sample_code": "AM-01-N",
                "filename": "AM-01-N.RAW",
                "metadata": {"points": 3},
                "two_theta": [3.0, 3.02, 3.04],
                "intensity": [10.0, 12.0, 11.0],
            },
        ):
            response = app.test_client().get("/argiloteca/analises/rec-1/drx/curva?sample_code=AM-01-N")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["sample_code"], "AM-01-N")


if __name__ == "__main__":
    unittest.main()
