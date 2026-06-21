"""
Projeto: Painel DRX Argiloteca

Descrição:
Valida contratos e fluxos do painel DRX Argiloteca, cobrindo processamento científico, classificação auxiliar e integração com dados de referência.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br


Instituição:
Universidade Federal do Rio Grande do Sul (UFRGS)

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
import tempfile
import unittest
from pathlib import Path

from argiloteca_custom.scripts.open_patterns.common import (
    amcsd_download_plan,
    build_cod_cif_url,
    build_cod_search_url,
    build_panel_index,
    load_argiloteca_vocabulary,
    normalize_mineral_name,
    parse_simple_peaks,
    parse_simple_xy,
    rruff_download_plan,
    score_match,
    write_jsonl,
)


class OpenPatternsIngestionTest(unittest.TestCase):
    """Representa a estrutura `OpenPatternsIngestionTest` dentro do fluxo técnico do painel Argiloteca, mantendo dados e operações relacionados ao módulo."""
    def test_normalize_mineral_name(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        self.assertEqual(normalize_mineral_name("Kaolinite"), "kaolinite")
        self.assertEqual(normalize_mineral_name("Kaolinite/Smectite"), "kaolinite smectite")
        self.assertEqual(normalize_mineral_name("Fuller's Earth"), "fullers earth")

    def test_load_argiloteca_vocabulary_manifest_and_jsonl(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            manifest = tmp / "webmineral_argilominerais_vocabulario_manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "id": "kaolinite",
                                "mineral": "Kaolinite",
                                "title_pt": "Caulinita",
                                "category": "species",
                                "family": "kaolin_group",
                                "lines": [{"d": 7.17, "i": 100}],
                            },
                            {"bad": "ignored"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            records = load_argiloteca_vocabulary(manifest)
            self.assertEqual(records[0]["id"], "kaolinite")
            self.assertEqual(records[0]["family"], "kaolin_group")

            jsonl = tmp / "argilominerais.jsonl"
            jsonl.write_text(
                '{"id":"illite","title":{"en":"Illite","pt":"Ilita"},"props":{"category":"species","family":"illite_mica"}}\n'
                "not-json\n",
                encoding="utf-8",
            )
            records = load_argiloteca_vocabulary(jsonl)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["mineral"], "Illite")

    def test_cod_search_url_builder(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        url = build_cod_search_url("Fuller's Earth", max_results=10)
        self.assertTrue(url.startswith("https://www.crystallography.net/cod/result?"))
        self.assertIn("format=json", url)
        self.assertIn("Fuller%27s+Earth", url)
        self.assertNotIn("wget", url)

    def test_cod_cif_url_builder(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        self.assertEqual(build_cod_cif_url("1000000"), "https://www.crystallography.net/cod/1000000.cif")

    def test_rruff_zip_manifest(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        default_names = [item["name"] for item in rruff_download_plan()]
        self.assertEqual(default_names, ["DIF.zip", "XY_Processed.zip"])
        self.assertNotIn("XY_RAW.zip", default_names)
        self.assertNotIn("Refinement_Data.zip", default_names)

        expanded_names = [item["name"] for item in rruff_download_plan(include_raw=True, include_refinement=True)]
        self.assertIn("XY_RAW.zip", expanded_names)
        self.assertIn("Refinement_Data.zip", expanded_names)

        amcsd_names = [item["name"] for item in amcsd_download_plan()]
        self.assertEqual(amcsd_names, ["cif.zip", "dif.zip"])
        self.assertNotIn("amc.zip", amcsd_names)

    def test_match_score_exact(self):
        """
        Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        term = {"mineral": "Kaolinite", "category": "species", "family": "kaolin_group"}
        score = score_match(term, {"matched_name": "Kaolinite", "family": "kaolin_group", "has_measured_xrd": True, "has_dif": True})
        self.assertGreaterEqual(score["score"], 0.8)
        self.assertEqual(score["curation_status"], "accepted")

    def test_match_score_group_not_species(self):
        """
        Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        term = {"mineral": "Kaolin", "category": "group", "family": "kaolin_group"}
        score = score_match(term, {"matched_name": "Kaolinite", "family": "kaolin_group", "has_measured_xrd": True})
        self.assertLess(score["score"], 0.8)
        self.assertIn("Grupo/material", " ".join(score["warnings"]))

    def test_parse_simple_xy(self):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        profile = parse_simple_xy("# two theta intensity\n12.4 100\n24.9 50\n")
        self.assertEqual(profile["points_count"], 2)
        self.assertEqual(profile["two_theta_deg"], [12.4, 24.9])
        self.assertEqual(profile["intensity"], [100.0, 50.0])

    def test_parse_simple_peaks(self):
        """
        Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        peaks = parse_simple_peaks("7.17 100\n3.57 70\n")
        self.assertEqual(len(peaks), 2)
        self.assertAlmostEqual(peaks[0]["d_A"], 7.17)
        self.assertGreater(peaks[0]["two_theta_deg"], 0)

    def test_panel_index_generation(self):
        """
        Verifica comportamento esperado do sistema com dados controlados para reduzir regressões no painel DRX.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        records = [
            {
                "argiloteca_id": "kaolinite",
                "source": "RRUFF",
                "source_record_id": "R000001",
                "data_kind": "measured_powder_xrd",
                "pattern_kind": "experimental",
                "peaks": [
                    {"d_A": 7.17, "relative_intensity": 100},
                    {"d_A": 3.57, "relative_intensity": 70},
                ],
                "source_record_url": "https://rruff.info/",
                "match_confidence": 0.9,
                "curation_status": "accepted",
                "warnings": ["auxiliar"],
            }
        ]
        panel = build_panel_index(records)
        self.assertEqual(panel[0]["argiloteca_id"], "kaolinite")
        self.assertEqual(panel[0]["curation_status"], "accepted")
        self.assertEqual(len(panel[0]["top_peaks"]), 2)

    def test_write_jsonl_roundtrip_shape(self):
        """
        Gera artefatos derivados, relatórios ou saídas serializadas com parâmetros e proveniência para auditoria posterior.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "open_patterns_index.jsonl"
            write_jsonl(path, [{"argiloteca_id": "kaolinite"}])
            self.assertEqual(path.read_text(encoding="utf-8").count("\n"), 1)


if __name__ == "__main__":
    unittest.main()

