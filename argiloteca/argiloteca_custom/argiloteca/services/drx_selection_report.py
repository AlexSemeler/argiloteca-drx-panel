"""
Projeto: Painel DRX Argiloteca

Descrição:
Selection-level DRX report contract for reproducible panel exports.

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

from __future__ import annotations

import hashlib
import json

from .drx import utc_now_iso
from .drx_ngc_workflow import DRX_NGC_WORKFLOW_SCHEMA


DRX_SELECTION_REPORT_SCHEMA = "argiloteca.drx.selection_report.v1"


def _config_hash(payload):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        payload: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = json.dumps(payload or {}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _first(value, *fallbacks):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
        *fallbacks: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if value not in (None, "", [], {}):
        return value
    for fallback in fallbacks:
        if fallback not in (None, "", [], {}):
            return fallback
    return None


def _compact_peak(peak):
    """
    Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
    
    Args:
        peak: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not isinstance(peak, dict):
        return {}
    return {
        "peak_index": peak.get("peak_index") or peak.get("index") or peak.get("peak_id"),
        "two_theta": peak.get("two_theta") or peak.get("center_2theta"),
        "d_angstrom": peak.get("d_angstrom") or peak.get("d") or peak.get("center_d_angstrom"),
        "relative_intensity": peak.get("relative_intensity") or peak.get("height") or peak.get("intensity"),
        "fwhm": peak.get("fwhm"),
    }


def render_drx_selection_report_html(report):
    """Render a printable backend HTML report from a selection contract."""
    from html import escape

    report = report or {}
    summary = report.get("summary") or {}
    rows = []
    for item in report.get("items") or []:
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('sample_code') or item.get('id') or 'N/D'))}</td>"
            f"<td>{escape(str(item.get('filename') or 'N/D'))}</td>"
            f"<td>{escape(str(item.get('preparation') or 'N/D'))}</td>"
            f"<td>{escape(str(item.get('peak_count') or 0))}</td>"
            f"<td>{escape(str(item.get('source_sha256') or 'N/D'))}</td>"
            "</tr>"
        )
    ngc_rows = []
    for candidate in ((report.get("ngc_summary") or {}).get("best_candidates") or []):
        ngc_rows.append(
            "<tr>"
            f"<td>{escape(str(candidate.get('sample_base') or 'N/D'))}</td>"
            f"<td>{escape(str(candidate.get('status') or 'N/D'))}</td>"
            f"<td>{escape(str(candidate.get('mineral_candidate') or 'N/D'))}</td>"
            f"<td>{escape(str(candidate.get('score') or 'N/D'))}</td>"
            f"<td>{escape(str(candidate.get('confidence') or 'N/D'))}</td>"
            "</tr>"
        )
    limitations = "".join(f"<li>{escape(str(item))}</li>" for item in report.get("limitations") or [])
    style = """
    body{font-family:Arial,sans-serif;color:#24332f;margin:0;background:#f7faf9}
    main{max-width:1120px;margin:0 auto;padding:24px}.card{background:#fff;border:1px solid #d8e1dd;border-radius:8px;padding:16px;margin:12px 0}
    h1{font-size:26px;margin:0 0 6px}h2{font-size:18px;margin:22px 0 10px}.meta,.note{color:#60706a}
    table{width:100%;border-collapse:collapse}th,td{border:1px solid #d8e1dd;padding:7px;font-size:13px;vertical-align:top}th{background:#eaf2ef;text-align:left}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}.warning{border-left:5px solid #b9892f;background:#fff8ef}
    """
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Relatório seleção DRX</title><style>{style}</style></head>
<body><main>
  <section class="card"><h1>Relatório técnico DRX da seleção</h1>
    <p class="meta">Schema: {escape(str(report.get('schema_version') or 'N/D'))} · Gerado em {escape(str(report.get('generated_at') or 'N/D'))}</p>
    <p class="note">{escape(str(report.get('interpretation_policy') or 'Relatório auxiliar; não confirma mineralogia.'))}</p>
  </section>
  <section class="card grid">
    <div><strong>Itens</strong><br>{escape(str(summary.get('item_count') or 0))}</div>
    <div><strong>Grupos N/G/C</strong><br>{escape(str(summary.get('ngc_group_count') or 0))}</div>
    <div><strong>Picos totais</strong><br>{escape(str(summary.get('total_peak_count') or 0))}</div>
    <div><strong>Hash input</strong><br>{escape(str((report.get('reproducibility') or {}).get('input_hash') or 'N/D'))}</div>
    <div><strong>Hash métodos</strong><br>{escape(str((report.get('reproducibility') or {}).get('methods_hash') or 'N/D'))}</div>
  </section>
  <section class="card"><h2>Difratogramas</h2><table><thead><tr><th>Amostra</th><th>Arquivo</th><th>Preparo</th><th>Picos</th><th>SHA-256</th></tr></thead><tbody>{''.join(rows) or '<tr><td colspan="5">N/D</td></tr>'}</tbody></table></section>
  <section class="card"><h2>Workflow N/G/C backend</h2><table><thead><tr><th>Amostra base</th><th>Status</th><th>Candidato</th><th>Score</th><th>Confiança</th></tr></thead><tbody>{''.join(ngc_rows) or '<tr><td colspan="5">N/D</td></tr>'}</tbody></table></section>
  <section class="card warning"><h2>Limitações científicas</h2><ul>{limitations or '<li>Resultados auxiliares; validar por curadoria.</li>'}</ul></section>
</main></body></html>"""


def _compact_item(item):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        item: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    item = item or {}
    metadata = item.get("metadata") or {}
    peaks = item.get("peaks") or item.get("advanced_peaks") or item.get("detected_peaks") or []
    return {
        "id": item.get("id") or item.get("diffractogram_id"),
        "filename": _first(item.get("filename"), metadata.get("original_filename"), metadata.get("filename")),
        "sample_code": _first(item.get("sample_code"), metadata.get("sample_code")),
        "sample_base": item.get("sample_base"),
        "preparation": _first(item.get("preparation"), item.get("treatment"), metadata.get("preparation"), metadata.get("treatment")),
        "source_sha256": _first(item.get("source_sha256"), metadata.get("source_sha256")),
        "record_id": _first(item.get("record_id"), metadata.get("record_id")),
        "peak_count": len(peaks or []),
        "peaks": [_compact_peak(peak) for peak in (peaks or [])[:20] if isinstance(peak, dict)],
        "qc_flags": item.get("qc_flags") or metadata.get("qc_flags") or [],
        "warnings": item.get("warnings") or metadata.get("warnings") or [],
    }


def _ngc_summary(ngc_workflow):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        ngc_workflow: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    ngc_workflow = ngc_workflow or {}
    groups = ngc_workflow.get("groups") or []
    return {
        "schema_version": ngc_workflow.get("schema_version"),
        "group_count": ngc_workflow.get("group_count") or len(groups),
        "item_count": ngc_workflow.get("item_count"),
        "best_candidates": [
            {
                "sample_base": group.get("sample_base"),
                "status": group.get("status"),
                "mineral_candidate": (group.get("best_candidate") or {}).get("mineral_candidate"),
                "score": (group.get("best_candidate") or {}).get("score"),
                "confidence": (group.get("best_candidate") or {}).get("confidence"),
            }
            for group in groups[:12]
        ],
    }


def build_drx_selection_report(*, items, ngc_workflow=None, view_parameters=None):
    """Build a reproducible report for the selected DRX comparison set."""
    compact_items = [_compact_item(item) for item in (items or []) if isinstance(item, dict)]
    methods = {
        "ngc_workflow_schema": DRX_NGC_WORKFLOW_SCHEMA,
        "selection_report_schema": DRX_SELECTION_REPORT_SCHEMA,
        "interpretation_policy": "relatorio consolidado auxiliar; nao confirma fase mineralogica",
    }
    input_payload = {
        "item_count": len(compact_items),
        "items": [
            {
                "id": item.get("id"),
                "filename": item.get("filename"),
                "sample_code": item.get("sample_code"),
                "sample_base": item.get("sample_base"),
                "preparation": item.get("preparation"),
                "source_sha256": item.get("source_sha256"),
            }
            for item in compact_items
        ],
        "view_parameters": view_parameters or {},
    }
    limitations = [
        "Relatorio de selecao para triagem e curadoria; nao e identificacao confirmatoria.",
        "Resultados N/G/C dependem de preparo correto, alinhamento de eixo e qualidade do peak-picking.",
        "Quantificacao mineralogica e Rietveld/Le Bail nao foram executados neste contrato.",
    ]
    if not compact_items:
        limitations.append("Nenhum difratograma foi informado para o relatorio.")
    if not ngc_workflow:
        limitations.append("Workflow N/G/C nao foi calculado para esta selecao.")

    return {
        "success": True,
        "schema_version": DRX_SELECTION_REPORT_SCHEMA,
        "generated_at": utc_now_iso(),
        "summary": {
            "item_count": len(compact_items),
            "ngc_group_count": (ngc_workflow or {}).get("group_count") or 0,
            "total_peak_count": sum(item.get("peak_count") or 0 for item in compact_items),
        },
        "input": input_payload,
        "methods": methods,
        "reproducibility": {
            "input_hash": _config_hash(input_payload),
            "methods_hash": _config_hash(methods),
            "ngc_workflow_hash": _config_hash(ngc_workflow or {}),
        },
        "items": compact_items,
        "ngc_workflow": ngc_workflow or {},
        "ngc_summary": _ngc_summary(ngc_workflow),
        "limitations": limitations,
        "interpretation_policy": "Relatorio tecnico consolidado auxiliar; validar com curadoria mineralogica, padroes e contexto geologico.",
    }
