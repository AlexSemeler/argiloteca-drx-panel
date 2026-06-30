# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: diagnostic_engine.py
#
# Descrição.........:
# Implementa regras explicáveis para argilominerais interestratificados e padrões 00l multi-tratamento.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Última atualização:
# 2026-06-25
#
# =============================================================================

"""
Implementa regras explicáveis para argilominerais interestratificados e padrões 00l multi-tratamento.

Responsabilidades:
    - preservar contratos públicos e estruturas JSON consumidas pelo painel;
    - registrar proveniência científica e técnica das operações realizadas;
    - manter separadas etapas de leitura, processamento, diagnóstico e exportação;
    - documentar limites de interpretação mineralógica quando houver regras DRX.

Notas científicas:
    Em módulos DRX, 2θ representa o eixo angular medido no difratograma e
    d-spacing representa o espaçamento interplanar calculado pela Lei de Bragg
    (nλ = 2d sen θ). Preparações natural, glicolada e calcinada são usadas para
    observar expansão, colapso, persistência ou destruição de picos basais.
"""

from __future__ import annotations

"""Motor principal de diagnostico para argilominerais interestratificados.

Fundamentacao cientifica:
    Implementa uma leitura conservadora do Capitulo 8: padrao 00l completo,
    comportamento multi-preparacao, superestrutura, ordenamento e diagnostico
    diferencial entre mistura fisica e interestratificacao.

Uso no painel:
    `diagnose_mixed_layer_pattern` e o ponto de entrada para chamadas do painel
    DRX, jobs em lote ou revisoes curatoriais. O retorno ja vem no formato XAI
    usado pela Argiloteca.
"""

from .explanation_engine import explain
from .mixed_layer_pattern_interpreter import interpret_pattern
from .peak_interpreter import normalize_peaks_by_preparation
from .candidate_ranker import rank_candidates
from .provenance_tracker import load_json


def diagnose_mixed_layer_pattern(peaks_by_preparation: dict, metadata: dict | None = None) -> dict:
    """Diagnostica candidatos de argilominerais interestratificados.

    Args:
        peaks_by_preparation: Picos agrupados por preparacao. Aceita aliases
            operacionais do painel, como `N`, `G`, `C`, `natural`,
            `glycolated` e `calcined`.
        metadata: Contexto opcional da amostra, como observacoes curatoriais,
            quimica auxiliar, qualidade do difratograma ou origem do RAW.

    Returns:
        Payload com versao do motor, politica de interpretacao, picos
        normalizados, interpretacao intermediaria e lista de candidatos XAI.

    Notes:
        A funcao nao confirma mineral por pico isolado. Quando a evidencia
        minima nao existe, retorna `mixed_layer_evidence_insufficient`.
    """
    peaks = normalize_peaks_by_preparation(peaks_by_preparation or {})
    interpreted = interpret_pattern(peaks)
    fs = set(interpreted["features"].get("features", []))
    rules = {r["rule_id"]: r for r in load_json("chapter8_rules_catalog.json")}
    candidates = []

    def add(name, score, rule_ids, missing=None, diff=None):
        """Adiciona candidato mantendo regra, fonte e lacunas explicaveis."""
        candidates.append({
            "candidate": name,
            "confidence": score,
            "evidence_for": [{"evidence": rules[r].get("diagnostic_implication"), "rule_id": r, "source": rules[r].get("source")} for r in rule_ids if r in rules],
            "evidence_against": [],
            "ambiguous_evidence": [],
            "missing_evidence": missing or [],
            "differential_diagnosis": diff or [],
            "composition_estimate": {},
            "ordering_estimate": interpreted["ordering"].get("ordering"),
            "required_follow_up": [] if score >= 0.7 else ["obtain/verify full 00l pattern across treatments"],
        })

    # I/S e outros interestratificados esmectiticos precisam de expansao com
    # EG e colapso/aumento de similaridade mica-like apos aquecimento.
    if "expands_with_eg_to_17A" in fs and "collapses_or_returns_to_10A_after_heating" in fs:
        add("illite/smectite_or_smectitic_mixed_layer", 0.68, ["behavior_IS_EG_then_heated_confirmation"], diff=[{"alternative": "discrete illite + smectite", "reason_rejected_or_retained": "requires fixed-peak check and full 00l pattern", "rule_id": "mixture_fixed_discrete_peaks"}])
    # A coexistencia de componente cloritico persistente e componente
    # expansivel favorece C/S, mas ainda exige diferencial com C/V.
    if "persistent_14A_component" in fs and "expands_with_eg_to_17A" in fs:
        add("chlorite/smectite", 0.7, ["behavior_CS_EG_expansion_favors_smectite_component"], diff=[{"alternative": "chlorite/vermiculite", "reason_rejected_or_retained": "EG expansion favors smectite component; verify Mg-glycerol if ambiguous", "rule_id": "behavior_CS_no_EG_ambiguous_CV"}])
    # Reflexoes longas/superestrutura elevam a hipotese de corrensita ou de
    # outro interestratificado ordenado, especialmente se houver desidratacao.
    if interpreted["superstructures"] and "long_period_superstructure_candidate" in fs:
        add("corrensite_or_ordered_mixed_layer", 0.78, ["superstructure_corrensite_00l_star", "behavior_corrensite_dehydrated_resolves_mixture"])
    # Mg-glicerol e usado como evidencia auxiliar para componente vermiculitico
    # quando o padrao permanece essencialmente semelhante ao air-dried.
    if "mg_glycerol_unchanged_14A" in fs:
        add("mica/vermiculite_or_chlorite/vermiculite", 0.62, ["behavior_MV_Mg_glycerol_proves_vermiculite"])
    if not candidates:
        add("mixed_layer_evidence_insufficient", 0.25, ["interstratification_migrating_composite_peaks"], missing=["EG, heated/dehydrated, and full 00l evidence are required"])

    ranked = rank_candidates(candidates)
    return {
        "engine_version": "argiloteca.chapter8_mixed_layer.v1",
        "policy": "no isolated peak is sufficient; use complete 00l and multi-treatment evidence",
        "normalized_peaks": peaks,
        "pattern_interpretation": interpreted,
        "candidates": [explain(c) for c in ranked],
        "metadata": metadata or {},
    }
