"""
Projeto: Painel DRX Argiloteca

Descricao:
Ponte entre o Painel DRX e GSAS-II. Este modulo registra jobs externos,
consulta disponibilidade do motor e compara a leitura Argiloteca com o resumo
produzido pelo worker GSAS-II, sem importar GSAS-II no processo Flask.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br

Politica:
`auxiliary_not_confirmatory`. O GSAS-II e usado como motor tecnico auxiliar
para leitura, validacao, GPX e refinamentos futuros curados; a interpretacao
mineralogica continua baseada na engine N/G/C da Argiloteca.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from .drx import RawParseError, parse_diffractogram_bytes, utc_now_iso
from .drx_external_jobs import get_external_job, submit_external_job


POLICY = "auxiliary_not_confirmatory"
DEFAULT_GSAS2_ROOT = Path("/home/invenio/invenio-project/tools/g2main_rhel")
DEFAULT_ARGILOTECA_LOCAL = Path("/home/invenio/invenio-project/argiloteca-local")
GSAS2_REFERENCE = (
    "Toby, B. H., & Von Dreele, R. B. (2013). GSAS-II: the genesis of a modern "
    "open-source all purpose crystallography software package. Journal of "
    "Applied Crystallography, 46(2), 544-549. doi:10.1107/S0021889813003531"
)
DEFAULT_REFINEMENT_RECIPE = {
    "recipe_id": "argiloteca.gsas2.refinement.curated_placeholder.v1",
    "policy": POLICY,
    "enabled": False,
    "allowed_modes": ["import_only", "peak_refinement_with_seed_peaks"],
    "blocked_modes": ["le_bail", "pawley", "rietveld"],
    "requirements": [
        "instrument_path curado",
        "fase CIF curada",
        "limites de refinamento definidos",
        "autorizacao explicita allow_phase_refinement=true",
        "revisao por especialista",
    ],
    "reason": "Refinamento estrutural automatico permanece bloqueado ate existir receita curada por laboratorio.",
}


def _gsas2_root() -> Path:
    """Return the configured GSAS-II root used by the external worker."""
    return Path(os.environ.get("ARGILOTECA_GSAS2_ROOT") or DEFAULT_GSAS2_ROOT).expanduser()


def _gsas2_python() -> Path:
    """Return the Python interpreter bundled with the configured GSAS-II."""
    root = _gsas2_root().resolve()
    configured = os.environ.get("ARGILOTECA_GSAS2_PYTHON")
    if configured:
        candidate = Path(configured).expanduser()
        try:
            candidate.resolve().relative_to(root)
            return candidate
        except Exception:
            pass
    return root / "bin" / "python"


def _gsas2_source() -> Path:
    """Return the GSAS-II source path for PYTHONPATH."""
    return Path(os.environ.get("ARGILOTECA_GSAS2_PYTHONPATH") or _gsas2_root() / "GSAS-II").expanduser()


def _adapter_script() -> Path:
    """Return the local GSAS-II adapter script path."""
    argiloteca_local = Path(os.environ.get("ARGILOTECA_LOCAL") or DEFAULT_ARGILOTECA_LOCAL).expanduser()
    return argiloteca_local / "app" / "argiloteca_custom" / "scripts" / "gsas2_external_adapter.py"


def gsas2_status(timeout_seconds=20):
    """Inspect GSAS-II availability by spawning its own Python interpreter."""
    python = _gsas2_python()
    source = _gsas2_source()
    adapter = _adapter_script()
    base_payload = {
        "engine": "gsas2",
        "policy": POLICY,
        "available": False,
        "python": str(python),
        "gsas2_root": str(_gsas2_root()),
        "gsas2_source": str(source),
        "adapter_script": str(adapter),
        "warnings": [],
        "references": [GSAS2_REFERENCE],
    }
    if not python.exists():
        base_payload["warnings"].append("Python do GSAS-II nao encontrado.")
        return base_payload
    if not adapter.exists():
        base_payload["warnings"].append("Adaptador GSAS-II da Argiloteca nao encontrado.")
        return base_payload

    code = (
        "import importlib.util, json; "
        f"spec=importlib.util.spec_from_file_location('argiloteca_gsas2_adapter', {str(adapter)!r}); "
        "mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); "
        "print(json.dumps(mod.inspect_gsas2_environment(), ensure_ascii=False))"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{source}{os.pathsep}{env.get('PYTHONPATH', '')}" if env.get("PYTHONPATH") else str(source)
    env["ARGILOTECA_GSAS2_ROOT"] = str(_gsas2_root())
    env["ARGILOTECA_GSAS2_PYTHON"] = str(python)
    env["ARGILOTECA_GSAS2_PYTHONPATH"] = str(source)
    try:
        proc = subprocess.run(
            [str(python), "-c", code],
            check=False,
            capture_output=True,
            text=True,
            timeout=int(timeout_seconds or 20),
            env=env,
        )
    except Exception as exc:
        base_payload["warnings"].append(f"Falha ao executar status GSAS-II: {exc}")
        return base_payload
    if proc.returncode != 0:
        base_payload["warnings"].append(proc.stderr.strip() or proc.stdout.strip() or "GSAS-II status falhou.")
        return base_payload
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception as exc:
        base_payload["warnings"].append(f"Status GSAS-II retornou JSON invalido: {exc}")
        base_payload["stdout"] = proc.stdout
        base_payload["stderr"] = proc.stderr
        return base_payload
    payload.setdefault("policy", POLICY)
    payload.setdefault("references", [GSAS2_REFERENCE])
    return payload


def _argiloteca_parse_summary(pattern_path):
    """Parse a local pattern with Argiloteca parsers and return compact metrics."""
    path = Path(pattern_path).expanduser()
    payload = {
        "success": False,
        "path": str(path),
        "number_of_points": 0,
        "warnings": [],
    }
    if not path.exists():
        payload["warnings"].append("Arquivo nao encontrado para parser Argiloteca.")
        return payload
    try:
        parsed = parse_diffractogram_bytes(path.read_bytes(), filename=path.name)
    except RawParseError as exc:
        payload["warnings"].append(str(exc))
        return payload
    except Exception as exc:
        payload["warnings"].append(f"Falha inesperada no parser Argiloteca: {exc}")
        return payload
    pairs = [
        (float(x), float(y))
        for x, y in zip(parsed.two_theta or [], parsed.intensity or [])
        if x is not None and y is not None
    ]
    if not pairs:
        payload["warnings"].append("Parser Argiloteca nao retornou pontos.")
        return payload
    max_pair = max(pairs, key=lambda item: item[1])
    y_values = [item[1] for item in pairs]
    x_values = [item[0] for item in pairs]
    return {
        "success": True,
        "path": str(path),
        "parser_metadata": parsed.metadata,
        "number_of_points": len(pairs),
        "x_min": min(x_values),
        "x_max": max(x_values),
        "y_min": min(y_values),
        "y_max": max(y_values),
        "y_mean": sum(y_values) / len(y_values),
        "y_max_position": max_pair[0],
    }


def compare_argiloteca_to_gsas2(pattern_path, gsas2_result=None):
    """Compare Argiloteca parser metrics with a completed GSAS-II adapter result."""
    argiloteca_parse = _argiloteca_parse_summary(pattern_path)
    adapter_result = gsas2_result or {}
    gsas2_parse = adapter_result.get("histogram_summary") or {}
    warnings = []
    if adapter_result.get("warnings"):
        warnings.extend(str(item) for item in adapter_result.get("warnings") or [])

    if not argiloteca_parse.get("success"):
        status = "argiloteca_failed"
    elif not gsas2_parse or not gsas2_parse.get("number_of_points"):
        status = "gsas2_failed"
    else:
        point_delta = abs(int(argiloteca_parse.get("number_of_points") or 0) - int(gsas2_parse.get("number_of_points") or 0))
        arg_x_span = abs(float(argiloteca_parse.get("x_max") or 0) - float(argiloteca_parse.get("x_min") or 0))
        gsas_x_span = abs(float(gsas2_parse.get("x_max") or 0) - float(gsas2_parse.get("x_min") or 0))
        span_delta = abs(arg_x_span - gsas_x_span)
        arg_y_max = abs(float(argiloteca_parse.get("y_max") or 0))
        gsas_y_max = abs(float(gsas2_parse.get("y_max") or 0))
        y_delta_fraction = abs(arg_y_max - gsas_y_max) / max(arg_y_max, gsas_y_max, 1.0)
        point_fraction = point_delta / max(int(argiloteca_parse.get("number_of_points") or 0), int(gsas2_parse.get("number_of_points") or 0), 1)
        if point_fraction <= 0.02 and span_delta <= 0.05 and y_delta_fraction <= 0.05:
            status = "compatible"
        elif point_fraction <= 0.10 and span_delta <= 0.25 and y_delta_fraction <= 0.25:
            status = "minor_difference"
        else:
            status = "major_difference"

    comparison = {
        "status": status,
        "point_count_delta": (
            abs(int(argiloteca_parse.get("number_of_points") or 0) - int(gsas2_parse.get("number_of_points") or 0))
            if gsas2_parse
            else None
        ),
        "x_min_delta": (
            abs(float(argiloteca_parse.get("x_min") or 0) - float(gsas2_parse.get("x_min") or 0))
            if gsas2_parse
            else None
        ),
        "x_max_delta": (
            abs(float(argiloteca_parse.get("x_max") or 0) - float(gsas2_parse.get("x_max") or 0))
            if gsas2_parse
            else None
        ),
        "y_max_delta": (
            abs(float(argiloteca_parse.get("y_max") or 0) - float(gsas2_parse.get("y_max") or 0))
            if gsas2_parse
            else None
        ),
    }
    return {
        "success": status in {"compatible", "minor_difference", "major_difference"},
        "policy": POLICY,
        "engine": "gsas2",
        "purpose": "external_pattern_import_validation",
        "argiloteca_parse": argiloteca_parse,
        "gsas2_parse": gsas2_parse,
        "comparison": comparison,
        "warnings": warnings,
        "provenance": {
            "created_at": utc_now_iso(),
            "python": sys.executable,
            "gsas2_result_project": adapter_result.get("project_gpx") or adapter_result.get("project_path"),
        },
    }


def submit_gsas2_pattern_validation(payload):
    """Register a GSAS-II validation job and include immediate Argiloteca metrics."""
    payload = dict(payload or {})
    payload["engine"] = "gsas2"
    payload.setdefault("allow_peak_refinement", False)
    payload.setdefault("allow_phase_refinement", False)
    pattern_path = payload.get("pattern_path") or payload.get("xrd_path") or payload.get("diffractogram_path")
    job_result = submit_external_job("gsas2", payload=payload)
    return {
        "success": bool(job_result.get("success")),
        "policy": POLICY,
        "engine": "gsas2",
        "job": job_result.get("job"),
        "argiloteca_parse": _argiloteca_parse_summary(pattern_path) if pattern_path else {},
        "warnings": [] if job_result.get("success") else [job_result.get("error")],
    }


def compare_completed_job(job_id):
    """Build a parser comparison from a completed external job when possible."""
    loaded = get_external_job(job_id)
    if not loaded.get("success"):
        return loaded
    job = loaded.get("job") or {}
    request = job.get("request") or {}
    adapter_result = ((job.get("result") or {}).get("adapter_result") or {})
    pattern_path = request.get("pattern_path") or request.get("xrd_path") or request.get("diffractogram_path")
    if not pattern_path:
        return {"success": False, "policy": POLICY, "error": "Job nao contem pattern_path para comparar."}
    return compare_argiloteca_to_gsas2(pattern_path, adapter_result)


def curated_instrument_path():
    """Return a curated GSAS-II instrument parameter file, when configured."""
    configured = os.environ.get("ARGILOTECA_GSAS2_INSTRUMENT_PATH") or os.environ.get("ARGILOTECA_DRX_GSAS2_INSTRUMENT_PATH")
    if not configured:
        return None
    path = Path(configured).expanduser()
    return str(path) if path.exists() else None


def seed_peaks_from_analysis(peaks, limit=12):
    """Convert Argiloteca peak rows into optional GSAS-II seed peaks."""
    rows = []
    for peak in peaks or []:
        if not isinstance(peak, dict):
            continue
        d_spacing = peak.get("d_spacing") or peak.get("d_angstrom") or peak.get("d")
        two_theta = peak.get("two_theta") or peak.get("center_2theta") or peak.get("observed_two_theta")
        intensity = peak.get("intensity") or peak.get("intensity_abs") or peak.get("relative_intensity") or 1.0
        row = {"intensity": intensity}
        if d_spacing:
            row["d_spacing"] = d_spacing
        elif two_theta:
            row["two_theta"] = two_theta
        else:
            continue
        rows.append(row)
        if len(rows) >= int(limit or 12):
            break
    return rows


def submit_temporary_upload_gsas2_validation(pattern_path, *, original_filename=None, seed_peaks=None, phase_paths=None):
    """Register a GSAS-II validation job for one temporary upload copy."""
    instrument_path = curated_instrument_path()
    request = {
        "engine": "gsas2",
        "pattern_path": str(pattern_path),
        "original_filename": original_filename,
        "instrument_path": instrument_path,
        "phase_paths": phase_paths or [],
        "allow_peak_refinement": bool(instrument_path and seed_peaks),
        "allow_phase_refinement": False,
        "seed_peaks": seed_peaks or [],
        "refinement_recipe": DEFAULT_REFINEMENT_RECIPE,
        "source": "arquivo_externo_temporario",
    }
    result = submit_gsas2_pattern_validation(request)
    warnings = list(result.get("warnings") or [])
    if not instrument_path:
        warnings.append("ARGILOTECA_GSAS2_INSTRUMENT_PATH nao configurado; GSAS-II pode gerar GPX sem resumo completo para alguns formatos.")
    job = result.get("job") or {}
    return {
        "success": bool(result.get("success")),
        "policy": POLICY,
        "engine": "gsas2",
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "instrument_path": instrument_path,
        "pattern_path": str(pattern_path),
        "allow_peak_refinement": request["allow_peak_refinement"],
        "refinement_recipe": DEFAULT_REFINEMENT_RECIPE,
        "argiloteca_parse": result.get("argiloteca_parse") or {},
        "warnings": warnings,
    }
