"""
Projeto: Painel DRX Argiloteca

Descrição:
Load Argiloteca's controlled vocabularies for mineral semantic linking.

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

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


def _default_vocab_root() -> Path:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return Path(__file__).resolve().parents[4] / "app_data" / "data" / "vocabularies"


def _text(value: Any) -> str | None:
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
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return str(value).strip() or None


def _slug_to_label(value: str) -> str:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return value.replace("_", " ").replace("-", " ").strip()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        items.append(json.loads(line))
    return items


@dataclass
class VocabularyTerm:
    """Controlled term from the Argiloteca vocabulary."""

    vocabulary: str
    id: str
    title_pt: str | None = None
    title_en: str | None = None
    category: str | None = None
    family: str | None = None
    broader: str | None = None
    status: str | None = None
    source: str | None = None
    aliases: tuple[str, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def preferred_label(self) -> str:
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        return self.title_pt or self.title_en or _slug_to_label(self.id)


@dataclass
class VocabularyBundle:
    """Aggregate view of mineral and mineral-group vocabularies."""

    minerals: dict[str, VocabularyTerm]
    groups: dict[str, VocabularyTerm]
    mineral_to_group: dict[str, str]

    def resolve_group(self, mineral_id: str) -> VocabularyTerm | None:
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            mineral_id: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        group_id = self.mineral_to_group.get(mineral_id)
        if group_id:
            return self.groups.get(group_id)

        mineral = self.minerals.get(mineral_id)
        if mineral and mineral.family:
            return self.groups.get(mineral.family)
        return None


def _build_aliases(term_id: str, title: dict[str, Any], props: dict[str, Any]) -> tuple[str, ...]:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        term_id: Valor de entrada consumido por esta etapa do fluxo.
        title: Valor de entrada consumido por esta etapa do fluxo.
        props: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    aliases: list[str] = []

    for value in (
        term_id,
        _slug_to_label(term_id),
        title.get("pt"),
        title.get("en"),
        props.get("broader"),
        props.get("family"),
    ):
        text = _text(value)
        if text and text not in aliases:
            aliases.append(text)

    return tuple(aliases)


def _load_terms(path: Path, vocabulary: str) -> dict[str, VocabularyTerm]:
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
        vocabulary: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    terms: dict[str, VocabularyTerm] = {}
    for item in _load_jsonl(path):
        term_id = item["id"]
        title = item.get("title") or {}
        props = item.get("props") or {}
        terms[term_id] = VocabularyTerm(
            vocabulary=vocabulary,
            id=term_id,
            title_pt=_text(title.get("pt")),
            title_en=_text(title.get("en")),
            category=_text(props.get("category")),
            family=_text(props.get("family")),
            broader=_text(props.get("broader")),
            status=_text(props.get("status")),
            source=_text(props.get("source")),
            aliases=_build_aliases(term_id, title, props),
            raw=item,
        )
    return terms


def load_vocabulary_bundle(root: Path | None = None) -> VocabularyBundle:
    """Load Argiloteca mineral vocabularies and mineral/group relationships."""

    vocab_root = root or _default_vocab_root()
    minerals = _load_terms(vocab_root / "argilominerais.jsonl", "argilominerais")
    groups = _load_terms(vocab_root / "grupo_mineralogico.jsonl", "grupo_mineralogico")
    mineral_to_group = json.loads(
        (vocab_root / "mapeamento_argilomineral_grupo.json").read_text(encoding="utf-8")
    )
    return VocabularyBundle(
        minerals=minerals,
        groups=groups,
        mineral_to_group=mineral_to_group,
    )
