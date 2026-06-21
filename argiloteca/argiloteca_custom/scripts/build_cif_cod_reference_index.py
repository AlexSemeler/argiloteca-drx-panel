#!/usr/bin/env python3
"""
Projeto: Painel DRX Argiloteca

Descrição:
Build a compact CIF/COD DRX reference index for Argiloteca. The script scans a curated CIF directory offline and writes a small JSON manifest consumed by the web backend. It does not copy CIF files.

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

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


DEFAULT_PROJECT = Path(__file__).resolve().parents[3]
DEFAULT_ENGINE_PYTHON = DEFAULT_PROJECT / "venvs" / "drx-science-py310" / "bin" / "python"
DEFAULT_SIMULATOR = Path(__file__).resolve().parent / "simulate_cif_xrd_pattern.py"


def _safe_text(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return str(value or "").strip().strip("'\"")


def _extract_metadata(text):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        text: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    metadata = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 1)
        if len(parts) < 2:
            continue
        key, value = parts[0], _safe_text(parts[1])
        if key in {"_chemical_name_mineral", "_chemical_name_common", "_chemical_name_systematic"}:
            metadata.setdefault("mineral_name", value)
        elif key == "_chemical_formula_sum":
            metadata.setdefault("formula", value)
        elif key in {"_database_code", "_cod_database_code"}:
            metadata.setdefault("cod_id", value)
    return metadata


def _sha256_file(path):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cod_id_from_name(path):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    match = re.search(r"(?:cod[_-]?)?(\d{6,})", path.stem, re.I)
    return match.group(1) if match else None


def _simulate_peaks(path, engine_python, simulator, wavelength, max_peaks):
    """
    Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
        engine_python: Valor de entrada consumido por esta etapa do fluxo.
        simulator: Valor de entrada consumido por esta etapa do fluxo.
        wavelength: Valor de entrada consumido por esta etapa do fluxo.
        max_peaks: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not engine_python.exists() or not simulator.exists():
        return [], {"success": False, "error": "motor cientifico indisponivel"}
    result = subprocess.run(
        [str(engine_python), str(simulator), str(path), wavelength],
        check=False,
        capture_output=True,
        text=True,
        timeout=45,
    )
    if result.returncode != 0:
        return [], {"success": False, "error": (result.stderr or result.stdout).strip()[:500]}
    try:
        payload = json.loads((result.stdout or "").splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return [], {"success": False, "error": "resposta invalida do simulador"}
    peaks = payload.get("peaks") or []
    return peaks[:max_peaks], payload


def build_index(input_dir, output_path, *, engine_python, simulator, wavelength, max_files, max_peaks, source_label=None):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        input_dir: Valor de entrada consumido por esta etapa do fluxo.
        output_path: Valor de entrada consumido por esta etapa do fluxo.
        engine_python: Valor de entrada consumido por esta etapa do fluxo.
        simulator: Valor de entrada consumido por esta etapa do fluxo.
        wavelength: Valor de entrada consumido por esta etapa do fluxo.
        max_files: Valor de entrada consumido por esta etapa do fluxo.
        max_peaks: Valor de entrada consumido por esta etapa do fluxo.
        source_label: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    input_dir = Path(input_dir)
    output_path = Path(output_path)
    references = []
    warnings = []
    for cif_path in sorted(input_dir.rglob("*.cif"))[:max_files]:
        try:
            text = cif_path.read_text(encoding="utf-8", errors="replace")
            metadata = _extract_metadata(text)
            digest = _sha256_file(cif_path)
            cod_id = metadata.get("cod_id") or _cod_id_from_name(cif_path)
            peaks, simulation = _simulate_peaks(cif_path, engine_python, simulator, wavelength, max_peaks)
            mineral_name = metadata.get("mineral_name") or simulation.get("formula") or cif_path.stem
            source = (source_label or "").strip().upper()
            if source not in {"COD", "CIF"}:
                source = "COD" if cod_id else "CIF"
            references.append(
                {
                    "reference_id": "cod:%s" % cod_id if cod_id else "cif:%s" % digest[:16],
                    "source": source,
                    "source_status": "curated_cif_manifest",
                    "cod_id": cod_id,
                    "mineral_name": mineral_name,
                    "formula": metadata.get("formula") or simulation.get("formula"),
                    "file_type": "cif",
                    "local_path": str(cif_path),
                    "source_sha256": digest,
                    "peaks": peaks,
                    "provenance": {
                        "source_format": "cif",
                        "simulation_engine": simulation.get("engine"),
                        "wavelength": wavelength,
                        "integration_policy": "referencia CIF/COD auxiliar; verificar licenca e curadoria antes de redistribuir",
                    },
                }
            )
        except Exception as exc:
            warnings.append("%s: %s" % (cif_path, exc))
    payload = {
        "schema_version": "argiloteca.drx.cif_cod_reference_index.v1",
        "source_dir": str(input_dir),
        "generated_by": Path(__file__).name,
        "references": references,
        "warnings": warnings[:50],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main(argv=None):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        argv: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", nargs="?", help="Diretorio curado com arquivos .cif")
    parser.add_argument("output_path", nargs="?", help="Manifesto JSON de saida")
    parser.add_argument("--input-dir", dest="input_dir_opt", help="Alias nomeado para o diretorio curado com CIFs.")
    parser.add_argument("--output", dest="output_path_opt", help="Alias nomeado para o manifesto JSON de saida.")
    parser.add_argument("--source", default=None, help="Fonte declarada para as referencias: COD ou CIF.")
    parser.add_argument("--engine-python", default=str(DEFAULT_ENGINE_PYTHON))
    parser.add_argument("--simulator", default=str(DEFAULT_SIMULATOR))
    parser.add_argument("--wavelength", default="CuKa")
    parser.add_argument("--max-files", type=int, default=1000)
    parser.add_argument("--max-peaks", type=int, default=80)
    args = parser.parse_args(argv)
    input_dir = args.input_dir_opt or args.input_dir
    output_path = args.output_path_opt or args.output_path
    if not input_dir or not output_path:
        parser.error("informe input_dir/output_path ou use --input-dir/--output")
    payload = build_index(
        input_dir,
        output_path,
        engine_python=Path(args.engine_python),
        simulator=Path(args.simulator),
        wavelength=args.wavelength,
        max_files=args.max_files,
        max_peaks=args.max_peaks,
        source_label=args.source,
    )
    print(json.dumps({"success": True, "references": len(payload["references"]), "output": output_path}))


if __name__ == "__main__":
    main(sys.argv[1:])
