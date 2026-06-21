#!/usr/bin/env python3
"""
Projeto: Painel DRX Argiloteca

Descrição:
GSAS-II adapter for Argiloteca DRX external jobs. This validates the GSAS-II scripting environment and creates an auditable adapter result. Full Rietveld/Le Bail execution is intentionally gated behind explicit curated inputs in the job manifest.

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
from pathlib import Path


def _read_json(path):
    """
    Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática.
    
    Args:
        path: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, payload):
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
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def main():
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        Nenhum argumento explícito.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    manifest_path = Path(os.environ["ARGILOTECA_DRX_JOB_MANIFEST"])
    result_path = Path(os.environ["ARGILOTECA_DRX_JOB_RESULT_JSON"])
    result_dir = Path(os.environ["ARGILOTECA_DRX_JOB_RESULT_DIR"])
    manifest = _read_json(manifest_path)
    request = manifest.get("request") or {}

    import GSASII.GSASIIscriptable as G2sc

    project_path = result_dir / "argiloteca_gsas2_adapter.gpx"
    project = G2sc.G2Project(newgpx=str(project_path))
    project.save()

    pattern_path = request.get("pattern_path") or request.get("xrd_path") or request.get("diffractogram_path")
    phase_paths = request.get("phase_paths") or request.get("cif_paths") or []
    if isinstance(phase_paths, str):
        phase_paths = [phase_paths]

    payload = {
        "success": True,
        "adapter": "gsas2",
        "mode": "validated_adapter",
        "gsas2_scriptable": getattr(G2sc, "__file__", None),
        "project_path": str(project_path),
        "inputs": {
            "pattern_path": pattern_path,
            "phase_paths": phase_paths,
        },
        "execution": {
            "refinement_run": False,
            "reason": "curated_pattern_and_phase_inputs_required",
        },
        "policy": (
            "GSAS-II adapter validado. Refinamento real exige padrao DRX, fases CIF/estrutura, "
            "parametros instrumentais e revisao curatorial; resultado nao e confirmatorio."
        ),
    }
    _write_json(result_path, payload)
    print(json.dumps({"success": True, "result_json": str(result_path)}))


if __name__ == "__main__":
    main()
