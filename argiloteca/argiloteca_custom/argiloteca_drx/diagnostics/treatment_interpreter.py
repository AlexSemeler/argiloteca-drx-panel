"""
Argiloteca DRX V3 - interpretador de comportamento N/G/C.

Autor: Alexandre Ribas Semeler
E-mail: alexandre.semeler@ufrgs.br

Este arquivo e uma versao em linguagem de programacao das regras operacionais
de identificacao de argilominerais por DRX em agregados orientados descritas
no fluxograma USGS:

    https://pubs.usgs.gov/of/2001//of01-041/htmldocs/flow/index.htm

Referencia adicional aplicada:
    Lanson, B. & Bouchet, A. (1995). Identification des mineraux argileux
    par diffraction des rayons X: apport du traitement numerique.
    Bull. Centres Rech. Explor.-Prod. Elf Aquitaine, 19(1), 91-118.
    Arquivo local: /home/invenio/invenio-project/textos/
    lanson-1995-bull-centres-rech-ep-19-91.pdf

Como a logica de Lanson & Bouchet 1995 esta aplicada:
    - interpret_treatments transforma bandas largas, ombros, assimetria e FWHM
      alto em behavior="broad_or_shoulder";
    - esse behavior alimenta mixed_layer_engine.detect_mixed_layers, evitando
      identificacao por simples posicao de pico;
    - expansao parcial N->G e registrada como hipotese de interestratificado,
      coerente com a critica ao uso isolado de tabelas de referencia.

Como a logica de Moore & Reynolds esta aplicada:
    - picos largos ou larguras muito diferentes continuam sendo marcadores de
      mistura/interestratificacao ou dominios cristalinos distintos;
    - a presenca de padrao de quartzo 4.26/3.34 A e registrada como behavior
      auxiliar para calibracao/competicao com ilita e 060;
    - respostas N/G/C continuam prioritarias sobre tabelas de pico.

Objetos/funcoes envolvidos:
    - interpret_treatments: funcao principal;
    - behaviors: lista de marcadores diagnosticos;
    - relations: arestas explicaveis usadas no grafo diagnostico;
    - input_completeness: metadado usado para limitar confianca.

No projeto Argiloteca, esse fluxograma nao e lido em tempo de execucao. Ele foi
traduzido para regras deterministicas que observam a resposta de picos basais
entre tres preparacoes:

    N = natural / air dried
    G = glicolada / ethylene glycol
    C = calcinada / heated

Responsabilidade deste modulo:
    1. normalizar os picos recebidos do parser DRX;
    2. detectar comportamentos fisico-mineralogicos entre N, G e C;
    3. produzir relacoes explicaveis para o grafo diagnostico;
    4. informar completude da entrada para bloquear conclusoes fortes quando
       faltam tratamentos ou picos.

Padrao de engenharia:
    - modulo puro e sem estado global mutavel;
    - nao executa loop infinito, daemon ou processamento em segundo plano;
    - os loops sao finitos e proporcionais ao numero de picos da amostra;
    - a funcao retorna dados estruturados, sem efeitos colaterais;
    - toda inferencia mantem policy="argiloteca_rule_based_diagnostic".


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

from .diagnostic_behavior_rules import POLICY
from .diagnostic_peak_rules import named_range
from .evidences import find_peak, normalize_peaks, relation


def _find_named_peak(peaks, range_id):
    """Busca pico usando faixa declarada no catalogo central de regras."""
    return find_peak(peaks, *named_range(range_id))


def interpret_treatments(peaks, metadata=None):
    """
    Interpreta o comportamento dos picos entre Natural, Glicolado e Calcinado.

    Args:
        peaks: Dicionario com listas de picos em "N", "G" e "C". Cada pico deve
            conter ao menos d-spacing em Angstrom, aceito pela funcao
            normalize_peaks.
        metadata: Metadados opcionais preservados para compatibilidade futura.
            Este modulo nao depende deles para as regras atuais.

    Returns:
        dict: Estrutura com:
            - policy: politica auxiliar nao confirmatoria;
            - peaks: picos normalizados por preparacao;
            - behaviors: eventos detectados, como expansao, colapso,
              persistencia e desaparecimento;
            - relations: arestas explicaveis N->G, G->C ou N->C;
            - input_completeness: contagem de tratamentos e picos disponiveis.

    Regras aplicadas:
        - esmectita/interestratificados expansivos: N ~12-16.86 A, G
          ~16.06-18.31 A, C ~9.65-10.37 A;
        - picos estaveis: janelas em 14 A, 10 A, 7.15 A, 9.4 A e 12.2 A;
        - corrensita/C-S ordenado: N ~29 A, G ~31-32 A e C ~24 A;
        - picos largos/assimetria/FWHM alto: alerta para ombro, mistura ou
          interestratificado.
    """
    # Entrada defensiva: centraliza a conversao de aliases, d-spacing e chaves
    # N/G/C em normalize_peaks para evitar manipulacao ad hoc em cada regra.
    normalized = normalize_peaks(peaks)
    n = normalized["N"]
    g = normalized["G"]
    c = normalized["C"]
    behaviors = []
    relations = []

    # Regra expansiva do fluxograma: um pico basal natural na janela de
    # esmectitas/interestratificados deve migrar para ~17 A apos glicolacao e
    # colapsar para ~10 A apos aquecimento para sustentar comportamento
    # expansivo completo.
    n14 = _find_named_peak(n, "smectite_n")
    g17 = _find_named_peak(g, "smectite_g")
    c10 = _find_named_peak(c, "smectite_c")
    if n14 and g17 and (g17["d"] - n14["d"]) >= 0.8:
        behaviors.append("expands_with_glycol")
        relations.append(relation("N:%0.2fA" % n14["d"], "G:%0.2fA" % g17["d"], "expands_to", "Basal peak expands after glycolation.", 0.4, g17["d"] - n14["d"], rule_id="behavior_expand_glycol"))
    if g17 and c10:
        behaviors.append("collapses_after_heating")
        relations.append(relation("G:%0.2fA" % g17["d"], "C:%0.2fA" % c10["d"], "collapses_to", "Expanded peak collapses after heating.", 0.4, c10["d"] - g17["d"], rule_id="behavior_collapse_heat"))

    # Loop finito sobre janelas basais diagnosticas. Ele substitui uma serie de
    # ifs repetidos por uma tabela local pequena, mantendo custo O(k * p), onde
    # k=5 janelas e p=numero de picos por tratamento.
    stable_windows = (
        ("chlorite_14a", "14A"),
        ("illite_10a", "10A"),
        ("kaolinite_7a", "7A"),
        ("kerolite_9_4a", "9.4A"),
        ("sepiolite_12a", "12A"),
    )
    for range_id, label in stable_windows:
        d_min, d_max = named_range(range_id)
        width = d_max - d_min
        np = find_peak(n, d_min, d_max)
        gp = find_peak(g, d_min, d_max)
        cp = find_peak(c, d_min, d_max)
        if np and gp and abs(np["d"] - gp["d"]) <= width:
            behaviors.append("stable_after_glycol")
            relations.append(relation("N:%s %.2fA" % (label, np["d"]), "G:%s %.2fA" % (label, gp["d"]), "persists_as", "Peak remains within tolerance after glycolation.", 0.15, gp["d"] - np["d"], rule_id="behavior_stable_glycol"))
        if np and cp and abs(np["d"] - cp["d"]) <= width:
            behaviors.append("persists_after_heating")
            relations.append(relation("N:%s %.2fA" % (label, np["d"]), "C:%s %.2fA" % (label, cp["d"]), "persists_as", "Peak persists after heating.", 0.15, cp["d"] - np["d"], rule_id="behavior_persist_heat"))
        if np and not cp:
            behaviors.append("disappears_after_heating")
            relations.append(relation("N:%s %.2fA" % (label, np["d"]), "C:absent", "disappears", "Peak is absent after heating within the diagnostic window.", 0.2, rule_id="behavior_disappears_heat"))
        if np and cp:
            try:
                n_intensity = float(np.get("intensity") or 0.0)
                c_intensity = float(cp.get("intensity") or 0.0)
            except (TypeError, ValueError):
                n_intensity = 0.0
                c_intensity = 0.0
            # Capitulo 7 da obra X-Ray Diffraction and the Identification and
            # Analysis of Clay Minerals aplicado em forma numerica:
            # - clorita: o pico 14 A persiste e pode aumentar apos aquecimento
            #   a cerca de 550 C;
            # - grupo da caulinita: o pico 7 A desaparece ou reduz fortemente
            #   apos aquecimento.
            # O loop permanece finito, percorrendo somente as cinco janelas
            # basais declaradas acima. Intensidade e usada como evidencia de
            # comportamento termico, nunca como confirmacao isolada.
            if n_intensity > 0 and c_intensity >= n_intensity * 1.20 and label == "14A":
                behaviors.append("increases_intensity_after_heating")
                relations.append(relation("N:%s %.2fA" % (label, np["d"]), "C:%s %.2fA" % (label, cp["d"]), "supports", "14 A peak persists and increases after heating, supporting chlorite over kaolin-group loss.", 0.25, cp["d"] - np["d"], rule_id="chapter7_chlorite_heat_intensity"))
            if n_intensity > 0 and c_intensity <= n_intensity * 0.30 and label == "7A":
                behaviors.append("strongly_reduced_after_heating")
                relations.append(relation("N:%s %.2fA" % (label, np["d"]), "C:%s %.2fA" % (label, cp["d"]), "supports", "7 A peak is strongly reduced after heating, supporting kaolin-group thermal loss.", 0.25, cp["d"] - np["d"], rule_id="chapter7_kaolin_heat_loss"))

    # Regra explicita do fluxograma para corrensita ou C/S regularmente
    # interestratificado: superestrutura longa em ~29 A, expansao para ~31-32 A
    # com glicol e reflexao aquecida perto de ~24 A.
    n29 = _find_named_peak(n, "corrensite_n_29a")
    g31 = _find_named_peak(g, "corrensite_g_31a")
    c24 = _find_named_peak(c, "corrensite_c_24a")
    if n29 and g31:
        behaviors.extend(["rational_sequence", "ordered_chlorite_smectite"])
        relations.append(relation("N:%0.2fA" % n29["d"], "G:%0.2fA" % g31["d"], "expands_to", "Long-spacing C/S superstructure expands with glycolation.", 0.45, g31["d"] - n29["d"], rule_id="corrensite_flow"))
    if c24:
        behaviors.append("appears_after_heating")
        relations.append(relation("C:%0.2fA" % c24["d"], "heated_pattern", "appears", "Peak appears after heating near the corrensite/C-S diagnostic window.", 0.2, rule_id="behavior_appears_heat"))

    # Varredura linear, interrompida no primeiro pico largo/assimetrico. Esse
    # marcador nao identifica mineral sozinho; ele informa a camada de
    # interestratificados e ambiguidades.
    for peak in n + g + c:
        if peak.get("broad") or peak.get("asymmetric") or peak.get("fwhm", 0) and peak.get("fwhm", 0) > 0.5:
            behaviors.append("broad_or_shoulder")
            relations.append(relation("peak:%0.2fA" % peak["d"], "broad_or_shoulder", "supports", "Broad/asymmetric peak or shoulder detected.", 0.2, rule_id="behavior_broad_or_shoulder"))
            break

    # Moore & Reynolds: quartzo e comum na fracao argila, tem posicoes
    # praticamente invariantes e pode funcionar como padrao interno. No painel
    # isso entra apenas como marcador auxiliar/competidor, principalmente
    # porque 3.34 A interfere com ilita e ~1.54 A pode interferir com 060.
    all_peaks = n + g + c
    quartz_100 = _find_named_peak(all_peaks, "quartz_100")
    quartz_101 = _find_named_peak(all_peaks, "quartz_101")
    if quartz_100 and quartz_101:
        behaviors.append("quartz_internal_standard_pattern")
        relations.append(relation("quartz:%0.2fA" % quartz_100["d"], "quartz:%0.2fA" % quartz_101["d"], "supports", "Quartz 100/101 pair detected as auxiliary internal standard/competitor.", 0.2, quartz_101["d"] - quartz_100["d"], rule_id="behavior_quartz_internal_standard"))

    # Se existe indicio de migracao N->G mas a regra completa nao foi satisfeita,
    # a engine registra expansao parcial em vez de forcar mineral puro.
    if "expands_with_glycol" not in behaviors and n14 and g17:
        behaviors.append("partial_expansion_with_glycol")

    # A saida e ordenada e sem duplicatas para facilitar testes, comparacao JSON
    # e reproducibilidade entre execucoes.
    return {
        "policy": POLICY,
        "peaks": normalized,
        "behaviors": sorted(set(behaviors)),
        "relations": relations,
        "input_completeness": {
            "has_N": bool(n),
            "has_G": bool(g),
            "has_C": bool(c),
            "treatment_count": sum(1 for key in ("N", "G", "C") if normalized[key]),
            "peak_count": sum(len(normalized[key]) for key in ("N", "G", "C")),
        },
    }
