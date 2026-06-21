"""
Projeto: Painel DRX Argiloteca

Descrição:
Parse factual mineral attributes from Mindat HTML pages.

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

from dataclasses import dataclass
import re
from typing import Any

from ...mineralogia import clean_text, parse_mindat_id


def _extract_label_value(html: str, labels: tuple[str, ...]) -> str | None:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        html: Valor de entrada consumido por esta etapa do fluxo.
        labels: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    for label in labels:
        patterns = (
            rf"{label}\s*</[^>]+>\s*<[^>]+>([^<]+)",
            rf"{label}\s*[:\-]\s*([^<\n\r]+)",
            rf"{label}\s*</span>\s*([^<\n\r]+)",
        )
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE)
            if match:
                return clean_text(match.group(1))
    return None


def _extract_synonyms(html: str) -> list[str]:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        html: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    match = re.search(r"Synonyms?\s*[:\-]\s*([^<\n\r]+)", html, flags=re.IGNORECASE)
    if not match:
        return []
    raw = clean_text(match.group(1)) or ""
    items = [item.strip() for item in re.split(r"[;,]", raw) if item.strip()]
    deduped: list[str] = []
    for item in items:
        if item not in deduped:
            deduped.append(item)
    return deduped


@dataclass
class MindatParsedRecord:
    """Structured, factual subset parsed from Mindat."""

    external_id: str | None
    external_uri: str
    name: str | None = None
    formula_ideal: str | None = None
    sistema_cristalino: str | None = None
    grupo_mineralogico: str | None = None
    classificacao_strunz: str | None = None
    classificacao_dana: str | None = None
    sinonimos: list[str] | None = None
    fonte_descricao: str = "Mindat"
    parser_status: str = "parsed"

    def to_dict(self) -> dict[str, Any]:
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
            "external_source": "Mindat",
            "external_id": self.external_id,
            "external_uri": self.external_uri,
            "nome_cientifico_padronizado": self.name,
            "formula_ideal": self.formula_ideal,
            "sistema_cristalino": self.sistema_cristalino,
            "grupo_mineralogico": self.grupo_mineralogico,
            "classificacao_strunz": self.classificacao_strunz,
            "classificacao_dana": self.classificacao_dana,
            "sinonimos": ", ".join(self.sinonimos or []),
            "fonte_descricao": self.fonte_descricao,
            "parser_status": self.parser_status,
        }


def parse_mindat_html(html: str, url: str) -> MindatParsedRecord:
    """Extract structured mineral attributes from a Mindat page body."""

    title_match = re.search(r"<title>\s*([^<]+?)\s*(?:-|\|)\s*Mindat", html, flags=re.IGNORECASE)
    name = clean_text(title_match.group(1)) if title_match else None

    record = MindatParsedRecord(
        external_id=parse_mindat_id(url),
        external_uri=url,
        name=name,
        formula_ideal=_extract_label_value(html, ("Ideal Chemistry", "Formula", "Ideal formula")),
        sistema_cristalino=_extract_label_value(html, ("Crystal System", "Crystal system")),
        grupo_mineralogico=_extract_label_value(html, ("Group", "Mineral Group", "Mineral group")),
        classificacao_strunz=_extract_label_value(html, ("Strunz", "Strunz classification")),
        classificacao_dana=_extract_label_value(html, ("Dana", "Dana classification")),
        sinonimos=_extract_synonyms(html),
    )
    return record
