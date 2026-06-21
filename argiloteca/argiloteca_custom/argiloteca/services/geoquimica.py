"""
Projeto: Painel DRX Argiloteca

Descrição:
Geoquimica network extraction and analysis. This module intentionally reads the existing Argiloteca custom fields. It does not define or require a parallel metadata schema. O painel combina composicao de oxidos, argilominerais, contexto geologico e assinaturas de uso em uma rede de analogias explicavel. As funcoes preservam os campos publicados e apenas os normalizam para visualizacao e filtros.

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

import json
import math
import re
import unicodedata
from collections import defaultdict
from functools import lru_cache
from pathlib import Path


OXIDE_FIELDS = (
    "SiO2",
    "Al2O3",
    "Fe2O3",
    "FeO",
    "TiO2",
    "MgO",
    "CaO",
    "Na2O",
    "K2O",
    "P2O5",
    "MnO",
    "LOI",
    "PF",
)

# Campos Argiloteca/Invenio consumidos diretamente. Estes nomes fazem parte do
# contrato dos registros e nao devem ser renomeados por conveniencia local.
COMPOSITION_FIELD = "arg:composicao_quimica_global"
SUMMARY_FIELD = "arg:proporcoes_resultados_principais"
ANALYSIS_RESULT_FIELD = "arg:analise_resultado"
MINERALS_FIELD = "arg:argilominerais"
LEGACY_MINERAL_NAME_FIELD = "arg:argilomineral_nome"

MIN_VALID_OXIDES = 3
DEFAULT_SIZE = 5000
PRIMARY_OXIDES = ("SiO2", "Al2O3", "Fe2O3", "MgO", "CaO", "K2O", "Na2O", "TiO2", "LOI", "PF")
AGGREGATED_OXIDE_FILTERS = ("SiO2", "Al2O3", "Fe2O3", "MgO")
GEOLOGICAL_LEVELS = ("eon", "era", "periodo", "epoca")
TEMPO_GEOLOGICO_PATH = (
    Path(__file__).resolve().parents[3] / "app_data" / "data" / "vocabularies" / "tempo_geologico.jsonl"
)
# Dimensoes e pesos usados na rede; manter separados facilita auditar quando uma
# relacao e quimica, mineralogica, contextual ou funcional.
ANALOGY_DIMENSIONS = (
    "score_geoquimico",
    "score_mineralogico",
    "score_contextual",
    "score_funcional",
)
ANALOGY_WEIGHT_PROFILES = {
    "composite": {
        "score_geoquimico": 0.45,
        "score_mineralogico": 0.30,
        "score_contextual": 0.15,
        "score_funcional": 0.10,
    },
    "geoquimico": {
        "score_geoquimico": 0.75,
        "score_mineralogico": 0.15,
        "score_contextual": 0.05,
        "score_funcional": 0.05,
    },
    "mineralogico": {
        "score_geoquimico": 0.20,
        "score_mineralogico": 0.60,
        "score_contextual": 0.10,
        "score_funcional": 0.10,
    },
    "contextual": {
        "score_geoquimico": 0.20,
        "score_mineralogico": 0.20,
        "score_contextual": 0.50,
        "score_funcional": 0.10,
    },
    "funcional": {
        "score_geoquimico": 0.20,
        "score_mineralogico": 0.20,
        "score_contextual": 0.10,
        "score_funcional": 0.50,
    },
}
ANALOGY_RELATION_TYPES = (
    "geoquimica_analoga",
    "grupo_mineralogico_compativel",
    "contexto_geologico_semelhante",
    "assinatura_funcional_semelhante",
    "analogia_composta",
)
CONFIDENCE_CLASSES = ("alta", "media", "baixa")
ANALOGY_CLASSES = ("confirmada", "provavel", "exploratoria")


def parse_float(value):
    """Return a float for user-entered numeric values, or None."""
    if value in (None, "", [], {}):
        return None
    if isinstance(value, (int, float)):
        if math.isfinite(value):
            return float(value)
        return None
    try:
        text = str(value).strip().replace("%", "").replace(",", ".")
        return float(text)
    except (TypeError, ValueError):
        return None


def safe_text(value):
    """Extract readable text from common Invenio metadata value shapes."""
    if value in (None, "", [], {}):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, dict):
        for key in ("pt-BR", "pt", "en", "en-US"):
            text = safe_text(value.get(key))
            if text:
                return text
        for nested in value.values():
            text = safe_text(nested)
            if text:
                return text
    if isinstance(value, list):
        for item in value:
            text = safe_text(item)
            if text:
                return text
    return str(value).strip() or None


def normalize_key(value):
    """Normalize ids and labels for tolerant comparisons."""
    text = safe_text(value)
    if not text:
        return None
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()


def record_title(record):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        record: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    metadata = record.get("metadata", {}) or {}
    record_id = record.get("id") or record.get("uuid") or "sem-id"
    return safe_text(metadata.get("title")) or f"Registro {record_id}"


def record_metadata(record):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        record: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return record.get("metadata", {}) or {}


def record_custom_fields(record):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        record: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    metadata = record_metadata(record)
    return record.get("custom_fields") or metadata.get("custom_fields") or {}


def hit_to_record(hit):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        hit: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if hasattr(hit, "to_dict"):
        try:
            hit = hit.to_dict()
        except Exception:
            pass
    if isinstance(hit, dict):
        if isinstance(hit.get("_source"), dict):
            return hit["_source"]
        return hit
    return {}


def search_records(size=DEFAULT_SIZE):
    """Read current published records from the InvenioRDM service."""
    from invenio_access.permissions import system_identity
    from invenio_rdm_records.proxies import current_rdm_records_service

    records = []
    page = 1
    page_size = min(max(int(size or DEFAULT_SIZE), 1), 1000)
    target = max(int(size or DEFAULT_SIZE), 1)

    while len(records) < target:
        result = current_rdm_records_service.search(
            identity=system_identity,
            params={"size": page_size, "page": page, "sort": "newest"},
        )
        page_hits = list(getattr(result, "hits", []) or [])
        records.extend(hit_to_record(hit) for hit in page_hits)
        if len(page_hits) < page_size:
            break
        page += 1

    return records[:target]


def parse_composition_text(text):
    """Extract oxide percentages from existing free-text proportion fields."""
    if not isinstance(text, str) or not text.strip():
        return {}

    values = {}
    for oxide in OXIDE_FIELDS:
        pattern = rf"\b{re.escape(oxide)}\b\s*[:=]?\s*(-?\d+(?:[.,]\d+)?)"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = parse_float(match.group(1))
            if value is not None:
                values[oxide] = value
    return values


def extract_oxides(custom_fields):
    """Return the best available oxide dictionary from existing custom fields."""
    oxides = {}
    structured = custom_fields.get(COMPOSITION_FIELD)
    has_structured_composition = isinstance(structured, dict) and bool(structured)
    if isinstance(structured, dict):
        for oxide in OXIDE_FIELDS:
            value = parse_float(structured.get(oxide))
            if value is not None and value >= 0:
                oxides[oxide] = value

    # Compatibility with legacy records only when there is no structured composition.
    if len(oxides) < MIN_VALID_OXIDES and not has_structured_composition:
        text_sources = (
            custom_fields.get("arg:composicao_proporcoes"),
            custom_fields.get("arg:composicao_descricao_componentes"),
        )
        for text in text_sources:
            oxides.update(parse_composition_text(text))
            if len(oxides) >= MIN_VALID_OXIDES:
                break

    return {oxide: value for oxide, value in oxides.items() if value is not None and value >= 0}


def extract_summary(custom_fields):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        custom_fields: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    summary = custom_fields.get(SUMMARY_FIELD)
    return summary if isinstance(summary, dict) else {}


@lru_cache(maxsize=1)
def get_mineral_matcher():
    """Cache the vocabulary-backed matcher used for record subjects."""
    try:
        from .mineral_linking import MineralMatcher
    except Exception:
        return None
    try:
        return MineralMatcher()
    except Exception:
        return None


def mineral_key(name):
    """Normalize mineral names for visual relation matching."""
    text = safe_text(name)
    if not text:
        return None
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def unique_texts(values):
    """Deduplicate readable labels while preserving a stable order."""
    values_by_key = {}
    for value in values or []:
        text = safe_text(value)
        key = mineral_key(text)
        if key and key not in values_by_key:
            values_by_key[key] = text
    return [values_by_key[key] for key in sorted(values_by_key)]


def tokenize_text(value):
    """Return normalized scientific tokens from a free-text field."""
    text = normalize_key(value)
    if not text:
        return set()
    return {token for token in text.split() if len(token) >= 3}


def split_structured_terms(*values):
    """Split common list-like scientific text fields into stable readable values."""
    items_by_key = {}
    for value in values:
        text = safe_text(value)
        if not text:
            continue
        for part in re.split(r"[;,/|\n]+", text):
            label = safe_text(part)
            key = normalize_key(label)
            if key and key not in items_by_key:
                items_by_key[key] = label
    return [items_by_key[key] for key in sorted(items_by_key)]


def text_overlap_score(left, right):
    """Compute a token-overlap score for descriptive scientific text."""
    left_tokens = tokenize_text(left)
    right_tokens = tokenize_text(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return round(len(left_tokens & right_tokens) / len(left_tokens | right_tokens), 4)


def jaccard_score(left_values, right_values):
    """Return a stable overlap score for controlled labels."""
    left = {normalize_key(value) for value in left_values or [] if normalize_key(value)}
    right = {normalize_key(value) for value in right_values or [] if normalize_key(value)}
    if not left or not right:
        return 0.0
    return round(len(left & right) / len(left | right), 4)


def numeric_similarity(left, right, scale=None):
    """Compare two numeric scientific indicators on a 0..1 scale."""
    left = parse_float(left)
    right = parse_float(right)
    if left is None or right is None:
        return 0.0
    scale = abs(scale) if scale not in (None, 0) else max(abs(left), abs(right), 1.0)
    delta = abs(left - right) / scale
    return round(max(0.0, 1.0 - min(delta, 1.0)), 4)


def choose_primary_label(values):
    """Return a representative readable label from a list."""
    labels = [safe_text(value) for value in values or [] if safe_text(value)]
    return labels[0] if labels else None


def summarize_text(*values):
    """Build a compact structured summary from multiple short fields."""
    parts = []
    for value in values:
        text = safe_text(value)
        if text:
            parts.append(text)
    return " | ".join(parts[:4]) or None


def extract_subject_terms(record):
    """Return the explicit metadata.subjects labels stored on the record."""
    subjects = []
    raw_subjects = record_metadata(record).get("subjects") or []

    if isinstance(raw_subjects, list):
        for item in raw_subjects:
            if isinstance(item, dict):
                label = safe_text(item.get("subject") or item.get("term") or item.get("id"))
            else:
                label = safe_text(item)
            if label:
                subjects.append(label)

    return unique_texts(subjects)


def extract_subject_mineral_map(record, matcher=None):
    """Infer controlled-vocabulary minerals and groups from metadata.subjects."""
    matcher = matcher or get_mineral_matcher()
    minerals = []
    groups = []
    matched_subjects = []

    for subject in extract_subject_terms(record):
        if not matcher:
            continue
        match = matcher.match_term(subject)
        if match.mineral:
            minerals.append(match.mineral.preferred_label)
            matched_subjects.append(subject)
        if match.group:
            groups.append(match.group.preferred_label)

    return {
        "subjects": extract_subject_terms(record),
        "matched_subjects": unique_texts(matched_subjects),
        "mineral_names": unique_texts(minerals),
        "mineral_groups": unique_texts(groups),
    }


def extract_sample_codes(custom_fields):
    """Return distinct sample codes associated with the record."""
    codes = []
    samples = custom_fields.get("arg:amostras")

    if isinstance(samples, list):
        for sample in samples:
            if not isinstance(sample, dict):
                continue
            code = safe_text(sample.get("codigo_amostra"))
            if code:
                codes.append(code)

    if not codes:
        legacy_code = safe_text(custom_fields.get("arg:amostra_codigo"))
        if legacy_code:
            codes.append(legacy_code)

    return unique_texts(codes)


def extract_methods(custom_fields):
    """Return analytical methods and techniques cited on the record."""
    return unique_texts(
        split_structured_terms(
            custom_fields.get("arg:metodo_descricao"),
            custom_fields.get("arg:metodo_tecnicas_utilizadas"),
            custom_fields.get("arg:metodologia_nome"),
            custom_fields.get("arg:metodologia_descricao"),
            custom_fields.get("arg:metodologia_equipamento_utilizado"),
            custom_fields.get("arg:metodologia_objetivo"),
            custom_fields.get("arg:pesquisa_metodologias_relacionadas"),
            custom_fields.get("arg:analise_metodos_relacionados"),
        )
    )


def extract_use_signatures(custom_fields):
    """Return flattened functional/application descriptors for the record."""
    return unique_texts(
        split_structured_terms(
            custom_fields.get("arg:usos_descricao"),
            custom_fields.get("arg:usos_aplicacoes_industriais"),
            custom_fields.get("arg:usos_aplicacoes_tecnologicas"),
            custom_fields.get("arg:usos_aplicacoes_cientificas"),
            custom_fields.get("arg:argilomineral_usos_aplicacoes"),
        )
    )


def extract_context_signature(custom_fields, mineral_entries):
    """Return contextual/geological descriptors for a record."""
    hierarchy = resolve_geological_hierarchy(
        [item.get("era_term") for item in mineral_entries] + [custom_fields.get("arg:origem_era_geologica")]
    )
    environment = safe_text(custom_fields.get("arg:origem_ambiente_formacao"))
    rock = safe_text(custom_fields.get("arg:origem_tipo_rocha"))
    formation = safe_text(custom_fields.get("arg:origem_formacao_geologica")) or choose_primary_label(
        [item.get("formation_geological") for item in mineral_entries]
    )

    return {
        "ambiente_formacao": environment,
        "rocha_hospedeira": rock,
        "era_geologica": hierarchy.get("era"),
        "periodo_geologico": hierarchy.get("periodo"),
        "epoca_geologica": hierarchy.get("epoca"),
        "formacao_geologica": formation,
        "hierarquia_geologica": hierarchy,
    }


def extract_mineral_names(custom_fields):
    """Return mineral names from the existing Argiloteca mineral fields."""
    names_by_key = {}
    entries = extract_mineral_entries(custom_fields)

    for mineral in entries:
        name = mineral.get("mineral_name")
        key = mineral_key(name)
        if key:
            names_by_key[key] = name

    return [names_by_key[key] for key in sorted(names_by_key)]


def extract_mineral_groups(custom_fields):
    """Return normalized mineral-group labels from existing mineral entries."""
    groups_by_key = {}

    for mineral in extract_mineral_entries(custom_fields):
        group = safe_text(mineral.get("mineral_group"))
        key = mineral_key(group)
        if key:
            groups_by_key[key] = group

    return [groups_by_key[key] for key in sorted(groups_by_key)]


def normalize_record(record, matcher=None):
    """Convert one Invenio record into the network node data model.

    A entrada e o registro bruto do servico; a saida agrega oxidos, minerais,
    amostra, contexto geologico e assinaturas de uso esperadas pelo painel.
    """
    custom_fields = record_custom_fields(record)
    oxides = extract_oxides(custom_fields)
    summary = extract_summary(custom_fields)
    record_id = record.get("id") or record.get("uuid")
    if not record_id:
        return None

    classe = safe_text(summary.get("classe_geoquimica"))
    componente = safe_text(summary.get("componente_dominante"))
    predominancia = safe_text(summary.get("predominancia_mineral"))
    fracao = parse_float(summary.get("fracao_argilosa_estimada"))
    razao = parse_float(summary.get("razao_Si_Al") or summary.get("razao_si_al"))
    mineral_entries = extract_mineral_entries(custom_fields)
    sample = extract_primary_sample(custom_fields)
    subject_map = extract_subject_mineral_map(record, matcher=matcher)
    mineral_names = unique_texts(extract_mineral_names(custom_fields) + subject_map["mineral_names"])
    mineral_groups = unique_texts(extract_mineral_groups(custom_fields) + subject_map["mineral_groups"])
    context = extract_context_signature(custom_fields, mineral_entries)
    methods = extract_methods(custom_fields)
    functional_signatures = extract_use_signatures(custom_fields)
    has_geoquimica = len(oxides) >= MIN_VALID_OXIDES

    if not has_geoquimica and not mineral_names:
        return None

    return {
        "id": record_id,
        "label": record_title(record),
        "title": f"{record_title(record)} - Perfil geoquimico",
        "has_geoquimica": has_geoquimica,
        "classe_geoquimica": classe,
        "componente_dominante": componente,
        "enriquecimento_relativo": safe_text(summary.get("enriquecimento_relativo")),
        "predominancia_mineral": predominancia,
        "resultado_analise": safe_text(custom_fields.get(ANALYSIS_RESULT_FIELD)),
        "observacoes": safe_text(summary.get("observacoes")),
        "fracao_argilosa_estimada": fracao,
        "razao_si_al": razao,
        "argilominerais": mineral_names,
        "grupos_minerais": mineral_groups,
        "sample_codes": extract_sample_codes(custom_fields),
        "sample_label": sample.get("sample_label"),
        "sample_locality": sample.get("locality"),
        "subjects": subject_map["subjects"],
        "subjects_mapeados": subject_map["matched_subjects"],
        "argilominerais_subject": subject_map["mineral_names"],
        "grupo_mineralogico_dominante": choose_primary_label(mineral_groups),
        "ambiente_formacao": context["ambiente_formacao"],
        "rocha_hospedeira": context["rocha_hospedeira"],
        "era_geologica": context["era_geologica"],
        "periodo_geologico": context["periodo_geologico"],
        "epoca_geologica": context["epoca_geologica"],
        "formacao_geologica": context["formacao_geologica"],
        "metodos_principais": methods[:6],
        "uses_signatures": functional_signatures,
        "resumo_estruturado": summarize_text(
            choose_primary_label(mineral_groups),
            context["ambiente_formacao"],
            context["rocha_hospedeira"],
            context["era_geologica"],
            safe_text(custom_fields.get(ANALYSIS_RESULT_FIELD)),
        ),
        "oxidos": {oxide: oxides[oxide] for oxide in OXIDE_FIELDS if oxide in oxides},
        "links": {
            "record_html": f"/records/{record_id}",
            "record_api": f"/api/records/{record_id}",
        },
    }


def apply_filters(records, filters):
    """Apply scientific filters before network edges or aggregations are built."""
    filtered = []
    for record in records:
        if filters.get("classe_geoquimica") and record.get("classe_geoquimica") != filters["classe_geoquimica"]:
            continue
        if filters.get("mineral_group") and filters["mineral_group"] not in (record.get("grupos_minerais") or []):
            continue
        if filters.get("argilomineral") and filters["argilomineral"] not in (record.get("argilominerais") or []):
            continue
        if filters.get("ambiente_formacao") and record.get("ambiente_formacao") != filters["ambiente_formacao"]:
            continue
        if filters.get("rocha_hospedeira") and record.get("rocha_hospedeira") != filters["rocha_hospedeira"]:
            continue
        if filters.get("era_geologica") and record.get("era_geologica") != filters["era_geologica"]:
            continue

        if not in_range(record["oxidos"].get("SiO2"), filters.get("sio2_min"), filters.get("sio2_max")):
            continue
        if not in_range(record["oxidos"].get("Al2O3"), filters.get("al2o3_min"), filters.get("al2o3_max")):
            continue
        if not in_range(record["oxidos"].get("Fe2O3"), filters.get("fe2o3_min"), filters.get("fe2o3_max")):
            continue
        if not in_range(record["oxidos"].get("TiO2"), filters.get("tio2_min"), filters.get("tio2_max")):
            continue
        if not in_range(record.get("fracao_argilosa_estimada"), filters.get("fracao_min"), filters.get("fracao_max")):
            continue
        if not in_range(record.get("razao_si_al"), filters.get("razao_si_al_min"), filters.get("razao_si_al_max")):
            continue
        filtered.append(record)
    return filtered


def sort_text_values(values):
    """Sort readable labels with accent-insensitive normalization."""
    return sorted({value for value in values if value}, key=lambda item: normalize_key(item) or "")


def build_network_filter_catalog(records):
    """Build scientific filter options for the analogy network page."""
    return {
        "mineral_group": sort_text_values(
            group for record in records for group in (record.get("grupos_minerais") or [])
        ),
        "argilomineral": sort_text_values(
            mineral for record in records for mineral in (record.get("argilominerais") or [])
        ),
        "ambiente_formacao": sort_text_values(record.get("ambiente_formacao") for record in records),
        "rocha_hospedeira": sort_text_values(record.get("rocha_hospedeira") for record in records),
        "era_geologica": sort_text_values(record.get("era_geologica") for record in records),
        "analysis_mode": sorted(ANALOGY_WEIGHT_PROFILES.keys()),
        "relation_type": list(ANALOGY_RELATION_TYPES),
        "analogy_class": list(ANALOGY_CLASSES),
        "confidence_class": list(CONFIDENCE_CLASSES),
    }


def sanitize_network_filters(filters, catalog):
    """Keep only valid scientific filter combinations for the network page."""
    sanitized = dict(filters or {})
    for key in ("mineral_group", "argilomineral", "ambiente_formacao", "rocha_hospedeira", "era_geologica"):
        value = safe_text(sanitized.get(key))
        valid_values = set(catalog.get(key) or [])
        sanitized[key] = value if value in valid_values else None

    mode = safe_text(sanitized.get("analysis_mode"))
    sanitized["analysis_mode"] = mode if mode in ANALOGY_WEIGHT_PROFILES else "composite"

    relation_type = safe_text(sanitized.get("relation_type"))
    sanitized["relation_type"] = relation_type if relation_type in ANALOGY_RELATION_TYPES else None

    analogy_class = safe_text(sanitized.get("analogy_class"))
    sanitized["analogy_class"] = analogy_class if analogy_class in ANALOGY_CLASSES else None

    confidence_class = safe_text(sanitized.get("confidence_class"))
    sanitized["confidence_class"] = confidence_class if confidence_class in CONFIDENCE_CLASSES else None
    return sanitized


def in_range(value, min_value, max_value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
        min_value: Valor de entrada consumido por esta etapa do fluxo.
        max_value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if value is None:
        return min_value is None and max_value is None
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def build_scaled_vectors(records):
    """Standardize oxide vectors so cosine/euclidean scores are comparable."""
    indexed_rows = [
        (index, [record["oxidos"].get(oxide, 0.0) for oxide in OXIDE_FIELDS])
        for index, record in enumerate(records)
        if record.get("has_geoquimica")
    ]
    if not indexed_rows:
        return {}

    raw = [row for _, row in indexed_rows]
    columns = list(zip(*raw))
    means = [sum(col) / len(col) for col in columns]
    scales = []
    for col, mean in zip(columns, means):
        variance = sum((value - mean) ** 2 for value in col) / len(col)
        scale = math.sqrt(variance)
        scales.append(scale or 1.0)

    return {
        index: [(value - means[idx]) / scales[idx] for idx, value in enumerate(row)]
        for index, row in indexed_rows
    }


def cosine_similarity(a, b):
    """
    Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
    
    Args:
        a: Valor de entrada consumido por esta etapa do fluxo.
        b: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return max(0.0, min(1.0, (dot / (norm_a * norm_b) + 1.0) / 2.0))


def euclidean_similarity(a, b):
    """
    Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
    
    Args:
        a: Valor de entrada consumido por esta etapa do fluxo.
        b: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    distance = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
    return 1.0 / (1.0 + distance)


def pairwise_similarities(records, metric):
    """Compute pairwise geoquimical similarity for records with enough oxides."""
    vectors = build_scaled_vectors(records)
    similarities = []
    for i, source in enumerate(records):
        source_vector = vectors.get(i)
        for j in range(i + 1, len(records)):
            target = records[j]
            target_vector = vectors.get(j)
            if not source_vector or not target_vector:
                continue
            if metric == "euclidean":
                score = euclidean_similarity(source_vector, target_vector)
            else:
                score = cosine_similarity(source_vector, target_vector)
            similarities.append((source["id"], target["id"], round(score, 4)))
    return similarities


def similarity_lookup(records, metric):
    """Index geoquimical vector similarities for constant-time pair access."""
    lookup = {}
    for source, target, score in pairwise_similarities(records, metric):
        lookup[(source, target)] = score
        lookup[(target, source)] = score
    return lookup


def confidence_class(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if value >= 0.75:
        return "alta"
    if value >= 0.5:
        return "media"
    return "baixa"


def analogy_class(score_total, confidence_value, supported_dimensions):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        score_total: Valor de entrada consumido por esta etapa do fluxo.
        confidence_value: Valor de entrada consumido por esta etapa do fluxo.
        supported_dimensions: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if score_total >= 0.72 and confidence_value >= 0.72 and supported_dimensions >= 3:
        return "confirmada"
    if score_total >= 0.5 and confidence_value >= 0.5 and supported_dimensions >= 2:
        return "provavel"
    return "exploratoria"


def determine_relation_type(scores):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        scores: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    strong_dimensions = [name for name, value in scores.items() if value >= 0.55]
    if len(strong_dimensions) >= 2:
        return "analogia_composta"
    dominant = max(scores.items(), key=lambda item: item[1])[0]
    return {
        "score_geoquimico": "geoquimica_analoga",
        "score_mineralogico": "grupo_mineralogico_compativel",
        "score_contextual": "contexto_geologico_semelhante",
        "score_funcional": "assinatura_funcional_semelhante",
    }.get(dominant, "analogia_composta")


def build_dimension_result(score, supported, evidence=None, differences=None):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        score: Valor de entrada consumido por esta etapa do fluxo.
        supported: Valor de entrada consumido por esta etapa do fluxo.
        evidence: Valor de entrada consumido por esta etapa do fluxo.
        differences: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return {
        "score": round(score, 4),
        "supported": supported,
        "evidence": evidence or [],
        "differences": differences or [],
    }


def score_geoquimico(record_a, record_b, similarity_map, metric):
    """Score chemical analogy from oxide vectors, Si/Al ratio and summaries."""
    evidence = []
    differences = []
    vector_score = similarity_map.get((record_a["id"], record_b["id"]), 0.0)
    ratio_score = numeric_similarity(record_a.get("razao_si_al"), record_b.get("razao_si_al"))
    fraction_score = numeric_similarity(
        record_a.get("fracao_argilosa_estimada"),
        record_b.get("fracao_argilosa_estimada"),
        scale=100.0,
    )
    class_score = 1.0 if record_a.get("classe_geoquimica") and record_a.get("classe_geoquimica") == record_b.get("classe_geoquimica") else 0.0
    supported = bool(record_a.get("has_geoquimica") and record_b.get("has_geoquimica"))

    if vector_score:
        evidence.append(
            {
                "dimension": "geoquimica",
                "label": "Semelhança vetorial dos óxidos principais",
                "value": round(vector_score, 4),
                "source": f"métrica {metric}",
            }
        )
    if ratio_score >= 0.6:
        evidence.append(
            {
                "dimension": "geoquimica",
                "label": "Razão Si/Al compatível",
                "value": round(ratio_score, 4),
                "source": "arg:proporcoes_resultados_principais.razao_Si_Al",
            }
        )
    elif record_a.get("razao_si_al") is not None and record_b.get("razao_si_al") is not None:
        differences.append("Razão Si/Al divergente entre os registros.")

    if fraction_score >= 0.6:
        evidence.append(
            {
                "dimension": "geoquimica",
                "label": "Fração argilosa estimada semelhante",
                "value": round(fraction_score, 4),
                "source": "arg:proporcoes_resultados_principais.fracao_argilosa_estimada",
            }
        )
    elif record_a.get("fracao_argilosa_estimada") is not None and record_b.get("fracao_argilosa_estimada") is not None:
        differences.append("Fração argilosa estimada com discrepância relevante.")

    if class_score:
        evidence.append(
            {
                "dimension": "geoquimica",
                "label": "Classe geoquímica coincidente",
                "value": 1.0,
                "source": "arg:proporcoes_resultados_principais.classe_geoquimica",
            }
        )
    elif record_a.get("classe_geoquimica") and record_b.get("classe_geoquimica"):
        differences.append("Classe geoquímica distinta.")

    score = round((0.6 * vector_score) + (0.2 * ratio_score) + (0.15 * fraction_score) + (0.05 * class_score), 4)
    return build_dimension_result(score, supported, evidence, differences)


def score_mineralogico(record_a, record_b):
    """Score mineralogical analogy from curated minerals, groups and subjects."""
    evidence = []
    differences = []
    mineral_score = jaccard_score(record_a.get("argilominerais"), record_b.get("argilominerais"))
    group_score = jaccard_score(record_a.get("grupos_minerais"), record_b.get("grupos_minerais"))
    subject_score = jaccard_score(record_a.get("subjects_mapeados"), record_b.get("subjects_mapeados"))
    supported = bool((record_a.get("argilominerais") or record_a.get("grupos_minerais")) and (record_b.get("argilominerais") or record_b.get("grupos_minerais")))

    if mineral_score:
        evidence.append(
            {
                "dimension": "mineralogica",
                "label": "Argilominerais compartilhados",
                "value": mineral_score,
                "source": "arg:argilominerais + metadata.subjects",
                "details": sorted(
                    set(record_a.get("argilominerais") or []).intersection(set(record_b.get("argilominerais") or []))
                ),
            }
        )
    if group_score:
        evidence.append(
            {
                "dimension": "mineralogica",
                "label": "Compatibilidade entre grupos mineralógicos",
                "value": group_score,
                "source": "arg:argilominerais.grupo + metadata.subjects",
            }
        )
    elif record_a.get("grupos_minerais") and record_b.get("grupos_minerais"):
        differences.append("Grupos mineralógicos sem interseção direta.")

    if subject_score:
        evidence.append(
            {
                "dimension": "mineralogica",
                "label": "Subjects mapeados coerentes",
                "value": subject_score,
                "source": "metadata.subjects",
            }
        )

    if not mineral_score and record_a.get("argilominerais") and record_b.get("argilominerais"):
        differences.append("Argilominerais identificados não convergem diretamente.")

    score = round((0.5 * mineral_score) + (0.35 * group_score) + (0.15 * subject_score), 4)
    return build_dimension_result(score, supported, evidence, differences)


def geological_hierarchy_score(record_a, record_b):
    """Score matching geological chronology levels without inventing hierarchy."""
    hierarchy_pairs = (
        ("era_geologica", 0.45),
        ("periodo_geologico", 0.35),
        ("epoca_geologica", 0.20),
    )
    score = 0.0
    supported = False
    for field, weight in hierarchy_pairs:
        left = record_a.get(field)
        right = record_b.get(field)
        if left and right:
            supported = True
            if left == right:
                score += weight
    return round(score, 4), supported


def score_contextual(record_a, record_b):
    """Score geological setting analogy from environment, host rock and time."""
    evidence = []
    differences = []
    environment_score = text_overlap_score(record_a.get("ambiente_formacao"), record_b.get("ambiente_formacao"))
    rock_score = text_overlap_score(record_a.get("rocha_hospedeira"), record_b.get("rocha_hospedeira"))
    formation_score = text_overlap_score(record_a.get("formacao_geologica"), record_b.get("formacao_geologica"))
    chronology_score, chronology_supported = geological_hierarchy_score(record_a, record_b)
    supported = any(
        [
            record_a.get("ambiente_formacao") and record_b.get("ambiente_formacao"),
            record_a.get("rocha_hospedeira") and record_b.get("rocha_hospedeira"),
            record_a.get("formacao_geologica") and record_b.get("formacao_geologica"),
            chronology_supported,
        ]
    )

    if environment_score:
        evidence.append(
            {
                "dimension": "contextual",
                "label": "Ambiente de formação semelhante",
                "value": environment_score,
                "source": "arg:origem_ambiente_formacao",
            }
        )
    elif record_a.get("ambiente_formacao") and record_b.get("ambiente_formacao"):
        differences.append("Ambiente de formação distinto ou fracamente comparável.")

    if rock_score:
        evidence.append(
            {
                "dimension": "contextual",
                "label": "Rocha hospedeira compatível",
                "value": rock_score,
                "source": "arg:origem_tipo_rocha",
            }
        )
    elif record_a.get("rocha_hospedeira") and record_b.get("rocha_hospedeira"):
        differences.append("Rocha hospedeira distinta.")

    if formation_score:
        evidence.append(
            {
                "dimension": "contextual",
                "label": "Formação/unidade geológica semelhante",
                "value": formation_score,
                "source": "arg:origem_formacao_geologica",
            }
        )
    elif record_a.get("formacao_geologica") and record_b.get("formacao_geologica"):
        differences.append("Formação geológica sem correspondência clara.")

    if chronology_score:
        evidence.append(
            {
                "dimension": "contextual",
                "label": "Recorte cronogeológico convergente",
                "value": chronology_score,
                "source": "arg:origem_era_geologica + vocabulário tempo geológico",
            }
        )
    elif chronology_supported:
        differences.append("Cronologia geológica em níveis distintos.")

    score = round((0.30 * environment_score) + (0.20 * rock_score) + (0.25 * formation_score) + (0.25 * chronology_score), 4)
    return build_dimension_result(score, supported, evidence, differences)


def score_funcional(record_a, record_b):
    """Score functional analogy from uses and registered analytical reading."""
    evidence = []
    differences = []
    use_score = jaccard_score(record_a.get("uses_signatures"), record_b.get("uses_signatures"))
    interpretation_score = text_overlap_score(record_a.get("resultado_analise"), record_b.get("resultado_analise"))
    supported = bool(record_a.get("uses_signatures") or record_a.get("resultado_analise")) and bool(
        record_b.get("uses_signatures") or record_b.get("resultado_analise")
    )

    if use_score:
        evidence.append(
            {
                "dimension": "funcional",
                "label": "Usos/aplicações compatíveis",
                "value": use_score,
                "source": "arg:usos_*",
            }
        )
    elif record_a.get("uses_signatures") and record_b.get("uses_signatures"):
        differences.append("Assinatura funcional distinta nas aplicações registradas.")

    if interpretation_score:
        evidence.append(
            {
                "dimension": "funcional",
                "label": "Interpretação analítica convergente",
                "value": interpretation_score,
                "source": ANALYSIS_RESULT_FIELD,
            }
        )
    elif record_a.get("resultado_analise") and record_b.get("resultado_analise"):
        differences.append("Interpretação registrada aponta usos ou leituras diferentes.")

    score = round((0.65 * use_score) + (0.35 * interpretation_score), 4)
    return build_dimension_result(score, supported, evidence, differences)


def score_analogy(record_a, record_b, similarity_map, metric, weights):
    """Build a multi-dimensional, explainable analogy assessment for one pair."""
    dimensions = {
        "score_geoquimico": score_geoquimico(record_a, record_b, similarity_map, metric),
        "score_mineralogico": score_mineralogico(record_a, record_b),
        "score_contextual": score_contextual(record_a, record_b),
        "score_funcional": score_funcional(record_a, record_b),
    }
    scores = {name: data["score"] for name, data in dimensions.items()}
    supported_scores = [data["score"] for data in dimensions.values() if data["supported"]]
    supported_dimensions = len(supported_scores)
    score_total = round(sum(scores[name] * weights[name] for name in ANALOGY_DIMENSIONS), 4)
    convergence = 0.6
    if len(supported_scores) >= 2:
        convergence = 1.0 - min(max(supported_scores) - min(supported_scores), 1.0)
    support_ratio = supported_dimensions / len(ANALOGY_DIMENSIONS)
    confidence_value = round((0.5 * score_total) + (0.25 * support_ratio) + (0.25 * convergence), 4)
    relation = determine_relation_type(scores)
    class_name = analogy_class(score_total, confidence_value, supported_dimensions)
    evidence = []
    differences = []
    for item in dimensions.values():
        evidence.extend(item["evidence"])
        differences.extend(item["differences"])

    if scores["score_geoquimico"] >= 0.65 and (scores["score_mineralogico"] < 0.35 or scores["score_contextual"] < 0.35):
        differences.append("Semelhança química com divergência mineralógica ou contextual.")
    if score_total < 0.45 and evidence:
        differences.append("Analogia parcial; recomenda-se verificação manual das evidências.")

    shared_argilominerais = sorted(
        set(record_a.get("argilominerais") or []).intersection(set(record_b.get("argilominerais") or []))
    )
    return {
        "weight": score_total,
        "similarity": score_total,
        "score_total": score_total,
        "score_geoquimico": scores["score_geoquimico"],
        "score_mineralogico": scores["score_mineralogico"],
        "score_contextual": scores["score_contextual"],
        "score_funcional": scores["score_funcional"],
        "confidence": confidence_value,
        "confidence_class": confidence_class(confidence_value),
        "analogy_class": class_name,
        "relation_type": relation,
        "supported_dimensions": supported_dimensions,
        "evidence": evidence,
        "differences": unique_texts(differences),
        "shared_argilominerais": shared_argilominerais,
        "convergence": round(convergence, 4),
    }


def build_mineral_network_map(records):
    """Summarize which records enter the network through each argilomineral."""
    minerals = defaultdict(lambda: {"groups": set(), "records": []})

    for record in records:
        groups = record.get("grupos_minerais") or []
        record_entry = {
            "id": record["id"],
            "label": record["label"],
            "record_html": (record.get("links") or {}).get("record_html"),
        }
        for mineral in record.get("argilominerais") or []:
            minerals[mineral]["groups"].update(groups)
            minerals[mineral]["records"].append(record_entry)

    items = []
    for mineral, data in sorted(minerals.items()):
        items.append(
            {
                "mineral": mineral,
                "groups": sorted(data["groups"]),
                "count_records": len({item["id"] for item in data["records"]}),
                "records": sorted(data["records"], key=lambda item: item["label"]),
            }
        )
    return items


def apply_edge_filters(edges, filters):
    """Apply scientific relation filters after analogy edges are computed."""
    filtered = []
    for edge in edges:
        if filters.get("relation_type") and edge.get("relation_type") != filters["relation_type"]:
            continue
        if filters.get("analogy_class") and edge.get("analogy_class") != filters["analogy_class"]:
            continue
        if filters.get("confidence_class") and edge.get("confidence_class") != filters["confidence_class"]:
            continue
        filtered.append(edge)
    return filtered


def relation_counts(edges):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        edges: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    counts = defaultdict(int)
    for edge in edges:
        counts[edge.get("relation_type") or "desconhecida"] += 1
    return dict(sorted(counts.items()))


def build_edges(records, metric="cosine", edge_mode="knn", k=3, threshold=0.8, weights=None):
    """Build explainable analogy edges between record nodes."""
    weights = weights or ANALOGY_WEIGHT_PROFILES["composite"]
    indexed_records = {record["id"]: record for record in records}
    similarity_map = similarity_lookup(records, metric)
    analyses = []

    for i, source in enumerate(records):
        for target in records[i + 1:]:
            analysis = score_analogy(source, target, similarity_map, metric, weights)
            analyses.append((source["id"], target["id"], analysis))

    edges_by_pair = {}
    if edge_mode == "threshold":
        selected = [item for item in analyses if item[2]["score_total"] >= threshold]
    else:
        by_node = defaultdict(list)
        for source_id, target_id, analysis in analyses:
            by_node[source_id].append((source_id, target_id, analysis))
            by_node[target_id].append((target_id, source_id, analysis))
        selected = []
        for items in by_node.values():
            selected.extend(sorted(items, key=lambda item: item[2]["score_total"], reverse=True)[:k])

    for source_id, target_id, analysis in selected:
        left, right = sorted((source_id, target_id))
        existing = edges_by_pair.get((left, right))
        if not existing or analysis["score_total"] >= existing["score_total"]:
            edges_by_pair[(left, right)] = dict(analysis)

    return [
        {
            "id": f"{source_id}__{target_id}",
            "source": source_id,
            "target": target_id,
            "source_label": indexed_records[source_id]["label"],
            "target_label": indexed_records[target_id]["label"],
            **data,
        }
        for (source_id, target_id), data in sorted(
            edges_by_pair.items(),
            key=lambda item: (-item[1]["score_total"], item[0][0], item[0][1]),
        )
    ]


def build_clusters(records, edges):
    """Group connected network nodes with a small union-find implementation."""
    parent = {record["id"]: record["id"] for record in records}

    def find(item):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            item: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left, right):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            left: Valor de entrada consumido por esta etapa do fluxo.
            right: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for edge in edges:
        union(edge["source"], edge["target"])

    grouped = defaultdict(list)
    for record in records:
        grouped[find(record["id"])].append(record)

    clusters = []
    cluster_by_node = {}
    for idx, members in enumerate(sorted(grouped.values(), key=len, reverse=True), start=1):
        cluster_id = f"cluster-{idx}"
        classes = [item.get("classe_geoquimica") for item in members if item.get("classe_geoquimica")]
        label_class = max(set(classes), key=classes.count) if classes else "sem classe"
        clusters.append({"id": cluster_id, "label": f"Cluster {label_class}", "size": len(members)})
        for member in members:
            cluster_by_node[member["id"]] = cluster_id

    return clusters, cluster_by_node


def node_size(record, degree):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        record: Valor de entrada consumido por esta etapa do fluxo.
        degree: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    fraction = record.get("fracao_argilosa_estimada")
    if fraction is not None:
        return max(18, min(42, 18 + math.sqrt(abs(fraction)) * 0.8))
    return max(18, min(36, 18 + degree * 4))


def decorate_nodes(records, edges, cluster_by_node):
    """Attach UI sizing/color hints while keeping scientific node fields intact."""
    degree = defaultdict(int)
    for edge in edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1

    nodes = []
    for record in records:
        item = dict(record)
        item["cluster"] = cluster_by_node.get(record["id"])
        item["ui"] = {
            "color_group": record.get("classe_geoquimica") or "sem-classe",
            "size": round(node_size(record, degree[record["id"]]), 2),
            "shape": "ellipse",
        }
        nodes.append(item)
    return nodes


def build_network(filters=None, metric="cosine", edge_mode="knn", k=3, threshold=0.8, size=DEFAULT_SIZE, analysis_mode="composite"):
    """Build the full geoquimica analogy graph returned by the API route."""
    filters = filters or {}
    metric = metric if metric in {"cosine", "euclidean"} else "cosine"
    edge_mode = edge_mode if edge_mode in {"knn", "threshold"} else "knn"
    analysis_mode = analysis_mode if analysis_mode in ANALOGY_WEIGHT_PROFILES else "composite"
    k = max(1, min(int(k or 3), 25))
    threshold = max(0.0, min(float(threshold or 0.8), 1.0))

    matcher = get_mineral_matcher()
    records = [normalize_record(record, matcher=matcher) for record in search_records(size=size)]
    records = [record for record in records if record]
    filter_catalog = build_network_filter_catalog(records)
    effective_filters = sanitize_network_filters(filters, filter_catalog)
    weights = ANALOGY_WEIGHT_PROFILES[effective_filters.get("analysis_mode") or analysis_mode]
    filtered_records = apply_filters(records, effective_filters)
    edges = build_edges(filtered_records, metric=metric, edge_mode=edge_mode, k=k, threshold=threshold, weights=weights)
    edges = apply_edge_filters(edges, effective_filters)
    clusters, cluster_by_node = build_clusters(filtered_records, edges)
    nodes = decorate_nodes(filtered_records, edges, cluster_by_node)
    mineral_map = build_mineral_network_map(filtered_records)
    warnings = []
    if not any(item.get("has_geoquimica") for item in nodes):
        warnings.append("Nenhum registro com geoquímica estruturada suficiente para comparação robusta.")
    if not edges:
        warnings.append("Nenhuma analogia atendeu aos critérios atuais; revise filtros ou reduza o limiar.")

    applied = {key: value for key, value in effective_filters.items() if value not in (None, "", False)}
    return {
        "meta": {
            "total_registros": len(nodes),
            "total_registros_lidos": len(records),
            "total_registros_com_geoquimica": sum(1 for item in nodes if item.get("has_geoquimica")),
            "total_registros_por_argilomineral": sum(1 for item in nodes if item.get("argilominerais")),
            "total_relacoes": len(edges),
            "metrica_similaridade": metric,
            "criterio_arestas": edge_mode,
            "k": k,
            "threshold": threshold,
            "analysis_mode": effective_filters.get("analysis_mode") or analysis_mode,
            "weights": weights,
            "filtros_aplicados": applied,
            "effective_params": {
                **applied,
                "metric": metric,
                "edge_mode": edge_mode,
                "k": k,
                "threshold": threshold,
                "analysis_mode": effective_filters.get("analysis_mode") or analysis_mode,
            },
            "relation_counts": relation_counts(edges),
            "warnings": warnings,
        },
        "filters": filter_catalog,
        "nodes": nodes,
        "edges": edges,
        "clusters": clusters,
        "mineral_map": mineral_map,
    }


@lru_cache(maxsize=1)
def load_geological_vocabulary():
    """Load the geological controlled vocabulary used by the Argiloteca."""
    terms_by_id = {}
    terms_by_key = {}

    if not TEMPO_GEOLOGICO_PATH.exists():
        return {"by_id": terms_by_id, "by_key": terms_by_key, "source": {}}

    with TEMPO_GEOLOGICO_PATH.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            term_id = safe_text(item.get("id"))
            title_pt = safe_text((item.get("title") or {}).get("pt"))
            title_en = safe_text((item.get("title") or {}).get("en"))
            props = item.get("props") or {}
            level = safe_text(props.get("nivel"))
            broader = safe_text(props.get("broader"))
            display = title_pt or title_en or term_id

            if not term_id or not level:
                continue

            entry = {
                "id": term_id,
                "label": display,
                "title_pt": title_pt,
                "title_en": title_en,
                "level": level,
                "broader": broader,
                "start_ma": parse_float(props.get("inicio_ma")),
                "end_ma": parse_float(props.get("fim_ma")),
            }
            terms_by_id[term_id] = entry

            for key in {normalize_key(term_id), normalize_key(title_pt), normalize_key(title_en)}:
                if key:
                    terms_by_key[key] = term_id

    source = {}
    first = next(iter(terms_by_id.values()), None)
    if first:
        source = {
            "path": str(TEMPO_GEOLOGICO_PATH),
            "scheme": "tempo_geologico",
            "source": "International Commission on Stratigraphy",
        }

    return {"by_id": terms_by_id, "by_key": terms_by_key, "source": source}


def resolve_geological_hierarchy(raw_terms):
    """Resolve a record/mineral geological term to eon > era > periodo > epoca."""
    vocabulary = load_geological_vocabulary()
    by_id = vocabulary["by_id"]
    by_key = vocabulary["by_key"]

    matched = None
    raw_label = None
    for candidate in raw_terms:
        raw_label = safe_text(candidate) or raw_label
        key = normalize_key(candidate)
        if not key:
            continue
        term_id = by_key.get(key)
        if term_id and term_id in by_id:
            matched = by_id[term_id]
            break

    hierarchy = {level: None for level in GEOLOGICAL_LEVELS}
    hierarchy["term"] = raw_label
    hierarchy["normalized_term"] = matched["label"] if matched else raw_label

    current = matched
    while current:
        level = current.get("level")
        if level in hierarchy and not hierarchy[level]:
            hierarchy[level] = current["label"]
        broader = current.get("broader")
        current = by_id.get(broader) if broader else None

    return hierarchy


def extract_primary_sample(custom_fields):
    """Extract a representative sample context for aggregate panels."""
    samples = custom_fields.get("arg:amostras")
    if isinstance(samples, list):
        for sample in samples:
            if isinstance(sample, dict):
                return {
                    "sample_id": safe_text(sample.get("sample_id")) or safe_text(sample.get("codigo_amostra")),
                    "sample_code": safe_text(sample.get("codigo_amostra")),
                    "sample_label": safe_text(sample.get("descricao_amostra"))
                    or safe_text(sample.get("local_coleta"))
                    or safe_text(sample.get("codigo_amostra")),
                    "locality": safe_text(sample.get("local_coleta")),
                    "sample_type": safe_text(sample.get("tipo_amostra"))
                    or safe_text(sample.get("contexto_geologico")),
                }

        # If a structured sample list exists, do not mask missing sample data with legacy fields.
        return {
            "sample_id": None,
            "sample_code": None,
            "sample_label": None,
            "locality": None,
            "sample_type": None,
        }

    return {
        "sample_id": None,
        "sample_code": None,
        "sample_label": safe_text(custom_fields.get("arg:amostra_descricao_local"))
        or safe_text(custom_fields.get("arg:amostra_local_coleta")),
        "locality": safe_text(custom_fields.get("arg:amostra_local_coleta"))
        or safe_text(custom_fields.get("arg:pesquisa_local")),
        "sample_type": safe_text(custom_fields.get("arg:amostra_tipo_amostra")),
    }


def extract_mineral_entries(custom_fields):
    """Return mineral entries with tolerant fallbacks for legacy data."""
    minerals = custom_fields.get(MINERALS_FIELD)
    entries = []
    has_structured_minerals = isinstance(minerals, list)

    if isinstance(minerals, list):
        for index, mineral in enumerate(minerals):
            if not isinstance(mineral, dict):
                continue
            entries.append(
                {
                    "entry_id": index + 1,
                    "mineral_name": safe_text(mineral.get("nome")),
                    "mineral_group": safe_text(mineral.get("grupo")),
                    "era_term": safe_text(mineral.get("era_geologica")),
                    "formation_geological": safe_text(mineral.get("formacao_geologica")),
                    "origin_summary": safe_text(mineral.get("origem_formacao")),
                    "traceability_status": safe_text(mineral.get("traceability_status")) or "pending_curation",
                    "relation_to_sample": safe_text(mineral.get("relation_to_sample")) or "candidate_in_sample",
                    "evidence_level": safe_text(mineral.get("evidence_level")) or "weak",
                    "validation_notes": safe_text(mineral.get("validation_notes")),
                    "external_source": safe_text(mineral.get("external_source")),
                }
            )

    if entries:
        return entries

    if has_structured_minerals:
        return []

    legacy_name = safe_text(custom_fields.get(LEGACY_MINERAL_NAME_FIELD))
    if legacy_name:
        return [
            {
                "entry_id": 1,
                "mineral_name": legacy_name,
                "mineral_group": None,
                "era_term": safe_text(custom_fields.get("arg:origem_era_geologica")),
                "formation_geological": safe_text(custom_fields.get("arg:origem_formacao_geologica")),
                "origin_summary": safe_text(custom_fields.get("arg:origem_ambiente_formacao")),
                "traceability_status": "pending_curation",
                "relation_to_sample": "candidate_in_sample",
                "evidence_level": "weak",
                "validation_notes": "Mineral legado sem evidencia mineralogica explicita.",
                "external_source": None,
            }
        ]

    return []


def aggregate_geochemical_rows(size=DEFAULT_SIZE):
    """Build flat scientific rows for the aggregated geochemical panel."""
    rows = []

    for record in search_records(size=size):
        custom_fields = record_custom_fields(record)
        oxides = extract_oxides(custom_fields)
        if len(oxides) < MIN_VALID_OXIDES:
            continue

        record_id = record.get("id") or record.get("uuid")
        if not record_id:
            continue

        summary = extract_summary(custom_fields)
        sample = extract_primary_sample(custom_fields)
        minerals = extract_mineral_entries(custom_fields) or [
            {
                "entry_id": 1,
                "mineral_name": None,
                "mineral_group": None,
                "era_term": safe_text(custom_fields.get("arg:origem_era_geologica")),
                "formation_geological": safe_text(custom_fields.get("arg:origem_formacao_geologica")),
                "origin_summary": safe_text(custom_fields.get("arg:origem_ambiente_formacao")),
            }
        ]

        for mineral in minerals:
            geological = resolve_geological_hierarchy(
                [
                    mineral.get("era_term"),
                    custom_fields.get("arg:origem_era_geologica"),
                ]
            )
            row = {
                "row_id": f"{record_id}::{mineral.get('entry_id', 1)}",
                "record_id": record_id,
                "record_title": record_title(record),
                "sample_id": sample.get("sample_id"),
                "sample_code": sample.get("sample_code"),
                "sample_label": sample.get("sample_label") or sample.get("sample_code"),
                "locality": sample.get("locality"),
                "sample_type": sample.get("sample_type"),
                "has_sample": bool(sample.get("sample_code") or sample.get("sample_label") or sample.get("locality")),
                "mineral_name": mineral.get("mineral_name"),
                "mineral_group": mineral.get("mineral_group"),
                "formation_geological": mineral.get("formation_geological")
                or safe_text(custom_fields.get("arg:origem_formacao_geologica")),
                "origin_summary": mineral.get("origin_summary")
                or safe_text(custom_fields.get("arg:origem_ambiente_formacao")),
                "eon": geological.get("eon"),
                "era": geological.get("era"),
                "periodo": geological.get("periodo"),
                "epoca": geological.get("epoca"),
                "geological_term": geological.get("normalized_term"),
                "classe_geoquimica": safe_text(summary.get("classe_geoquimica")),
                "componente_dominante": safe_text(summary.get("componente_dominante")),
                "predominancia_mineral": safe_text(summary.get("predominancia_mineral")),
                "mineral_traceability_status": mineral.get("traceability_status") or "pending_curation",
                "mineral_relation_to_sample": mineral.get("relation_to_sample") or "candidate_in_sample",
                "mineral_evidence_level": mineral.get("evidence_level") or "weak",
                "mineral_validation_notes": mineral.get("validation_notes"),
                "mineral_external_source": mineral.get("external_source"),
                "fracao_argilosa_estimada": parse_float(summary.get("fracao_argilosa_estimada")),
                "oxides": {oxide: oxides[oxide] for oxide in OXIDE_FIELDS if oxide in oxides},
                "links": {
                    "record_html": f"/records/{record_id}",
                    "record_api": f"/api/records/{record_id}",
                },
            }
            rows.append(row)

    return rows


def apply_aggregated_filters(rows, filters):
    """Apply page filters to the flattened geochemical rows."""
    filtered = []
    query = normalize_key(filters.get("q"))
    argilomineral_filter = normalize_key(filters.get("argilomineral"))

    for row in rows:
        if filters.get("eon") and row.get("eon") != filters["eon"]:
            continue
        if filters.get("era") and row.get("era") != filters["era"]:
            continue
        if filters.get("periodo") and row.get("periodo") != filters["periodo"]:
            continue
        if filters.get("epoca") and row.get("epoca") != filters["epoca"]:
            continue
        if filters.get("mineral_group") and row.get("mineral_group") != filters["mineral_group"]:
            continue
        if argilomineral_filter and normalize_key(row.get("mineral_name")) != argilomineral_filter:
            continue
        if filters.get("has_sample") == "true" and not row.get("has_sample"):
            continue
        if filters.get("has_sample") == "false" and row.get("has_sample"):
            continue

        for oxide in AGGREGATED_OXIDE_FILTERS:
            value = row["oxides"].get(oxide)
            minimum = filters.get(f"{oxide.lower()}_min")
            maximum = filters.get(f"{oxide.lower()}_max")
            if not in_range(value, minimum, maximum):
                break
        else:
            if query:
                haystack = " ".join(
                    filter(
                        None,
                        [
                            row.get("record_title"),
                            row.get("sample_code"),
                            row.get("sample_label"),
                            row.get("mineral_name"),
                            row.get("mineral_group"),
                            row.get("formation_geological"),
                            row.get("locality"),
                        ],
                    )
                )
                if query not in (normalize_key(haystack) or ""):
                    continue
            filtered.append(row)

    return filtered


def unique_options(rows, key):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        rows: Valor de entrada consumido por esta etapa do fluxo.
        key: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return sorted({row.get(key) for row in rows if row.get(key)})


def aggregate_dimension(rows, dimension):
    """Aggregate flat rows by one scientific dimension and oxide averages."""
    grouped = defaultdict(list)
    for row in rows:
        label = row.get(dimension) or "Não informado"
        grouped[label].append(row)

    items = []
    for label, members in grouped.items():
        averages = {}
        for oxide in OXIDE_FIELDS:
            values = [member["oxides"].get(oxide) for member in members if member["oxides"].get(oxide) is not None]
            if values:
                averages[oxide] = round(sum(values) / len(values), 4)
        items.append(
            {
                "label": label,
                "count_rows": len(members),
                "count_records": len({member["record_id"] for member in members}),
                "averages": averages,
            }
        )

    return sorted(items, key=lambda item: (-item["count_rows"], item["label"]))


def oxide_statistics(rows):
    """Calculate descriptive oxide statistics for the aggregated panel."""
    stats = {}
    for oxide in OXIDE_FIELDS:
        values = [row["oxides"].get(oxide) for row in rows if row["oxides"].get(oxide) is not None]
        if not values:
            continue
        stats[oxide] = {
            "count": len(values),
            "mean": round(sum(values) / len(values), 4),
            "min": round(min(values), 4),
            "max": round(max(values), 4),
        }
    return stats


def build_aggregated_dataset(filters=None, size=DEFAULT_SIZE):
    """Return a phase-1 aggregated dataset for the new geochemical atlas page."""
    filters = filters or {}
    rows = aggregate_geochemical_rows(size=size)
    filtered_rows = apply_aggregated_filters(rows, filters)
    vocabulary = load_geological_vocabulary()

    return {
        "success": True,
        "meta": {
            "total_rows": len(filtered_rows),
            "total_rows_read": len(rows),
            "total_records": len({row["record_id"] for row in filtered_rows}),
            "total_records_read": len({row["record_id"] for row in rows}),
            "filters": {key: value for key, value in filters.items() if value not in (None, "", False)},
            "geological_vocabulary": vocabulary.get("source", {}),
            "implemented_phase": 1,
        },
        "filters": {
            "eon": unique_options(rows, "eon"),
            "era": unique_options(rows, "era"),
            "periodo": unique_options(rows, "periodo"),
            "epoca": unique_options(rows, "epoca"),
            "mineral_group": unique_options(rows, "mineral_group"),
            "argilomineral": unique_options(rows, "mineral_name"),
        },
        "records": filtered_rows,
        "summary": {
            "with_sample": sum(1 for row in filtered_rows if row.get("has_sample")),
            "with_era": sum(1 for row in filtered_rows if row.get("era")),
            "with_group": sum(1 for row in filtered_rows if row.get("mineral_group")),
            "oxide_statistics": oxide_statistics(filtered_rows),
        },
        "aggregations": {
            "by_era": aggregate_dimension(filtered_rows, "era"),
            "by_periodo": aggregate_dimension(filtered_rows, "periodo"),
            "by_epoca": aggregate_dimension(filtered_rows, "epoca"),
            "by_mineral_group": aggregate_dimension(filtered_rows, "mineral_group"),
            "by_argilomineral": aggregate_dimension(filtered_rows, "mineral_name"),
        },
    }


def find_record_detail(record_id):
    """Return the normalized node detail for one record id, when visible."""
    for record in search_records(size=DEFAULT_SIZE):
        if record.get("id") == record_id or record.get("uuid") == record_id:
            return normalize_record(record)
    return None
