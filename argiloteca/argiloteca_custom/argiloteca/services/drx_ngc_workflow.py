"""
Projeto: Painel DRX Argiloteca

Descrição:
Versioned N/G/C workflow interpretation for clay-mineral DRX screening.

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

Referência aplicada:
- Lanson, B. & Bouchet, A. (1995). Identification des mineraux argileux
  par diffraction des rayons X: apport du traitement numerique.
  Bull. Centres Rech. Explor.-Prod. Elf Aquitaine, 19(1), 91-118.
  Arquivo local: /home/invenio/invenio-project/textos/
  lanson-1995-bull-centres-rech-ep-19-91.pdf

Como a lógica da referência está aplicada neste arquivo:
- _mixed_layer_warnings transforma respostas parciais, ombros, largura e
  deslocamentos de picos em avisos de mistura/interestratificado.
- interpret_clay_minerals_ngc e _assemble_ngc_group preservam esses avisos no
  payload do painel, evitando identificação por pico isolado.
- A engine V3 é chamada por interpret_ngc_v3 e adiciona diagnostic_interpretation
  com mixed_layer_candidates, ambiguities e confidence_scores.

Referência estrutural aplicada:
- Meunier, Clays, 2005.
  Arquivo local: /home/invenio/invenio-project/Clays_Meunier.pdf

Como a lógica de Meunier está aplicada neste arquivo:
- Este workflow não reimplementa Meunier diretamente; ele coleta e repassa para
  interpret_ngc_v3 os metadados que a engine usa para aplicar Meunier:
  d060, context, morphology e chemistry.
- O retorno diagnostic_interpretation inclui octahedral_classification,
  mixed_layer_candidates, range_comparison e provenance, onde a referencia
  aparece como "meunier_2005".


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

import math
import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from argiloteca.drx_core.contracts import DRX_NGC_WORKFLOW_SCHEMA
from argiloteca_drx.diagnostics.diagnostic_behavior_rules import (
    CONFIRMED_BY_RULES,
    POLICY,
    POSSIBLE_BY_RULES,
    PROBABLE_BY_RULES,
)
from argiloteca_drx.diagnostics.diagnostic_peak_rules import mapped_ranges, targeted_basal_ranges

try:
    from argiloteca_drx.diagnostics import interpret_ngc as interpret_ngc_v3
except Exception:  # pragma: no cover - optional compatibility layer
    interpret_ngc_v3 = None

DEFAULT_WAVELENGTH_A = 1.5406
DIAGNOSTIC_RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "diagnostic_rules_ngc.json"
WEBMINERAL_MANIFEST_CANDIDATES = [
    Path(__file__).resolve().parents[4] / "data" / "drx" / "webmineral" / "webmineral_argilominerais_vocabulario_manifest.json",
    Path(__file__).resolve().parents[4] / "data" / "drx" / "saida_argiloteca_drx" / "webmineral_argilominerais_vocabulario.json",
    Path(__file__).resolve().parents[4] / "povoamento" / "visualizacao-drx" / "webmineral" / "webmineral_argilominerais_vocabulario_manifest.json",
]

DIAGNOSTIC_RANGES = mapped_ranges("workflow_diagnostic_ranges")
SCRIPT_INTERVAL_RANGES = mapped_ranges("script_interval_ranges")
TARGETED_BASAL_RANGES = targeted_basal_ranges()

PREPARATION_ORDER = {"natural": 0, "glicolado": 1, "calcinado": 2, "indeterminado": 3}


def _finite_float(value):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _d_from_two_theta(two_theta_deg, wavelength_a=DEFAULT_WAVELENGTH_A):
    """
    Converte posição angular 2θ em espaçamento interplanar d pela Lei de Bragg.

    A interpretação de argilominerais usa d-spacing como domínio principal porque
    as reflexões basais 001/002/003 são comparadas entre lâminas natural,
    glicolada e calcinada. O cálculo assume n=1 e comprimento de onda Cu-Kα por
    padrão, mas aceita outro valor para preservar rastreabilidade.

    Args:
        two_theta_deg: Posição observada do pico em graus 2θ.
        wavelength_a: Comprimento de onda em Å usado na coleta ou simulação.
    Returns:
        d-spacing em Å, ou None quando a entrada não permite cálculo físico.
    Raises:
        Exception: Não levanta erro deliberadamente; entradas inválidas retornam None.
    """
    two_theta = _finite_float(two_theta_deg)
    wavelength = _finite_float(wavelength_a) or DEFAULT_WAVELENGTH_A
    if two_theta is None or two_theta <= 0:
        return None
    theta = math.radians(two_theta / 2.0)
    sine = math.sin(theta)
    if sine <= 0:
        return None
    return wavelength / (2.0 * sine)


def _preparation_key(value):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = str(value or "").strip().lower()
    text = text.replace("_", "-").replace(" ", "-")
    if text in {"n", "nat", "natural", "normal", "ad", "air-dried", "airdry", "secagem-ao-ar"}:
        return "natural"
    if text in {"g", "eg", "glycolated", "glicolado", "glicolada", "ethylene-glycol", "etilenoglicol"}:
        return "glicolado"
    if text in {"c", "h", "heated", "aquecido", "aquecida", "calcined", "calcinado", "calcinada", "400c", "550c"}:
        return "calcinado"
    return "indeterminado"


def _sample_base(item):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        item: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    for key in ("sample_base", "sampleBase", "sample_id", "sample_code"):
        value = str((item or {}).get(key) or "").strip()
        if value:
            return value
    filename = str((item or {}).get("filename") or (item or {}).get("original_filename") or "").strip()
    return filename.rsplit(".", 1)[0] if filename else "sem-amostra"


def _peak_d(peak):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        peak: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    d_value = _finite_float(
        (peak or {}).get("d_angstrom")
        or (peak or {}).get("d")
        or (peak or {}).get("d_A")
        or (peak or {}).get("d_a")
        or (peak or {}).get("d_spacing")
        or (peak or {}).get("center_d_angstrom")
    )
    if d_value is not None:
        return d_value
    return _d_from_two_theta(
        (peak or {}).get("twoTheta_deg")
        or (peak or {}).get("two_theta")
        or (peak or {}).get("2theta")
        or (peak or {}).get("center_2theta"),
        (peak or {}).get("wavelength_A") or (peak or {}).get("wavelength_a") or DEFAULT_WAVELENGTH_A,
    )


def _peak_intensity(peak):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        peak: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return _finite_float(
        (peak or {}).get("i_abs")
        or (peak or {}).get("absolute_intensity")
        or (peak or {}).get("relative_intensity")
        or (peak or {}).get("height")
        or (peak or {}).get("intensity")
        or 1.0
    ) or 0.0


def _compact_peak(peak):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        peak: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not peak:
        return None
    intensity = _peak_intensity(peak)
    return {
        "d_angstrom": round(_peak_d(peak), 5) if _peak_d(peak) is not None else None,
        "two_theta": _finite_float(peak.get("two_theta") or peak.get("2theta") or peak.get("center_2theta")),
        "intensity_abs": round(intensity, 4),
        "relative_intensity": round(_finite_float(peak.get("i_norm")) or intensity, 4),
        "fwhm": _finite_float(peak.get("fwhm")),
        "area": _finite_float(peak.get("area")),
        "tau": _finite_float(peak.get("tau")),
        "peak_index": peak.get("peak_index") or peak.get("index") or peak.get("peak_id"),
    }


def _strongest_peak(peaks, d_min, d_max):
    """
    Seleciona o pico mais intenso dentro de uma janela diagnóstica em Å.

    A intensidade é usada apenas para escolher a melhor observação dentro da faixa,
    não como prova mineralógica. A identificação continua dependendo da resposta
    N/G/C: expansão com glicol, colapso/perda térmica ou persistência dos picos
    basais e companheiros.

    Args:
        peaks: Lista de picos observados, cada um com d-spacing ou 2θ.
        d_min: Limite inferior da faixa diagnóstica em Å.
        d_max: Limite superior da faixa diagnóstica em Å.
    Returns:
        Pico mais intenso na faixa ou None quando a faixa não foi observada.
    Raises:
        Exception: Propaga erros apenas se a lista de entrada não seguir o contrato.
    """
    candidates = []
    for peak in peaks or []:
        d_value = _peak_d(peak)
        if d_value is None or d_value < d_min or d_value > d_max:
            continue
        candidates.append(peak)
    if not candidates:
        return None
    return max(candidates, key=_peak_intensity)


def _item_from_payload(item):
    """
    Normaliza um difratograma recebido da UI para o contrato interno N/G/C.

    O painel pode enviar picos globais, picos avançados e a varredura basal
    direcionada. Esta função junta essas fontes em uma lista única para que picos
    fracos em 14 Å, 7 Å, 5 Å, 4,72 Å ou 3,57 Å não desapareçam apenas por não
    estarem no top-N global. A origem `targeted_basal_peak_scan` é preservada para
    auditoria científica no payload.

    Args:
        item: Dicionário serializado de um difratograma selecionado no painel.
    Returns:
        Item normalizado com preparo, amostra-base, picos e candidatos auxiliares.
    Raises:
        Exception: Propaga erros inesperados de estruturas não serializáveis.
    """
    metadata = (item or {}).get("metadata") or {}
    preparation = _preparation_key(
        (item or {}).get("preparation")
        or (item or {}).get("treatment")
        or metadata.get("preparation")
        or metadata.get("treatment")
    )
    peaks = (
        (item or {}).get("peaks")
        or (item or {}).get("advanced_peaks")
        or (item or {}).get("detected_peaks")
        or metadata.get("peaks")
        or []
    )
    targeted_basal_peaks = [
        row for row in ((item or {}).get("targeted_basal_peaks") or metadata.get("targeted_basal_peaks") or [])
        if isinstance(row, dict)
    ]
    targeted_observed = []
    for row in targeted_basal_peaks:
        if row.get("status") not in {"strong", "weak", "shoulder"}:
            continue
        observed = row.get("observed_peak") if isinstance(row.get("observed_peak"), dict) else row
        if not observed:
            continue
        targeted_observed.append(
            {
                **observed,
                "d_angstrom": observed.get("d_angstrom") or row.get("observed_d_angstrom"),
                "two_theta": observed.get("two_theta") or row.get("observed_two_theta"),
                "i_abs": observed.get("intensity") or row.get("intensity"),
                "relative_intensity": observed.get("relative_intensity") or row.get("relative_intensity"),
                "fwhm": observed.get("fwhm") or row.get("fwhm"),
                "area": observed.get("area") or row.get("area"),
                "targeted_range_id": row.get("range_id"),
                "targeted_status": row.get("status"),
                "source": "targeted_basal_peak_scan",
            }
        )
    return {
        "id": (item or {}).get("id") or (item or {}).get("diffractogram_id"),
        "filename": (item or {}).get("filename") or metadata.get("original_filename"),
        "sample_base": _sample_base({**metadata, **(item or {})}),
        "preparation": preparation,
        "peaks": [peak for peak in peaks if isinstance(peak, dict)] + targeted_observed,
        "targeted_basal_peaks": targeted_basal_peaks,
        "mineral_candidates": [
            candidate for candidate in (item or {}).get("mineral_candidates") or []
            if isinstance(candidate, dict)
        ][:8],
        "metadata": {
            "d060": (item or {}).get("d060") or metadata.get("d060"),
            "morphology": (item or {}).get("morphology") or metadata.get("morphology") or [],
            "chemistry": (item or {}).get("chemistry") or metadata.get("chemistry") or {},
            "context": (item or {}).get("context") or metadata.get("context") or [],
        },
        "warnings": list((item or {}).get("warnings") or metadata.get("warnings") or []),
    }


def _compact_targeted_rows(items):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        items: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    rows = []
    for item in items or []:
        for row in (item or {}).get("targeted_basal_peaks") or []:
            if not isinstance(row, dict):
                continue
            rows.append(
                {
                    "filename": item.get("filename"),
                    "preparation": item.get("preparation"),
                    "range_id": row.get("range_id"),
                    "mineral": row.get("mineral"),
                    "label": row.get("label"),
                    "status": row.get("status"),
                    "expected_d_min": row.get("expected_d_min"),
                    "expected_d_max": row.get("expected_d_max"),
                    "observed_d_angstrom": row.get("observed_d_angstrom"),
                    "observed_two_theta": row.get("observed_two_theta"),
                    "intensity": row.get("intensity"),
                    "relative_intensity": row.get("relative_intensity"),
                    "local_contrast": row.get("local_contrast"),
                    "fwhm": row.get("fwhm"),
                    "area": row.get("area"),
                    "interpretation_policy": row.get("interpretation_policy"),
                }
            )
    return rows


def _script_peak_tables(items, limit=15):
    """Return script-like peak tables per preparation for panel display."""
    rows = []
    for item in sorted(items or [], key=lambda row: PREPARATION_ORDER.get(row.get("preparation"), 99)):
        peaks = []
        for peak in (item or {}).get("peaks") or []:
            if not isinstance(peak, dict):
                continue
            compact = _compact_peak(peak)
            if not compact or compact.get("d_angstrom") is None:
                continue
            source = peak.get("source") or peak.get("detection_method")
            peaks.append(
                {
                    **compact,
                    "source": source,
                    "targeted_range_id": peak.get("targeted_range_id"),
                    "targeted_status": peak.get("targeted_status"),
                }
            )
        peaks = sorted(
            peaks,
            key=lambda peak: (
                _finite_float(peak.get("two_theta")) if _finite_float(peak.get("two_theta")) is not None else 999.0,
                str(peak.get("peak_index") or ""),
            ),
        )[:limit]
        rows.append(
            {
                "preparation": item.get("preparation"),
                "filename": item.get("filename"),
                "peak_count": len(peaks),
                "peaks": peaks,
            }
        )
    return rows


def _script_report(sample_base, interval_minerals, interval_diagnostics, items):
    """Expose the batch-script style output in the versioned workflow payload."""
    diagnostics = []
    for row in interval_diagnostics or []:
        if not isinstance(row, dict):
            continue
        diagnostics.append(
            {
                "mineral": row.get("mineral"),
                "rule": row.get("rule"),
                "message": row.get("message"),
                "observations": row.get("observations") or {},
            }
        )
    return {
        "title": "Diagnostico comparativo N/G/C",
        "sample_base": sample_base,
        "detected_minerals": interval_minerals or [],
        "diagnostics": diagnostics,
        "peak_tables": _script_peak_tables(items),
        "policy": POLICY,
        "policy_scope": "rule_based_confirmation_within_argiloteca_ngc_engine",
    }


def _range_peak(item, range_key):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        item: Valor de entrada consumido por esta etapa do fluxo.
        range_key: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    d_min, d_max = DIAGNOSTIC_RANGES[range_key]
    return _compact_peak(_strongest_peak(item.get("peaks") or [], d_min, d_max))


def _interval_peak_intensity(peaks, d_min, d_max):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        peaks: Valor de entrada consumido por esta etapa do fluxo.
        d_min: Valor de entrada consumido por esta etapa do fluxo.
        d_max: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    values = []
    for peak in peaks or []:
        d_value = _peak_d(peak)
        if d_value is None or d_value < d_min or d_value > d_max:
            continue
        values.append(_peak_intensity(peak))
    return max(values) if values else 0.0


def _interval_observation(item, range_key):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        item: Valor de entrada consumido por esta etapa do fluxo.
        range_key: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    d_min, d_max = SCRIPT_INTERVAL_RANGES[range_key]
    peak = _strongest_peak((item or {}).get("peaks") or [], d_min, d_max)
    compact = _compact_peak(peak)
    return {
        "range_key": range_key,
        "expected_d_min": d_min,
        "expected_d_max": d_max,
        "intensity_abs": round(_interval_peak_intensity((item or {}).get("peaks") or [], d_min, d_max), 6),
        "observed_peak": compact,
    }


def _diagnostic_observation(item, range_key):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        item: Valor de entrada consumido por esta etapa do fluxo.
        range_key: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    d_min, d_max = DIAGNOSTIC_RANGES[range_key]
    peak = _strongest_peak((item or {}).get("peaks") or [], d_min, d_max)
    compact = _compact_peak(peak)
    return {
        "range_key": range_key,
        "expected_d_min": d_min,
        "expected_d_max": d_max,
        "intensity_abs": round(_interval_peak_intensity((item or {}).get("peaks") or [], d_min, d_max), 6),
        "observed_peak": compact,
    }


def _companion_peak_set(natural, glycolated, calcined):
    """
    Retorna reflexoes companheiras usadas para evitar pico isolado.

    Brindley & Brown, 1980:
        o objeto "kaolinite" combina 7 A em N/G/C com o pico companheiro 3.57 A.
        Esses campos alimentam _ngc_behavior, _mixed_layer_warnings e os cards
        do painel, mas permanecem auxiliares porque 7 A sobrepoe clorita,
        serpentina, dickita/nacrita e haloisita.
    """
    representative = natural or glycolated or calcined or {}
    return {
        "smectite": {
            "natural_12_15a": _interval_observation(natural, "smectite_n"),
            "glycolated_17a": _interval_observation(glycolated, "smectite_g"),
            "calcined_10a": _interval_observation(calcined, "smectite_c"),
        },
        "illite": {
            "stable_10a_n": _interval_observation(natural, "illite_10a_n"),
            "stable_10a_g": _interval_observation(glycolated, "illite_10a_g"),
            "stable_10a_c": _interval_observation(calcined, "illite_10a_c"),
            "companion_5a": _diagnostic_observation(representative, "illite_5a"),
            "companion_3_33a": _diagnostic_observation(representative, "illite_3_33a"),
        },
        "kaolinite": {
            "natural_7a": _interval_observation(natural, "kaolinite_7a_n"),
            "glycolated_7a": _interval_observation(glycolated, "kaolinite_7a_g"),
            "calcined_7a": _interval_observation(calcined, "kaolinite_7a_c_check"),
            "companion_3_57a": _diagnostic_observation(representative, "kaolinite_3_57a"),
        },
        "chlorite": {
            "natural_14a": _interval_observation(natural, "chlorite_14a_n"),
            "glycolated_14a": _interval_observation(glycolated, "chlorite_14a_g"),
            "calcined_14a": _interval_observation(calcined, "chlorite_14a_c"),
            "companion_7a": _diagnostic_observation(representative, "chlorite_7a"),
            "companion_4_72a": _diagnostic_observation(representative, "chlorite_4_72a"),
            "companion_3_53a": _diagnostic_observation(representative, "chlorite_3_5a"),
        },
        "quartz_auxiliary": {
            "quartz_101": _interval_observation(representative, "quartz_101"),
            "quartz_100": _interval_observation(representative, "quartz_100"),
        },
    }


def _peak_present(observation):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        observation: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return _observation_intensity(observation) > 0


def _ngc_behavior(companion_peaks):
    """Summarize N/G/C response for the mineral rules shown in the panel."""
    smectite = companion_peaks.get("smectite") or {}
    illite = companion_peaks.get("illite") or {}
    kaolinite = companion_peaks.get("kaolinite") or {}
    chlorite = companion_peaks.get("chlorite") or {}
    return {
        "smectite_expansion": {
            "status": "complete" if all(_peak_present(smectite.get(key)) for key in ("natural_12_15a", "glycolated_17a", "calcined_10a")) else "partial",
            "message": "Expansao N->G e colapso em C avaliam esmectita/interestratificados.",
        },
        "illite_stability": {
            "status": "stable" if all(_peak_present(illite.get(key)) for key in ("stable_10a_n", "stable_10a_g", "stable_10a_c")) else "partial",
            "message": "Persistencia de ~10 A em N/G/C favorece ilita/mica.",
        },
        "kaolinite_heating_loss": {
            "status": "destroyed" if _peak_present(kaolinite.get("natural_7a")) and not _peak_present(kaolinite.get("calcined_7a")) else "partial_or_persistent",
            "message": "Perda forte de ~7 A em C separa caulinita de clorita.",
        },
        "chlorite_heating_resistance": {
            "status": "preserved" if _peak_present(chlorite.get("natural_14a")) and _peak_present(chlorite.get("calcined_14a")) else "partial",
            "message": "Persistencia de ~14 A em C favorece clorita; colapso sugere vermiculita/interestratificado.",
        },
    }


def _mixed_layer_warnings(companion_peaks):
    """
    Gera avisos para respostas que devem ser revisadas como misturas.

    Aplicacao de Lanson & Bouchet 1995:
        respostas expansivas parciais, picos sobrepostos e comportamento termico
        incompleto sao tratados como sinais de bandas complexas, defeitos ou
        interestratificacao. A funcao nao classifica mineral; ela preserva o
        alerta no payload para impedir conclusao por tabela simples de picos.
    """
    warnings = []
    smectite = companion_peaks.get("smectite") or {}
    kaolinite = companion_peaks.get("kaolinite") or {}
    chlorite = companion_peaks.get("chlorite") or {}
    illite = companion_peaks.get("illite") or {}
    quartz = companion_peaks.get("quartz_auxiliary") or {}
    smectite_hits = sum(1 for key in ("natural_12_15a", "glycolated_17a", "calcined_10a") if _peak_present(smectite.get(key)))
    if 0 < smectite_hits < 3:
        warnings.append("Resposta expansiva parcial sugere mistura ou interestratificado; revisar ombros, largura e deslocamento dos picos.")
    if _peak_present(kaolinite.get("natural_7a")) and _peak_present(kaolinite.get("calcined_7a")) and _peak_present(chlorite.get("natural_14a")):
        warnings.append("Pico ~7 A persistente com ~14 A associado sugere clorita ou mistura caulinita+clorita; nao tratar 7 A isolado como caulinita.")
    if _peak_present(chlorite.get("natural_14a")) and not _peak_present(chlorite.get("calcined_14a")):
        warnings.append("Pico 14-14,5 A sem resistencia clara ao aquecimento pode indicar vermiculita/interestratificado; considerar saturacao Mg/K ou glicerol.")
    if _peak_present(illite.get("companion_3_33a")) and _peak_present(quartz.get("quartz_101")):
        warnings.append("Reflexao ~3,33 A de ilita/mica pode estar sobreposta ao quartzo ~3,34 A; nao usar esse pico isoladamente.")
    return warnings


def _script_interval_diagnostics(natural, glycolated, calcined):
    """
    Reproduz a lógica do script de bancada para diagnóstico comparativo N/G/C.

    Esta rotina gera mensagens compactas semelhantes às impressas no script usado
    pelo geólogo: ilita por 10 Å estável, esmectita por expansão N→G e colapso em
    C, caulinita por perda do 7 Å na calcinação, clorita por 14 Å preservado e
    quartzo como referência auxiliar. O resultado alimenta a interface, mas
    permanece classificado como triagem auxiliar.

    Args:
        natural: Item normalizado da preparação natural/normal.
        glycolated: Item normalizado da preparação glicolada.
        calcined: Item normalizado da preparação calcinada/aquecida.
    Returns:
        Tupla com minerais triados e diagnósticos textuais com observações.
    Raises:
        Exception: Propaga erros inesperados de estrutura de pico inválida.
    """
    peaks_n = (natural or {}).get("peaks") or []
    peaks_g = (glycolated or {}).get("peaks") or []
    peaks_c = (calcined or {}).get("peaks") or []
    diagnostics = []
    minerals = []

    int_n_10 = _interval_peak_intensity(peaks_n, *SCRIPT_INTERVAL_RANGES["illite_10a_n"])
    int_g_10 = _interval_peak_intensity(peaks_g, *SCRIPT_INTERVAL_RANGES["illite_10a_g"])
    int_c_10 = _interval_peak_intensity(peaks_c, *SCRIPT_INTERVAL_RANGES["illite_10a_c"])
    if int_n_10 > 0 and int_g_10 > 0 and int_c_10 > 0:
        minerals.append("Ilita")
        diagnostics.append({
            "mineral": "Ilita",
            "rule": "stable_10a_ngc",
            "message": "ILITA Detectada: Pico estavel entre %.1f-%.1f A (Int. N: %.0f cps)." % (
                SCRIPT_INTERVAL_RANGES["illite_10a"][0],
                SCRIPT_INTERVAL_RANGES["illite_10a"][1],
                int_n_10,
            ),
            "observations": {
                "natural": _interval_observation(natural, "illite_10a_n"),
                "glycolated": _interval_observation(glycolated, "illite_10a_g"),
                "calcined": _interval_observation(calcined, "illite_10a_c"),
            },
        })

    int_n_es = _interval_peak_intensity(peaks_n, *SCRIPT_INTERVAL_RANGES["smectite_n"])
    int_g_es = _interval_peak_intensity(peaks_g, *SCRIPT_INTERVAL_RANGES["smectite_g"])
    int_c_es = _interval_peak_intensity(peaks_c, *SCRIPT_INTERVAL_RANGES["smectite_c"])
    if int_n_es > 0 and int_g_es > 0 and int_c_es > 0:
        minerals.append("Esmectita")
        diagnostics.append({
            "mineral": "Esmectita",
            "rule": "glycol_expansion_calcined_collapse",
            "message": "ESMECTITA Detectada: Expansao p/ %.1f-%.1f A no Glicol e colapso na Calcinada." % (
                SCRIPT_INTERVAL_RANGES["smectite_g"][0],
                SCRIPT_INTERVAL_RANGES["smectite_g"][1],
            ),
            "observations": {
                "natural": _interval_observation(natural, "smectite_n"),
                "glycolated": _interval_observation(glycolated, "smectite_g"),
                "calcined": _interval_observation(calcined, "smectite_c"),
            },
        })

    # Brindley & Brown, 1980 aplicado na rotina legada: 7 A em N/G e perda forte
    # em C favorecem grupo da caulinita. A regra usa intensidade relativa para
    # representar destruicao/reducao termica e nao confirma especie.
    int_n_7 = _interval_peak_intensity(peaks_n, *SCRIPT_INTERVAL_RANGES["kaolinite_7a_n"])
    int_g_7 = _interval_peak_intensity(peaks_g, *SCRIPT_INTERVAL_RANGES["kaolinite_7a_g"])
    int_c_7 = _interval_peak_intensity(peaks_c, *SCRIPT_INTERVAL_RANGES["kaolinite_7a_c_check"])
    if int_n_7 > 0 and int_g_7 > 0 and int_c_7 < (0.1 * int_n_7):
        minerals.append("Caulinita")
        diagnostics.append({
            "mineral": "Caulinita",
            "rule": "7a_destroyed_by_calcination",
            "message": "CAULINITA Detectada: Pico entre %.1f-%.1f A destruido na Calcinacao." % (
                SCRIPT_INTERVAL_RANGES["kaolinite_7a"][0],
                SCRIPT_INTERVAL_RANGES["kaolinite_7a"][1],
            ),
            "observations": {
                "natural": _interval_observation(natural, "kaolinite_7a_n"),
                "glycolated": _interval_observation(glycolated, "kaolinite_7a_g"),
                "calcined": _interval_observation(calcined, "kaolinite_7a_c_check"),
            },
        })

    int_n_cl_14 = _interval_peak_intensity(peaks_n, *SCRIPT_INTERVAL_RANGES["chlorite_14a_n"])
    int_c_cl_14 = _interval_peak_intensity(peaks_c, *SCRIPT_INTERVAL_RANGES["chlorite_14a_c"])
    if int_n_cl_14 > 0 and int_c_cl_14 > 0:
        minerals.append("Clorita")
        status = "intensificado" if int_c_cl_14 > int_n_cl_14 else "preservado"
        diagnostics.append({
            "mineral": "Clorita",
            "rule": "14a_preserved_or_intensified_calcined",
            "message": "CLORITA Detectada: Pico ~14.2 A %s na Calcinada (Int C: %.0f cps)." % (status, int_c_cl_14),
            "observations": {
                "natural": _interval_observation(natural, "chlorite_14a_n"),
                "glycolated": _interval_observation(glycolated, "chlorite_14a_g"),
                "calcined": _interval_observation(calcined, "chlorite_14a_c"),
            },
        })

    int_n_qz_101 = _interval_peak_intensity(peaks_n, *SCRIPT_INTERVAL_RANGES["quartz_101_n"])
    int_g_qz_101 = _interval_peak_intensity(peaks_g, *SCRIPT_INTERVAL_RANGES["quartz_101_g"])
    int_c_qz_101 = _interval_peak_intensity(peaks_c, *SCRIPT_INTERVAL_RANGES["quartz_101_c"])
    int_n_qz_100 = _interval_peak_intensity(peaks_n, *SCRIPT_INTERVAL_RANGES["quartz_100"])
    if int_n_qz_101 > 0 and int_g_qz_101 > 0 and int_c_qz_101 > 0:
        minerals.append("Quartzo")
        message = "QUARTZO Detectado: Pico principal da ordem 101 imutavel nos 3 tratamentos (Int. N: %.0f cps)." % int_n_qz_101
        if int_n_qz_100 > 0:
            message += " Confirmado por pico secundario (100) em ~4.32 A."
        diagnostics.append({
            "mineral": "Quartzo",
            "rule": "stable_quartz_101_ngc",
            "message": message,
            "observations": {
                "natural_101": _interval_observation(natural, "quartz_101_n"),
                "glycolated_101": _interval_observation(glycolated, "quartz_101_g"),
                "calcined_101": _interval_observation(calcined, "quartz_101_c"),
                "natural_100": _interval_observation(natural, "quartz_100"),
            },
        })

    if not diagnostics:
        diagnostics.append({
            "mineral": None,
            "rule": "inconclusive_interval_screening",
            "message": "Inconclusivo para minerais primarios avaliados ou picos sobrepostos/ausentes.",
            "observations": {},
        })
    return sorted(set(minerals)), diagnostics


def _candidate_hint(items, *terms):
    """Return True when curated/classifier candidates already suggest a target."""
    targets = [str(term or "").casefold() for term in terms if str(term or "").strip()]
    for item in items or []:
        for candidate in (item or {}).get("mineral_candidates") or []:
            text = " ".join(
                str(candidate.get(key) or "")
                for key in ("mineral", "argilomineral_id", "group", "family")
            ).casefold()
            if any(term in text for term in targets):
                return True
    return False


def _observation_intensity(observation):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        observation: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not isinstance(observation, dict):
        return 0.0
    return _finite_float(observation.get("intensity_abs")) or 0.0


def _screening_entry(mineral, status, score, message, observations, warnings=None, companion_peaks=None, behavior=None):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        mineral: Valor de entrada consumido por esta etapa do fluxo.
        status: Valor de entrada consumido por esta etapa do fluxo.
        score: Valor de entrada consumido por esta etapa do fluxo.
        message: Valor de entrada consumido por esta etapa do fluxo.
        observations: Valor de entrada consumido por esta etapa do fluxo.
        warnings: Valor de entrada consumido por esta etapa do fluxo.
        companion_peaks: Valor de entrada consumido por esta etapa do fluxo.
        behavior: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return {
        "mineral": mineral,
        "status": status,
        "score": round(min(1.0, max(0.0, score)), 4),
        "message": message,
        "observations": observations,
        "companion_peaks": companion_peaks or {},
        "ngc_behavior": behavior or {},
        "warnings": [warning for warning in warnings or [] if warning],
        "interpretation_policy": POLICY,
        "policy_scope": "rule_based_confirmation_within_argiloteca_ngc_engine",
    }


def _targeted_clay_screening(natural, glycolated, calcined, all_items, companion_peaks=None, behavior=None, mixed_warnings=None):
    """
    Triar argilominerais-alvo combinando faixas basais e comportamento N/G/C.

    A função evita classificar por pico isolado. Esmectita exige padrão de
    expansão/colapso, ilita depende de 10 Å persistente, caulinita depende da perda
    do 7 Å no aquecimento e clorita depende do 14 Å preservado com picos
    companheiros quando disponíveis. Casos incompletos retornam `possible` ou
    `mixed_layer_suspected`, nunca confirmação automática.

    Args:
        natural: Item normalizado da preparação natural.
        glycolated: Item normalizado da preparação glicolada.
        calcined: Item normalizado da preparação calcinada.
        all_items: Lista original de itens usada para ler candidatos auxiliares.
        companion_peaks: Picos companheiros já calculados, se houver.
        behavior: Resumo de resposta N/G/C já calculado, se houver.
        mixed_warnings: Avisos de mistura/interestratificado já calculados.
    Returns:
        Lista de entradas de triagem com mineral, status, score e evidências.
    Raises:
        Exception: Propaga erros estruturais do payload recebido.
    """
    companion_peaks = companion_peaks or _companion_peak_set(natural, glycolated, calcined)
    behavior = behavior or _ngc_behavior(companion_peaks)
    mixed_warnings = mixed_warnings or _mixed_layer_warnings(companion_peaks)
    smectite = companion_peaks.get("smectite") or {}
    smectite_hits = sum(1 for key in ("natural_12_15a", "glycolated_17a", "calcined_10a") if _peak_present(smectite.get(key)))
    if smectite_hits == 3:
        smectite_status = "detected"
        smectite_message = "Esmectita provavel: pico 13,46-16,86 A em N expande para 16,06-18,31 A em G e colapsa para 9,65-10,37 A em C."
        smectite_score = 0.88
    elif smectite_hits > 0:
        smectite_status = "mixed_layer_suspected" if smectite_hits == 2 else "possible"
        smectite_message = "Esmectita/interestratificado possivel: resposta expansiva ou colapso incompleto requer revisao manual."
        smectite_score = 0.48 if smectite_hits == 1 else 0.64
    else:
        smectite_status = "not_observed"
        smectite_message = "Esmectita nao observada pelos intervalos expansivos principais."
        smectite_score = 0.0

    n_10 = _interval_observation(natural, "illite_10a_n")
    g_10 = _interval_observation(glycolated, "illite_10a_g")
    c_10 = _interval_observation(calcined, "illite_10a_c")
    illite_hits = sum(1 for row in (n_10, g_10, c_10) if _observation_intensity(row) > 0)
    illite_hint = _candidate_hint(all_items, "illite", "ilita", "mica")
    if illite_hits == 3:
        illite_status = "detected"
        illite_message = "Ilita/mica sugerida: pico ~10 A estavel nos tratamentos N/G/C."
    elif illite_hits > 0 or illite_hint:
        illite_status = "possible"
        illite_message = "Ilita/mica possivel: ha pico/candidato ~10 A, mas a estabilidade N/G/C esta incompleta."
    else:
        illite_status = "not_observed"
        illite_message = "Ilita/mica nao observada pelos intervalos principais."

    n_7 = _interval_observation(natural, "kaolinite_7a_n")
    g_7 = _interval_observation(glycolated, "kaolinite_7a_g")
    c_7 = _interval_observation(calcined, "kaolinite_7a_c_check")
    n_7_i = _observation_intensity(n_7)
    g_7_i = _observation_intensity(g_7)
    c_7_i = _observation_intensity(c_7)
    kaolinite_hint = _candidate_hint(all_items, "kaolinite", "caulinita", "kaolin")
    if n_7_i > 0 and g_7_i > 0 and c_7_i < (0.1 * n_7_i):
        kaolinite_status = "detected"
        kaolinite_message = "Caulinita sugerida: pico 7 A presente em N/G e destruido ou muito reduzido na calcinacao."
    elif n_7_i > 0 or g_7_i > 0 or kaolinite_hint:
        kaolinite_status = "possible"
        kaolinite_message = "Caulinita possivel: ha evidencia em ~7 A, mas a destruicao na calcinacao nao fechou."
    else:
        kaolinite_status = "not_observed"
        kaolinite_message = "Caulinita nao observada pelos intervalos principais."

    n_cl14 = _interval_observation(natural, "chlorite_14a_n")
    c_cl14 = _interval_observation(calcined, "chlorite_14a_c")
    n_cl14_i = _observation_intensity(n_cl14)
    c_cl14_i = _observation_intensity(c_cl14)
    n_35 = _diagnostic_observation(natural, "chlorite_3_5a") if natural else {}
    n_35_i = _observation_intensity(n_35)
    chlorite_hint = _candidate_hint(all_items, "chlorite", "clorita", "clinochlore", "chamosite")
    chlorite_warnings = ["Clorita e caulinita podem se sobrepor em ~7 A; use 14 A, 3,5 A e comportamento na calcinacao."]
    if n_cl14_i > 0 and c_cl14_i > 0:
        chlorite_status = "detected"
        chlorite_state = "intensificado" if c_cl14_i > n_cl14_i else "preservado"
        chlorite_message = "Clorita sugerida: pico basal ~14 A %s na calcinada." % chlorite_state
        chlorite_score = 0.86
    elif chlorite_hint and (n_cl14_i > 0 or c_cl14_i > 0 or n_35_i > 0):
        chlorite_status = "possible"
        chlorite_message = "Clorita possivel: candidato curatorial/classificador e reflexoes auxiliares presentes, mas 14 A N/C nao fechou."
        chlorite_score = 0.62
    elif n_cl14_i > 0 or c_cl14_i > 0 or n_35_i > 0 or chlorite_hint:
        chlorite_status = "possible"
        chlorite_message = "Clorita possivel: ha sinal parcial em faixas diagnosticas, revisar picos fracos/sobrepostos."
        chlorite_score = 0.48
    else:
        chlorite_status = "not_observed"
        chlorite_message = "Clorita nao observada pelos intervalos principais."
        chlorite_score = 0.0

    if chlorite_status == "detected" and smectite_status == "detected":
        smectite_status = "mixed_layer_suspected"
        smectite_score = min(smectite_score, 0.62)
        smectite_message = (
            "Resposta expansiva coexistente com clorita preservada; tratar como mistura/interestratificado possivel e revisar manualmente."
        )
        mixed_warnings = list(mixed_warnings) + [
            "Evidencia simultanea de expansao e clorita preservada nao deve ser lida como esmectita pura."
        ]

    return [
        _screening_entry(
            "Esmectita",
            smectite_status,
            smectite_score,
            smectite_message,
            smectite,
            mixed_warnings if smectite_status != "not_observed" else [],
            companion_peaks=smectite,
            behavior=behavior.get("smectite_expansion"),
        ),
        _screening_entry(
            "Clorita",
            chlorite_status,
            chlorite_score,
            chlorite_message,
            {
                "natural_14a": n_cl14,
                "calcined_14a": c_cl14,
                "natural_3_5a": n_35,
            },
            chlorite_warnings,
            companion_peaks=companion_peaks.get("chlorite"),
            behavior=behavior.get("chlorite_heating_resistance"),
        ),
        _screening_entry(
            "Caulinita",
            kaolinite_status,
            0.82 if kaolinite_status == "detected" else (0.45 if kaolinite_status == "possible" else 0.0),
            kaolinite_message,
            {
                "natural_7a": n_7,
                "glycolated_7a": g_7,
                "calcined_7a": c_7,
            },
            ["Pico 7 A isolado nao separa caulinita de clorita sem aquecimento e reflexoes associadas."],
            companion_peaks=companion_peaks.get("kaolinite"),
            behavior=behavior.get("kaolinite_heating_loss"),
        ),
        _screening_entry(
            "Ilita",
            illite_status,
            0.78 if illite_status == "detected" else (0.42 if illite_status == "possible" else 0.0),
            illite_message,
            {
                "natural_10a": n_10,
                "glycolated_10a": g_10,
                "calcined_10a": c_10,
            },
            ["Pico 10 A tambem pode representar mica; usar reflexoes associadas e contexto geologico."],
            companion_peaks=companion_peaks.get("illite"),
            behavior=behavior.get("illite_stability"),
        ),
    ]


def _evidence(label, item, range_key):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        label: Valor de entrada consumido por esta etapa do fluxo.
        item: Valor de entrada consumido por esta etapa do fluxo.
        range_key: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    peak = _range_peak(item, range_key)
    if not peak:
        return None
    d_min, d_max = DIAGNOSTIC_RANGES[range_key]
    return {
        "label": label,
        "preparation": item.get("preparation"),
        "filename": item.get("filename"),
        "range_key": range_key,
        "expected_d_min": d_min,
        "expected_d_max": d_max,
        "observed_peak": peak,
    }


def _best_by_preparation(items):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        items: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    by_prep = {}
    duplicates = defaultdict(int)
    for item in sorted(items, key=lambda row: PREPARATION_ORDER.get(row.get("preparation"), 99)):
        prep = item.get("preparation")
        duplicates[prep] += 1
        by_prep.setdefault(prep, item)
    return by_prep, {key: count for key, count in duplicates.items() if count > 1}


def _confidence(score, complete_trio):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        score: Valor de entrada consumido por esta etapa do fluxo.
        complete_trio: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if score >= 0.78 and complete_trio:
        return "alta"
    if score >= 0.58:
        return "media"
    if score >= 0.35:
        return "baixa/media"
    return "baixa"


def _candidate(mineral, score, evidences, warnings, complete_trio):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        mineral: Valor de entrada consumido por esta etapa do fluxo.
        score: Valor de entrada consumido por esta etapa do fluxo.
        evidences: Valor de entrada consumido por esta etapa do fluxo.
        warnings: Valor de entrada consumido por esta etapa do fluxo.
        complete_trio: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    score = round(min(1.0, max(0.0, score)), 4)
    return {
        "mineral_candidate": mineral,
        "score": score,
        "confidence": _confidence(score, complete_trio),
        "evidence": [row for row in evidences if row],
        "warnings": [row for row in warnings if row],
        "interpretation_policy": POLICY,
        "policy_scope": "rule_based_confirmation_within_argiloteca_ngc_engine",
    }


@lru_cache(maxsize=1)
def load_diagnostic_rules_ngc():
    """Load versioned N/G/C diagnostic rules kept separate from WebMineral."""
    try:
        return json.loads(DIAGNOSTIC_RULES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "version": "argiloteca.drx.ngc.diagnostic_rules.unavailable",
            "interpretation_policy": POLICY,
            "policy_scope": "rule_based_confirmation_within_argiloteca_ngc_engine",
            "rules": [],
        }


@lru_cache(maxsize=1)
def load_webmineral_vocabulary_summary():
    """Load compact WebMineral vocabulary metadata for family/category context."""
    for path in WEBMINERAL_MANIFEST_CANDIDATES:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        records = payload.get("records") if isinstance(payload, dict) else payload
        if not isinstance(records, list):
            continue
        by_family = defaultdict(int)
        by_category = defaultdict(int)
        ids_by_family = defaultdict(list)
        for row in records:
            if not isinstance(row, dict):
                continue
            family = row.get("family") or (row.get("props") or {}).get("family") or "unknown"
            category = row.get("category") or (row.get("props") or {}).get("category") or "unknown"
            mineral_id = row.get("id")
            by_family[family] += 1
            by_category[category] += 1
            if mineral_id and len(ids_by_family[family]) < 20:
                ids_by_family[family].append(mineral_id)
        return {
            "available": True,
            "path": str(path),
            "record_count": len(records),
            "families": dict(by_family),
            "categories": dict(by_category),
            "sample_ids_by_family": {key: value for key, value in ids_by_family.items()},
            "usage_policy": "WebMineral d/I e vocabulario sao evidencias auxiliares; regras N/G/C governam a interpretacao.",
        }
    return {
        "available": False,
        "path": None,
        "record_count": 0,
        "families": {},
        "categories": {},
        "usage_policy": "Vocabulario WebMineral local nao localizado; interpretacao usa somente regras N/G/C.",
    }


def _obs_peak(observation):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        observation: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if not isinstance(observation, dict):
        return None
    return observation.get("observed_peak") if isinstance(observation.get("observed_peak"), dict) else None


def _obs_d(observation):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        observation: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    peak = _obs_peak(observation)
    return _finite_float((peak or {}).get("d_angstrom"))


def _format_peak_text(prefix, observation):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        prefix: Valor de entrada consumido por esta etapa do fluxo.
        observation: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    peak = _obs_peak(observation)
    if not peak:
        return None
    d_value = _finite_float(peak.get("d_angstrom"))
    two_theta = _finite_float(peak.get("two_theta"))
    intensity = _finite_float(peak.get("intensity_abs") or peak.get("relative_intensity"))
    bits = [prefix]
    if d_value is not None:
        bits.append("d %.2f A" % d_value)
    if two_theta is not None:
        bits.append("2θ %.2f°" % two_theta)
    if intensity is not None:
        bits.append("int. %.1f" % intensity)
    return " / ".join(bits)


def _normalise_score(score):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        score: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return round(min(1.0, max(0.0, score)), 4)


def _candidate_status(score, critical_ok=True, provisional=False, ambiguous=False):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        score: Valor de entrada consumido por esta etapa do fluxo.
        critical_ok: Valor de entrada consumido por esta etapa do fluxo.
        provisional: Valor de entrada consumido por esta etapa do fluxo.
        ambiguous: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    if ambiguous:
        return "ambíguo"
    if provisional:
        return "provisório" if score >= 0.4 else "possível"
    if score >= 0.80 and critical_ok:
        return "provável"
    if score >= 0.60:
        return "provável"
    if score >= 0.40:
        return "possível"
    return "descartado"


def _candidate_interpretation(
    candidate_id,
    family,
    label,
    level,
    score,
    status,
    evidence_for=None,
    evidence_against=None,
    matched_peaks=None,
    missing_evidence=None,
    overlaps=None,
    recommended_tests=None,
    explanation=None,
    warnings=None,
):
    """
    Monta um candidato mineralógico no contrato público da API N/G/C.

    O objeto separa evidências a favor, contra, picos casados, lacunas,
    sobreposições e testes adicionais. Essa separação deixa claro para a UI que o
    resultado é uma hipótese técnica auditável, não uma identificação mineralógica
    confirmatória.

    Args:
        candidate_id: Identificador estável da hipótese ou família mineral.
        family: Família mineralógica usada para aplicar regras diagnósticas.
        label: Nome em português apresentado ao usuário.
        level: Nível de resolução, como grupo, série ou interestratificado.
        score: Pontuação auxiliar entre 0 e 1.
        status: Status textual cauteloso, por exemplo provável ou possível.
        evidence_for: Evidências que sustentam a hipótese.
        evidence_against: Conflitos ou sinais contrários.
        matched_peaks: Picos observados usados no raciocínio.
        missing_evidence: Preparações, picos ou metadados ausentes.
        overlaps: Sobreposições mineralógicas conhecidas.
        recommended_tests: Testes adicionais recomendados.
        explanation: Explicação curta em português.
        warnings: Avisos científicos e operacionais.
    Returns:
        Dicionário serializável para API e frontend.
    Raises:
        Exception: Propaga erros inesperados de serialização dos campos.
    """
    return {
        "candidateId": candidate_id,
        "family": family,
        "candidateLabelPt": label,
        "level": level,
        "score": _normalise_score(score),
        "status": status,
        "evidenceFor": [row for row in evidence_for or [] if row],
        "evidenceAgainst": [row for row in evidence_against or [] if row],
        "matchedPeaks": [row for row in matched_peaks or [] if row],
        "missingEvidence": [row for row in missing_evidence or [] if row],
        "overlaps": [row for row in overlaps or [] if row],
        "recommendedAdditionalTests": [row for row in recommended_tests or [] if row],
        "explanationPt": explanation or "",
        "warnings": [row for row in warnings or [] if row],
        "interpretationPolicy": POLICY,
        "policyScope": "rule_based_confirmation_within_argiloteca_ngc_engine",
    }


def _observations_for_clay_rules(natural, glycolated, calcined):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        natural: Valor de entrada consumido por esta etapa do fluxo.
        glycolated: Valor de entrada consumido por esta etapa do fluxo.
        calcined: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return {
        "kaolin_n_7": _interval_observation(natural, "kaolinite_7a_n"),
        "kaolin_g_7": _interval_observation(glycolated, "kaolinite_7a_g"),
        "kaolin_c_7": _interval_observation(calcined, "kaolinite_7a_c_check"),
        "kaolin_3_57": _diagnostic_observation(natural or glycolated or calcined or {}, "kaolinite_3_57a"),
        "chlorite_n_14": _interval_observation(natural, "chlorite_14a_n"),
        "chlorite_g_14": _interval_observation(glycolated, "chlorite_14a_g"),
        "chlorite_c_14": _interval_observation(calcined, "chlorite_14a_c"),
        "chlorite_7": _diagnostic_observation(natural or glycolated or calcined or {}, "chlorite_7a"),
        "chlorite_4_72": _diagnostic_observation(natural or glycolated or calcined or {}, "chlorite_4_72a"),
        "chlorite_3_53": _diagnostic_observation(natural or glycolated or calcined or {}, "chlorite_3_5a"),
        "smectite_n": _interval_observation(natural, "smectite_n"),
        "smectite_g": _interval_observation(glycolated, "smectite_g"),
        "smectite_c": _interval_observation(calcined, "smectite_c"),
        "illite_n_10": _interval_observation(natural, "illite_10a_n"),
        "illite_g_10": _interval_observation(glycolated, "illite_10a_g"),
        "illite_c_10": _interval_observation(calcined, "illite_10a_c"),
        "illite_5": _diagnostic_observation(natural or glycolated or calcined or {}, "illite_5a"),
        "illite_3_33": _diagnostic_observation(natural or glycolated or calcined or {}, "illite_3_33a"),
        "quartz_101": (
            _interval_observation(natural, "quartz_101_n")
            or _interval_observation(glycolated, "quartz_101_g")
            or _interval_observation(calcined, "quartz_101_c")
        ),
    }


def _matched_peak(label, observation, preparation=None, rule_id=None):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        label: Valor de entrada consumido por esta etapa do fluxo.
        observation: Valor de entrada consumido por esta etapa do fluxo.
        preparation: Valor de entrada consumido por esta etapa do fluxo.
        rule_id: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    peak = _obs_peak(observation)
    if not peak:
        return None
    return {
        "label": label,
        "ruleId": rule_id,
        "preparation": preparation,
        "d_A": _finite_float(peak.get("d_angstrom")),
        "twoTheta_deg": _finite_float(peak.get("two_theta")),
        "intensity": _finite_float(peak.get("intensity_abs")),
        "relative_intensity": _finite_float(peak.get("relative_intensity")),
        "fwhm": _finite_float(peak.get("fwhm")),
    }


def interpret_clay_minerals_ngc(sample_id, peaks_by_preparation, wavelength_a=DEFAULT_WAVELENGTH_A, metadata=None, vocabulary=None, diagnostic_rules=None, options=None):
    """
    Interpreta argilominerais a partir do comportamento entre N, G e C.

    O vocabulário WebMineral fornece família, categoria e linhas d/I auxiliares,
    mas o score principal vem de regras de preparação: expansão por glicol,
    colapso/perda por aquecimento e persistência de reflexões basais. Por isso o
    retorno limita a resolução a grupo/família quando N/G/C não distingue espécie,
    como em esmectitas, cloritas e micas.

    Args:
        sample_id: Identificador da amostra ou grupo N/G/C.
        peaks_by_preparation: Picos separados por preparação natural, glicolada e calcinada.
        wavelength_a: Comprimento de onda usado para conversão 2θ→d quando necessário.
        metadata: Metadados opcionais, como temperatura de calcinação.
        vocabulary: Resumo opcional do vocabulário WebMineral local.
        diagnostic_rules: Regras N/G/C versionadas carregadas do JSON.
        options: Opções futuras de tolerância e política de interpretação.
    Returns:
        Payload JSON com candidatos, avisos globais, picos casados e política.
    Raises:
        Exception: Propaga erros inesperados de estruturas de entrada inválidas.
    """
    diagnostic_rules = diagnostic_rules or load_diagnostic_rules_ngc()
    vocabulary = vocabulary or load_webmineral_vocabulary_summary()
    metadata = metadata or {}
    peaks_by_preparation = peaks_by_preparation or {}
    natural = {"preparation": "natural", "peaks": peaks_by_preparation.get("natural") or []}
    glycolated = {"preparation": "glicolado", "peaks": peaks_by_preparation.get("glycolated") or peaks_by_preparation.get("glicolado") or []}
    calcined = {"preparation": "calcinado", "peaks": peaks_by_preparation.get("calcined") or peaks_by_preparation.get("calcinado") or []}
    if not natural["peaks"]:
        natural = None
    if not glycolated["peaks"]:
        glycolated = None
    if not calcined["peaks"]:
        calcined = None

    observations = _observations_for_clay_rules(natural, glycolated, calcined)
    missing = [
        label
        for label, item in (("natural", natural), ("glycolated", glycolated), ("calcined", calcined))
        if not item
    ]
    global_warnings = [
        "Interpretação qualitativa/semiquantitativa; não retornar porcentagem mineralógica sem módulo quantitativo separado.",
        "WebMineral d/I é catálogo auxiliar e não prova final; comportamento N/G/C prevalece.",
    ]
    if missing:
        global_warnings.append("Preparações ausentes: %s; não usar linguagem confirmatória." % ", ".join(missing))
    calc_temp = _finite_float(metadata.get("temperature_C") or metadata.get("calcination_temperature_C"))
    if calcined and calc_temp is None:
        global_warnings.append("Temperatura/tempo de calcinação não informados; interpretação térmica pode ser ambígua.")
    elif calcined and calc_temp < 500:
        global_warnings.append("Calcinação abaixo de 500 °C; não aplicar destruição forte de caulinita como C550.")

    candidates = []

    n7 = _observation_intensity(observations["kaolin_n_7"])
    g7 = _observation_intensity(observations["kaolin_g_7"])
    c7 = _observation_intensity(observations["kaolin_c_7"])
    has_kaolin_3_57 = _peak_present(observations["kaolin_3_57"])
    has_chlorite_14 = any(
        _peak_present(observations[key])
        for key in ("chlorite_n_14", "chlorite_g_14", "chlorite_c_14")
    )
    has_chlorite_aux = any(
        _peak_present(observations[key])
        for key in ("chlorite_4_72", "chlorite_3_53")
    )
    kaolin_score = 0.0
    kaolin_for = []
    kaolin_against = []
    if n7 > 0:
        kaolin_score += 0.25
        kaolin_for.append(_format_peak_text("Pico ~7 Å presente em N", observations["kaolin_n_7"]))
    if g7 > 0:
        kaolin_score += 0.20
        kaolin_for.append(_format_peak_text("Pico ~7 Å presente em G", observations["kaolin_g_7"]))
    if n7 > 0 and g7 > 0 and abs((_obs_d(observations["kaolin_n_7"]) or 0) - (_obs_d(observations["kaolin_g_7"]) or 0)) <= 0.25:
        kaolin_score += 0.20
        kaolin_for.append("Pico 7 Å permanece sem deslocamento relevante N→G.")
    if calcined and n7 > 0 and (c7 == 0 or c7 < 0.25 * n7):
        kaolin_score += 0.25
        kaolin_for.append("Pico ~7 Å ausente ou fortemente reduzido em C.")
    elif n7 > 0 and not calcined:
        kaolin_against.append("Sem preparo calcinado, ausência de pico em C não pode ser usada para separar caulinita de clorita/serpentina.")
    if has_kaolin_3_57:
        kaolin_score += 0.10
        kaolin_for.append(_format_peak_text("Pico companheiro ~3,57 Å presente", observations["kaolin_3_57"]))
    if n7 > 0 and c7 >= 0.5 * n7:
        kaolin_score -= 0.25
        kaolin_against.append("Pico ~7 Å persiste forte em C; isso penaliza caulinita pura.")
    chlorite_set = all(_peak_present(observations[key]) for key in ("chlorite_n_14", "chlorite_7", "chlorite_4_72", "chlorite_3_53"))
    if chlorite_set:
        kaolin_score -= 0.20
        kaolin_against.append("Conjunto 14/7/4,72/3,53 Å favorece clorita ou mistura caulinita+clorita.")
    kaolin_discriminant = bool(calcined and n7 > 0 and (c7 == 0 or c7 < 0.25 * n7))
    if (n7 > 0 or g7 > 0) and not kaolin_discriminant:
        kaolin_score = min(kaolin_score, 0.38 if has_kaolin_3_57 else 0.32)
        kaolin_against.append("7 Å sem perda térmica documentada é evidência ambígua; não classificar caulinita como resultado final.")
    candidates.append(_candidate_interpretation(
        "kaolin_group",
        "kaolin_group",
        "Grupo da caulinita",
        "group",
        kaolin_score,
        _candidate_status(kaolin_score, critical_ok=not missing),
        kaolin_for,
        kaolin_against,
        [
            _matched_peak("kaolin_001_n", observations["kaolin_n_7"], "natural", "kaolin_group_ngc"),
            _matched_peak("kaolin_001_g", observations["kaolin_g_7"], "glycolated", "kaolin_group_ngc"),
            _matched_peak("kaolin_001_c", observations["kaolin_c_7"], "calcined", "kaolin_group_ngc"),
            _matched_peak("kaolin_002", observations["kaolin_3_57"], None, "kaolin_group_ngc"),
        ],
        ["G ausente impede avaliar ausência de expansão.", "C ausente impede separar caulinita de clorita."] if missing else [],
        ["Clorita e serpentina também podem contribuir em ~7 Å."],
        ["FTIR", "pico 060", "verificação de clorita por 14/7/4,72/3,53 Å"],
        "Grupo caulinítico é favorecido quando 7 Å não expande no glicol e perde intensidade após calcinação.",
        ["N/G/C resolve grupo caulinítico; não afirmar kaolinite vs dickite vs nacrite sem evidência adicional."],
    ))

    cl_score = 0.0
    cl_for = []
    cl_against = []
    if _peak_present(observations["chlorite_n_14"]) or _peak_present(observations["chlorite_g_14"]) or _peak_present(observations["chlorite_c_14"]):
        cl_score += 0.30
        cl_for.append(_format_peak_text("Pico basal 14-15 Å observado", observations["chlorite_n_14"] or observations["chlorite_g_14"] or observations["chlorite_c_14"]))
    if _peak_present(observations["chlorite_7"]):
        cl_score += 0.20
        cl_for.append(_format_peak_text("Reflexão associada ~7 Å", observations["chlorite_7"]))
    if _peak_present(observations["chlorite_4_72"]):
        cl_score += 0.15
        cl_for.append(_format_peak_text("Reflexão associada ~4,72 Å", observations["chlorite_4_72"]))
    if _peak_present(observations["chlorite_3_53"]):
        cl_score += 0.15
        cl_for.append(_format_peak_text("Reflexão associada ~3,53 Å", observations["chlorite_3_53"]))
    if _peak_present(observations["chlorite_n_14"]) and not _peak_present(observations["smectite_g"]):
        cl_score += 0.20
        cl_for.append("14 Å não expande claramente para ~17 Å em G.")
    if _peak_present(observations["chlorite_n_14"]) and _peak_present(observations["chlorite_c_14"]):
        cl_score += 0.20
        cl_for.append("Pico 14-15 Å persiste no aquecimento.")
    if _peak_present(observations["smectite_g"]):
        cl_score -= 0.30
        cl_against.append("Há expansão para ~17 Å em G, o que favorece esmectita/interestratificado.")
    chlorite_discriminant = bool(has_chlorite_14 and (has_chlorite_aux or _peak_present(observations["chlorite_c_14"])))
    if _peak_present(observations["chlorite_7"]) and not chlorite_discriminant:
        cl_score = min(cl_score, 0.34)
        cl_against.append("Reflexão ~7 Å sem 14 Å/4,72 Å/3,53 Å diagnósticos não separa clorita de caulinita/serpentina.")
    candidates.append(_candidate_interpretation(
        "chlorite_group",
        "chlorite_group",
        "Grupo da clorita",
        "group",
        cl_score,
        _candidate_status(cl_score, critical_ok=not missing),
        cl_for,
        cl_against,
        [
            _matched_peak("chlorite_001", observations["chlorite_n_14"], "natural", "chlorite_group_ngc"),
            _matched_peak("chlorite_001_c", observations["chlorite_c_14"], "calcined", "chlorite_group_ngc"),
            _matched_peak("chlorite_002", observations["chlorite_7"], None, "chlorite_group_ngc"),
            _matched_peak("chlorite_003", observations["chlorite_4_72"], None, "chlorite_group_ngc"),
            _matched_peak("chlorite_004", observations["chlorite_3_53"], None, "chlorite_group_ngc"),
        ],
        ["Falta conjunto completo 14/7/4,72/3,53 Å."] if cl_score < 0.80 else [],
        ["Caulinita compartilha ~7 Å; vermiculita pode aparecer perto de 14 Å."],
        ["química", "pico 060", "FTIR", "comparação com padrão curado"],
        "Clorita é favorecida por 14 Å preservado em C com reflexões associadas 7/4,72/3,53 Å.",
        ["Não resolver clinochlore/chamosite/etc. apenas por N/G/C."],
    ))

    sm_score = 0.0
    sm_for = []
    sm_against = []
    if _peak_present(observations["smectite_n"]):
        sm_score += 0.30
        sm_for.append(_format_peak_text("Pico 12-16,5 Å em N", observations["smectite_n"]))
    if _peak_present(observations["smectite_g"]):
        sm_score += 0.40
        sm_for.append(_format_peak_text("Expansão para ~17 Å em G", observations["smectite_g"]))
    if _peak_present(observations["smectite_c"]):
        sm_score += 0.25
        sm_for.append(_format_peak_text("Colapso para ~10 Å em C", observations["smectite_c"]))
    if _peak_present(observations["smectite_n"]) and _peak_present(observations["smectite_g"]):
        delta = (_obs_d(observations["smectite_g"]) or 0) - (_obs_d(observations["smectite_n"]) or 0)
        if delta > 1.2:
            sm_score += 0.15
            sm_for.append("Expansão N→G maior que 1,2 Å.")
    if not _peak_present(observations["smectite_g"]) and chlorite_set:
        sm_score -= 0.25
        sm_against.append("Sem expansão glicolada e com conjunto forte de clorita.")
    candidates.append(_candidate_interpretation(
        "smectite_group",
        "smectite_group",
        "Grupo da esmectita",
        "group",
        sm_score,
        _candidate_status(sm_score, critical_ok=bool(glycolated and calcined)),
        sm_for,
        sm_against,
        [
            _matched_peak("smectite_n", observations["smectite_n"], "natural", "smectite_group_ngc"),
            _matched_peak("smectite_g", observations["smectite_g"], "glycolated", "smectite_group_ngc"),
            _matched_peak("smectite_c", observations["smectite_c"], "calcined", "smectite_group_ngc"),
        ],
        ["Sem G não avaliar expansão; sem C não avaliar colapso térmico."] if ("glycolated" in missing or "calcined" in missing) else [],
        ["Clorita/vermiculita podem ocorrer perto de 14 Å se não houver expansão."],
        ["saturação Mg/K", "glicerol", "modelagem de interestratificados"],
        "Esmectita é favorecida por expansão com glicol e colapso térmico.",
        ["Não separar espécies de esmectita apenas por N/G/C."],
    ))

    il_score = 0.0
    il_for = []
    il_against = []
    stable_10_hits = sum(1 for key in ("illite_n_10", "illite_g_10", "illite_c_10") if _peak_present(observations[key]))
    if stable_10_hits == 3:
        il_score += 0.35
        il_for.append("Pico ~10 Å estável em N/G/C.")
    elif stable_10_hits:
        il_score += 0.18
        il_for.append("Pico ~10 Å aparece em parte das preparações.")
    if _peak_present(observations["illite_n_10"]) and not _peak_present(observations["smectite_g"]):
        il_score += 0.20
        il_for.append("Não há expansão para ~17 Å em G.")
    if _peak_present(observations["illite_c_10"]):
        il_score += 0.15
        il_for.append("Pico ~10 Å persiste em C.")
    if _peak_present(observations["illite_5"]):
        il_score += 0.15
        il_for.append(_format_peak_text("Pico companheiro ~5 Å", observations["illite_5"]))
    if _peak_present(observations["illite_3_33"]):
        il_score += 0.10
        il_for.append(_format_peak_text("Pico companheiro ~3,33 Å", observations["illite_3_33"]))
    if _peak_present(observations["illite_3_33"]) and _peak_present(observations["quartz_101"]) and stable_10_hits < 2:
        il_score -= 0.15
        il_against.append("Pico ~3,33 Å pode ser explicado por quartzo ~3,34 Å sem suporte suficiente de 10 Å.")
    candidates.append(_candidate_interpretation(
        "illite_mica",
        "illite_mica",
        "Ilita/mica",
        "series",
        il_score,
        _candidate_status(il_score, critical_ok=stable_10_hits == 3),
        il_for,
        il_against,
        [
            _matched_peak("illite_001_n", observations["illite_n_10"], "natural", "illite_mica_ngc"),
            _matched_peak("illite_001_g", observations["illite_g_10"], "glycolated", "illite_mica_ngc"),
            _matched_peak("illite_001_c", observations["illite_c_10"], "calcined", "illite_mica_ngc"),
            _matched_peak("illite_002", observations["illite_5"], None, "illite_mica_ngc"),
            _matched_peak("illite_003", observations["illite_3_33"], None, "illite_mica_ngc"),
        ],
        ["Picos companheiros ~5 Å e ~3,33 Å ausentes ou incompletos."] if il_score < 0.75 else [],
        ["Quartzo 101 em ~3,34 Å pode sobrepor 3,33 Å de ilita/mica."],
        ["química", "pico 060", "padrão de pó randômico"],
        "Ilita/mica é favorecida por 10 Å estável nos três tratamentos.",
        ["Muscovita e outras micas compartilham 10 Å; manter nível série/grupo sem química."],
    ))

    verm_score = 0.0
    verm_for = []
    if _peak_present(observations["chlorite_n_14"]) and not _peak_present(observations["smectite_g"]):
        verm_score += 0.30
        verm_for.append("14 Å em N sem expansão clara para ~17 Å em G.")
    if _peak_present(observations["chlorite_n_14"]) and not _peak_present(observations["chlorite_c_14"]):
        verm_score += 0.20
        verm_for.append("14 Å colapsa ou enfraquece em C.")
    if chlorite_set:
        verm_score -= 0.20
    candidates.append(_candidate_interpretation(
        "vermiculite_group",
        "vermiculite_group",
        "Vermiculita/interestratificado 14 Å",
        "ambiguous",
        verm_score,
        _candidate_status(verm_score, provisional=True),
        verm_for,
        ["Conjunto completo de clorita persistente reduz hipótese de vermiculita."] if chlorite_set else [],
        [_matched_peak("vermiculite_14a", observations["chlorite_n_14"], "natural", "vermiculite_group_ngc")],
        ["N/G/C sozinho é insuficiente para vermiculita robusta."],
        ["Clorita e interestratificados também podem gerar 14 Å."],
        ["saturação K/Mg", "glicerol", "controle de umidade"],
        "Vermiculita permanece provisória sem tratamentos K/Mg/glicerol.",
        ["Nunca tratar vermiculita como detectada forte apenas por N/G/C."],
    ))

    mixed_score = 0.0
    mixed_for = []
    broad_peaks = []
    for item in (natural, glycolated, calcined):
        for peak in (item or {}).get("peaks") or []:
            fwhm = _finite_float(peak.get("fwhm"))
            d_value = _peak_d(peak)
            if fwhm is not None and fwhm >= 0.8 and d_value is not None and 9.0 <= d_value <= 18.6:
                broad_peaks.append(peak)
    partial_smectite = 0 < sum(1 for key in ("smectite_n", "smectite_g", "smectite_c") if _peak_present(observations[key])) < 3
    if partial_smectite:
        mixed_score += 0.30
        mixed_for.append("Resposta expansiva/colapso parcial entre N/G/C.")
    if stable_10_hits and _peak_present(observations["smectite_g"]):
        mixed_score += 0.30
        mixed_for.append("Coexistem 10 Å estável e banda expansiva.")
    if broad_peaks:
        mixed_score += 0.20
        mixed_for.append("Pico largo/ombro entre 10 e 17 Å sugere interestratificado ou baixa cristalinidade.")
    if cl_score >= 0.6 and kaolin_score >= 0.4 and c7 > 0:
        mixed_score = max(mixed_score, 0.55)
        mixed_for.append("Caulinita e clorita têm evidências simultâneas; mistura provável.")
    unresolved_7a_overlap = bool(
        (n7 > 0 or g7 > 0 or _peak_present(observations["chlorite_7"]))
        and not kaolin_discriminant
        and not chlorite_discriminant
    )
    if unresolved_7a_overlap:
        global_warnings.append(
            "Sobreposição 7 Å clorita/caulinita/serpentina sem discriminante N/G/C suficiente; resultado mineralógico principal fica inconclusivo."
        )
        mixed_score = max(mixed_score, 0.52)
        mixed_for.append("Pico ~7 Å é compartilhado por caulinita, clorita e serpentina sem evidência discriminante suficiente.")
    candidates.append(_candidate_interpretation(
        "kaolin_chlorite_overlap_7a" if unresolved_7a_overlap else "mixed_layer",
        "ambiguous_overlap" if unresolved_7a_overlap else "mixed_layer",
        "Inconclusivo (sobreposição 7 Å)" if unresolved_7a_overlap else "Interestratificado ou mistura",
        "ambiguous" if unresolved_7a_overlap else "interstratified",
        mixed_score,
        "ambíguo" if unresolved_7a_overlap else _candidate_status(mixed_score, ambiguous=mixed_score >= 0.4),
        mixed_for,
        [],
        [_matched_peak("broad_or_shoulder", {"observed_peak": _compact_peak(broad_peaks[0])}, None, "mixed_layer_ngc") if broad_peaks else None],
        ["Sem modelagem específica, não atribuir mineral puro."],
        ["Corrensita, clorita/esmectita e ilita/esmectita podem gerar respostas parciais."],
        ["modelagem de interestratificados", "amostras saturadas", "padrões curados"],
        "Resposta parcial, larga ou coexistente deve ser tratada como mistura/interestratificado.",
        [],
    ))

    candidates = sorted(candidates, key=lambda row: row.get("score") or 0.0, reverse=True)
    return {
        "sampleId": sample_id,
        "wavelengthA": _finite_float(wavelength_a) or DEFAULT_WAVELENGTH_A,
        "candidates": candidates,
        "globalWarnings": global_warnings,
        "missingPreparations": missing,
        "matchedPeaks": [peak for candidate in candidates for peak in candidate.get("matchedPeaks", [])],
        "diagnosticRulesVersion": diagnostic_rules.get("version"),
        "vocabularySummary": vocabulary,
        "version": "argiloteca.drx.ngc.clay_interpretation.v1",
        "interpretationPolicy": POLICY,
        "policyScope": "rule_based_confirmation_within_argiloteca_ngc_engine",
        "diagnosticLabels": [CONFIRMED_BY_RULES, PROBABLE_BY_RULES, POSSIBLE_BY_RULES],
    }


interpretClayMineralsNGC = interpret_clay_minerals_ngc


def _interpret_group(sample_base, items):
    """
    Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida.
    
    Args:
        sample_base: Valor de entrada consumido por esta etapa do fluxo.
        items: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    by_prep, duplicates = _best_by_preparation(items)
    natural = by_prep.get("natural")
    glycolated = by_prep.get("glicolado")
    calcined = by_prep.get("calcinado")
    complete_trio = bool(natural and glycolated and calcined)
    available = sorted(by_prep.keys(), key=lambda key: PREPARATION_ORDER.get(key, 99))
    warnings = []
    if not complete_trio:
        warnings.append("Grupo N/G/C incompleto; conclusoes devem permanecer fracas.")
    if duplicates:
        warnings.append("Ha duplicatas por preparo; foi usada a primeira curva de cada preparo.")

    interval_minerals, interval_diagnostics = _script_interval_diagnostics(natural, glycolated, calcined)
    companion_peaks = _companion_peak_set(natural, glycolated, calcined)
    ngc_behavior = _ngc_behavior(companion_peaks)
    mixed_layer_warnings = _mixed_layer_warnings(companion_peaks)
    targeted_basal_peaks = _compact_targeted_rows(items)
    target_screening = _targeted_clay_screening(
        natural,
        glycolated,
        calcined,
        items,
        companion_peaks=companion_peaks,
        behavior=ngc_behavior,
        mixed_warnings=mixed_layer_warnings,
    )
    clay_interpretation = interpret_clay_minerals_ngc(
        sample_base,
        {
            "natural": (natural or {}).get("peaks") or [],
            "glycolated": (glycolated or {}).get("peaks") or [],
            "calcined": (calcined or {}).get("peaks") or [],
        },
        metadata={
            "available_preparations": available,
            "duplicates": duplicates,
        },
    )
    diagnostic_interpretation = None
    if interpret_ngc_v3:
        try:
            # Ponte para a engine V3: os picos N/G/C vao junto com d060,
            # contexto, morfologia e quimica. Esses metadados sao onde a logica
            # de Meunier e aplicada de fato para octaedria, argilas magnesianas,
            # minerais fibrosos e interestratificados.
            diagnostic_interpretation = interpret_ngc_v3(
                {
                    "N": (natural or {}).get("peaks") or [],
                    "G": (glycolated or {}).get("peaks") or [],
                    "C": (calcined or {}).get("peaks") or [],
                },
                metadata={
                    "sample_id": sample_base,
                    "d060": next(
                        (
                            (item.get("metadata") or {}).get("d060")
                            for item in items or []
                            if (item.get("metadata") or {}).get("d060") is not None
                        ),
                        None,
                    ),
                    "available_preparations": available,
                    "duplicates": duplicates,
                    "context": [
                        value
                        for item in items or []
                        for value in ((item.get("metadata") or {}).get("context") or [])
                    ],
                    "morphology": [
                        value
                        for item in items or []
                        for value in ((item.get("metadata") or {}).get("morphology") or [])
                    ],
                    "chemistry": next(
                        (
                            (item.get("metadata") or {}).get("chemistry")
                            for item in items or []
                            if (item.get("metadata") or {}).get("chemistry")
                        ),
                        {},
                    ),
                },
            ).get("diagnostic_interpretation")
        except Exception as exc:
            warnings.append("Falha ao executar engine DRX V3: %s" % exc)
    screening_by_mineral = {
        str(row.get("mineral") or "").casefold(): row
        for row in target_screening
        if isinstance(row, dict)
    }
    chlorite_screening_detected = (screening_by_mineral.get("clorita") or {}).get("status") == "detected"
    candidates = []
    smectite_evidence = [
        _evidence("Expansao glicolada proxima de 17 A", glycolated or {}, "smectite_glycolated_17a"),
        _evidence("Colapso/posicao calcinada proxima de 10 A", calcined or {}, "smectite_calcined_10a"),
    ]
    smectite_score = (0.52 if smectite_evidence[0] else 0.0) + (0.24 if smectite_evidence[1] else 0.0) + (0.14 if natural else 0.0)
    smectite_warnings = ["Pico glicolado isolado nao separa todos os interestratificados."]
    if chlorite_screening_detected and smectite_score > 0:
        smectite_score = min(smectite_score, 0.74)
        smectite_warnings.append(
            "Clorita com 14 A preservado e picos companheiros reduz a confianca da leitura expansiva isolada; avaliar mistura manualmente."
        )
    if any(smectite_evidence):
        candidates.append(
            _candidate(
                "esmectita expansiva",
                smectite_score,
                smectite_evidence,
                warnings + smectite_warnings,
                complete_trio,
            )
        )

    chlorite_evidence = [
        _evidence("Basal proximo de 14 A", natural or glycolated or calcined or {}, "chlorite_14a"),
        _evidence("Reflexao associada proxima de 7 A", natural or glycolated or calcined or {}, "chlorite_7a"),
        _evidence("Reflexao associada proxima de 3,5 A", natural or glycolated or calcined or {}, "chlorite_3_5a"),
    ]
    chlorite_score = (0.42 if chlorite_evidence[0] else 0.0) + (0.24 if chlorite_evidence[1] else 0.0) + (0.18 if chlorite_evidence[2] else 0.0)
    if chlorite_screening_detected:
        chlorite_score = max(chlorite_score, 0.92)
    if chlorite_evidence[0] or (chlorite_evidence[1] and chlorite_evidence[2]):
        candidates.append(
            _candidate(
                "clorita/vermiculita",
                chlorite_score,
                chlorite_evidence,
                warnings + ["Clorita, vermiculita e esmectita natural podem se sobrepor em baixo angulo."],
                complete_trio,
            )
        )
    elif any(row.get("mineral") == "Clorita" and row.get("status") == "possible" for row in target_screening):
        chlorite_screen = next(row for row in target_screening if row.get("mineral") == "Clorita")
        candidates.append(
            _candidate(
                "clorita",
                chlorite_screen.get("score") or 0.48,
                [
                    observation
                    for observation in (chlorite_screen.get("observations") or {}).values()
                    if isinstance(observation, dict) and observation.get("observed_peak")
                ],
                warnings + chlorite_screen.get("warnings", []),
                complete_trio,
            )
        )

    kaolinite_evidence = [
        _evidence("Caulinita 001 proxima de 7,15 A", natural or glycolated or calcined or {}, "kaolinite_7a"),
        _evidence("Caulinita 002 proxima de 3,57 A", natural or glycolated or calcined or {}, "kaolinite_3_57a"),
    ]
    kaolinite_score = (0.38 if kaolinite_evidence[0] else 0.0) + (0.38 if kaolinite_evidence[1] else 0.0) + (0.08 if calcined else 0.0)
    if any(kaolinite_evidence):
        candidates.append(
            _candidate(
                "caulinita",
                kaolinite_score,
                kaolinite_evidence,
                warnings + ["Pico 7 A pode sobrepor clorita; reflexao 3,57 A e comportamento ao aquecimento sao essenciais."],
                complete_trio,
            )
        )

    unresolved_7a_overlap = bool(
        (kaolinite_evidence[0] or chlorite_evidence[1])
        and not chlorite_evidence[0]
        and not calcined
    )
    if unresolved_7a_overlap:
        candidates = [
            candidate
            for candidate in candidates
            if candidate.get("mineral_candidate") not in ("caulinita", "clorita", "clorita/vermiculita")
        ]
        candidates.append(
            _candidate(
                "inconclusivo: sobreposição 7 Å clorita/caulinita",
                0.52,
                [kaolinite_evidence[0] or chlorite_evidence[1]],
                warnings + [
                    "Pico ~7 Å isolado ou sem preparo calcinado não decide entre caulinita, clorita e serpentina.",
                    "Para decidir clorita, exigir 14 Å com 4,72/3,53 Å ou persistência térmica; para caulinita, exigir perda em C e/ou suporte 3,57 Å coerente.",
                ],
                complete_trio,
            )
        )

    illite_evidence = [
        _evidence("Ilita/mica 001 proxima de 10 A em natural", natural or {}, "illite_10a"),
        _evidence("Ilita/mica 001 proxima de 10 A em glicolado", glycolated or {}, "illite_10a"),
        _evidence("Ilita/mica 001 proxima de 10 A em calcinado", calcined or {}, "illite_10a"),
    ]
    illite_hits = len([row for row in illite_evidence if row])
    if illite_hits:
        candidates.append(
            _candidate(
                "ilita/mica",
                min(0.86, 0.24 + (0.22 * illite_hits)),
                illite_evidence,
                warnings + ["Pico 10 A tambem pode representar micas; usar reflexoes associadas e contexto geologico."],
                complete_trio,
            )
        )

    trajectory = {
        "natural_001": _range_peak(natural or {}, "chlorite_14a") or _range_peak(natural or {}, "illite_10a"),
        "glycolated_001": _range_peak(glycolated or {}, "smectite_glycolated_17a") or _range_peak(glycolated or {}, "illite_10a"),
        "calcined_001": _range_peak(calcined or {}, "smectite_calcined_10a") or _range_peak(calcined or {}, "illite_10a"),
    }
    candidates = sorted(candidates, key=lambda row: row.get("score") or 0.0, reverse=True)
    return {
        "sample_base": sample_base,
        "status": "trio completo" if complete_trio else "trio incompleto",
        "available_preparations": available,
        "duplicates": duplicates,
        "trajectory": trajectory,
        "candidates": candidates,
        "best_candidate": candidates[0] if candidates else None,
        "interval_minerals": interval_minerals,
        "interval_diagnostics": interval_diagnostics,
        "script_report": _script_report(sample_base, interval_minerals, interval_diagnostics, items),
        "target_screening": target_screening,
        "clay_interpretation": clay_interpretation,
        "diagnostic_interpretation": diagnostic_interpretation,
        "targeted_basal_peaks": targeted_basal_peaks,
        "companion_peaks": companion_peaks,
        "ngc_behavior": ngc_behavior,
        "mixed_layer_warnings": mixed_layer_warnings,
        "warnings": warnings,
    }


def build_ngc_workflow(items):
    """
    Agrupa difratogramas selecionados e executa o workflow N/G/C versionado.

    A entrada vem do painel e pode conter RAWs externos, snapshots da Argiloteca ou
    resultados avançados. O agrupamento por amostra-base impede que candidatos por
    RAW isolado dominem a leitura quando há trio N/G/C completo. O retorno mantém a
    política auxiliar/não confirmatória em todos os grupos.

    Args:
        items: Lista de difratogramas selecionados ou carregados no painel.
    Returns:
        Payload serializável com grupos, diagnósticos, candidatos e avisos.
    Raises:
        Exception: Propaga erros estruturais não tratados pelo chamador da API.
    """
    normalised_items = [_item_from_payload(item) for item in items or [] if isinstance(item, dict)]
    groups = defaultdict(list)
    for item in normalised_items:
        groups[item["sample_base"]].append(item)
    group_payloads = [
        _interpret_group(sample_base, rows)
        for sample_base, rows in sorted(groups.items(), key=lambda pair: pair[0])
    ]
    return {
        "success": True,
        "schema_version": DRX_NGC_WORKFLOW_SCHEMA,
        "group_count": len(group_payloads),
        "item_count": len(normalised_items),
        "groups": group_payloads,
        "diagnostic_ranges": DIAGNOSTIC_RANGES,
        "script_interval_ranges": SCRIPT_INTERVAL_RANGES,
        "interpretation_policy": POLICY,
        "policy_scope": "rule_based_confirmation_within_argiloteca_ngc_engine",
        "diagnostic_labels": [CONFIRMED_BY_RULES, PROBABLE_BY_RULES, POSSIBLE_BY_RULES],
    }
