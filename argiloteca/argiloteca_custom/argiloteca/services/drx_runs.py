"""
Projeto: Painel DRX Argiloteca

Descrição:
Filesystem-backed DRX AnalysisRun artifact registry.

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

import hashlib
import json
import os
import uuid
from pathlib import Path

from argiloteca.drx_core.contracts import DRX_CORE_VERSION, DRX_RUN_ARTIFACT_SCHEMA, auxiliary_policy

from .drx import utc_now_iso


DEFAULT_RUNS_DIR = (
    Path(os.environ.get("INVENIO_INSTANCE_PATH") or Path(__file__).resolve().parents[4] / "instance")
    / "argiloteca_drx_runs"
)


def _runs_dir():
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    path = Path(os.environ.get("ARGILOTECA_DRX_RUNS_DIR") or DEFAULT_RUNS_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_run_id(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return "".join(ch for ch in str(value or "") if ch.isalnum() or ch in {"-", "_"})


def _run_path(run_id):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        run_id: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    safe_id = _safe_run_id(run_id)
    if not safe_id:
        raise ValueError("run_id invalido.")
    return _runs_dir() / f"{safe_id}.json"


def _hash_payload(payload):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        payload: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = json.dumps(payload or {}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def persist_drx_run(
    *,
    analysis_run=None,
    technical_report=None,
    selection_report=None,
    inputs=None,
    outputs=None,
    parameters=None,
    record_id=None,
    sample_code=None,
    run_id=None,
):
    """Persist a versioned DRX run artifact under instance/argiloteca_drx_runs."""
    now = utc_now_iso()
    run_id = _safe_run_id(run_id) or ("drx-run-" + uuid.uuid4().hex[:16])
    payload = {
        "success": True,
        "schema_version": DRX_RUN_ARTIFACT_SCHEMA,
        "run_id": run_id,
        "created_at": now,
        "updated_at": now,
        "record_id": record_id or (analysis_run or {}).get("input", {}).get("record_id"),
        "sample_code": sample_code or (analysis_run or {}).get("input", {}).get("sample_code"),
        "engine": {
            "name": "argiloteca_drx_core",
            "version": DRX_CORE_VERSION,
        },
        "inputs": inputs or {},
        "parameters": parameters or {},
        "analysis_run": analysis_run or {},
        "technical_report": technical_report or {},
        "selection_report": selection_report or {},
        "outputs": outputs or {},
        "reproducibility": {
            "artifact_hash": None,
            "input_hash": _hash_payload(inputs or {}),
            "parameters_hash": _hash_payload(parameters or {}),
            "analysis_hash": _hash_payload(analysis_run or {}),
            "report_hash": _hash_payload(technical_report or selection_report or {}),
        },
        "interpretation_policy": auxiliary_policy("drx"),
    }
    payload["reproducibility"]["artifact_hash"] = _hash_payload(
        {key: value for key, value in payload.items() if key != "reproducibility"}
    )
    path = _run_path(run_id)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    payload["artifact_path"] = str(path)
    return payload


def get_drx_run(run_id):
    """Load one persisted DRX run artifact."""
    try:
        payload = json.loads(_run_path(run_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"success": False, "error": "Run DRX nao encontrado."}
    except (json.JSONDecodeError, ValueError):
        return {"success": False, "error": "Run DRX corrompido ou invalido."}
    payload["artifact_path"] = str(_run_path(run_id))
    return payload


def list_drx_runs(*, record_id=None, sample_code=None, limit=50):
    """List run artifacts without opening unrelated directories."""
    rows = []
    for path in sorted(_runs_dir().glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        if len(rows) >= int(limit or 50):
            break
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if record_id and str(payload.get("record_id") or "") != str(record_id):
            continue
        if sample_code and str(payload.get("sample_code") or "") != str(sample_code):
            continue
        rows.append(
            {
                "run_id": payload.get("run_id"),
                "schema_version": payload.get("schema_version"),
                "created_at": payload.get("created_at"),
                "updated_at": payload.get("updated_at"),
                "record_id": payload.get("record_id"),
                "sample_code": payload.get("sample_code"),
                "engine": payload.get("engine") or {},
                "summary": (payload.get("technical_report") or payload.get("selection_report") or {}).get("summary") or {},
                "artifact_hash": (payload.get("reproducibility") or {}).get("artifact_hash"),
            }
        )
    return {
        "success": True,
        "schema_version": DRX_RUN_ARTIFACT_SCHEMA,
        "total": len(rows),
        "runs": rows,
        "interpretation_policy": auxiliary_policy("drx"),
    }
