#!/usr/bin/env python3
"""
Projeto: Painel DRX Argiloteca

Descrição:
Fit DRX/XRD peaks with lmfit PseudoVoigtModel in the isolated venv.

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
import math
import sys
from pathlib import Path

import numpy as np
from lmfit.models import PseudoVoigtModel


def _d_spacing(two_theta, wavelength):
    """
    Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar.
    
    Args:
        two_theta: Valor de entrada consumido por esta etapa do fluxo.
        wavelength: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    theta = math.radians(float(two_theta) / 2.0)
    sine = math.sin(theta)
    if sine <= 0:
        return None
    return wavelength / (2.0 * sine)


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
        raise SystemExit("usage: fit_peaks_lmfit.py <payload.json>")
    payload = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    x = np.asarray(payload.get("two_theta") or [], dtype=float)
    y = np.asarray(payload.get("corrected") or [], dtype=float)
    peaks = [int(index) for index in (payload.get("peak_indices") or []) if 0 <= int(index) < len(x)]
    wavelength = float(payload.get("wavelength_angstrom") or 1.5406)
    window = float(payload.get("window_two_theta") or 0.35)
    rows = []
    for number, peak_index in enumerate(peaks, start=1):
        center_guess = float(x[peak_index])
        mask = (x >= center_guess - window) & (x <= center_guess + window)
        xw = x[mask]
        yw = y[mask]
        if len(xw) < 5 or float(np.nanmax(yw)) <= 0:
            continue
        model = PseudoVoigtModel(prefix="p_")
        params = model.make_params()
        params["p_center"].set(value=center_guess, min=float(xw.min()), max=float(xw.max()))
        params["p_amplitude"].set(value=max(float(np.trapezoid(yw, xw)), 1e-9), min=0)
        params["p_sigma"].set(value=max(window / 4.0, 1e-4), min=1e-5, max=max(window * 2.0, 1e-4))
        params["p_fraction"].set(value=0.5, min=0, max=1)
        try:
            result = model.fit(yw, params, x=xw, nan_policy="omit")
        except Exception as exc:
            rows.append({"peak_index": number, "fit_success": False, "fit_message": str(exc)[:300]})
            continue
        best = result.params
        center = float(best["p_center"].value)
        fwhm = float(best["p_fwhm"].value) if "p_fwhm" in best else None
        height = float(best["p_height"].value) if "p_height" in best else float(np.nanmax(result.best_fit))
        d_value = _d_spacing(center, wavelength)
        rows.append(
            {
                "peak_index": number,
                "fit_success": bool(result.success),
                "fit_message": str(result.message)[:300],
                "center_2theta": round(center, 6),
                "center_2theta_stderr": round(float(best["p_center"].stderr), 8) if best["p_center"].stderr is not None else None,
                "center_d_angstrom": round(d_value, 6) if d_value else None,
                "amplitude": round(float(best["p_amplitude"].value), 8),
                "height": round(height, 8),
                "fwhm": round(fwhm, 8) if fwhm else None,
                "sigma": round(float(best["p_sigma"].value), 8),
                "fraction": round(float(best["p_fraction"].value), 8),
                "redchi": round(float(result.redchi), 8) if result.redchi is not None else None,
                "aic": round(float(result.aic), 8) if result.aic is not None else None,
                "bic": round(float(result.bic), 8) if result.bic is not None else None,
                "profile_model": "pseudo_voigt",
                "model_name": "lmfit.PseudoVoigtModel",
                "source_index": peak_index,
            }
        )
    print(json.dumps({"success": True, "method": "lmfit.PseudoVoigtModel", "fit_results": rows}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv)
