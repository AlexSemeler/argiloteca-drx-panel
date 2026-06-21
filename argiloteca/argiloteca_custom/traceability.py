"""
Projeto: Painel DRX Argiloteca

Descrição:
Standalone traceability validation module for invenio.cfg imports. This file intentionally lives at the top level of the ``argiloteca_custom`` package so it can be imported without triggering the heavier ``argiloteca`` package bootstrap.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br

Colaboradores:
- Lucas Jantsch
- Arthur Oliveira

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

from datetime import date, datetime
import re

from invenio_drafts_resources.services.records.components import ServiceComponent
from invenio_i18n import gettext as _
from marshmallow_utils.fields import babel as marshmallow_babel
from marshmallow import ValidationError, fields

from argiloteca_custom.mineralogia import (
    MINDAT_SOURCE,
    build_mindat_uri,
    clean_text,
    enrich_mineral_semantics,
    parse_mindat_id,
    resolve_external_reference,
    resolve_mineral_group,
    resolve_short_description,
)
from argiloteca_custom.scientific_traceability import normalize_record_traceability


TRACEABILITY_FIELDS = (
    "arg:argilominerais",
    "arg:pesquisas_campo",
    "arg:amostras",
    "arg:analises",
    "arg:publicacoes_relacionadas",
    "arg:evidencias_mineralogicas",
    "arg:composicao_quimica_global",
    "arg:usos_argilomineral_nome",
    "arg:descricao_componentes",
    "arg:composicao_descricao_componentes",
    "arg:composicao_proporcoes",
    "arg:usos_descricao",
    "arg:usos_aplicacoes_industriais",
    "arg:usos_aplicacoes_tecnologicas",
    "arg:usos_aplicacoes_cientificas",
)

CUSTOM_TEXT_FIELDS = (
    "arg:argilomineral_nome",
    "arg:argilomineral_grupo",
    "arg:argilomineral_descricao",
    "arg:argilomineral_estrutura_cristalina",
    "arg:argilomineral_propriedades_especiais",
    "arg:argilomineral_origem_formacao",
    "arg:argilomineral_era_geologica",
    "arg:argilomineral_formacao_geologica",
    "arg:argilomineral_usos_aplicacoes",
    "arg:origem_ambiente_formacao",
    "arg:origem_tipo_rocha",
    "arg:origem_era_geologica",
    "arg:origem_formacao_geologica",
    "arg:usos_argilomineral_nome",
    "arg:usos_descricao",
    "arg:usos_aplicacoes_industriais",
    "arg:usos_aplicacoes_tecnologicas",
    "arg:usos_aplicacoes_cientificas",
    "arg:metodo_descricao",
    "arg:metodo_tecnicas_utilizadas",
    "arg:metodologia_nome",
    "arg:metodologia_descricao",
    "arg:metodologia_equipamento_utilizado",
    "arg:metodologia_objetivo",
    "arg:equipamento_nome",
    "arg:equipamento_descricao",
    "arg:equipamento_fabricante",
    "arg:pesquisa_local",
    "arg:pesquisa_data",
    "arg:pesquisa_responsavel",
    "arg:amostra_data_coleta",
    "arg:amostra_local_coleta",
    "arg:amostra_descricao_local",
    "arg:amostra_tipo_amostra",
    "arg:descricao_componentes",
    "arg:composicao_descricao_componentes",
    "arg:composicao_proporcoes",
    "arg:analise_descricao",
    "arg:analise_resultado",
    "arg:analise_data",
    "arg:analise_equipamento",
    "arg:publicacao_amostras_relacionadas",
    "arg:publicacao_argilominerais_relacionados",
    "arg:pesquisa_metodologias_relacionadas",
    "arg:analise_metodos_relacionados",
)

STRUCTURED_TEXT_SUBFIELDS = {
    "arg:argilominerais": (
        "codigo_amostra",
        "nome",
        "nome_cientifico_padronizado",
        "sinonimos",
        "formula_ideal",
        "grupo",
        "grupo_mineralogico",
        "subgrupo_mineralogico",
        "descricao",
        "descricao_curta",
        "estrutura_cristalina",
        "classe_estrutural",
        "sistema_cristalino",
        "classificacao_strunz",
        "classificacao_dana",
        "propriedades_especiais",
        "propriedades_relevantes",
        "origem_formacao",
        "ambiente_tipico_formacao",
        "era_geologica",
        "formacao_geologica",
        "usos_aplicacoes",
        "external_source",
        "external_id",
        "external_uri",
        "fonte_descricao",
        "observacao_proveniencia",
        "licenca_fonte",
        "data_ultima_sincronizacao",
        "traceability_status",
        "assertion_type",
        "evidence_level",
        "validation_notes",
        "relation_to_sample",
    ),
    "arg:pesquisas_campo": (
        "campanha_id",
        "titulo",
        "data_inicio",
        "data_fim",
        "responsavel",
        "equipe",
        "area_estudo",
        "objetivo",
        "observacoes",
    ),
    "arg:amostras": (
        "codigo_amostra",
        "campanha_id",
        "data_coleta",
        "responsavel_coleta",
        "local_coleta",
        "descricao_local",
        "contexto_geologico",
        "tempo_geologico",
        "rocha_hospedeira",
        "tipo_amostra",
        "observacoes_campo",
    ),
    "arg:analises": (
        "analise_id",
        "codigo_amostra",
        "metodo",
        "data_analise",
        "laboratorio",
        "equipamento",
        "condicoes_analise",
        "resultado_principal",
        "interpretacao",
        "arquivo_resultado",
        "observacoes",
        "traceability_status",
        "assertion_type",
        "evidence_level",
        "validation_notes",
    ),
    "arg:evidencias_mineralogicas": (
        "id",
        "sample_id",
        "analysis_id",
        "source_type",
        "evidence_text",
        "source_excerpt",
        "evidence_method",
        "mineral_name_detected",
        "normalized_mineral_name",
        "relation_to_sample",
        "traceability_status",
        "assertion_type",
        "evidence_level",
        "validation_notes",
    ),
    "arg:publicacoes_relacionadas": (
        "tipo",
        "titulo",
        "autores",
        "ano",
        "doi",
        "url",
        "fonte_ou_revista",
        "record_id",
        "identificador_externo",
        "codigo_amostra",
        "codigo_analise",
        "argilomineral_nome",
        "relacao_com_registro",
        "papel_da_amostra",
        "observacoes",
    ),
}

OBJECT_TEXT_SUBFIELDS = {
    "arg:composicao_quimica_global": (
        "codigo_amostra",
        "componente_dominante",
        "enriquecimento_relativo",
        "predominancia_mineral",
        "classe_geoquimica",
        "observacoes",
        "traceability_status",
        "assertion_type",
        "evidence_level",
        "validation_notes",
    ),
}

GENERIC_TEXT_KEYS = {
    "title",
    "description",
    "label",
    "name",
    "text",
    "value",
    "subtitle",
    "caption",
    "statement",
    "notes",
    "note",
    "observacoes",
    "observacao",
    "titulo",
    "descricao",
    "descricao_curta",
    "nome",
}

REPEATABLE_FIELD_FALLBACKS = {
    "arg:argilominerais": "nome",
    "arg:pesquisas_campo": "titulo",
    "arg:amostras": "observacoes_campo",
    "arg:analises": "observacoes",
    "arg:publicacoes_relacionadas": "observacoes",
    "arg:evidencias_mineralogicas": "evidence_text",
}

OBJECT_FIELD_FALLBACKS = {
    "arg:composicao_quimica_global": "observacoes",
}


def _text(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return clean_text(value)


def _flatten_text(value):
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
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, (list, tuple, set)):
        return "\n\n".join(
            chunk for chunk in (_flatten_text(item) for item in value) if chunk
        )
    if isinstance(value, dict):
        for key in (
            "en",
            "pt",
            "pt-BR",
            "value",
            "text",
            "label",
            "description",
            "title",
            "name",
        ):
            nested = value.get(key)
            if nested not in (None, ""):
                flat = _flatten_text(nested)
                if flat:
                    return flat
        return "\n\n".join(
            chunk for chunk in (_flatten_text(item) for item in value.values()) if chunk
        )
    return str(value)


def _sanitize_string_field(container, key):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        container: Valor de entrada consumido por esta etapa do fluxo.
        key: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not isinstance(container, dict) or key not in container:
        return
    value = container.get(key)
    if value is None or isinstance(value, str):
        return
    container[key] = _flatten_text(value)


def _sanitize_mapping_field(container, key):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        container: Valor de entrada consumido por esta etapa do fluxo.
        key: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not isinstance(container, dict) or key not in container:
        return
    value = container.get(key)
    if value is None or isinstance(value, dict):
        return
    if isinstance(value, (list, tuple, set)):
        mapped = {}
        for item in value:
            if isinstance(item, dict):
                mapped.update(item)
                continue
            if isinstance(item, (list, tuple)) and len(item) == 2:
                mapped[str(item[0])] = item[1]
                continue
            text = _flatten_text(item).strip()
            if text:
                mapped[text] = text
        container[key] = mapped
        return
    text = _flatten_text(value).strip()
    container[key] = {"value": text} if text else {}


def _normalize_structured_blocks(custom_fields):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        custom_fields: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not isinstance(custom_fields, dict):
        return

    for field, subfields in STRUCTURED_TEXT_SUBFIELDS.items():
        block = custom_fields.get(field)
        if block is None:
            continue
        if isinstance(block, dict):
            block = [block]
        elif not isinstance(block, list):
            block = [block]

        fallback_key = REPEATABLE_FIELD_FALLBACKS.get(field) or subfields[0]
        normalized_block = []
        for item in block:
            if isinstance(item, dict):
                normalized_block.append(item)
                continue
            text = _flatten_text(item).strip()
            if text:
                normalized_block.append({fallback_key: text})
        custom_fields[field] = normalized_block

    for field, subfields in OBJECT_TEXT_SUBFIELDS.items():
        block = custom_fields.get(field)
        if block is None or isinstance(block, dict):
            continue
        fallback_key = OBJECT_FIELD_FALLBACKS.get(field) or subfields[0]
        text = _flatten_text(block).strip()
        custom_fields[field] = {fallback_key: text} if text else {}


def _sanitize_payload_strings(payload):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        payload: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not isinstance(payload, dict):
        return payload

    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        _sanitize_string_field(metadata, "title")
        _sanitize_string_field(metadata, "description")
        additional_descriptions = metadata.get("additional_descriptions")
        if isinstance(additional_descriptions, list):
            for item in additional_descriptions:
                _sanitize_string_field(item, "description")
        rights = metadata.get("rights")
        if isinstance(rights, list):
            for item in rights:
                _sanitize_mapping_field(item, "props")
        funding = metadata.get("funding")
        if isinstance(funding, list):
            for item in funding:
                if isinstance(item, dict):
                    _sanitize_mapping_field(item.get("funder"), "props")

    custom_fields = payload.get("custom_fields")
    if not isinstance(custom_fields, dict):
        return payload

    _normalize_structured_blocks(custom_fields)

    for field in CUSTOM_TEXT_FIELDS:
        _sanitize_string_field(custom_fields, field)

    for field, subfields in STRUCTURED_TEXT_SUBFIELDS.items():
        block = custom_fields.get(field)
        if not isinstance(block, list):
            continue
        for item in block:
            if not isinstance(item, dict):
                continue
            for subfield in subfields:
                _sanitize_string_field(item, subfield)

    for field, subfields in OBJECT_TEXT_SUBFIELDS.items():
        block = custom_fields.get(field)
        if not isinstance(block, dict):
            continue
        for subfield in subfields:
            _sanitize_string_field(block, subfield)

    def _walk(container):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            container: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        if isinstance(container, dict):
            for key, value in list(container.items()):
                if key in GENERIC_TEXT_KEYS and value is not None and not isinstance(value, str):
                    container[key] = _flatten_text(value)
                    value = container[key]
                _walk(value)
        elif isinstance(container, list):
            for item in container:
                _walk(item)

    _walk(metadata)
    _walk(custom_fields)

    return payload


def _sanitize_record_payload(record):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        record: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if record is None:
        return

    metadata = {}
    custom_fields = {}
    if hasattr(record, "get"):
        metadata = record.get("metadata", {}) or {}
        custom_fields = record.get("custom_fields", {}) or {}
    else:
        metadata = getattr(record, "metadata", {}) or {}
        custom_fields = getattr(record, "custom_fields", {}) or {}

    payload = {"metadata": metadata, "custom_fields": custom_fields}
    _sanitize_payload_strings(payload)

    if hasattr(record, "metadata"):
        record.metadata = payload["metadata"]
    else:
        record["metadata"] = payload["metadata"]

    if hasattr(record, "custom_fields"):
        record.custom_fields = payload["custom_fields"]
    else:
        record["custom_fields"] = payload["custom_fields"]


class ArgilotecaDraftSanitizerComponent(ServiceComponent):
    """Normalize legacy non-string values before edit/read/update flows."""

    def create(self, identity, data=None, record=None, errors=None, **kwargs):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            identity: Valor de entrada consumido por esta etapa do fluxo.
            data: Valor de entrada consumido por esta etapa do fluxo.
            record: Valor de entrada consumido por esta etapa do fluxo.
            errors: Valor de entrada consumido por esta etapa do fluxo.
            **kwargs: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        _sanitize_payload_strings(data)

    def update(self, identity, data=None, record=None, **kwargs):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            identity: Valor de entrada consumido por esta etapa do fluxo.
            data: Valor de entrada consumido por esta etapa do fluxo.
            record: Valor de entrada consumido por esta etapa do fluxo.
            **kwargs: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        _sanitize_payload_strings(data)

    def update_draft(self, identity, data=None, record=None, errors=None, **kwargs):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            identity: Valor de entrada consumido por esta etapa do fluxo.
            data: Valor de entrada consumido por esta etapa do fluxo.
            record: Valor de entrada consumido por esta etapa do fluxo.
            errors: Valor de entrada consumido por esta etapa do fluxo.
            **kwargs: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        _sanitize_payload_strings(data)

    def edit(self, identity, draft=None, record=None, **kwargs):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            identity: Valor de entrada consumido por esta etapa do fluxo.
            draft: Valor de entrada consumido por esta etapa do fluxo.
            record: Valor de entrada consumido por esta etapa do fluxo.
            **kwargs: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        _sanitize_record_payload(draft)

    def read_draft(self, identity, draft=None, **kwargs):
        """
        Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
        
        Args:
            identity: Valor de entrada consumido por esta etapa do fluxo.
            draft: Valor de entrada consumido por esta etapa do fluxo.
            **kwargs: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        _sanitize_record_payload(draft)


class LegacySafeDictField(fields.Dict):
    """Accept legacy non-mapping values during UI serialization."""

    def _coerce_legacy_value(self, value):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            value: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        if value is None or isinstance(value, dict):
            return value
        if isinstance(value, (list, tuple, set)):
            mapped = {}
            for item in value:
                if isinstance(item, dict):
                    mapped.update(item)
                    continue
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    mapped[str(item[0])] = item[1]
                    continue
                text = _flatten_text(item).strip()
                if text:
                    mapped[text] = text
            return mapped
        text = _flatten_text(value).strip()
        return {"value": text} if text else {}

    def _serialize(self, value, attr, obj, **kwargs):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            value: Valor de entrada consumido por esta etapa do fluxo.
            attr: Valor de entrada consumido por esta etapa do fluxo.
            obj: Valor de entrada consumido por esta etapa do fluxo.
            **kwargs: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        return super()._serialize(self._coerce_legacy_value(value), attr, obj, **kwargs)


def _install_global_dict_compat():
    """Monkey patch marshmallow Dict serialization for legacy payloads."""

    if getattr(fields.Dict, "_argiloteca_legacy_safe", False):
        return

    original_serialize = fields.Dict._serialize

    def _legacy_safe_serialize(self, value, attr, obj, **kwargs):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            value: Valor de entrada consumido por esta etapa do fluxo.
            attr: Valor de entrada consumido por esta etapa do fluxo.
            obj: Valor de entrada consumido por esta etapa do fluxo.
            **kwargs: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        if value is not None and not isinstance(value, dict):
            value = LegacySafeDictField()._coerce_legacy_value(value)
        return original_serialize(self, value, attr, obj, **kwargs)

    fields.Dict._serialize = _legacy_safe_serialize
    fields.Dict._argiloteca_legacy_safe = True


_install_global_dict_compat()


def _install_babel_locale_compat():
    """Allow legacy localized dictionaries such as {'value': '...'}."""

    if getattr(marshmallow_babel, "_argiloteca_legacy_locale_safe", False):
        return

    original_gettext_from_dict = marshmallow_babel.gettext_from_dict
    original_format_locale = marshmallow_babel.BabelFormatField.locale.fget

    def _normalize_locale_token(value):
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
            return "en"
        if isinstance(value, str):
            value = value.strip()
            return value.replace("-", "_") if value else "en"
        return value

    def _legacy_safe_format_locale(self):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        return _normalize_locale_token(original_format_locale(self))

    def _legacy_safe_gettext_from_dict(catalog, locale, default_locale):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            catalog: Valor de entrada consumido por esta etapa do fluxo.
            locale: Valor de entrada consumido por esta etapa do fluxo.
            default_locale: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        if not isinstance(catalog, dict):
            return catalog

        for key in (
            "value",
            "text",
            "label",
            "title",
            "name",
            "description",
            "pt-BR",
            "pt",
            "en",
        ):
            value = catalog.get(key)
            if isinstance(value, str) and value.strip():
                if key in {"pt-BR", "pt", "en"}:
                    break
                return value

        normalized_catalog = {}
        for key, value in catalog.items():
            if not isinstance(value, str):
                value = _flatten_text(value)
            if not value:
                continue
            normalized_key = _normalize_locale_token(key)
            try:
                marshmallow_babel.Locale.parse(normalized_key)
            except Exception:
                continue
            normalized_catalog[normalized_key] = value

        if normalized_catalog:
            return original_gettext_from_dict(
                normalized_catalog,
                _normalize_locale_token(locale),
                _normalize_locale_token(default_locale),
            )

        flattened = _flatten_text(catalog).strip()
        return flattened or ""

    def _legacy_safe_babel_serialize(self, value, attr, obj, **kwargs):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            value: Valor de entrada consumido por esta etapa do fluxo.
            attr: Valor de entrada consumido por esta etapa do fluxo.
            obj: Valor de entrada consumido por esta etapa do fluxo.
            **kwargs: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        if isinstance(value, dict):
            value = _legacy_safe_gettext_from_dict(
                value,
                self.locale,
                self.default_locale,
            )
        if value is None:
            return None
        return fields.String._serialize(self, value, attr, obj, **kwargs)

    marshmallow_babel.gettext_from_dict = _legacy_safe_gettext_from_dict
    marshmallow_babel.BabelFormatField.locale = property(_legacy_safe_format_locale)
    marshmallow_babel.BabelGettextDictField._serialize = _legacy_safe_babel_serialize
    marshmallow_babel._argiloteca_legacy_locale_safe = True


_install_babel_locale_compat()


def install_ui_serializer_compat():
    """Patch UI serializer schemas to tolerate legacy dict-like values."""

    from invenio_rdm_records.resources.serializers.ui.schema import RightsSchema
    from invenio_vocabularies.contrib.funders.serializer import FunderL10NItemSchema
    from invenio_vocabularies.resources.serializer import VocabularyL10NItemSchema

    rights_props = LegacySafeDictField()
    funder_props = LegacySafeDictField(dump_only=True)
    vocab_props = LegacySafeDictField(dump_only=True)

    RightsSchema.props = rights_props
    RightsSchema._declared_fields["props"] = rights_props

    FunderL10NItemSchema.props = funder_props
    FunderL10NItemSchema._declared_fields["props"] = funder_props

    VocabularyL10NItemSchema.props = vocab_props
    VocabularyL10NItemSchema._declared_fields["props"] = vocab_props


def _is_iso_date(value):
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
        return True
    if isinstance(value, (date, datetime)):
        return True
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _append_error(errors, field, message):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        errors: Valor de entrada consumido por esta etapa do fluxo.
        field: Valor de entrada consumido por esta etapa do fluxo.
        message: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    errors.append({"field": field, "messages": [message]})


def _has_meaningful_value(value):
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
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _has_structured_content(item):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        item: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not isinstance(item, dict):
        return _has_meaningful_value(item)
    return any(_has_meaningful_value(value) for value in item.values())


def _meaningful_items(items):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        items: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not isinstance(items, list):
        return []
    return [item for item in items if _has_structured_content(item)]


def _is_valid_year(value):
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
        return True
    return bool(re.fullmatch(r"\d{4}", str(value).strip()))


def _looks_like_url(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = _text(value)
    if not text:
        return False
    return text.startswith(("http://", "https://"))


def _looks_like_doi(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = _text(value)
    if not text:
        return False
    return bool(re.fullmatch(r"10\.\S+/\S+", text))


def _extract_file_keys(record):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        record: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if record is None:
        return set()

    keys = set()
    files = getattr(record, "files", None)
    if not files:
        return keys

    try:
        for item in files.values():
            key = getattr(item, "key", None)
            if key:
                keys.add(key)
    except Exception:
        pass

    try:
        for key in files.keys():
            if key:
                keys.add(str(key))
    except Exception:
        pass

    return keys


class ArgilotecaTraceabilityComponent(ServiceComponent):
    """Cross-block validation for the additive traceability model."""

    def create(self, identity, data=None, record=None, errors=None, **kwargs):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            identity: Valor de entrada consumido por esta etapa do fluxo.
            data: Valor de entrada consumido por esta etapa do fluxo.
            record: Valor de entrada consumido por esta etapa do fluxo.
            errors: Valor de entrada consumido por esta etapa do fluxo.
            **kwargs: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        self._validate(data=data, record=record)

    def update_draft(self, identity, data=None, record=None, errors=None, **kwargs):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            identity: Valor de entrada consumido por esta etapa do fluxo.
            data: Valor de entrada consumido por esta etapa do fluxo.
            record: Valor de entrada consumido por esta etapa do fluxo.
            errors: Valor de entrada consumido por esta etapa do fluxo.
            **kwargs: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        self._validate(data=data, record=record)

    def _validate(self, data=None, record=None):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            data: Valor de entrada consumido por esta etapa do fluxo.
            record: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        validation_errors = []
        custom_fields = (data or {}).get("custom_fields") or {}
        if not any(field in custom_fields for field in TRACEABILITY_FIELDS):
            return
        normalize_record_traceability(custom_fields)

        pesquisas = _meaningful_items(custom_fields.get("arg:pesquisas_campo") or [])
        amostras = _meaningful_items(custom_fields.get("arg:amostras") or [])
        analises = _meaningful_items(custom_fields.get("arg:analises") or [])
        publicacoes = _meaningful_items(custom_fields.get("arg:publicacoes_relacionadas") or [])
        argilominerais = _meaningful_items(custom_fields.get("arg:argilominerais") or [])
        composicao_global = custom_fields.get("arg:composicao_quimica_global") or {}
        descricao_componentes = _text(custom_fields.get("arg:descricao_componentes"))
        composicao_descricao_componentes = _text(
            custom_fields.get("arg:composicao_descricao_componentes")
        )
        composicao_proporcoes = _text(custom_fields.get("arg:composicao_proporcoes"))
        usos_argilomineral_nome = _text(custom_fields.get("arg:usos_argilomineral_nome"))
        usos_descricao = _text(custom_fields.get("arg:usos_descricao"))
        usos_aplicacoes_industriais = _text(
            custom_fields.get("arg:usos_aplicacoes_industriais")
        )
        usos_aplicacoes_tecnologicas = _text(
            custom_fields.get("arg:usos_aplicacoes_tecnologicas")
        )
        usos_aplicacoes_cientificas = _text(
            custom_fields.get("arg:usos_aplicacoes_cientificas")
        )

        campanha_ids = set()
        for idx, campanha in enumerate(pesquisas):
            if not isinstance(campanha, dict):
                continue
            campanha_id = _text(campanha.get("campanha_id"))
            field_base = f"custom_fields.arg:pesquisas_campo.{idx}.campanha_id"
            if not campanha_id:
                _append_error(validation_errors, field_base, _("campanha_id is required."))
                continue
            if campanha_id in campanha_ids:
                _append_error(
                    validation_errors,
                    field_base,
                    _("campanha_id must be unique within the record."),
                )
            campanha_ids.add(campanha_id)

            for key in ("data_inicio", "data_fim"):
                if not _is_iso_date(campanha.get(key)):
                    _append_error(
                        validation_errors,
                        f"custom_fields.arg:pesquisas_campo.{idx}.{key}",
                        _("Date must use ISO-8601 format (YYYY-MM-DD)."),
                    )

        codigo_amostras = set()
        for idx, amostra in enumerate(amostras):
            if not isinstance(amostra, dict):
                continue

            codigo = _text(amostra.get("codigo_amostra"))
            campanha_id = _text(amostra.get("campanha_id"))
            codigo_field = f"custom_fields.arg:amostras.{idx}.codigo_amostra"

            if not codigo:
                _append_error(validation_errors, codigo_field, _("codigo_amostra is required."))
            elif codigo in codigo_amostras:
                _append_error(
                    validation_errors,
                    codigo_field,
                    _("codigo_amostra must be unique within the record."),
                )
            elif codigo:
                codigo_amostras.add(codigo)

            if not campanha_id:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:amostras.{idx}.campanha_id",
                    _("campanha_id is required."),
                )
            elif campanha_id not in campanha_ids:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:amostras.{idx}.campanha_id",
                    _("campanha_id must reference an item declared in arg:pesquisas_campo."),
                )

            if not _is_iso_date(amostra.get("data_coleta")):
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:amostras.{idx}.data_coleta",
                    _("Date must use ISO-8601 format (YYYY-MM-DD)."),
                )

        unique_sample_code = next(iter(codigo_amostras), None) if len(codigo_amostras) == 1 else None

        analise_ids = set()
        file_keys = _extract_file_keys(record)
        for idx, analise in enumerate(analises):
            if not isinstance(analise, dict):
                continue

            analise_id = _text(analise.get("analise_id"))
            codigo = _text(analise.get("codigo_amostra"))
            metodo = _text(analise.get("metodo"))

            if not analise_id:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:analises.{idx}.analise_id",
                    _("analise_id is required."),
                )
            elif analise_id in analise_ids:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:analises.{idx}.analise_id",
                    _("analise_id must be unique within the record."),
                )
            else:
                analise_ids.add(analise_id)

            if not codigo:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:analises.{idx}.codigo_amostra",
                    _("codigo_amostra is required."),
                )
            elif codigo not in codigo_amostras:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:analises.{idx}.codigo_amostra",
                    _("codigo_amostra must reference an item declared in arg:amostras."),
                )

            if not metodo:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:analises.{idx}.metodo",
                    _("metodo is required."),
                )

            if not _is_iso_date(analise.get("data_analise")):
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:analises.{idx}.data_analise",
                    _("Date must use ISO-8601 format (YYYY-MM-DD)."),
                )

            arquivo_resultado = _text(analise.get("arquivo_resultado"))
            if arquivo_resultado and file_keys and arquivo_resultado not in file_keys:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:analises.{idx}.arquivo_resultado",
                    _("arquivo_resultado should match an existing file key of the record."),
                )

        composicao_campos = (
            "SiO2",
            "Al2O3",
            "Fe2O3",
            "FeO",
            "MgO",
            "CaO",
            "K2O",
            "Na2O",
            "TiO2",
            "MnO",
            "P2O5",
            "PF",
            "LOI",
        )
        has_composicao_quimica = any(
            _has_meaningful_value(composicao_global.get(campo))
            for campo in composicao_campos
        )
        has_composicao_contexto = any(
            (
                has_composicao_quimica,
                descricao_componentes,
                composicao_descricao_componentes,
                composicao_proporcoes,
                _text(composicao_global.get("codigo_amostra")),
            )
        )

        if has_composicao_contexto and amostras:
            composicao_codigo_amostra = _text(composicao_global.get("codigo_amostra"))
            if not composicao_codigo_amostra:
                _append_error(
                    validation_errors,
                    "custom_fields.arg:composicao_quimica_global.codigo_amostra",
                    _(
                        "codigo_amostra is required for arg:composicao_quimica_global and must identify the analyzed sample."
                    ),
                )
            elif composicao_codigo_amostra not in codigo_amostras:
                _append_error(
                    validation_errors,
                    "custom_fields.arg:composicao_quimica_global.codigo_amostra",
                    _("codigo_amostra must reference an item declared in arg:amostras."),
                )

        nomes_argilominerais = set()
        for idx, mineral in enumerate(argilominerais):
            if not isinstance(mineral, dict):
                continue
            normalized_mineral = enrich_mineral_semantics(mineral)
            if isinstance(normalized_mineral, dict):
                mineral.clear()
                mineral.update(normalized_mineral)
            else:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:argilominerais.{idx}",
                    _(
                        "arg:argilominerais must contain structured objects; a legacy non-object value was found."
                    ),
                )
                continue
            codigo_amostra = _text(mineral.get("codigo_amostra"))
            nome = _text(mineral.get("nome"))
            nome_padronizado = _text(mineral.get("nome_cientifico_padronizado"))
            formula_ideal = _text(mineral.get("formula_ideal"))
            grupo_mineralogico = resolve_mineral_group(mineral)
            external_reference = resolve_external_reference(mineral)
            descricao_curta = resolve_short_description(mineral)
            mineral_has_content = any(
                [
                    codigo_amostra,
                    nome,
                    nome_padronizado,
                    _text(mineral.get("grupo")),
                    grupo_mineralogico,
                    _text(mineral.get("descricao")),
                    _text(mineral.get("descricao_curta")),
                    _text(mineral.get("estrutura_cristalina")),
                    _text(mineral.get("classe_estrutural")),
                    _text(mineral.get("sistema_cristalino")),
                    formula_ideal,
                    _text(mineral.get("propriedades_especiais")),
                    _text(mineral.get("propriedades_relevantes")),
                    _text(mineral.get("origem_formacao")),
                    _text(mineral.get("ambiente_tipico_formacao")),
                    _text(mineral.get("era_geologica")),
                    _text(mineral.get("formacao_geologica")),
                    _text(mineral.get("usos_aplicacoes")),
                    _text(mineral.get("external_source")),
                    _text(mineral.get("external_id")),
                    _text(mineral.get("external_uri")),
                    _has_meaningful_value(mineral.get("latitude")),
                    _has_meaningful_value(mineral.get("longitude")),
                    _has_meaningful_value(mineral.get("altitude")),
                ]
            )
            if mineral_has_content and not codigo_amostra and unique_sample_code:
                mineral["codigo_amostra"] = unique_sample_code
                codigo_amostra = unique_sample_code
            if mineral_has_content and amostras and not codigo_amostra:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:argilominerais.{idx}.codigo_amostra",
                    _(
                        "codigo_amostra is required for arg:argilominerais and must identify the interpreted sample."
                    ),
                )
            elif codigo_amostra and codigo_amostras and codigo_amostra not in codigo_amostras:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:argilominerais.{idx}.codigo_amostra",
                    _("codigo_amostra must reference an item declared in arg:amostras."),
                )
            canonical_name = nome_padronizado or nome
            if canonical_name:
                nomes_argilominerais.add(canonical_name)

            if nome_padronizado and not nome:
                mineral["nome"] = nome_padronizado

            if external_reference["source"] == MINDAT_SOURCE:
                external_id = external_reference["id"]
                external_uri = external_reference["uri"]
                if not external_id:
                    _append_error(
                        validation_errors,
                        f"custom_fields.arg:argilominerais.{idx}.external_id",
                        _("external_id is required when external_source is Mindat."),
                    )
                elif not str(external_id).isdigit():
                    _append_error(
                        validation_errors,
                        f"custom_fields.arg:argilominerais.{idx}.external_id",
                        _("Mindat external_id must be numeric."),
                    )

                if not external_uri:
                    mineral["external_uri"] = build_mindat_uri(external_id)
                else:
                    parsed_id = parse_mindat_id(external_uri)
                    if not parsed_id:
                        _append_error(
                            validation_errors,
                            f"custom_fields.arg:argilominerais.{idx}.external_uri",
                            _(
                                "Mindat external_uri must use the pattern "
                                "https://www.mindat.org/min-<id>.html."
                            ),
                        )
                    elif external_id and parsed_id != str(external_id):
                        _append_error(
                            validation_errors,
                            f"custom_fields.arg:argilominerais.{idx}.external_uri",
                            _("Mindat external_uri must match external_id."),
                        )

            if formula_ideal and grupo_mineralogico and not descricao_curta:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:argilominerais.{idx}.descricao_curta",
                    _(
                        "descricao_curta must be available when formula_ideal and "
                        "grupo_mineralogico are informed."
                    ),
                )

        unique_mineral_name = (
            next(iter(nomes_argilominerais), None) if len(nomes_argilominerais) == 1 else None
        )

        for idx, publicacao in enumerate(publicacoes):
            if not isinstance(publicacao, dict):
                continue

            codigo = _text(publicacao.get("codigo_amostra"))
            titulo = _text(publicacao.get("titulo"))
            tipo = _text(publicacao.get("tipo"))
            relacao = _text(publicacao.get("relacao_com_registro"))
            codigo_analise = _text(publicacao.get("codigo_analise"))
            argilomineral_nome = _text(publicacao.get("argilomineral_nome"))
            ano = _text(publicacao.get("ano"))
            doi = _text(publicacao.get("doi"))
            url = _text(publicacao.get("url"))
            if amostras and not codigo:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:publicacoes_relacionadas.{idx}.codigo_amostra",
                    _("codigo_amostra is required."),
                )
            elif codigo and codigo_amostras and codigo not in codigo_amostras:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:publicacoes_relacionadas.{idx}.codigo_amostra",
                    _("codigo_amostra must reference an item declared in arg:amostras."),
                )

            if not titulo:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:publicacoes_relacionadas.{idx}.titulo",
                    _("titulo is required."),
                )

            if not tipo:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:publicacoes_relacionadas.{idx}.tipo",
                    _("tipo is required."),
                )

            if not relacao:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:publicacoes_relacionadas.{idx}.relacao_com_registro",
                    _("relacao_com_registro is required."),
                )

            if not _is_valid_year(ano):
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:publicacoes_relacionadas.{idx}.ano",
                    _("ano must use the YYYY format."),
                )

            record_id = _text(publicacao.get("record_id"))
            externo = _text(publicacao.get("identificador_externo"))
            if not record_id and not externo and not doi and not url:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:publicacoes_relacionadas.{idx}",
                    _("Provide record_id, identificador_externo, doi or url."),
                )

            if doi and not _looks_like_doi(doi):
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:publicacoes_relacionadas.{idx}.doi",
                    _("doi must use a valid DOI syntax."),
                )

            if url and not _looks_like_url(url):
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:publicacoes_relacionadas.{idx}.url",
                    _("url must start with http:// or https://."),
                )

            if codigo_analise and analise_ids and codigo_analise not in analise_ids:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:publicacoes_relacionadas.{idx}.codigo_analise",
                    _("codigo_analise must reference an item declared in arg:analises."),
                )

            if argilomineral_nome and nomes_argilominerais and argilomineral_nome not in nomes_argilominerais:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:publicacoes_relacionadas.{idx}.argilomineral_nome",
                    _("argilomineral_nome must reference an item declared in arg:argilominerais."),
                )

            if relacao == "discute_analise" and analises and not codigo_analise:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:publicacoes_relacionadas.{idx}.codigo_analise",
                    _("codigo_analise is required when relacao_com_registro is discute_analise."),
                )

            if relacao == "fundamenta_argilomineral" and argilominerais and not argilomineral_nome:
                _append_error(
                    validation_errors,
                    f"custom_fields.arg:publicacoes_relacionadas.{idx}.argilomineral_nome",
                    _(
                        "argilomineral_nome is required when relacao_com_registro is fundamenta_argilomineral."
                    ),
                )

        usos_has_content = any(
            [
                usos_descricao,
                usos_aplicacoes_industriais,
                usos_aplicacoes_tecnologicas,
                usos_aplicacoes_cientificas,
            ]
        )
        if usos_has_content and not usos_argilomineral_nome and unique_mineral_name:
            custom_fields["arg:usos_argilomineral_nome"] = unique_mineral_name
            usos_argilomineral_nome = unique_mineral_name
        if validation_errors:
            messages = {}
            for item in validation_errors:
                field = item["field"]
                messages.setdefault(field, [])
                messages[field].extend(item["messages"])
            raise ValidationError(messages)
