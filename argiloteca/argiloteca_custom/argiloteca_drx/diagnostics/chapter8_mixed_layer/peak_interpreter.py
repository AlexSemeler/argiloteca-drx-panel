# =============================================================================
# Projeto...........: Argiloteca – Painel de DRX
# Módulo............: peak_interpreter.py
#
# Descrição.........:
# Implementa regras explicáveis para argilominerais interestratificados e padrões 00l multi-tratamento.
#
# Autor.............:
# Alexandre Ribas Semeler
# alexandre.semeler@ufrgs.br
#
# Última atualização:
# 2026-06-25
#
# =============================================================================

"""
Implementa regras explicáveis para argilominerais interestratificados e padrões 00l multi-tratamento.

Responsabilidades:
    - preservar contratos públicos e estruturas JSON consumidas pelo painel;
    - registrar proveniência científica e técnica das operações realizadas;
    - manter separadas etapas de leitura, processamento, diagnóstico e exportação;
    - documentar limites de interpretação mineralógica quando houver regras DRX.

Notas científicas:
    Em módulos DRX, 2θ representa o eixo angular medido no difratograma e
    d-spacing representa o espaçamento interplanar calculado pela Lei de Bragg
    (nλ = 2d sen θ). Preparações natural, glicolada e calcinada são usadas para
    observar expansão, colapso, persistência ou destruição de picos basais.
"""

from __future__ import annotations

"""Normalizacao de picos para a camada de interestratificados.

O painel recebe picos de diferentes rotinas, algumas com d-spacing e outras com
2theta. Este modulo padroniza os campos antes da aplicacao das regras do
Capitulo 8.
"""

import math

CU_KA = 1.5406


def two_theta_to_d(two_theta: float, wavelength: float = CU_KA) -> float:
    """Converte 2theta em d-spacing usando a lei de Bragg.

    A configuracao padrao usa CuKalpha, coerente com os padroes calculados
    citados no Capitulo 8, salvo quando outra radiacao for informada.
    """
    theta = math.radians(float(two_theta) / 2.0)
    return wavelength / (2.0 * math.sin(theta))


def normalize_peak(peak: dict) -> dict:
    """Normaliza um pico individual para conter `d_A` quando possivel."""
    row = dict(peak or {})
    if row.get("d") is None and row.get("d_A") is None and row.get("two_theta") is not None:
        row["d_A"] = two_theta_to_d(float(row["two_theta"]))
    if row.get("d") is not None and row.get("d_A") is None:
        row["d_A"] = row.get("d")
    return row


def normalize_peaks_by_preparation(peaks_by_preparation: dict) -> dict:
    """Agrupa picos pelos estados experimentais padronizados da Argiloteca."""
    aliases = {"N": "air_dried", "natural": "air_dried", "G": "ethylene_glycol_solvated", "glycolated": "ethylene_glycol_solvated", "C": "heated_375C", "calcined": "heated_375C"}
    out = {}
    for key, peaks in (peaks_by_preparation or {}).items():
        norm_key = aliases.get(key, key)
        out.setdefault(norm_key, [])
        out[norm_key].extend(normalize_peak(p) for p in (peaks or []))
    return out


def find_peak(peaks, center, tolerance=0.35, field="d_A"):
    """Localiza o pico mais proximo de um centro dentro da tolerancia."""
    best = None
    best_delta = None
    for peak in peaks or []:
        value = peak.get(field)
        if value is None:
            continue
        delta = abs(float(value) - center)
        if delta <= tolerance and (best_delta is None or delta < best_delta):
            best = peak
            best_delta = delta
    return best
