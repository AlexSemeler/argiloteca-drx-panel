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


def calcular_largura_zona_morta(d_spacing):
    """Retorna o raio da zona-morta em Å sem alterar a detecção SciPy."""
    if d_spacing > 20.0:
        return 2.5
    if d_spacing > 18.5:
        return 2.0
    if d_spacing > 15.0:
        return 1.8
    if d_spacing > 13.5:
        return 1.5
    if d_spacing > 11.0:
        return 1.0
    if d_spacing > 9.0:
        return 0.8
    if d_spacing > 7.5:
        return 0.5
    if d_spacing > 6.5:
        return 0.4
    if d_spacing > 4.5:
        return 0.2
    if d_spacing > 3.0:
        return 0.1
    return 0.05


def obter_multiplicador_ruido(d_spacing):
    """Retorna o multiplicador de ruído por faixa de d-spacing."""
    if d_spacing > 20.0:
        return 4.0
    if d_spacing > 18.5:
        return 3.0
    if d_spacing > 16.0:
        return 2.0
    if d_spacing > 15.0:
        return 2.0
    if d_spacing > 13.5:
        return 2.0
    if d_spacing > 12.5:
        return 3.0
    if d_spacing > 11.0:
        return 4.0
    if d_spacing > 10.5:
        return 3.0
    if d_spacing > 9.6:
        return 2.0
    if d_spacing > 9.0:
        return 3.0
    if d_spacing > 8.0:
        return 4.0
    if d_spacing > 7.5:
        return 3.0
    if d_spacing > 6.9:
        return 2.0
    if d_spacing > 6.0:
        return 4.0
    if d_spacing > 5.5:
        return 4.0
    if d_spacing > 4.8:
        return 2.5
    if d_spacing > 4.5:
        return 2.5
    if d_spacing > 4.1:
        return 2.0
    if d_spacing > 3.5:
        return 2.5
    if d_spacing > 3.2:
        return 2.0
    if d_spacing > 3.0:
        return 4.0
    return 4.0


def _dynamic_detection_context(d_spacing):
    """Descreve a faixa usada apenas para explicação do pico."""
    if d_spacing > 20.0:
        return "ruídos longos / baixa angulação"
    if d_spacing > 18.5:
        return "cauda da esmectita glicolada"
    if d_spacing > 16.0:
        return "núcleo da esmectita glicolada"
    if d_spacing > 13.5:
        return "clorita basal / esmectita natural"
    if d_spacing > 12.5:
        return "minerais interestratificados"
    if d_spacing > 11.0:
        return "zona árida"
    if d_spacing > 10.5:
        return "ombro da ilita"
    if d_spacing > 9.6:
        return "núcleo da ilita basal"
    if d_spacing > 9.0:
        return "cauda da ilita / esmectita calcinada"
    if d_spacing > 8.0:
        return "zona árida"
    if d_spacing > 7.5:
        return "ombro da caulinita"
    if d_spacing > 6.9:
        return "núcleo da caulinita basal"
    if d_spacing > 6.0:
        return "zona árida"
    if d_spacing > 4.8:
        return "ordem 002 da ilita"
    if d_spacing > 4.5:
        return "ordem 003 da clorita"
    if d_spacing > 4.1:
        return "quartzo 100"
    if d_spacing > 3.5:
        return "ordem 002 da caulinita"
    if d_spacing > 3.2:
        return "quartzo 101 / ilita 003"
    if d_spacing > 3.0:
        return "zona árida"
    return "fim do espectro / alto ruído instrumental"


def _bragg_d_spacing(two_theta, wavelength):
    """Converte 2θ para d apenas quando λ numérico foi informado."""
    try:
        wavelength = float(wavelength)
        theta_rad = np.radians(float(two_theta) / 2.0)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(wavelength) or wavelength <= 0 or not np.isfinite(theta_rad) or theta_rad <= 0:
        return None
    denominator = 2.0 * np.sin(theta_rad)
    if denominator <= 0:
        return None
    d_spacing = wavelength / denominator
    return float(d_spacing) if np.isfinite(d_spacing) and d_spacing > 0 else None


def _dynamic_detection_metadata(two_theta, wavelength):
    """Monta metadado explicável sem confirmar mineral."""
    d_spacing = _bragg_d_spacing(two_theta, wavelength)
    if d_spacing is None:
        return {
            "applied": False,
            "reason": "d_spacing unavailable or wavelength not explicit",
        }
    return {
        "applied": True,
        "dead_zone_A": calcular_largura_zona_morta(d_spacing),
        "noise_multiplier": obter_multiplicador_ruido(d_spacing),
        "context": _dynamic_detection_context(d_spacing),
    }


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
    wavelength_angstrom = payload.get("wavelength_angstrom") or payload.get("lambda_angstrom")
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
                "dynamic_detection": _dynamic_detection_metadata(float(two_theta[peak_index]), wavelength_angstrom),
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
