"""
Classificador auxiliar da reflexao 060 para a engine DRX V3.

Autor: Alexandre Ribas Semeler
E-mail: alexandre.semeler@ufrgs.br

Referencia aplicada:
    Meunier, Clays, 2005.
    Arquivo local: /home/invenio/invenio-project/Clays_Meunier.pdf

Referencia complementar aplicada:
    Moore & Reynolds, X-Ray Diffraction and the Identification and Analysis of
    Clay Minerals.
    Arquivo local: /home/invenio/invenio-project/textos/MooreandReynolds.pdf

Como a logica de Meunier esta aplicada neste arquivo:
    - classify_octahedral transforma d060 em evidencia estrutural auxiliar:
      ~1.49-1.50 A favorece dioctaedrico, ~1.52 A e intermediario ou
      especifico, e ~1.54 A favorece trioctaedrico.
    - A funcao compara essa classe com o candidato mineral quando fornecido,
      preenchendo supports ou contradicts.
    - Nao ha classe, objeto mutavel global, loop residente ou confirmacao
      mineralogica por d060 isolado; a funcao usa uma cadeia condicional finita
      e retorna JSON pequeno para a arvore decisoria.
    - Moore & Reynolds alerta que quartzo pode interferir perto de d=1.542 A;
      por isso a janela trioctaedrica adiciona warning para verificar o padrao
      de quartzo quando d060 e usado.


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


def classify_octahedral(d060, tolerance=0.015, candidate=None):
    """
    Classifica d060 segundo as janelas estruturais auxiliares de Meunier.

    Args:
        d060: Espacamento da reflexao 060 em Angstrom.
        tolerance: Folga numerica aplicada a cada janela.
        candidate: Candidato opcional com octahedral_type esperado.

    Returns:
        dict: Tipo octaedrico auxiliar, evidencia textual, suportes,
        contradicoes e aviso de que d060 nao confirma mineral sozinho.
    """
    warnings = ["d060 is auxiliary and must not be used alone for final identification."]
    supports = []
    contradicts = []
    try:
        value = float(d060)
    except (TypeError, ValueError):
        return {
            "octahedral_type": "unknown",
            "evidence": "No d060 value supplied.",
            "supports": supports,
            "contradicts": contradicts,
            "warnings": warnings,
        }
    source_references = [
        ("kaolinite", 1.490, "dioctahedral"),
        ("illite_muscovite", 1.499, "dioctahedral"),
        ("glauconite", 1.511, "mineral_specific"),
        ("saponite", 1.520, "ambiguous_octahedral"),
        ("nontronite", 1.521, "ambiguous_octahedral"),
        ("hectorite", 1.530, "mineral_specific"),
        ("biotite", 1.538, "trioctahedral"),
        ("vermiculite", 1.541, "mineral_specific"),
        ("berthierine", 1.555, "trioctahedral"),
        ("palygorskite", 1.560, "fibrous_channel"),
    ]
    compatibilities = [
        {
            "mineral": mineral,
            "source_value_angstrom": reference,
            "distance_angstrom": round(abs(value - reference), 6),
            "octahedral_type": source_type,
            "within_operational_tolerance": abs(value - reference) <= tolerance,
        }
        for mineral, reference, source_type in source_references
        if abs(value - reference) <= tolerance
    ]
    # Source ranges published by Table 7.4 are tested separately from the
    # operational tolerance around point values.
    for mineral, lower, upper, source_type in [
        ("montmorillonite", 1.492, 1.504, "dioctahedral"),
        ("serpentines", 1.531, 1.538, "trioctahedral"),
        ("chlorites", 1.538, 1.549, "trioctahedral"),
        ("sepiolite", 1.540, 1.550, "trioctahedral"),
    ]:
        if lower - tolerance <= value <= upper + tolerance:
            compatibilities.append({
                "mineral": mineral,
                "source_range_angstrom": [lower, upper],
                "distance_angstrom": 0.0 if lower <= value <= upper else round(min(abs(value - lower), abs(value - upper)), 6),
                "octahedral_type": source_type,
                "within_operational_tolerance": True,
            })
    # Structural class remains a broad auxiliary summary. Mineral matches are
    # deliberately non-exclusive and remain available in ``compatibilities``.
    if 1.485 <= value <= 1.505:
        kind = "dioctahedral"
    elif 1.515 <= value <= 1.525:
        kind = "ambiguous"
    elif 1.530 <= value <= 1.570:
        kind = "trioctahedral"
    else:
        kind = "unknown"
    evidence = f"d060 has {len(compatibilities)} non-exclusive Table 7.4 compatibility match(es)."
    if abs(value - 1.542) <= tolerance:
        warnings.append("Moore & Reynolds: quartz at d=1.542 A can interfere; check the quartz companion reflection near 1.82 A.")
    expected = (candidate or {}).get("octahedral_type") if isinstance(candidate, dict) else None
    if expected and expected != "unknown":
        # Comparacao auxiliar com o candidato: registra suporte/contradicao,
        # mas nao altera a identificacao final sem N/G/C e picos companheiros.
        if expected == kind or (kind == "intermediate" and expected in {"dioctahedral", "trioctahedral"}):
            supports.append((candidate or {}).get("label") or (candidate or {}).get("mineral") or "candidate")
        elif kind != "unknown":
            contradicts.append((candidate or {}).get("label") or (candidate or {}).get("mineral") or "candidate")
    return {
        "octahedral_type": kind,
        "d060": value,
        "operational_tolerance_angstrom": tolerance,
        "tolerance_basis": "caller_or_pipeline; not a source range",
        "compatibilities": sorted(compatibilities, key=lambda row: row["distance_angstrom"]),
        "evidence": evidence,
        "supports": supports,
        "contradicts": contradicts,
        "warnings": warnings,
    }
