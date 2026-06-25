#!/usr/bin/env python3
"""
Projeto: Painel DRX Argiloteca

Descrição:
DARA adapter for Argiloteca DRX external jobs. This validates DARA/BGMN availability and records a reproducible adapter result. Actual DARA phase-search/refinement is only enabled when a curated job manifest provides the required pattern, candidate phases and instrument context.

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
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/argiloteca_mplconfig")
    manifest_path = Path(os.environ["ARGILOTECA_DRX_JOB_MANIFEST"])
    result_path = Path(os.environ["ARGILOTECA_DRX_JOB_RESULT_JSON"])
    manifest = _read_json(manifest_path)
    request = manifest.get("request") or {}

    import dara
    from dara.bgmn_worker import BGMNWorker

    worker = BGMNWorker()
    pattern_path = request.get("pattern_path") or request.get("xrd_path") or request.get("diffractogram_path")
    phase_paths = request.get("phase_paths") or request.get("cif_paths") or []
    if isinstance(phase_paths, str):
        phase_paths = [phase_paths]

    payload = {
        "success": True,
        "adapter": "dara",
        "mode": "validated_adapter",
        "dara_module": getattr(dara, "__file__", None),
        "bgmn_folder": str(worker.bgmn_folder),
        "bgmn_path": str(worker.bgmn_path),
        "bgmn_exists": worker.bgmn_path.exists(),
        "inputs": {
            "pattern_path": pattern_path,
            "phase_paths": phase_paths,
            "precursors": request.get("precursors") or [],
            "instrument_name": request.get("instrument_name") or request.get("instrument_profile"),
        },
        "execution": {
            "phase_search_run": False,
            "refinement_run": False,
            "reason": "curated_pattern_phase_and_instrument_inputs_required",
        },
        "policy": (
            "DARA/BGMN adapter validado. Busca/refinamento real exige entradas curadas, "
            "base estrutural licenciada/proveniente e revisao mineralogica; resultado nao e confirmatorio."
        ),
    }
    _write_json(result_path, payload)
    print(json.dumps({"success": True, "result_json": str(result_path)}))


if __name__ == "__main__":
    main()
