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
    # Meunier: valores proximos de 1.49-1.50 A favorecem estruturas
    # dioctaedricas, usados para montmorillonita/nontronita e caulinitas.
    if 1.49 - tolerance <= value <= 1.50 + tolerance:
        kind = "dioctahedral"
        evidence = "d060 near 1.49-1.50 A favors dioctahedral clay minerals."
    # Meunier: ~1.52 A pode representar transicao/intermediario ou familias
    # especificas; o codigo exige quimica/contexto antes de especializar.
    elif 1.52 - tolerance <= value <= 1.52 + tolerance:
        kind = "intermediate"
        evidence = "d060 near 1.52 A is intermediate or mineral-specific and needs chemistry/context."
    # Meunier: ~1.54 A favorece argilominerais trioctaedricos como saponita,
    # estevensita, biotita, clorita trioctaedrica e serpentina.
    elif 1.54 - tolerance <= value <= 1.54 + tolerance:
        kind = "trioctahedral"
        evidence = "d060 near 1.54 A favors trioctahedral clay minerals."
        warnings.append("Moore & Reynolds: quartz near d=1.542 A can interfere with d060; check quartz companion peaks before using this as support.")
    else:
        kind = "unknown"
        evidence = "d060 is outside the simple diagnostic windows used by this engine."
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
        "evidence": evidence,
        "supports": supports,
        "contradicts": contradicts,
        "warnings": warnings,
    }
