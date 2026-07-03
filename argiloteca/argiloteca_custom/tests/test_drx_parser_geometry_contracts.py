"""Testes pequenos de contrato para parser e geometria DRX.

Estes testes documentam o comportamento atual sem alterar o pipeline: o parser
textual aceita curvas simples 2theta/intensidade, a geometria separa 2theta de
theta e os novos contratos continuam sem assumir comprimento de onda.
"""

from __future__ import annotations

import math
import unittest

from argiloteca_drx_core.curves import CurveParseError, calculate_d_spacing, parse_curve_bytes
from argiloteca_drx_core.geometry import bragg_from_two_theta
from argiloteca_drx_core.models import Diffractogram, validate_axis_lengths


def _curve_text(separator: str) -> bytes:
    """Gera uma curva tabular com mais pontos que o minimo do parser."""

    rows = ["two_theta{}intensity".format(separator)]
    for index in range(12):
        rows.append("{:.2f}{}{}".format(5.0 + index * 0.02, separator, 100 + index))
    return ("\n".join(rows) + "\n").encode("utf-8")


class DrxParserGeometryContractsTest(unittest.TestCase):
    """Valida contratos de parser/geometria sem tocar em regras N/G/C."""

    def test_parse_curve_bytes_reads_simple_csv_two_theta_intensity(self):
        curve = parse_curve_bytes(_curve_text(","), filename="sample.csv")

        self.assertEqual(len(curve.two_theta), 12)
        self.assertEqual(len(curve.intensity), 12)
        self.assertEqual(curve.two_theta[0], 5.0)
        self.assertEqual(curve.intensity[-1], 111.0)
        self.assertEqual(curve.metadata["parser_format"], "text_curve")

    def test_parse_curve_bytes_reads_semicolon_and_tab_text_curves(self):
        semicolon_curve = parse_curve_bytes(_curve_text(";"), filename="sample.txt")
        tab_curve = parse_curve_bytes(_curve_text("\t"), filename="sample.xy")

        self.assertEqual(semicolon_curve.two_theta[1], 5.02)
        self.assertEqual(tab_curve.intensity[1], 101.0)
        self.assertEqual(semicolon_curve.metadata["detected_format"], "text two-column diffractogram")
        self.assertEqual(tab_curve.metadata["detected_format"], "text two-column diffractogram")

    def test_parse_curve_bytes_reports_empty_file_as_controlled_error(self):
        with self.assertRaises(CurveParseError):
            parse_curve_bytes(b"", filename="empty.csv")

    def test_calculate_d_spacing_uses_explicit_wavelength_and_two_theta(self):
        d_spacing = calculate_d_spacing(8.84, wavelength=1.5406)
        expected = 1.5406 / (2.0 * math.sin(math.radians(8.84 / 2.0)))

        self.assertAlmostEqual(d_spacing, expected, places=9)

    def test_bragg_from_two_theta_reports_invalid_or_insufficient_inputs(self):
        invalid_lambda = bragg_from_two_theta(8.84, wavelength_angstrom=0)
        invalid_angle = bragg_from_two_theta(0, wavelength_angstrom=1.5406)
        missing_angle = bragg_from_two_theta("not-a-number", wavelength_angstrom=1.5406)

        self.assertEqual(invalid_lambda.status, "invalid")
        self.assertEqual(invalid_angle.status, "invalid")
        self.assertEqual(missing_angle.status, "insufficient_data")
        self.assertIsNone(invalid_lambda.d_spacing_angstrom)

    def test_contract_models_do_not_assume_wavelength_even_if_geometry_has_legacy_default(self):
        curve = Diffractogram(two_theta=[8.84], intensity=[100.0])
        legacy_geometry = bragg_from_two_theta(8.84)

        self.assertIsNone(curve.wavelength_angstrom)
        self.assertEqual(legacy_geometry.wavelength_angstrom, 1.5406)
        self.assertEqual(legacy_geometry.status, "valid")

    def test_validate_axis_lengths_handles_misaligned_arrays_without_exception(self):
        validation = validate_axis_lengths([5.0, 5.02, 5.04], [100.0])

        self.assertFalse(validation["valid"])
        self.assertEqual(validation["two_theta_points"], 3)
        self.assertEqual(validation["intensity_points"], 1)

    def test_geometry_keeps_two_theta_and_theta_distinct(self):
        calculation = bragg_from_two_theta(12.0, wavelength_angstrom=1.5406)

        self.assertEqual(calculation.two_theta_deg, 12.0)
        self.assertEqual(calculation.theta_deg, 6.0)
        self.assertNotEqual(calculation.two_theta_deg, calculation.theta_deg)
        self.assertEqual(calculation.rule_id, "chapter3_two_theta_to_d_spacing")


if __name__ == "__main__":
    unittest.main()
