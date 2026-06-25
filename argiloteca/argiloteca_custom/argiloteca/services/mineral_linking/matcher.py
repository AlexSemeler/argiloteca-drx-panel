"""
Projeto: Painel DRX Argiloteca

Descrição:
Resolve controlled-vocabulary minerals against internal or external names.

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

from dataclasses import dataclass
import re
import unicodedata

from .vocabulary import VocabularyBundle, VocabularyTerm, load_vocabulary_bundle


def normalize_term(value: str | None) -> str | None:
    """Normalize a mineral label for tolerant matching."""

    if not value:
        return None
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()
    return cleaned or None


@dataclass
class MatchResult:
    """Structured result of a controlled-vocabulary mineral lookup."""

    query: str
    normalized_query: str | None
    mineral: VocabularyTerm | None
    group: VocabularyTerm | None
    matched_alias: str | None
    match_source: str

    def to_dict(self) -> dict[str, object]:
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        return {
            "query": self.query,
            "normalized_query": self.normalized_query,
            "matched_alias": self.matched_alias,
            "match_source": self.match_source,
            "mineral_id": self.mineral.id if self.mineral else None,
            "mineral_label": self.mineral.preferred_label if self.mineral else None,
            "group_id": self.group.id if self.group else None,
            "group_label": self.group.preferred_label if self.group else None,
        }


class MineralMatcher:
    """Vocabulary-backed matcher for Argiloteca minerals."""

    def __init__(self, bundle: VocabularyBundle | None = None):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            bundle: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        self.bundle = bundle or load_vocabulary_bundle()
        self._alias_to_id: dict[str, tuple[str, str]] = {}
        self._build_index()

    def _build_index(self) -> None:
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            Nenhum argumento explícito.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        for term_id, term in self.bundle.minerals.items():
            for alias in term.aliases:
                normalized = normalize_term(alias)
                if normalized and normalized not in self._alias_to_id:
                    self._alias_to_id[normalized] = (term_id, alias)

    def match_term(self, query: str | None) -> MatchResult:
        """
        Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica.
        
        Args:
            query: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        normalized = normalize_term(query)
        if not normalized:
            return MatchResult(
                query=query or "",
                normalized_query=None,
                mineral=None,
                group=None,
                matched_alias=None,
                match_source="empty",
            )

        term_and_alias = self._alias_to_id.get(normalized)
        if not term_and_alias:
            return MatchResult(
                query=query or "",
                normalized_query=normalized,
                mineral=None,
                group=None,
                matched_alias=None,
                match_source="unmatched",
            )

        term_id, alias = term_and_alias
        mineral = self.bundle.minerals.get(term_id)
        group = self.bundle.resolve_group(term_id)
        return MatchResult(
            query=query or "",
            normalized_query=normalized,
            mineral=mineral,
            group=group,
            matched_alias=alias,
            match_source="alias" if alias != term_id else "id",
        )
