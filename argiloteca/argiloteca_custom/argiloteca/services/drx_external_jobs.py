"""
Projeto: Painel DRX Argiloteca

Descrição:
External DRX job registry for GSAS-II/DARA-style integrations.

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

import json
import os
import shlex
import subprocess
import uuid
from pathlib import Path

from .drx import utc_now_iso
from argiloteca.drx_core.contracts import DRX_EXTERNAL_JOB_SCHEMA


SUPPORTED_EXTERNAL_ENGINES = {"gsas2", "dara"}
ENGINE_COMMAND_ENV = {
    "gsas2": "ARGILOTECA_DRX_GSAS2_COMMAND",
    "dara": "ARGILOTECA_DRX_DARA_COMMAND",
}
TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}
DEFAULT_JOBS_DIR = (
    Path(os.environ.get("INVENIO_INSTANCE_PATH") or Path(__file__).resolve().parents[4] / "instance")
    / "argiloteca_drx_jobs"
)


def _jobs_dir():
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    path = Path(os.environ.get("ARGILOTECA_DRX_JOBS_DIR") or DEFAULT_JOBS_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _job_path(job_id):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        job_id: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    safe_id = "".join(ch for ch in str(job_id or "") if ch.isalnum() or ch in {"-", "_"})
    return _jobs_dir() / f"{safe_id}.json"


def _job_artifact_dir(job_id):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        job_id: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    safe_id = "".join(ch for ch in str(job_id or "") if ch.isalnum() or ch in {"-", "_"})
    path = _jobs_dir() / safe_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_job(job):
    """
    Gera artefatos derivados, relatórios ou saídas serializadas com parâmetros e proveniência para auditoria posterior.
    
    Args:
        job: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    job = dict(job or {})
    job["updated_at"] = utc_now_iso()
    _job_path(job.get("job_id")).write_text(json.dumps(job, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return job


def submit_external_job(engine, payload=None):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        engine: Valor de entrada consumido por esta etapa do fluxo.
        payload: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    engine_key = str(engine or "").strip().casefold()
    if engine_key not in SUPPORTED_EXTERNAL_ENGINES:
        return {
            "success": False,
            "error": "Motor externo nao suportado. Use gsas2 ou dara.",
            "supported_engines": sorted(SUPPORTED_EXTERNAL_ENGINES),
        }
    job_id = "drx-job-" + uuid.uuid4().hex[:16]
    now = utc_now_iso()
    job = {
        "schema_version": DRX_EXTERNAL_JOB_SCHEMA,
        "job_id": job_id,
        "engine": engine_key,
        "status": "queued",
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "finished_at": None,
        "request": payload or {},
        "adapter": {
            "engine": engine_key,
            "command_env": ENGINE_COMMAND_ENV[engine_key],
            "timeout_seconds": int(os.environ.get("ARGILOTECA_DRX_EXTERNAL_JOB_TIMEOUT", "1800")),
            "input_manifest_name": "input_manifest.json",
            "result_manifest_name": "result.json",
            "execution_mode": "offline_worker",
        },
        "execution_policy": "job externo registrado; execucao deve ocorrer fora da request Flask",
        "result": {},
        "result_path": None,
        "logs": [],
        "warnings": [
            "GSAS-II/DARA nao sao executados dentro do processo Flask.",
            "Rietveld/Le Bail exigem curadoria, parametros instrumentais e arquivos de entrada versionados.",
        ],
    }
    _job_path(job_id).write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "job": job}


def get_external_job(job_id):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        job_id: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    path = _job_path(job_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"success": False, "error": "Job DRX externo nao encontrado."}
    except json.JSONDecodeError:
        return {"success": False, "error": "Job DRX externo corrompido."}
    return {"success": True, "job": payload}


def list_external_jobs(status=None, limit=50):
    """List persisted jobs from the bounded jobs directory."""
    rows = []
    for path in sorted(_jobs_dir().glob("*.json"), key=lambda item: item.stat().st_mtime):
        if len(rows) >= int(limit or 50):
            break
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if status and job.get("status") != status:
            continue
        rows.append(job)
    return {"success": True, "jobs": rows, "total": len(rows)}


def claim_next_external_job():
    """Move the oldest queued job to running for an offline worker."""
    for job in list_external_jobs(status="queued", limit=1000).get("jobs") or []:
        job["status"] = "running"
        job["started_at"] = utc_now_iso()
        job.setdefault("logs", []).append({"at": utc_now_iso(), "message": "Job reivindicado pelo worker offline."})
        return _write_job(job)
    return None


def complete_external_job(job_id, *, status, result=None, result_path=None, log=None, warnings=None):
    """Persist a terminal or intermediate status for one external DRX job."""
    loaded = get_external_job(job_id)
    if not loaded.get("success"):
        return loaded
    job = loaded["job"]
    job["status"] = status
    if status in TERMINAL_STATUSES:
        job["finished_at"] = utc_now_iso()
    if result is not None:
        job["result"] = result
    if result_path is not None:
        job["result_path"] = str(result_path)
    if log:
        job.setdefault("logs", []).append({"at": utc_now_iso(), "message": str(log)})
    if warnings:
        job.setdefault("warnings", []).extend(str(item) for item in warnings)
    return {"success": True, "job": _write_job(job)}


def _adapter_command(engine):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        engine: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    env_name = ENGINE_COMMAND_ENV.get(engine)
    command = os.environ.get(env_name or "")
    return env_name, command


def _write_input_manifest(job, result_dir):
    """
    Gera artefatos derivados, relatórios ou saídas serializadas com parâmetros e proveniência para auditoria posterior.
    
    Args:
        job: Valor de entrada consumido por esta etapa do fluxo.
        result_dir: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    manifest = {
        "schema_version": "argiloteca.drx.external_job.input_manifest.v1",
        "job_id": job.get("job_id"),
        "engine": job.get("engine"),
        "created_at": utc_now_iso(),
        "request": job.get("request") or {},
        "policy": {
            "run_outside_flask_request": True,
            "no_manual_rietveld": True,
            "result_is_auxiliary_until_curated": True,
        },
    }
    path = result_dir / "input_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def run_external_job_adapter(job):
    """Execute one claimed external job through a configured command adapter.

    The adapter command is optional by design. Without configuration the worker
    records a deterministic failed/not_configured result instead of attempting
    to import GSAS-II or DARA inside the web process.
    """
    if not job:
        return {"success": False, "error": "Job externo vazio."}
    job_id = job.get("job_id")
    engine = str(job.get("engine") or "").casefold()
    if engine not in SUPPORTED_EXTERNAL_ENGINES:
        return complete_external_job(
            job_id,
            status="failed",
            result={"implemented": False, "reason": "unsupported_engine", "engine": engine},
            log="Motor externo nao suportado pelo contrato atual.",
        )

    result_dir = _job_artifact_dir(job_id)
    input_manifest = _write_input_manifest(job, result_dir)
    env_name, command = _adapter_command(engine)
    if not command:
        return complete_external_job(
            job_id,
            status="failed",
            result={
                "implemented": False,
                "reason": "adapter_not_configured",
                "engine": engine,
                "required_env": env_name,
                "input_manifest": str(input_manifest),
            },
            result_path=result_dir,
            log=f"Adapter {engine} nao configurado; defina {env_name} para executar offline.",
            warnings=[
                "Nenhuma execucao GSAS-II/DARA foi realizada.",
                "Configure um adapter externo e rode o worker fora da request Flask.",
            ],
        )

    timeout = int((job.get("adapter") or {}).get("timeout_seconds") or os.environ.get("ARGILOTECA_DRX_EXTERNAL_JOB_TIMEOUT", "1800"))
    stdout_path = result_dir / "stdout.log"
    stderr_path = result_dir / "stderr.log"
    result_manifest = result_dir / "result.json"
    env = os.environ.copy()
    env.update(
        {
            "ARGILOTECA_DRX_JOB_ID": str(job_id),
            "ARGILOTECA_DRX_JOB_ENGINE": engine,
            "ARGILOTECA_DRX_JOB_MANIFEST": str(input_manifest),
            "ARGILOTECA_DRX_JOB_RESULT_DIR": str(result_dir),
            "ARGILOTECA_DRX_JOB_RESULT_JSON": str(result_manifest),
        }
    )
    try:
        process = subprocess.run(
            shlex.split(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return complete_external_job(
            job_id,
            status="failed",
            result={
                "implemented": True,
                "reason": "adapter_timeout",
                "engine": engine,
                "timeout_seconds": timeout,
                "input_manifest": str(input_manifest),
            },
            result_path=result_dir,
            log=f"Adapter {engine} excedeu timeout de {timeout}s.",
        )
    except OSError as exc:
        return complete_external_job(
            job_id,
            status="failed",
            result={
                "implemented": True,
                "reason": "adapter_execution_error",
                "engine": engine,
                "error": str(exc),
                "input_manifest": str(input_manifest),
            },
            result_path=result_dir,
            log=f"Falha ao executar adapter {engine}: {exc}",
        )

    stdout_path.write_text(process.stdout or "", encoding="utf-8")
    stderr_path.write_text(process.stderr or "", encoding="utf-8")
    adapter_payload = {}
    if result_manifest.exists():
        try:
            adapter_payload = json.loads(result_manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            adapter_payload = {"result_manifest_error": str(exc)}

    status = "succeeded" if process.returncode == 0 else "failed"
    result = {
        "implemented": True,
        "engine": engine,
        "returncode": process.returncode,
        "input_manifest": str(input_manifest),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "adapter_result": adapter_payload,
        "policy": "Resultado GSAS-II/DARA e artefato auxiliar ate revisao e curadoria mineralogica.",
    }
    return complete_external_job(
        job_id,
        status=status,
        result=result,
        result_path=result_dir,
        log=f"Adapter {engine} finalizado com codigo {process.returncode}.",
    )
