"""Contratos estaticos dos renderizadores N/G/C do painel DRX.

Estes testes nao executam o navegador. Eles protegem a migracao gradual do
frontend para contratos backend garantindo que o JS ainda prefere os payloads
estruturados e preserva fallback legado antes de qualquer remocao de codigo.
"""

from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JS_PATH = PROJECT_ROOT / "argiloteca" / "static" / "js" / "drx-comparacao.js"


def read_panel_js() -> str:
    return JS_PATH.read_text(encoding="utf-8")


def function_body(source: str, function_name: str) -> str:
    marker = f"function {function_name}"
    start = source.find(marker)
    if start < 0:
        raise AssertionError(f"Funcao {function_name} nao encontrada")
    brace_start = source.find("{", start)
    if brace_start < 0:
        raise AssertionError(f"Corpo de {function_name} nao encontrado")
    depth = 0
    for index in range(brace_start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace_start : index + 1]
    raise AssertionError(f"Corpo de {function_name} nao terminou")


class DrxNgcFrontendRendererContractsTest(unittest.TestCase):
    def test_evidence_renderer_prefers_backend_contract_and_keeps_fallback(self):
        source = read_panel_js()
        self.assertIn("function backendNgcEvidenceSummaryForSelection", source)
        self.assertIn("function renderNgcEvidenceSummaryFromBackend", source)
        self.assertIn("function buildNgcEvidenceSummaryWithBackendFallback", source)
        self.assertIn("argiloteca.drx.ngc.evidence_summary.v1", source)
        self.assertIn("const behaviorFallback = renderBehaviorCards", source)
        self.assertIn("buildNgcEvidenceSummaryWithBackendFallback(group, behaviorFallback)", source)
        self.assertIn("Resumo das evidências N-G-C", source)

    def test_evidence_renderer_does_not_duplicate_source_rules_section(self):
        body = function_body(read_panel_js(), "renderNgcEvidenceSummaryFromBackend")
        self.assertIn('section.key !== "source_rules"', body)
        self.assertIn("section.items", body)
        self.assertIn("argilo-drx__ngc-evidence-card", body)

    def test_source_rule_renderer_prefers_backend_contract_and_keeps_fallback(self):
        source = read_panel_js()
        self.assertIn("function backendSourceRuleSummaryCandidate", source)
        self.assertIn("function renderSourceRulePanelFromBackend", source)
        self.assertIn("argiloteca.drx.ngc.source_rule_summary.v1", source)
        self.assertIn("const backendPanel = renderSourceRulePanelFromBackend(candidate)", source)
        self.assertIn("if (backendPanel) return backendPanel", source)

    def test_source_rule_renderer_still_prints_table_rows(self):
        body = function_body(read_panel_js(), "renderSourceRulePanelFromBackend")
        self.assertIn("Regras aplicadas", body)
        self.assertIn("Dados das tabelas", body)
        self.assertIn("renderSourceTablePreview", body)
        self.assertIn("profile_references", body)
        self.assertIn("row.tables", body)

    def test_legacy_renderers_remain_available_for_compatibility(self):
        source = read_panel_js()
        self.assertIn("function renderBehaviorCards", source)
        self.assertIn("function renderRangeDiagnosticCard", source)
        self.assertIn("function renderSourceRulePanel(candidate)", source)
        self.assertIn("diagnostic.source_rule_index", source)
        self.assertIn("diagnostic.source_mineral_profiles", source)


if __name__ == "__main__":
    unittest.main()
