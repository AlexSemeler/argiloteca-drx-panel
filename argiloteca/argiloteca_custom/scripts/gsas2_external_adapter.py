#!/usr/bin/env python3
"""
Projeto: Painel DRX Argiloteca

Descricao:
GSAS-II adapter for Argiloteca DRX external jobs. The adapter runs outside the
Flask request path, imports diffraction patterns when enough metadata is
available, creates an auditable GPX project and emits a structured result JSON.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br

Instituicao:

Projeto:
Argiloteca / CPAA

Politica:
Resultados GSAS-II sao auxiliares e nao confirmatorios. A interpretacao
mineralogica principal continua sendo a engine N/G/C da Argiloteca.
"""

from __future__ import annotations

import importlib
import json
import math
import os
import subprocess
import sys
import traceback
from pathlib import Path


POLICY = "auxiliary_not_confirmatory"
ENGINE_ROLE = "external_auxiliary_diffraction_engine"
LICENSE_NOTICE = (
    "This product includes software produced by UChicago Argonne, LLC under "
    "Contract No. DE-AC02-06CH11357 with the Department of Energy."
)
GSAS2_REFERENCE = (
    "Toby, B. H., & Von Dreele, R. B. (2013). GSAS-II: the genesis of a modern "
    "open-source all purpose crystallography software package. Journal of "
    "Applied Crystallography, 46(2), 544-549. doi:10.1107/S0021889813003531"
)
POWDER_IMPORTER_FILES = [
    "G2pwd_BrukerRAW.py",
    "G2pwd_BrukerBRML.py",
    "G2pwd_xye.py",
    "G2pwd_csv.py",
    "G2pwd_fxye.py",
    "G2pwd_CIF.py",
    "G2pwd_Panalytical.py",
    "G2pwd_rigaku.py",
    "G2pwd_GPX.py",
]
CORE_DATA_FILES = [
    "GSASII/atmdata.py",
    "GSASII/FormFactors.py",
    "GSASII/ElementTable.py",
    "GSASII/ImageCalibrants.py",
    "GSASII/Substances.py",
    "GSASII/defaultIparms.py",
    "GSASII/NIST_profile",
    "sources/DIFFaXsubs",
]


def _read_json(path: Path) -> dict:
    """Read the worker manifest without assuming optional keys exist."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    """Write a deterministic JSON artifact for the external job registry."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _path_or_none(value) -> Path | None:
    """Normalize an optional path field from the job manifest."""
    if not value:
        return None
    try:
        return Path(str(value)).expanduser().resolve()
    except Exception:
        return None


def _module_available(name: str) -> bool:
    """Return True when a GSAS-II Python or binary module can be imported."""
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


def _git_commit(path: Path) -> str | None:
    """Return the local GSAS-II git commit when the installer kept metadata."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    if proc.returncode == 0:
        return proc.stdout.strip() or None
    return None


def inspect_gsas2_environment() -> dict:
    """Inspect the GSAS-II installation used by this adapter."""
    root_env = os.environ.get("ARGILOTECA_GSAS2_ROOT")
    if root_env:
        gsas2_root = Path(root_env).expanduser()
    elif (Path(sys.prefix) / "GSAS-II").exists():
        gsas2_root = Path(sys.prefix)
    else:
        gsas2_root = Path(sys.prefix).parent
    gsas2_source = Path(os.environ.get("ARGILOTECA_GSAS2_PYTHONPATH") or gsas2_root / "GSAS-II").expanduser()
    if ":" in str(gsas2_source):
        gsas2_source = Path(str(gsas2_source).split(":", 1)[0])

    warnings: list[str] = []
    scriptable_path = None
    scriptable_import = False
    try:
        import GSASII.GSASIIscriptable as G2sc

        scriptable_import = True
        scriptable_path = getattr(G2sc, "__file__", None)
    except Exception as exc:
        warnings.append(f"GSASIIscriptable nao importou: {exc}")

    importers_dir = gsas2_source / "GSASII" / "imports"
    powder_importers = [
        {"name": name, "path": str(importers_dir / name), "present": (importers_dir / name).exists()}
        for name in POWDER_IMPORTER_FILES
    ]
    core_data_files = [
        {"name": item, "path": str(gsas2_source / item), "present": (gsas2_source / item).exists()}
        for item in CORE_DATA_FILES
    ]
    version_file = gsas2_source / "GSASII-bin" / "GSASIIversion.txt"
    version_text = None
    try:
        version_text = version_file.read_text(encoding="utf-8").strip()
    except Exception:
        pass

    return {
        "engine": "gsas2",
        "policy": POLICY,
        "available": bool(scriptable_import),
        "python": sys.executable,
        "gsas2_root": str(gsas2_root),
        "gsas2_source": str(gsas2_source),
        "scriptable_import": scriptable_import,
        "gsas2_scriptable_path": scriptable_path,
        "binary_modules": {
            "pyspg": _module_available("pyspg"),
            "pypowder": _module_available("pypowder"),
            "pydiffax": _module_available("pydiffax"),
        },
        "git_commit": _git_commit(gsas2_source),
        "version_file": str(version_file),
        "version": version_text,
        "powder_importers": powder_importers,
        "core_data_files": core_data_files,
        "warnings": warnings,
        "license_notice": LICENSE_NOTICE,
        "references": [GSAS2_REFERENCE],
    }


def _finite_float(value):
    """Convert a numeric value to float or None."""
    try:
        result = float(value)
    except Exception:
        return None
    return result if math.isfinite(result) else None


def _histogram_summary(hist) -> dict:
    """Extract a compact pattern summary from a GSAS-II powder histogram."""
    x_values = [_finite_float(value) for value in hist.getdata("x")]
    y_values = [_finite_float(value) for value in hist.getdata("Yobs")]
    pairs = [(x, y) for x, y in zip(x_values, y_values) if x is not None and y is not None]
    if not pairs:
        return {
            "histogram_name": getattr(hist, "name", None),
            "number_of_points": 0,
            "inferred_x_axis": "two_theta_or_tof_unknown",
        }
    max_pair = max(pairs, key=lambda item: item[1])
    y_series = [item[1] for item in pairs]
    x_series = [item[0] for item in pairs]
    return {
        "histogram_name": getattr(hist, "name", None),
        "number_of_points": len(pairs),
        "x_min": min(x_series),
        "x_max": max(x_series),
        "y_min": min(y_series),
        "y_max": max(y_series),
        "y_mean": sum(y_series) / len(y_series),
        "y_max_position": max_pair[0],
        "inferred_x_axis": "two_theta_or_tof_unknown",
    }


def _phase_summary(phase) -> dict:
    """Extract best-effort phase metadata without requiring refinement."""
    summary = {"name": getattr(phase, "name", None)}
    for attr in ("composition", "density"):
        try:
            value = getattr(phase, attr)
            summary[attr] = value() if callable(value) else value
        except Exception:
            pass
    try:
        summary["cell"] = phase.get_cell()
    except Exception:
        pass
    return summary


def _parse_exported_peaks(path: Path) -> list[dict]:
    """Parse the simple text peak export produced by GSAS-II when available."""
    if not path.exists():
        return []
    peaks = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        tokens = line.split()
        numbers = []
        for token in tokens:
            value = _finite_float(token)
            if value is not None:
                numbers.append(value)
        if len(numbers) >= 2:
            peaks.append({"position": numbers[0], "area_or_intensity": numbers[1], "raw": line})
    return peaks


def run_adapter(manifest: dict, result_dir: Path) -> dict:
    """Run the GSAS-II import workflow for one Argiloteca external job."""
    import GSASII.GSASIIscriptable as G2sc

    request = manifest.get("request") or {}
    result_dir.mkdir(parents=True, exist_ok=True)
    project_path = result_dir / "argiloteca_gsas2_adapter.gpx"
    log_path = result_dir / "gsas2_adapter.log"
    warnings: list[str] = []
    errors: list[dict] = []

    pattern_path = _path_or_none(request.get("pattern_path") or request.get("xrd_path") or request.get("diffractogram_path"))
    instrument_path = _path_or_none(request.get("instrument_path") or request.get("iparams") or request.get("instrument_parameters"))
    format_hint = request.get("format_hint") or request.get("fmthint")
    phase_paths = request.get("phase_paths") or request.get("cif_paths") or []
    if isinstance(phase_paths, str):
        phase_paths = [phase_paths]
    phase_paths = [_path_or_none(path) for path in phase_paths]
    phase_paths = [path for path in phase_paths if path is not None]
    seed_peaks = [item for item in request.get("seed_peaks") or [] if isinstance(item, dict)]
    allow_peak_refinement = bool(request.get("allow_peak_refinement"))
    allow_phase_refinement = bool(request.get("allow_phase_refinement"))

    project = G2sc.G2Project(newgpx=str(project_path))
    hist = None
    histogram_summary = None
    peak_export_path = None
    peak_refinement = {
        "peak_refinement_run": False,
        "reason": "not_requested" if not allow_peak_refinement else "histogram_required",
    }

    if pattern_path is None:
        warnings.append("pattern_path nao informado; GPX criado apenas para validacao do ambiente.")
    elif not pattern_path.exists():
        warnings.append(f"pattern_path inexistente: {pattern_path}")
    else:
        try:
            hist = project.add_powder_histogram(
                str(pattern_path),
                iparams=str(instrument_path) if instrument_path and instrument_path.exists() else None,
                fmthint=str(format_hint) if format_hint else None,
            )
            if isinstance(hist, list):
                hist = hist[0] if hist else None
            histogram_summary = _histogram_summary(hist) if hist is not None else None
        except Exception as exc:
            warnings.append(
                "GSAS-II nao importou o padrao. Forneca instrument_path quando o formato nao trouxer "
                f"parametros instrumentais embutidos. Erro: {exc}"
            )
            errors.append({"stage": "add_powder_histogram", "error": str(exc), "traceback": traceback.format_exc()})

    phase_summaries = []
    phase_import_errors = []
    for phase_path in phase_paths:
        if not phase_path.exists():
            phase_import_errors.append({"path": str(phase_path), "error": "phase_path inexistente"})
            continue
        try:
            kwargs = {"phasefile": str(phase_path)}
            if hist is not None:
                kwargs["histograms"] = [hist]
            phase = project.add_phase(**kwargs)
            phase_summaries.append(_phase_summary(phase))
        except Exception as exc:
            phase_import_errors.append({"path": str(phase_path), "error": str(exc)})

    if allow_peak_refinement:
        if hist is None:
            peak_refinement = {"peak_refinement_run": False, "reason": "histogram_required"}
        elif not instrument_path:
            peak_refinement = {"peak_refinement_run": False, "reason": "instrument_parameters_required"}
        else:
            try:
                for seed in seed_peaks:
                    d_spacing = _finite_float(seed.get("d_spacing"))
                    area = _finite_float(seed.get("area") or seed.get("intensity") or seed.get("relative_intensity") or 1.0) or 1.0
                    two_theta = _finite_float(seed.get("two_theta") or seed.get("ttheta"))
                    if d_spacing:
                        hist.add_peak(area=area, dspace=d_spacing)
                    elif two_theta:
                        hist.add_peak(area=area, ttheta=two_theta)
                refine_result = hist.refine_peaks()
                peak_export_path = result_dir / "gsas2_peaks.txt"
                hist.Export_peaks(str(peak_export_path))
                peak_refinement = {
                    "peak_refinement_run": True,
                    "result_type": type(refine_result).__name__,
                    "export_path": str(peak_export_path),
                    "peaks": _parse_exported_peaks(peak_export_path),
                }
            except Exception as exc:
                peak_refinement = {"peak_refinement_run": False, "reason": "peak_refinement_error", "error": str(exc)}
                errors.append({"stage": "refine_peaks", "error": str(exc), "traceback": traceback.format_exc()})

    if allow_phase_refinement:
        warnings.append(
            "allow_phase_refinement recebido, mas refinamento de fase/Rietveld permanece bloqueado sem receita "
            "curada explicita. Nenhum refinamento de fase foi executado."
        )

    project.save()
    log_path.write_text(
        "\n".join(
            [
                "Argiloteca GSAS-II adapter",
                f"policy={POLICY}",
                f"project={project_path}",
                f"pattern_path={pattern_path}",
                f"instrument_path={instrument_path}",
                f"phase_paths={[str(path) for path in phase_paths]}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    env = inspect_gsas2_environment()
    return {
        "success": not any(error.get("stage") == "add_powder_histogram" for error in errors),
        "policy": POLICY,
        "engine": "gsas2",
        "engine_role": ENGINE_ROLE,
        "mode": "pattern_import_validation",
        "gsas2_root": env.get("gsas2_root"),
        "gsas2_python": sys.executable,
        "gsas2_scriptable_path": getattr(G2sc, "__file__", None),
        "project_gpx": str(project_path),
        "project_path": str(project_path),
        "input_files": {
            "pattern_path": str(pattern_path) if pattern_path else None,
            "instrument_path": str(instrument_path) if instrument_path else None,
            "phase_paths": [str(path) for path in phase_paths],
        },
        "outputs": {
            "gpx": str(project_path),
            "log": str(log_path),
            "peaks": str(peak_export_path) if peak_export_path else None,
        },
        "histogram_imported": hist is not None,
        "histogram_summary": histogram_summary,
        "phase_count": len(phase_summaries),
        "phase_names": [item.get("name") for item in phase_summaries if item.get("name")],
        "phase_summaries": phase_summaries,
        "phase_import_errors": phase_import_errors,
        "peak_refinement": peak_refinement,
        "execution": {
            "refinement_run": False,
            "phase_refinement_run": False,
            "reason": "gsas2_used_for_auxiliary_import_validation",
        },
        "warnings": warnings + env.get("warnings", []),
        "errors": errors,
        "license_notice": LICENSE_NOTICE,
        "references": [GSAS2_REFERENCE],
    }


def main() -> int:
    """Entry point used by the offline external job worker."""
    manifest_path = Path(os.environ["ARGILOTECA_DRX_JOB_MANIFEST"])
    result_path = Path(os.environ["ARGILOTECA_DRX_JOB_RESULT_JSON"])
    result_dir = Path(os.environ["ARGILOTECA_DRX_JOB_RESULT_DIR"])
    try:
        manifest = _read_json(manifest_path)
        payload = run_adapter(manifest, result_dir)
        _write_json(result_path, payload)
        print(json.dumps({"success": True, "result_json": str(result_path)}))
        return 0
    except Exception as exc:
        payload = {
            "success": False,
            "policy": POLICY,
            "engine": "gsas2",
            "engine_role": ENGINE_ROLE,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "warnings": ["Falha nao tratada convertida em result.json estruturado."],
            "license_notice": LICENSE_NOTICE,
            "references": [GSAS2_REFERENCE],
        }
        _write_json(result_path, payload)
        print(json.dumps({"success": False, "result_json": str(result_path), "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
