"""
Projeto: Painel DRX Argiloteca

Descrição:
Scientific traceability helpers for Argiloteca records. The helpers in this module are intentionally pure-Python and schema-light so they can be reused by the Invenio service component, PDF extractors, tests and templates without needing the full application bootstrap.

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

from __future__ import annotations

from datetime import datetime, timezone
import re
import unicodedata
from typing import Any


TRACEABILITY_STATUSES = {
    "confirmed",
    "measured",
    "observed",
    "extracted",
    "inferred",
    "enriched",
    "pending_curation",
    "rejected",
}
ASSERTION_TYPES = {
    "field_observation",
    "laboratory_measurement",
    "pdf_extraction",
    "table_extraction",
    "text_extraction",
    "automatic_inference",
    "external_enrichment",
    "human_curated_interpretation",
}
EVIDENCE_LEVELS = {"direct", "indirect", "weak", "absent"}
MINERAL_EVIDENCE_RELATIONS = {
    "confirmed_in_sample",
    "candidate_in_sample",
    "mentioned_in_document",
    "external_reference_only",
    "vocabulary_expansion",
}
MINERAL_EVIDENCE_SOURCE_TYPES = {
    "pdf_text",
    "pdf_table",
    "xrd",
    "xrf",
    "sem_eds",
    "petrography",
    "mindat",
    "local_vocabulary",
    "manual_curation",
    "unknown",
}

DIRECT_MINERAL_METHOD_PATTERNS = (
    r"\bDRX\b",
    r"\bXRD\b",
    r"difra[cç][aã]o de raios x",
    r"x[- ]ray diffraction",
    r"\bSEM[- ]?EDS\b",
    r"\bMEV[- ]?EDS\b",
    r"\bEDS\b",
    r"microscopia eletr[oô]nica",
    r"petrograf",
    r"thin section",
    r"se[cç][aã]o delgada",
)
SYNTHETIC_SAMPLE_PATTERNS = (
    r"codigo sintetico",
    r"c[oó]digo sint[eé]tico",
    r"amostra explicita confiavel",
    r"amostra expl[ií]cita confi[aá]vel",
    r"nao apresentou amostra",
    r"n[aã]o apresentou amostra",
)
CHLORITE_EXPANSION_TERMS = {
    "baileycloro",
    "baileychlore",
    "chamosita",
    "chamosite",
    "clinocloro",
    "clinochlore",
    "cookeita",
    "cookeite",
    "donbassita",
    "donbassite",
    "nimita",
    "nimite",
    "pennantita",
    "pennantite",
    "sudoita",
    "sudoite",
}


def clean_text(value: Any) -> str:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    if isinstance(value, dict):
        for key in ("pt-BR", "pt", "en", "value", "text", "label", "title", "name"):
            text = clean_text(value.get(key))
            if text:
                return text
        return " ".join(clean_text(item) for item in value.values() if clean_text(item))
    if isinstance(value, (list, tuple, set)):
        return " ".join(clean_text(item) for item in value if clean_text(item))
    return str(value).strip()


def normalize_key(value: Any) -> str:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = clean_text(value)
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()


def clamp_confidence(value: Any) -> float | None:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, number))


def now_iso() -> str:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def has_synthetic_sample_warning(*values: Any) -> bool:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        *values: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = normalize_key(" ".join(clean_text(value) for value in values))
    return any(re.search(pattern, text, re.I) for pattern in SYNTHETIC_SAMPLE_PATTERNS)


def is_direct_mineralogical_method(*values: Any) -> bool:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        *values: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = " ".join(clean_text(value) for value in values)
    return any(re.search(pattern, text, re.I) for pattern in DIRECT_MINERAL_METHOD_PATTERNS)


def traceability_metadata(
    *,
    traceability_status: str,
    assertion_type: str,
    evidence_level: str,
    requires_human_review: bool,
    validation_notes: str,
    confidence: Any = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        traceability_status: Valor de entrada consumido por esta etapa do fluxo.
        assertion_type: Valor de entrada consumido por esta etapa do fluxo.
        evidence_level: Valor de entrada consumido por esta etapa do fluxo.
        requires_human_review: Valor de entrada consumido por esta etapa do fluxo.
        validation_notes: Valor de entrada consumido por esta etapa do fluxo.
        confidence: Valor de entrada consumido por esta etapa do fluxo.
        provenance: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    status = traceability_status if traceability_status in TRACEABILITY_STATUSES else "pending_curation"
    assertion = assertion_type if assertion_type in ASSERTION_TYPES else "automatic_inference"
    level = evidence_level if evidence_level in EVIDENCE_LEVELS else "weak"
    metadata = {
        "traceability_status": status,
        "assertion_type": assertion,
        "evidence_level": level,
        "requires_human_review": bool(requires_human_review),
        "validation_notes": clean_text(validation_notes),
    }
    score = clamp_confidence(confidence)
    if score is not None:
        metadata["confidence"] = score
    if provenance:
        metadata["provenance"] = {
            key: value
            for key, value in provenance.items()
            if value not in (None, "", [], {})
        }
    return metadata


def normalize_provenance(value: Any = None, **overrides: Any) -> dict[str, Any]:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
        **overrides: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    provenance = dict(value or {}) if isinstance(value, dict) else {}
    provenance.update({key: val for key, val in overrides.items() if val not in (None, "", [], {})})
    if "updated_at" not in provenance and "generated_at" not in provenance:
        provenance["generated_at"] = now_iso()
    return provenance


def classify_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        analysis: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    result_text = clean_text(analysis.get("resultado_principal") or analysis.get("interpretacao") or analysis.get("observacoes"))
    source_file = clean_text(analysis.get("arquivo_resultado"))
    method = clean_text(analysis.get("metodo"))
    if has_synthetic_sample_warning(result_text, analysis.get("interpretacao")):
        return traceability_metadata(
            traceability_status="inferred",
            assertion_type="pdf_extraction",
            evidence_level="weak",
            requires_human_review=True,
            validation_notes="Analise vinculada a codigo sintetico por ausencia de amostra explicita confiavel no PDF.",
            provenance=normalize_provenance(
                analysis.get("provenance"),
                source_file=source_file,
                extraction_method=method or "extracao_pdf",
            ),
        )
    if method and normalize_key(method) in {"extracao pdf", "pdf extraction"}:
        return traceability_metadata(
            traceability_status="extracted",
            assertion_type="pdf_extraction",
            evidence_level="indirect",
            requires_human_review=True,
            validation_notes="Analise criada por extracao automatica de PDF.",
            provenance=normalize_provenance(analysis.get("provenance"), source_file=source_file, extraction_method=method),
        )
    return traceability_metadata(
        traceability_status="pending_curation",
        assertion_type="human_curated_interpretation",
        evidence_level="weak",
        requires_human_review=True,
        validation_notes="Analise legada sem status de rastreabilidade explicito.",
        provenance=normalize_provenance(analysis.get("provenance"), source_file=source_file),
    )


def classify_composition(composition: dict[str, Any], composition_notes: str = "") -> dict[str, Any]:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        composition: Valor de entrada consumido por esta etapa do fluxo.
        composition_notes: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    provenance = normalize_provenance(composition.get("provenance"))
    method = clean_text(provenance.get("extraction_method") or composition.get("extraction_method"))
    source_table = clean_text(provenance.get("source_table") or composition.get("source_table"))
    notes = clean_text(composition_notes or composition.get("validation_notes") or composition.get("observacoes"))
    text = normalize_key(" ".join([method, source_table, notes]))
    if any(token in text for token in ("oxide rows first value", "tabela", "table", "oxidos", "oxides")):
        return traceability_metadata(
            traceability_status="extracted",
            assertion_type="table_extraction",
            evidence_level="indirect",
            requires_human_review=True,
            confidence=composition.get("confidence"),
            validation_notes="Composicao quimica extraida de tabela de oxidos; nao confirma mineralogia por si so.",
            provenance=provenance,
        )
    return traceability_metadata(
        traceability_status="pending_curation",
        assertion_type="automatic_inference",
        evidence_level="weak",
        requires_human_review=True,
        confidence=composition.get("confidence"),
        validation_notes="Composicao legada sem evidencia analitica direta explicitada.",
        provenance=provenance,
    )


def classify_mineral(mineral: dict[str, Any], evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        mineral: Valor de entrada consumido por esta etapa do fluxo.
        evidence: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    evidence = evidence or {}
    source_type = clean_text(evidence.get("source_type") or mineral.get("source_type")).lower()
    external_source = normalize_key(mineral.get("external_source") or evidence.get("external_source_name"))
    relation = clean_text(evidence.get("relation_to_sample") or mineral.get("relation_to_sample"))
    name_key = normalize_key(mineral.get("nome_cientifico_padronizado") or mineral.get("nome"))

    if relation == "confirmed_in_sample" or source_type in {"xrd", "xrf", "sem_eds", "petrography", "manual_curation"}:
        return traceability_metadata(
            traceability_status="confirmed",
            assertion_type="human_curated_interpretation" if source_type == "manual_curation" else "laboratory_measurement",
            evidence_level="direct",
            requires_human_review=False,
            confidence=evidence.get("confidence") or mineral.get("confidence"),
            validation_notes="Mineral confirmado por evidencia mineralogica direta ou curadoria humana.",
            provenance=normalize_provenance(evidence.get("provenance") or mineral.get("provenance")),
        )
    if external_source == "mindat" or source_type == "mindat":
        return traceability_metadata(
            traceability_status="enriched",
            assertion_type="external_enrichment",
            evidence_level="absent",
            requires_human_review=True,
            confidence=evidence.get("confidence") or mineral.get("confidence"),
            validation_notes="Mindat e fonte externa de enriquecimento taxonomico, nao prova de ocorrencia na amostra.",
            provenance=normalize_provenance(evidence.get("provenance") or mineral.get("provenance")),
        )
    if source_type == "local_vocabulary" or name_key in CHLORITE_EXPANSION_TERMS or relation == "vocabulary_expansion":
        return traceability_metadata(
            traceability_status="pending_curation",
            assertion_type="automatic_inference",
            evidence_level="weak",
            requires_human_review=True,
            confidence=evidence.get("confidence") or mineral.get("confidence"),
            validation_notes="Mineral associado por vocabulario ou expansao taxonomica; requer curadoria antes de confirmacao.",
            provenance=normalize_provenance(evidence.get("provenance") or mineral.get("provenance")),
        )
    if relation == "mentioned_in_document" or source_type == "pdf_text":
        return traceability_metadata(
            traceability_status="extracted",
            assertion_type="text_extraction",
            evidence_level="indirect",
            requires_human_review=True,
            confidence=evidence.get("confidence") or mineral.get("confidence"),
            validation_notes="Mineral mencionado no documento, sem confirmacao analitica direta da amostra.",
            provenance=normalize_provenance(evidence.get("provenance") or mineral.get("provenance")),
        )
    return traceability_metadata(
        traceability_status="inferred",
        assertion_type="automatic_inference",
        evidence_level="weak",
        requires_human_review=True,
        confidence=evidence.get("confidence") or mineral.get("confidence"),
        validation_notes="Hipotese mineralogica; composicao quimica global nao confirma especie mineral.",
        provenance=normalize_provenance(evidence.get("provenance") or mineral.get("provenance")),
    )


def build_mineralogical_evidence(
    *,
    sample_id: str,
    analysis_id: str = "",
    source_type: str = "unknown",
    evidence_text: str = "",
    evidence_method: str = "",
    mineral_name_detected: str = "",
    normalized_mineral_name: str = "",
    relation_to_sample: str = "candidate_in_sample",
    provenance: dict[str, Any] | None = None,
    confidence: Any = None,
    validation_notes: str = "",
) -> dict[str, Any]:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        sample_id: Valor de entrada consumido por esta etapa do fluxo.
        analysis_id: Valor de entrada consumido por esta etapa do fluxo.
        source_type: Valor de entrada consumido por esta etapa do fluxo.
        evidence_text: Valor de entrada consumido por esta etapa do fluxo.
        evidence_method: Valor de entrada consumido por esta etapa do fluxo.
        mineral_name_detected: Valor de entrada consumido por esta etapa do fluxo.
        normalized_mineral_name: Valor de entrada consumido por esta etapa do fluxo.
        relation_to_sample: Valor de entrada consumido por esta etapa do fluxo.
        provenance: Valor de entrada consumido por esta etapa do fluxo.
        confidence: Valor de entrada consumido por esta etapa do fluxo.
        validation_notes: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    source_type = source_type if source_type in MINERAL_EVIDENCE_SOURCE_TYPES else "unknown"
    relation = relation_to_sample if relation_to_sample in MINERAL_EVIDENCE_RELATIONS else "candidate_in_sample"
    evidence = {
        "id": normalize_key(f"{sample_id}-{analysis_id}-{normalized_mineral_name or mineral_name_detected}-{source_type}").replace(" ", "-")[:96],
        "sample_id": clean_text(sample_id),
        "analysis_id": clean_text(analysis_id),
        "source_type": source_type,
        "evidence_text": clean_text(evidence_text),
        "source_excerpt": clean_text(evidence_text),
        "evidence_method": clean_text(evidence_method),
        "mineral_name_detected": clean_text(mineral_name_detected),
        "normalized_mineral_name": clean_text(normalized_mineral_name or mineral_name_detected),
        "relation_to_sample": relation,
    }
    evidence.update(
        traceability_metadata(
            traceability_status="confirmed" if relation == "confirmed_in_sample" else "pending_curation",
            assertion_type="laboratory_measurement" if relation == "confirmed_in_sample" else "text_extraction",
            evidence_level="direct" if relation == "confirmed_in_sample" else "indirect",
            requires_human_review=relation != "confirmed_in_sample",
            confidence=confidence,
            validation_notes=validation_notes or "Evidencia mineralogica criada pela camada de rastreabilidade.",
            provenance=normalize_provenance(provenance),
        )
    )
    return evidence


def normalize_record_traceability(custom_fields: dict[str, Any]) -> dict[str, Any]:
    """Mutate and return custom_fields with conservative traceability defaults."""
    if not isinstance(custom_fields, dict):
        return {}

    analyses = custom_fields.get("arg:analises")
    if isinstance(analyses, list):
        for analysis in analyses:
            if isinstance(analysis, dict) and "traceability_status" not in analysis:
                analysis.update(classify_analysis(analysis))

    composition = custom_fields.get("arg:composicao_quimica_global")
    if isinstance(composition, dict) and "traceability_status" not in composition:
        composition.update(classify_composition(composition, custom_fields.get("arg:composicao_proporcoes")))

    evidence_items = custom_fields.get("arg:evidencias_mineralogicas")
    if not isinstance(evidence_items, list):
        evidence_items = []
        custom_fields["arg:evidencias_mineralogicas"] = evidence_items

    evidence_by_name = {
        normalize_key(item.get("normalized_mineral_name") or item.get("mineral_name_detected")): item
        for item in evidence_items
        if isinstance(item, dict)
    }

    minerals = custom_fields.get("arg:argilominerais")
    if isinstance(minerals, list):
        for mineral in minerals:
            if not isinstance(mineral, dict):
                continue
            mineral_name = mineral.get("nome_cientifico_padronizado") or mineral.get("nome")
            evidence = evidence_by_name.get(normalize_key(mineral_name), {})
            metadata = classify_mineral(mineral, evidence)
            for key, value in metadata.items():
                mineral.setdefault(key, value)
            if not mineral.get("relation_to_sample"):
                if mineral.get("traceability_status") == "confirmed":
                    mineral["relation_to_sample"] = "confirmed_in_sample"
                elif mineral.get("traceability_status") == "enriched":
                    mineral["relation_to_sample"] = "external_reference_only"
                elif normalize_key(mineral_name) in CHLORITE_EXPANSION_TERMS:
                    mineral["relation_to_sample"] = "vocabulary_expansion"
                else:
                    mineral["relation_to_sample"] = "candidate_in_sample"

    return custom_fields


def validateArgilotecaTraceability(chain: dict[str, Any]) -> dict[str, Any]:
    """Validate a research-data chain and return a Portuguese audit summary."""
    custom_fields = chain.get("custom_fields", chain) if isinstance(chain, dict) else {}
    custom_fields = custom_fields if isinstance(custom_fields, dict) else {}
    analyses = custom_fields.get("arg:analises") or []
    composition = custom_fields.get("arg:composicao_quimica_global") or {}
    minerals = custom_fields.get("arg:argilominerais") or []
    evidence_items = custom_fields.get("arg:evidencias_mineralogicas") or []

    alerts: list[str] = []
    weak_links: list[str] = []
    pending_fields: list[str] = []
    recommendations: list[str] = []

    analysis_text = " ".join(clean_text(item) for analysis in analyses if isinstance(analysis, dict) for item in (
        analysis.get("resultado_principal"),
        analysis.get("interpretacao"),
        analysis.get("observacoes"),
    ))
    if has_synthetic_sample_warning(analysis_text):
        alerts.append("A analise indica codigo sintetico ou amostra explicita nao confiavel.")
        weak_links.append("Amostra fisica -> Analise")
        pending_fields.append("arg:analises.resultado_principal")

    if isinstance(composition, dict) and composition:
        provenance = composition.get("provenance") if isinstance(composition.get("provenance"), dict) else {}
        if composition.get("traceability_status") in {"inferred", "extracted", "pending_curation"}:
            weak_links.append("Analise -> Composicao quimica")
        if composition.get("assertion_type") == "table_extraction":
            if not provenance.get("source_file"):
                alerts.append("Composicao de tabela sem source_file.")
                pending_fields.append("arg:composicao_quimica_global.provenance.source_file")
            if not provenance.get("source_table"):
                alerts.append("Composicao de tabela sem source_table.")
                pending_fields.append("arg:composicao_quimica_global.provenance.source_table")

    direct_evidence_names = {
        normalize_key(item.get("normalized_mineral_name") or item.get("mineral_name_detected"))
        for item in evidence_items
        if isinstance(item, dict) and item.get("relation_to_sample") == "confirmed_in_sample"
    }
    has_direct_mineral_evidence = bool(direct_evidence_names)
    for idx, mineral in enumerate(minerals if isinstance(minerals, list) else []):
        if not isinstance(mineral, dict):
            continue
        name_key = normalize_key(mineral.get("nome_cientifico_padronizado") or mineral.get("nome"))
        relation = mineral.get("relation_to_sample")
        source = normalize_key(mineral.get("external_source"))
        status = mineral.get("traceability_status")
        if source == "mindat":
            alerts.append(f"{clean_text(mineral.get('nome')) or 'Mineral'} vem de Mindat e deve ser enriquecimento externo.")
            weak_links.append("Argilomineral -> Fonte externa")
        if relation != "confirmed_in_sample" and name_key not in direct_evidence_names:
            pending_fields.append(f"arg:argilominerais.{idx}.evidencia_mineralogica")
        if status == "confirmed" and relation != "confirmed_in_sample" and name_key not in direct_evidence_names:
            alerts.append(f"{clean_text(mineral.get('nome')) or 'Mineral'} esta confirmado sem evidencia mineralogica direta.")
            weak_links.append("Composicao quimica -> Argilomineral")

    uses_text = " ".join(
        clean_text(custom_fields.get(key))
        for key in (
            "arg:usos_descricao",
            "arg:usos_aplicacoes_industriais",
            "arg:usos_aplicacoes_tecnologicas",
            "arg:usos_aplicacoes_cientificas",
        )
    )
    if uses_text and re.search(r"automatic|automaticamente|extraid|inferid|PDF", uses_text, re.I):
        weak_links.append("Argilomineral -> Usos e aplicacoes")
        pending_fields.append("arg:usos_*")

    if not has_direct_mineral_evidence and minerals:
        alerts.append("Nao ha evidencia mineralogica direta ligando mineral identificado a amostra.")
        weak_links.append("Composicao quimica -> Evidencia mineralogica")
        recommendations.append("Registrar DRX/XRD, SEM-EDS, petrografia ou trecho documental explicito antes de promover mineral a confirmado.")

    if alerts and "Amostra fisica -> Analise" in weak_links:
        overall = "weak"
    elif alerts or weak_links:
        overall = "partial"
    elif custom_fields:
        overall = "complete"
    else:
        overall = "invalid"

    if not recommendations:
        recommendations.append("Manter os status conservadores ate curadoria cientifica humana.")

    return {
        "overall_status": overall,
        "status_geral": overall,
        "alerts": sorted(set(alerts)),
        "alertas": sorted(set(alerts)),
        "weak_links": sorted(set(weak_links)),
        "elos_frageis": sorted(set(weak_links)),
        "pending_curation_fields": sorted(set(pending_fields)),
        "campos_pendentes_curadoria": sorted(set(pending_fields)),
        "explanation_pt": (
            "Cadeia com rastreabilidade fraca: ha amostra/analise ou mineralogia inferida sem evidencia direta."
            if overall == "weak"
            else "Cadeia parcialmente rastreavel; alguns elos dependem de curadoria ou evidencia adicional."
            if overall == "partial"
            else "Cadeia completa com evidencias explicitas para os principais elos."
            if overall == "complete"
            else "Cadeia invalida ou sem dados suficientes para auditoria."
        ),
        "recommendations": recommendations,
        "recomendacoes": recommendations,
    }


validateResearchDataTraceability = validateArgilotecaTraceability
