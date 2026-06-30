# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: explanation_engine.py
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

"""Montagem da explicacao XAI para candidatos do Capitulo 8."""

from .confidence_estimator import status_from_confidence


def explain(candidate: dict) -> dict:
    """Normaliza um candidato para o formato explicavel da Argiloteca.

    Args:
        candidate: Candidato interno com evidencias, fontes e estimativas.

    Returns:
        Objeto JSON pronto para exibicao no painel, com evidencias a favor,
        contra, ambiguas, lacunas e diagnosticos diferenciais.
    """
    score = float(candidate.get("confidence", 0.0))
    return {
        "candidate": candidate.get("candidate"),
        "confidence": score,
        "diagnostic_status": status_from_confidence(score),
        "evidence_for": candidate.get("evidence_for", []),
        "evidence_against": candidate.get("evidence_against", []),
        "ambiguous_evidence": candidate.get("ambiguous_evidence", []),
        "missing_evidence": candidate.get("missing_evidence", []),
        "differential_diagnosis": candidate.get("differential_diagnosis", []),
        "composition_estimate": candidate.get("composition_estimate", {}),
        "ordering_estimate": candidate.get("ordering_estimate", ""),
        "required_follow_up": candidate.get("required_follow_up", []),
    }
