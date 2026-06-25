#!/usr/bin/env python3
"""
Projeto: Painel DRX Argiloteca

Descrição:
Detect DRX/XRD peaks using scipy.signal.find_peaks in the isolated venv.

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
import sys
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks


def main(argv):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        argv: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if len(argv) < 2:
        raise SystemExit("usage: detect_peaks_scipy.py <payload.json>")
    payload = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    two_theta = np.asarray(payload.get("two_theta") or [], dtype=float)
    normalized = np.asarray(payload.get("normalized") or [], dtype=float)
    if len(two_theta) != len(normalized) or len(two_theta) < 3:
        print(json.dumps({"success": False, "error": "curva insuficiente para find_peaks"}))
        return
    start_two_theta = float(payload.get("start_two_theta") or 4.0)
    prominence = float(payload.get("prominence") or 0.02)
    min_distance = float(payload.get("min_distance") or 0.18)
    max_peaks = int(payload.get("max_peaks") or 40)
    step = float(np.nanmedian(np.diff(two_theta))) if len(two_theta) > 1 else min_distance
    distance_points = max(1, int(round(min_distance / max(step, 1e-9))))
    candidates, properties = find_peaks(normalized, prominence=prominence, distance=distance_points)
    rows = []
    prominences = properties.get("prominences") if isinstance(properties, dict) else None
    for row_index, peak_index in enumerate(candidates.tolist()):
        if float(two_theta[peak_index]) < start_two_theta:
            continue
        rows.append(
            {
                "index": int(peak_index),
                "two_theta": round(float(two_theta[peak_index]), 6),
                "normalized_height": round(float(normalized[peak_index]), 8),
                "prominence": round(float(prominences[row_index]), 8) if prominences is not None else None,
            }
        )
    rows.sort(key=lambda row: row.get("normalized_height") or 0.0, reverse=True)
    print(
        json.dumps(
            {
                "success": True,
                "method": "scipy.signal.find_peaks",
                "distance_points": distance_points,
                "peaks": rows[:max_peaks],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main(sys.argv)
