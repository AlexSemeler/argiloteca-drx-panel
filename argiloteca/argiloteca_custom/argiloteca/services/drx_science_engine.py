"""
Projeto: Painel DRX Argiloteca

Descrição:
Isolated scientific engine bridge for DRX/XRD routines.

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


Fundamentacao cientifica revisada:
    Este arquivo integra o Painel DRX da Argiloteca, projeto fundamentado nas
    referencias cientificas revisadas para interpretacao auxiliar de DRX de
    argilominerais: Brindley & Brown (1980), Bailey (1980/1988),
    Moore & Reynolds (1989/1997), Drits & Tchoubar (1990),
    Lanson & Bouchet (1995), Meunier, Clays (2005), fluxograma USGS para
    identificacao de argilominerais por DRX e referencias empiricas Pre-Sal
    UFRGS/Petrobras.

Autoria cientifica e curadoria:
    Alexandre Ribas Semeler
    E-mail: alexandre.semler@ufrgs.br

Politica de interpretacao:
    Resultados mineralogicos sao auxiliares e nao confirmatorios. O codigo
    combina comportamento N/G/C, picos companheiros, d060, ambiguidades,
    contexto e proveniencia; nao confirma mineral por pico isolado.
"""

from __future__ import annotations

import importlib.metadata
import json
import os
import subprocess
import tempfile
from pathlib import Path


DRX_SCIENCE_ENGINE_SCHEMA = "argiloteca.drx.science_engine.v1"
DEFAULT_DRX_SCIENCE_PYTHON = Path(__file__).resolve().parents[4] / "venvs" / "drx-science-py310" / "bin" / "python"
DEFAULT_CIF_SIMULATOR = Path(__file__).resolve().parents[2] / "scripts" / "simulate_cif_xrd_pattern.py"
DEFAULT_SCIPY_PEAK_DETECTOR = Path(__file__).resolve().parents[2] / "scripts" / "detect_peaks_scipy.py"
DEFAULT_LMFIT_PEAK_FITTER = Path(__file__).resolve().parents[2] / "scripts" / "fit_peaks_lmfit.py"
DEFAULT_ENGINE_TIMEOUT_SECONDS = 45


def science_python_path():
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return Path(os.environ.get("ARGILOTECA_DRX_SCIENCE_PYTHON") or DEFAULT_DRX_SCIENCE_PYTHON)


def cif_simulator_path():
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return Path(os.environ.get("ARGILOTECA_DRX_CIF_SIMULATOR") or DEFAULT_CIF_SIMULATOR)


def scipy_peak_detector_path():
    """
    Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return Path(os.environ.get("ARGILOTECA_DRX_SCIPY_PEAK_DETECTOR") or DEFAULT_SCIPY_PEAK_DETECTOR)


def lmfit_peak_fitter_path():
    """
    Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return Path(os.environ.get("ARGILOTECA_DRX_LMFIT_PEAK_FITTER") or DEFAULT_LMFIT_PEAK_FITTER)


def _engine_env():
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    env = dict(os.environ)
    env.setdefault("MPLCONFIGDIR", "/tmp/argiloteca_mpl")
    # Keep the scientific interpreter isolated from the Flask/Invenio import path.
    env.pop("PYTHONPATH", None)
    return env


def _last_json_line(text):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        text: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    for line in reversed((text or "").splitlines()):
        if line.strip().startswith("{"):
            return line.strip()
    return text or ""


def _run_engine(args, timeout=DEFAULT_ENGINE_TIMEOUT_SECONDS):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        args: Valor de entrada consumido por esta etapa do fluxo.
        timeout: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    engine_python = science_python_path()
    if not engine_python.exists():
        return {
            "success": False,
            "error": "Python do motor cientifico DRX nao encontrado.",
            "engine_python": str(engine_python),
        }
    try:
        result = subprocess.run(
            [str(engine_python), *[str(arg) for arg in args]],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_engine_env(),
        )
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Tempo limite excedido no motor cientifico DRX.",
            "engine_python": str(engine_python),
        }
    if result.returncode != 0:
        return {
            "success": False,
            "error": (result.stderr or result.stdout or "Falha no motor cientifico DRX.").strip()[:1000],
            "engine_python": str(engine_python),
        }
    try:
        payload = json.loads(_last_json_line(result.stdout))
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "Motor cientifico DRX retornou resposta invalida.",
            "engine_python": str(engine_python),
        }
    if not isinstance(payload, dict):
        return {
            "success": False,
            "error": "Motor cientifico DRX retornou payload invalido.",
            "engine_python": str(engine_python),
        }
    payload.setdefault("engine_python", str(engine_python))
    return payload


def simulate_cif_pattern(content, filename=None, wavelength="CuKa"):
    """Simulate powder XRD peaks for CIF bytes using the isolated engine."""
    simulator = cif_simulator_path()
    if not simulator.exists():
        return {
            "success": False,
            "error": "Script simulador CIF nao encontrado.",
            "simulator": str(simulator),
        }
    suffix = Path(filename or "reference.cif").suffix or ".cif"
    with tempfile.NamedTemporaryFile("wb", suffix=suffix, delete=True) as fp:
        fp.write(content)
        fp.flush()
        payload = _run_engine([simulator, fp.name, wavelength])
    payload.setdefault("simulator", str(simulator))
    return payload


def detect_peaks_scipy(two_theta, normalized, *, start_two_theta=4.0, prominence=0.02, min_distance=0.18, max_peaks=40):
    """Detect peaks with scipy.signal.find_peaks in the isolated engine."""
    detector = scipy_peak_detector_path()
    if not detector.exists():
        return {
            "success": False,
            "error": "Script de deteccao SciPy nao encontrado.",
            "detector": str(detector),
        }
    payload = {
        "two_theta": list(two_theta or []),
        "normalized": list(normalized or []),
        "start_two_theta": start_two_theta,
        "prominence": prominence,
        "min_distance": min_distance,
        "max_peaks": max_peaks,
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=True) as fp:
        json.dump(payload, fp)
        fp.flush()
        result = _run_engine([detector, fp.name], timeout=20)
    result.setdefault("detector", str(detector))
    return result


def fit_peaks_lmfit(two_theta, corrected, peak_indices, *, wavelength_angstrom=1.5406, window_two_theta=0.35):
    """Fit selected peaks with lmfit PseudoVoigtModel in the isolated engine."""
    fitter = lmfit_peak_fitter_path()
    if not fitter.exists():
        return {
            "success": False,
            "error": "Script de ajuste lmfit nao encontrado.",
            "fitter": str(fitter),
        }
    payload = {
        "two_theta": list(two_theta or []),
        "corrected": list(corrected or []),
        "peak_indices": list(peak_indices or []),
        "wavelength_angstrom": wavelength_angstrom,
        "window_two_theta": window_two_theta,
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=True) as fp:
        json.dump(payload, fp)
        fp.flush()
        result = _run_engine([fitter, fp.name], timeout=30)
    result.setdefault("fitter", str(fitter))
    return result


def science_engine_status():
    """Return a compact status payload for the isolated scientific engine."""
    engine_python = science_python_path()
    simulator = cif_simulator_path()
    payload = {
        "schema_version": DRX_SCIENCE_ENGINE_SCHEMA,
        "available": False,
        "engine_python": str(engine_python),
        "engine_python_exists": engine_python.exists(),
        "cif_simulator": str(simulator),
        "cif_simulator_exists": simulator.exists(),
        "scipy_peak_detector": str(scipy_peak_detector_path()),
        "scipy_peak_detector_exists": scipy_peak_detector_path().exists(),
        "lmfit_peak_fitter": str(lmfit_peak_fitter_path()),
        "lmfit_peak_fitter_exists": lmfit_peak_fitter_path().exists(),
        "packages": {},
    }
    if not engine_python.exists():
        payload["error"] = "Python do motor cientifico DRX nao encontrado."
        return payload
    probe = _run_engine(
        [
            "-c",
            (
                "import importlib.metadata as m, json; "
                "names=['numpy','scipy','pandas','matplotlib','lmfit','pybaselines','pymatgen']; "
                "print(json.dumps({'success': True, 'packages': {n: m.version(n) for n in names}}))"
            ),
        ],
        timeout=20,
    )
    if not probe.get("success"):
        payload["error"] = probe.get("error")
        return payload
    payload["available"] = bool(simulator.exists() and scipy_peak_detector_path().exists() and lmfit_peak_fitter_path().exists())
    payload["packages"] = probe.get("packages") or {}
    try:
        payload["bridge_package_version"] = importlib.metadata.version("argiloteca")
    except importlib.metadata.PackageNotFoundError:
        payload["bridge_package_version"] = None
    return payload
