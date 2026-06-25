"""
Projeto: Painel DRX Argiloteca

Descrição:
Backend technical report builders for DRX analyses.

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


Fundamentacao cientifica revisada:
    Este arquivo integra o Painel DRX da Argiloteca, projeto fundamentado nas
    referencias cientificas revisadas para interpretacao auxiliar de DRX de
    argilominerais: Brindley & Brown (1980), Bailey (1980/1988),
    Moore & Reynolds (1989/1997), Drits & Tchoubar (1990),
    Lanson & Bouchet (1995), Meunier, Clays (2005), fluxograma USGS para
    identificacao de argilominerais por DRX e referencias empiricas Pre-Sal
    UFRGS/Petrobras.

Autoria cientifica e curadoria:
    Alexandre Ribas Semeler
    E-mail: alexandre.semler@ufrgs.br

Politica de interpretacao:
    Resultados mineralogicos sao auxiliares e nao confirmatorios. O codigo
    combina comportamento N/G/C, picos companheiros, d060, ambiguidades,
    contexto e proveniencia; nao confirma mineral por pico isolado.
"""

from __future__ import annotations

from html import escape

from argiloteca.drx_core.contracts import DRX_TECHNICAL_REPORT_SCHEMA, auxiliary_policy


def _qc_messages(rows):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        rows: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    messages = []
    for row in rows or []:
        if isinstance(row, str):
            messages.append(row)
            continue
        message = row.get("message") or row.get("code") or row.get("flag")
        if message:
            messages.append(str(message))
    return messages


def _candidate_summary(candidates, limit=6):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        candidates: Valor de entrada consumido por esta etapa do fluxo.
        limit: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    rows = []
    for candidate in (candidates or [])[:limit]:
        rows.append(
            {
                "mineral": candidate.get("mineral") or candidate.get("title_pt") or candidate.get("argilomineral_id"),
                "score": candidate.get("score"),
                "confidence": candidate.get("confidence"),
                "matched_lines": candidate.get("matched_lines"),
                "source": candidate.get("source"),
                "status": candidate.get("validation_status") or candidate.get("status") or "candidate",
            }
        )
    return rows


def _peak_summary(peaks, limit=20):
    """
    Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
    
    Args:
        peaks: Valor de entrada consumido por esta etapa do fluxo.
        limit: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    rows = []
    for peak in (peaks or [])[:limit]:
        rows.append(
            {
                "peak_index": peak.get("peak_index"),
                "two_theta": peak.get("two_theta") or peak.get("center_2theta"),
                "d_angstrom": peak.get("d_angstrom") or peak.get("d") or peak.get("center_d_angstrom"),
                "relative_intensity": peak.get("relative_intensity") or peak.get("intensity_relative"),
                "fwhm": peak.get("fwhm"),
                "source": peak.get("source") or peak.get("detection_method"),
            }
        )
    return rows


def build_drx_technical_report(
    *,
    analysis_run,
    advanced_processing,
    identification=None,
    diagnostic_evidence=None,
    reference_comparison=None,
):
    """Build a compact, versioned report payload for one DRX analysis."""
    identification = identification or {}
    advanced_processing = advanced_processing or {}
    analysis_run = analysis_run or {}
    diagnostic_evidence = diagnostic_evidence or []
    reference_comparison = reference_comparison or {}
    peaks = advanced_processing.get("peaks") or identification.get("peaks") or []
    candidates = identification.get("candidates") or []
    qc_messages = _qc_messages(advanced_processing.get("qc_flags") or [])
    limitations = [
        "Relatorio tecnico assistido; nao confirma fase mineral sem curadoria.",
        "FWHM e tamanho de cristalito, quando presentes, nao incluem correcao instrumental.",
        "Quantificacao mineralogica por Rietveld/Le Bail nao foi executada nesta analise.",
    ]
    if not diagnostic_evidence:
        limitations.append("Nenhuma regra diagnostica backend encontrou evidencia nas faixas configuradas.")
    if identification.get("classification_error"):
        limitations.append("Classificacao mineral auxiliar indisponivel: " + str(identification.get("classification_error")))
    if reference_comparison.get("warnings"):
        limitations.extend(str(item) for item in reference_comparison.get("warnings") or [])

    return {
        "schema_version": DRX_TECHNICAL_REPORT_SCHEMA,
        "analysis_schema_version": analysis_run.get("schema_version"),
        "generated_at": analysis_run.get("generated_at"),
        "input": analysis_run.get("input") or {},
        "summary": {
            "peak_count": len(peaks),
            "fit_count": len(advanced_processing.get("fit_results") or []),
            "candidate_count": len(candidates),
            "diagnostic_evidence_count": len(diagnostic_evidence),
            "qc_flag_count": len(qc_messages),
            "reference_match_count": reference_comparison.get("matched_peak_count") or 0,
        },
        "methods": analysis_run.get("methods") or {},
        "reproducibility": analysis_run.get("reproducibility") or {},
        "peaks": _peak_summary(peaks),
        "mineral_candidates": _candidate_summary(candidates),
        "diagnostic_evidence": diagnostic_evidence,
        "reference_comparison": reference_comparison,
        "quality_flags": qc_messages,
        "limitations": limitations,
        "interpretation_policy": analysis_run.get("interpretation_policy")
        or auxiliary_policy("drx"),
    }


def _cell(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if value is None:
        return "N/D"
    return escape(str(value))


def _table(headers, rows):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        headers: Valor de entrada consumido por esta etapa do fluxo.
        rows: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not rows:
        return "<p>Nenhum dado disponível.</p>"
    head = "".join(f"<th>{escape(str(header))}</th>" for header in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{_cell(row.get(key))}</td>" for key, _label in headers) + "</tr>")
    labels = "".join(f"<th>{escape(str(label))}</th>" for _key, label in headers)
    return "<table><thead><tr>" + labels + "</tr></thead><tbody>" + "".join(body) + "</tbody></table>"


def render_drx_technical_report_html(report):
    """Render a backend HTML view from a versioned DRX technical report."""
    report = report or {}
    input_payload = report.get("input") or {}
    summary = report.get("summary") or {}
    reproducibility = report.get("reproducibility") or {}
    style = """
    body{font-family:Arial,sans-serif;color:#24332f;margin:0;background:#f7faf9}
    main{max-width:1120px;margin:0 auto;padding:24px}
    h1{font-size:26px;margin:0 0 6px} h2{font-size:18px;margin:24px 0 10px}
    .meta,.note{color:#60706a}.card{background:#fff;border:1px solid #d8e1dd;border-radius:8px;padding:16px;margin:12px 0}
    table{width:100%;border-collapse:collapse;background:#fff} th,td{border:1px solid #d8e1dd;padding:7px;vertical-align:top;font-size:13px}
    th{background:#eaf2ef;text-align:left}.warning{border-left:5px solid #b9892f;background:#fff8ef}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}.kv strong{display:block;color:#31524b}
    """
    peak_headers = [
        ("peak_index", "#"),
        ("two_theta", "2θ"),
        ("d_angstrom", "d Å"),
        ("relative_intensity", "Int. rel."),
        ("fwhm", "FWHM"),
        ("source", "Fonte"),
    ]
    candidate_headers = [
        ("mineral", "Mineral"),
        ("score", "Score"),
        ("confidence", "Conf."),
        ("matched_lines", "Linhas"),
        ("source", "Fonte"),
        ("status", "Status"),
    ]
    diagnostic_headers = [
        ("mineral_candidate", "Candidato"),
        ("label", "Regra"),
        ("observed_d_angstrom", "d observado"),
        ("observed_two_theta", "2θ observado"),
        ("warning", "Aviso"),
    ]
    reference = report.get("reference_comparison") or {}
    reference_headers = [
        ("reference_peak_index", "Ref."),
        ("observed_peak_index", "Obs."),
        ("reference_two_theta", "2θ ref."),
        ("observed_two_theta", "2θ obs."),
        ("delta_two_theta", "Δ2θ"),
        ("reference_d_angstrom", "d ref."),
        ("observed_d_angstrom", "d obs."),
    ]
    limitations = "".join(f"<li>{_cell(item)}</li>" for item in report.get("limitations") or [])
    quality = "".join(f"<li>{_cell(item)}</li>" for item in report.get("quality_flags") or [])
    return f"""<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Relatório técnico DRX</title><style>{style}</style></head>
<body><main>
  <section class="card">
    <h1>Relatório técnico DRX</h1>
    <p class="meta">Schema: {_cell(report.get('schema_version'))} · Gerado em {_cell(report.get('generated_at'))}</p>
    <p class="note">{_cell(report.get('interpretation_policy'))}</p>
  </section>
  <section class="card grid">
    <div class="kv"><strong>Arquivo</strong>{_cell(input_payload.get('filename'))}</div>
    <div class="kv"><strong>Amostra</strong>{_cell(input_payload.get('sample_code'))}</div>
    <div class="kv"><strong>Parser</strong>{_cell(input_payload.get('parser_format'))}</div>
    <div class="kv"><strong>Pontos</strong>{_cell(input_payload.get('points'))}</div>
    <div class="kv"><strong>Hash input</strong>{_cell(reproducibility.get('input_hash'))}</div>
    <div class="kv"><strong>Hash métodos</strong>{_cell(reproducibility.get('methods_hash'))}</div>
  </section>
  <section class="card grid">
    <div class="kv"><strong>Picos</strong>{_cell(summary.get('peak_count'))}</div>
    <div class="kv"><strong>Ajustes</strong>{_cell(summary.get('fit_count'))}</div>
    <div class="kv"><strong>Candidatos</strong>{_cell(summary.get('candidate_count'))}</div>
    <div class="kv"><strong>Evidências diagnósticas</strong>{_cell(summary.get('diagnostic_evidence_count'))}</div>
    <div class="kv"><strong>Picos ref. casados</strong>{_cell(summary.get('reference_match_count'))}</div>
  </section>
  <section class="card"><h2>Picos</h2>{_table(peak_headers, report.get('peaks') or [])}</section>
  <section class="card"><h2>Candidatos minerais</h2>{_table(candidate_headers, report.get('mineral_candidates') or [])}</section>
  <section class="card"><h2>Evidências diagnósticas</h2>{_table(diagnostic_headers, report.get('diagnostic_evidence') or [])}</section>
  <section class="card"><h2>Comparação com referência</h2>
    <p class="note">Score: {_cell(reference.get('score'))} · Cobertura ponderada: {_cell(reference.get('weighted_coverage'))} · Política: {_cell(reference.get('interpretation_policy'))}</p>
    {_table(reference_headers, reference.get('matches') or [])}
  </section>
  <section class="card warning"><h2>Limitações</h2><ul>{limitations}</ul></section>
  <section class="card"><h2>Flags de qualidade</h2><ul>{quality or '<li>Nenhuma flag registrada.</li>'}</ul></section>
</main></body></html>"""
