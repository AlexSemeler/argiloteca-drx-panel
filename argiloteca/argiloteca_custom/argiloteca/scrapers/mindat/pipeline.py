"""
Projeto: Painel DRX Argiloteca

Descrição:
Curated pipeline that links Argiloteca vocabulary terms to Mindat data.

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

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable

from ...mineralogia import MINDAT_SOURCE, build_mindat_uri, resolve_short_description

from ...services.mineral_linking import MineralMatcher, load_vocabulary_bundle
from .client import MindatClient
from .parser import parse_mindat_html


def _utc_now() -> str:
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PipelineArtifacts:
    """Concrete output paths written by a scraper run."""

    minerals_path: Path
    matching_path: Path
    pending_path: Path
    report_path: Path
    log_path: Path


def _read_json(path: Path) -> Any:
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    """
    Gera artefatos derivados, relatórios ou saídas serializadas com parâmetros e proveniência para auditoria posterior.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
        payload: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_curated_seeds(path: Path | None) -> dict[str, Any]:
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not path or not path.exists():
        return {}
    return _read_json(path)


def _iter_selected_terms(bundle, only_terms: Iterable[str] | None = None, limit: int | None = None):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        bundle: Valor de entrada consumido por esta etapa do fluxo.
        only_terms: Valor de entrada consumido por esta etapa do fluxo.
        limit: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    requested = {item.strip().lower() for item in (only_terms or []) if item and item.strip()}
    count = 0
    for term in bundle.minerals.values():
        if term.category not in (None, "species", "mineral", "phyllosilicate"):
            continue
        if requested and term.id.lower() not in requested and (term.title_pt or "").lower() not in requested and (term.title_en or "").lower() not in requested:
            continue
        yield term
        count += 1
        if limit and count >= limit:
            break


def run_mindat_pipeline(
    output_dir: Path,
    cache_dir: Path,
    log_dir: Path,
    curated_seeds_path: Path | None = None,
    only_terms: list[str] | None = None,
    limit: int | None = None,
    allow_network: bool = False,
    fixture_dir: Path | None = None,
) -> PipelineArtifacts:
    """Run the controlled vocabulary-driven Mindat collection pipeline."""

    bundle = load_vocabulary_bundle()
    matcher = MineralMatcher(bundle)
    client = MindatClient(cache_dir=cache_dir, allow_network=allow_network)
    seeds = _load_curated_seeds(curated_seeds_path)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    minerals_path = output_dir / f"mindat_minerais_{timestamp}.json"
    matching_path = output_dir / f"mindat_matching_{timestamp}.json"
    pending_path = output_dir / f"mindat_pendencias_{timestamp}.json"
    report_path = output_dir / f"mindat_relatorio_{timestamp}.json"
    log_path = log_dir / f"mindat_execucao_{timestamp}.log"

    minerals: list[dict[str, Any]] = []
    matching: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    logs: list[str] = []

    for term in _iter_selected_terms(bundle, only_terms=only_terms, limit=limit):
        logs.append(f"[{term.id}] iniciando resolucao semantica")
        seed = seeds.get(term.id) or {}
        match = matcher.match_term(term.preferred_label)
        group = bundle.resolve_group(term.id)
        candidate_uri = seed.get("external_uri") or (
            build_mindat_uri(seed.get("external_id")) if seed.get("external_id") else None
        )

        row: dict[str, Any] = {
            "vocabulary_id": term.id,
            "preferred_pt": term.title_pt,
            "preferred_en": term.title_en,
            "aliases": list(term.aliases),
            "group_id": group.id if group else None,
            "group_label": group.preferred_label if group else None,
            "matching": match.to_dict(),
            "source_status": "seeded" if seed else "unresolved",
            "external_source": MINDAT_SOURCE,
            "external_id": seed.get("external_id"),
            "external_uri": candidate_uri,
            "collected_at": _utc_now(),
        }

        if seed:
            structured = {
                "nome": term.title_pt or term.title_en,
                "nome_cientifico_padronizado": seed.get("nome_cientifico_padronizado") or term.title_en,
                "formula_ideal": seed.get("formula_ideal"),
                "classe_estrutural": seed.get("classe_estrutural"),
                "sistema_cristalino": seed.get("sistema_cristalino"),
                "grupo_mineralogico": seed.get("grupo_mineralogico") or (group.preferred_label if group else None),
                "ambiente_tipico_formacao": seed.get("ambiente_tipico_formacao"),
                "external_source": MINDAT_SOURCE,
                "external_id": seed.get("external_id"),
                "external_uri": candidate_uri,
                "fonte_descricao": seed.get("fonte_descricao") or MINDAT_SOURCE,
                "licenca_fonte": seed.get("licenca_fonte"),
                "observacao_proveniencia": seed.get("observacao_proveniencia"),
            }
            row["structured_metadata"] = structured
            row["descricao_curta"] = resolve_short_description(structured)
            row["confidence"] = "confirmed_seed"
            minerals.append(row)
            matching.append(
                {
                    "vocabulary_id": term.id,
                    "mindat_external_id": seed.get("external_id"),
                    "mindat_uri": candidate_uri,
                    "status": "confirmed_seed",
                    "group_id": group.id if group else None,
                }
            )
            logs.append(f"[{term.id}] resolvido por seed curada")
            continue

        if fixture_dir:
            fixture_path = fixture_dir / f"{term.id}.html"
            if fixture_path.exists():
                parsed = parse_mindat_html(fixture_path.read_text(encoding="utf-8"), candidate_uri or "")
                row["structured_metadata"] = parsed.to_dict()
                row["descricao_curta"] = resolve_short_description(parsed.to_dict())
                row["source_status"] = "fixture_parsed"
                row["confidence"] = "fixture"
                minerals.append(row)
                matching.append(
                    {
                        "vocabulary_id": term.id,
                        "mindat_external_id": parsed.external_id,
                        "mindat_uri": parsed.external_uri,
                        "status": "fixture_parsed",
                        "group_id": group.id if group else None,
                    }
                )
                logs.append(f"[{term.id}] resolvido por fixture local")
                continue

        if candidate_uri:
            fetched = client.fetch(candidate_uri)
            logs.append(f"[{term.id}] fetch={fetched.error or fetched.status} cache={fetched.from_cache}")
            if fetched.ok and fetched.body:
                parsed = parse_mindat_html(fetched.body, candidate_uri)
                row["structured_metadata"] = parsed.to_dict()
                row["descricao_curta"] = resolve_short_description(parsed.to_dict())
                row["source_status"] = "live_parsed"
                row["confidence"] = "parsed"
                minerals.append(row)
                matching.append(
                    {
                        "vocabulary_id": term.id,
                        "mindat_external_id": parsed.external_id,
                        "mindat_uri": parsed.external_uri,
                        "status": "live_parsed",
                        "group_id": group.id if group else None,
                    }
                )
                continue

        pending.append(
            {
                "vocabulary_id": term.id,
                "preferred_label": term.preferred_label,
                "group_id": group.id if group else None,
                "candidate_uri": candidate_uri,
                "status": "pending_curation",
                "reason": "no_seed_or_live_match",
                "matching": match.to_dict(),
            }
        )
        matching.append(
            {
                "vocabulary_id": term.id,
                "mindat_external_id": None,
                "mindat_uri": candidate_uri,
                "status": "pending_curation",
                "group_id": group.id if group else None,
            }
        )
        logs.append(f"[{term.id}] pendente para curadoria")

    report = {
        "generated_at": _utc_now(),
        "allow_network": allow_network,
        "terms_total": len(minerals) + len(pending),
        "terms_confirmed": len([item for item in matching if item["status"] in {"confirmed_seed", "live_parsed", "fixture_parsed"}]),
        "terms_pending": len(pending),
        "groups_identified": sorted({item["group_id"] for item in matching if item.get("group_id")}),
        "fields_collected": sorted(
            {
                field
                for item in minerals
                for field, value in (item.get("structured_metadata") or {}).items()
                if value not in (None, "", [])
            }
        ),
    }

    _write_json(minerals_path, minerals)
    _write_json(matching_path, matching)
    _write_json(pending_path, pending)
    _write_json(report_path, report)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(logs) + "\n", encoding="utf-8")

    return PipelineArtifacts(
        minerals_path=minerals_path,
        matching_path=matching_path,
        pending_path=pending_path,
        report_path=report_path,
        log_path=log_path,
    )
