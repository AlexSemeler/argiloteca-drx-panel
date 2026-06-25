"""
Argiloteca DRX V3 - arvore decisoria explicavel para argilominerais.

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
    - interpret_ngc chama detect_mixed_layers para nao forcar mineral puro
      quando ha banda larga, ombro, expansao parcial ou sequencia nao resolvida;
    - _build_candidates mantem competidores e warnings quando ha sobreposicao
      de picos, evitando identificacao por tabela simples;
    - score_candidate recebe ambiguidades e completude para impedir confianca
      alta em dados incompletos.

Referencia estrutural aplicada:
    Meunier, Clays, 2005.
    Arquivo local: /home/invenio/invenio-project/Clays_Meunier.pdf

Como a logica de Meunier esta aplicada:
    - classify_octahedral classifica d060 como evidencia auxiliar
      dioctaedrica, intermediaria ou trioctaedrica.
    - _build_candidates usa essa classe para refinar esmectitas
      dioctaedricas/trioctaedricas, clorita, biotita, kerolita e serpentina.
    - detect_mixed_layers e LITERATURE_DIAGNOSTIC_RANGES trazem as estruturas
      2:1, 2:1:1, fibrosas/canais e interestratificadas descritas por Meunier.
    - interpret_ngc preserva essas evidencias em octahedral_classification,
      mixed_layer_candidates, range_comparison, provenance e references.

Referencia aplicada para Moore & Reynolds:
    - O fluxo de interpretacao explicita que quartzo pode ser competidor e
      padrao interno, sobretudo em 3.34 A e na interferencia d060 ~1.54 A.
    - A separacao caulinita/clorita, vermiculita/esmectita e minerais fibrosos
      permanece dependente de tratamentos, picos companheiros, morfologia e
      montagens adequadas, nao de match unico de faixa.
    - _recommended_tests adiciona glicerol, K-saturacao, aquecimento moderado
      e verificacao de padrao de quartzo quando as ambiguidades aparecem.

Objetos/funcoes envolvidos:
    - interpret_ngc: orquestra a engine e injeta mixed_layer_candidates;
    - _build_candidates: transforma comportamento em candidatos auxiliares;
    - combined_candidates: lista final ordenada por score;
    - diagnostic_graph: grafo de evidencias/regras exibido e exportado.

No sistema Argiloteca, o fluxograma foi convertido em uma engine deterministica
e auditavel. A engine combina:

    1. comportamento N->G->C;
    2. conjuntos de picos companheiros;
    3. reflexao 060 quando disponivel;
    4. ambiguidades mineralogicas;
    5. referencias bibliograficas, empiricas e contexto Pre-Sal;
    6. motor de confianca e serializacao InvenioRDM.

Principio cientifico central:
    nenhum mineral e confirmado por pico isolado, intensidade isolada ou match
    simples de faixa. Toda saida e auxiliar, com
    policy="argiloteca_rule_based_diagnostic".

Padrao de engenharia:
    - funcoes puras, sem estado global mutavel;
    - sem loop infinito ou servico residente;
    - loops finitos sobre candidatos/interestratificados detectados;
    - dados retornados em JSON estruturado e testavel;
    - regras pequenas e rastreaveis por evidencia, competidores e explicacao;
    - saida compativel com painel DRX e exportacao InvenioRDM.


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

from .ambiguity_rules import evaluate_ambiguities
from .chapter7_knowledge import SOURCE_ID as CHAPTER7_SOURCE_ID
from .chapter7_knowledge import chapter7_profile, chapter7_rule_index, get_chapter7_knowledge
from .confidence_engine import score_candidate
from .diagnostic_behavior_rules import ENGINE_VERSION, POLICY
from .diagnostic_graph import build_diagnostic_graph
from .diagnostic_peak_rules import named_range
from .evidences import evidence, find_peak
from .literature_ranges import LITERATURE_DIAGNOSTIC_RANGES, REFERENCES
from .mixed_layer_engine import detect_mixed_layers
from .octahedral_classifier import classify_octahedral
from .peak_sets import evaluate_peak_sets
from .presalt_reference_dataset import PRESALT_REFERENCE_DATASET
from .range_comparator import compare_ranges
from .serializers import serialize_for_invenio
from .treatment_interpreter import interpret_treatments


def _find_named_peak(peaks, range_id):
    """Busca pico usando as faixas operacionais do catalogo central."""
    return find_peak(peaks, *named_range(range_id))


def _candidate(label, family, behavior_score, peak_set_score, d060_score, thermal_score, proximity_score, evidences, explain, competitors=None, warnings=None, requires_companions=False):
    """
    Cria um candidato mineralogico padronizado.

    Args:
        label: Identificador do mineral, grupo ou interestratificado.
        family: Familia mineralogica usada para agrupamento no painel.
        behavior_score: Peso da resposta N/G/C.
        peak_set_score: Peso dos picos companheiros avaliados em peak_sets.py.
        d060_score: Peso da reflexao 060 quando disponivel.
        thermal_score: Peso da resposta ao aquecimento.
        proximity_score: Peso da proximidade aos intervalos esperados.
        evidences: Lista de evidencias explicaveis.
        explain: Texto curto para o painel e JSON.
        competitors: Minerais que competem pela mesma janela diagnostica.
        warnings: Alertas cientificos ou de completude.
        requires_companions: Indica que picos companheiros sao obrigatorios
            para evitar conclusao por pico isolado.

    Returns:
        dict: Candidato no contrato interno da engine.

    Aplicacao de Meunier:
        o objeto guarda family, d060_score, thermal_score e competitors para
        transportar a leitura estrutural (dioctaedrico/trioctaedrico, 2:1,
        2:1:1, fibroso ou interestratificado) ate o motor de confianca e o
        painel.
    """
    return {
        "label": label,
        "family": family,
        "behavior_score": behavior_score,
        "peak_set_score": peak_set_score,
        "d060_score": d060_score,
        "thermal_score": thermal_score,
        "proximity_score": proximity_score,
        "evidences": evidences,
        "relations": [],
        "explain": explain,
        "competitors": competitors or [],
        "warnings": warnings or [],
        "requires_companions": requires_companions,
    }


def _behavior_candidates(behavior):
    """
    Liga cada marcador comportamental N/G/C as relacoes com valores observados.

    A engine de tratamento gera dois niveis de saida: uma lista curta de
    comportamentos e uma lista auditavel de relacoes N->G->C. Esta funcao une as
    duas para o painel nao exibir apenas nomes como stable_after_glycol.
    """
    behavior = behavior or {}
    relations = behavior.get("relations") or []
    by_behavior = {
        "expands_with_glycol": ("behavior_expand_glycol",),
        "collapses_after_heating": ("behavior_collapse_heat",),
        "stable_after_glycol": ("behavior_stable_glycol",),
        "persists_after_heating": ("behavior_persist_heat",),
        "disappears_after_heating": ("behavior_disappears_heat",),
        # Capitulo 7, X-Ray Diffraction and the Identification and Analysis of
        # Clay Minerals: a caulinita perde/reduz fortemente o 7 A apos
        # aquecimento, enquanto clorita tende a persistir e pode aumentar em
        # 14 A. Estes IDs ligam a deteccao numerica de treatment_interpreter.py
        # as relacoes explicaveis exibidas no painel.
        "strongly_reduced_after_heating": ("chapter7_kaolin_heat_loss",),
        "increases_intensity_after_heating": ("chapter7_chlorite_heat_intensity",),
        "appears_after_heating": ("behavior_appears_heat",),
        "broad_or_shoulder": ("behavior_broad_or_shoulder",),
        "quartz_internal_standard_pattern": ("behavior_quartz_internal_standard",),
        "partial_expansion_with_glycol": ("behavior_expand_glycol", "corrensite_flow"),
        "rational_sequence": ("corrensite_flow",),
        "ordered_chlorite_smectite": ("corrensite_flow",),
    }
    out = []
    for item in behavior.get("behaviors") or []:
        rule_ids = by_behavior.get(item, ())
        matched = [
            row for row in relations
            if row.get("rule_id") in rule_ids or row.get("type") == item
        ]
        out.append({
            "behavior": item,
            "relations": matched,
            "values": [
                "%s -> %s" % (row.get("source") or "N/D", row.get("target") or "N/D")
                for row in matched
            ],
            "explanations": [
                row.get("explanation")
                for row in matched
                if row.get("explanation")
            ],
        })
    return out


def _infer_d060_from_peaks(behavior):
    """
    Procura uma reflexao candidata a 060 nos picos N/G/C quando d060 nao veio
    como metadado explicito.

    A inferencia fica limitada a janela 1.485-1.555 A e e marcada como
    auxiliar, porque Moore & Reynolds alerta que quartzo perto de 1.54 A pode
    interferir na leitura. O valor inferido nunca confirma mineral sozinho.
    """
    candidates = []
    for preparation, rows in ((behavior or {}).get("peaks") or {}).items():
        for peak in rows or []:
            try:
                d_value = float(peak.get("d"))
            except (TypeError, ValueError):
                continue
            if 1.485 <= d_value <= 1.555:
                centers = (1.50, 1.52, 1.54)
                candidates.append({
                    "d": d_value,
                    "preparation": preparation,
                    "intensity": peak.get("intensity"),
                    "distance": min(abs(d_value - center) for center in centers),
                })
    if not candidates:
        return None
    candidates.sort(key=lambda row: (row["distance"], -float(row.get("intensity") or 0.0)))
    return candidates[0]


def _peak_set_score(peak_sets, label):
    """
    Recupera a pontuacao de um conjunto de picos companheiros.

    O loop e finito e percorre apenas a lista calculada por evaluate_peak_sets.
    Quando o conjunto nao foi reconhecido, retorna 0.0 para manter a regra
    conservadora.
    """
    for row in peak_sets:
        if row["label"] == label:
            return row["score"]
    return 0.0


def _context_has(metadata, *terms):
    """
    Verifica contexto e quimica textual para reforcos auxiliares.

    Usado para distinguir hipoteses que compartilham comportamento DRX, por
    exemplo saponita versus estevensita em contexto Mg/Pre-Sal. Esse metodo nao
    confirma mineral sozinho; apenas aumenta suporte contextual.

    Meunier entra aqui como criterio contextual para argilominerais
    magnesianos: saponita, estevensita, kerolita e K/S compartilham janelas DRX
    e precisam de quimica/contexto para ganhar especificidade.
    """
    context = " ".join(str(value).lower() for value in ((metadata or {}).get("context") or []))
    chemistry = " ".join("%s %s" % (key, value) for key, value in ((metadata or {}).get("chemistry") or {}).items()).lower()
    text = context + " " + chemistry
    return any(term.lower() in text for term in terms)


def _build_candidates(behavior, peak_sets, octahedral, metadata):
    """
    Converte comportamentos N/G/C em candidatos mineralogicos.

    Args:
        behavior: Saida de treatment_interpreter.interpret_treatments.
        peak_sets: Candidatos por picos companheiros.
        octahedral: Classificacao auxiliar da reflexao 060.
        metadata: Contexto, morfologia e quimica disponiveis.

    Returns:
        list[dict]: Candidatos ainda sem pontuacao final de confianca.

    Observacao de arquitetura:
        Esta funcao e a traducao mais direta do fluxograma USGS para regras de
        codigo. Cada bloco if representa uma decisao mineralogica rastreavel.

    Aplicacao de Meunier:
        os blocos abaixo usam d060, expansibilidade, persistencia termica e
        estrutura 1:1, 2:1, 2:1:1, fibrosa/canal ou interestratificada para
        transformar comportamento N/G/C em candidatos auxiliares.
    """
    peaks = behavior["peaks"]
    b = set(behavior["behaviors"])
    n = peaks["N"]
    g = peaks["G"]
    c = peaks["C"]
    candidates = []

    # Meunier + fluxograma: esmectitas 2:1 expandem com etilenoglicol e
    # colapsam com aquecimento. d060/contexto Mg refinam para
    # saponita/estevensita ou esmectita dioctaedrica, mas nao confirmam especie.
    if "expands_with_glycol" in b and "collapses_after_heating" in b:
        d060_kind = octahedral.get("octahedral_type")
        candidates.append(_candidate(
            "smectite_group",
            "smectite_group",
            1.0,
            _peak_set_score(peak_sets, "smectite_group"),
            0.5 if d060_kind != "unknown" else 0.0,
            1.0,
            0.8,
            [evidence("smectite_ngc", "behavior", "Basal peak expands after glycolation and collapses after heating.", 0.8)],
            "Pico basal expandiu em G e colapsou para ~10 A em C; usar como grupo esmectitico auxiliar.",
            competitors=[{"competitor": "vermiculite", "reason": "14 A natural can overlap without full expansion."}, {"competitor": "chlorite_smectite", "reason": "Mixed layers can show partial expandable behavior."}],
        ))
        if d060_kind in {"trioctahedral", "intermediate"} or _context_has(metadata, "Mg", "presalt", "lacustrine", "evaporitic"):
            label = "stevensite" if _context_has(metadata, "presalt", "evaporitic", "lacustrine") else "saponite"
            candidates.append(_candidate(
                label,
                "smectite_group",
                0.9,
                _peak_set_score(peak_sets, "smectite_group"),
                1.0 if d060_kind == "trioctahedral" else 0.5,
                0.8,
                0.7,
                [evidence("trioctahedral_smectite", "d060_context", "Expandable smectite with trioctahedral/Mg contextual support.", 0.7)],
                "Esmectita expansiva com evidencia auxiliar de carater trioctaedrico/Mg; saponita e estevensita competem por quimica.",
                competitors=[{"competitor": "saponite", "reason": "comportamento expansivo semelhante; distinguir por Mg-Al e carga."}, {"competitor": "stevensite", "reason": "Mg trioctahedral smectite; contexto Pre-Sal reforca."}],
            ))
        elif d060_kind == "dioctahedral":
            candidates.append(_candidate(
                "montmorillonite_or_nontronite",
                "smectite_group",
                0.85,
                _peak_set_score(peak_sets, "smectite_group"),
                1.0,
                0.8,
                0.6,
                [evidence("dioctahedral_smectite", "d060", "Expandable smectite with d060 near dioctahedral range.", 0.7)],
                "Esmectita dioctaedrica provavel; separar montmorillonita/nontronita exige quimica.",
                competitors=[{"competitor": "saponite", "reason": "expansao semelhante, d060 e quimica separam."}],
            ))

    # Meunier + fluxograma: cloritas 2:1:1 mantem 14 A em N/G/C, sem expansao
    # para ~17 A. A regra exige picos companheiros porque 14 A tambem pode
    # representar esmectita, vermiculita ou C/S.
    if _find_named_peak(n, "chlorite_14a_n") and _find_named_peak(g, "chlorite_14a_g") and _find_named_peak(c, "chlorite_14a_c"):
        candidates.append(_candidate(
            "chlorite",
            "chlorite_group",
            0.85,
            _peak_set_score(peak_sets, "chlorite_group"),
            1.0 if octahedral.get("octahedral_type") == "trioctahedral" else 0.3,
            0.9,
            0.8,
            [evidence("chlorite_ngc", "behavior", "14 A peak persists through N/G/C without expansion to 17 A.", 0.7)],
            "Clorita e favorecida por conjunto 14/7/4.72/3.53 A persistente e ausencia de expansao glicolada.",
            competitors=[{"competitor": "vermiculite", "reason": "14 A without glycol expansion can overlap; heating collapse separates."}, {"competitor": "smectite", "reason": "smectite expands to ~17 A."}],
            requires_companions=True,
        ))
        if octahedral.get("octahedral_type") == "dioctahedral":
            candidates.append(_candidate(
                "dioctahedral_chlorite",
                "chlorite_group",
                0.75,
                _peak_set_score(peak_sets, "chlorite_group"),
                1.0,
                0.8,
                0.7,
                [evidence("dioctahedral_chlorite", "d060", "Chlorite-like behavior with d060 near 1.50 A.", 0.7)],
                "Hipotese de clorita dioctaedrica; requer quimica e padrao 060/hkl.",
            ))

    # Meunier + fluxograma: vermiculita compete na janela 14 A, com pouca ou
    # nenhuma expansao glicolada e colapso parcial/total para 10-12 A apos
    # aquecimento. Mantida como hipotese provisoria.
    if _find_named_peak(n, "vermiculite_14a") and _find_named_peak(g, "vermiculite_14a") and _find_named_peak(c, "vermiculite_collapse"):
        candidates.append(_candidate(
            "vermiculite",
            "vermiculite_group",
            0.75,
            0.35,
            0.3,
            0.8,
            0.6,
            [evidence("vermiculite_flow", "behavior", "14 A peak does not expand clearly and collapses partly/totally with heating.", 0.7)],
            "Vermiculita e hipotese provisoria quando 14 A nao expande e colapsa para ~10-12 A.",
            competitors=[{"competitor": "chlorite", "reason": "chlorite persists at 14 A after heating."}, {"competitor": "smectite", "reason": "smectite expands to ~17 A in G."}],
        ))

    # Meunier + fluxograma: ilita/mica 2:1 nao expansiva preserva ~10 A nos
    # tres tratamentos. O pico ~3.33 A e tratado com competidor quartzo para
    # evitar falso positivo.
    if _find_named_peak(n, "illite_10a") and _find_named_peak(g, "illite_10a") and _find_named_peak(c, "illite_10a"):
        candidates.append(_candidate(
            "illite_mica",
            "illite_mica",
            0.85,
            _peak_set_score(peak_sets, "illite_mica"),
            0.6 if octahedral.get("octahedral_type") != "unknown" else 0.0,
            0.8,
            0.8,
            [evidence("illite_mica_ngc", "behavior", "10 A peak is stable through N/G/C.", 0.7)],
            "Ilita/mica e favorecida por 10 A estavel nos tres tratamentos, com 5 A e 3.33 A como suporte.",
            competitors=[{"competitor": "quartz", "reason": "3.33-3.34 A can be quartz unless 10 A and 5 A are present."}, {"competitor": "palygorskite", "reason": "10.5 A fibrous clay can overlap in low resolution."}],
            requires_companions=True,
        ))
        if octahedral.get("octahedral_type") == "trioctahedral":
            candidates.append(_candidate(
                "biotite",
                "illite_mica",
                0.55,
                _peak_set_score(peak_sets, "illite_mica"),
                1.0,
                0.6,
                0.5,
                [evidence("biotite_flow", "d060", "10 A mica-like peak with d060 near 1.54 A.", 0.6)],
                "Biotita e competidor mica trioctaedrico; exige quimica/padrao de po.",
            ))

    # Brindley & Brown, 1980 aplicado aqui: as reflexoes ~7 A e ~3.57 A entram
    # como suporte do grupo da caulinita, mas a decisao usa comportamento N/G/C
    # para evitar identificacao por pico isolado. Por isso a regra retorna
    # kaolin_group, nao kaolinite/dickite/nacrite como especie.
    n7 = _find_named_peak(n, "kaolinite_7a_n")
    g7 = _find_named_peak(g, "kaolinite_7a_g")
    c7 = _find_named_peak(c, "kaolinite_7a_c_check")
    kaolin_thermal_loss = not c7 or "strongly_reduced_after_heating" in b
    if n7 and g7 and kaolin_thermal_loss:
        candidates.append(_candidate(
            "kaolin_group",
            "kaolin_group",
            0.85,
            _peak_set_score(peak_sets, "kaolin_group"),
            0.7 if octahedral.get("octahedral_type") == "dioctahedral" else 0.2,
            1.0,
            0.8,
            [evidence("chapter7_kaolin_heat_loss", "behavior", "7 A peak stays after glycolation and disappears/reduces strongly after heating.", 0.8)],
            "Comportamento N-G-C favorece grupo da caulinita; especie requer hkl/morfologia.",
            competitors=[{"competitor": "chlorite", "reason": "chlorite contributes near 7 A but should have 14/4.72/3.53 A."}, {"competitor": "serpentine", "reason": "serpentine also occurs near 7 A and may persist."}],
            requires_companions=True,
        ))

    # Meunier + Pre-Sal: kerolita/talco sao argilominerais magnesianos 2:1
    # nao expansivos. Pico ~9.4 A compete com talco/ilita e exige suporte
    # quimico/contextual para interpretacao mais forte.
    if _find_named_peak(n, "kerolite_9_4a") and _find_named_peak(g, "kerolite_9_4a") and not _find_named_peak(g, "smectite_g"):
        candidates.append(_candidate(
            "kerolite",
            "talc_kerolite_group",
            0.75,
            _peak_set_score(peak_sets, "kerolite_talc"),
            0.8 if octahedral.get("octahedral_type") == "trioctahedral" else 0.2,
            0.5,
            0.7,
            [evidence("kerolite_presalt", "behavior", "9.35-9.45 A non-expandable peak; Mg/pre-salt context strengthens.", 0.7)],
            "Kerolita e hipotese auxiliar para pico ~9.4 A nao expansivel, especialmente com contexto magnesiano/Pre-Sal.",
            competitors=[{"competitor": "talc", "reason": "talco/kerolita exigem cristalinidade e quimica."}, {"competitor": "illite_mica", "reason": "10 A mica-like phase can be close in low resolution."}],
        ))

    # Meunier + fluxograma: sepiolita e mineral fibroso/canal, com janela
    # ~12-12.5 A estavel. O fluxograma recomenda morfologia e reflexoes
    # adicionais; por isso a saida permanece auxiliar.
    if _find_named_peak(n, "sepiolite_12a") and _find_named_peak(g, "sepiolite_12a"):
        candidates.append(_candidate(
            "sepiolite",
            "fibrous_channel",
            0.65,
            _peak_set_score(peak_sets, "sepiolite"),
            0.2,
            0.5,
            0.6,
            [evidence("sepiolite_flow", "behavior", "12-12.5 A peak does not expand with glycolation.", 0.6)],
            "Sepiolita requer morfologia fibrosa/hkl; N/G/C sozinho e auxiliar.",
        ))

    # Meunier + fluxograma: paligorsquita e fibrosa/canal, com janela
    # ~10.3-10.5 A estavel. Compete com fases 10 A e deve ser validada por
    # morfologia fibrosa e hkl adicionais.
    if _find_named_peak(n, "palygorskite_10_5a") and _find_named_peak(g, "palygorskite_10_5a"):
        candidates.append(_candidate(
            "palygorskite",
            "fibrous_channel",
            0.65,
            _peak_set_score(peak_sets, "palygorskite"),
            0.2,
            0.5,
            0.6,
            [evidence("palygorskite_flow", "behavior", "10.3-10.5 A peak does not expand with glycolation.", 0.6)],
            "Paligorsquita requer morfologia fibrosa/hkl; compete com 10 A mica/halloysita.",
        ))

    # Meunier + fluxograma: serpentina e trioctaedrica e pode ocupar 7 A. A
    # regra existe para nao classificar automaticamente todo 7 A como caulinita.
    if _find_named_peak(n, "chlorite_7a") and _find_named_peak(g, "chlorite_7a") and _find_named_peak(c, "chlorite_7a") and octahedral.get("octahedral_type") == "trioctahedral":
        candidates.append(_candidate(
            "serpentine",
            "serpentine_group",
            0.55,
            0.2,
            1.0,
            0.4,
            0.5,
            [evidence("serpentine_flow", "d060_behavior", "7 A non-expanding peak with trioctahedral d060.", 0.5)],
            "Serpentina compete com caulinita/clorita no 7 A; morfologia/hkl sao necessarios.",
        ))

    return candidates


def _recommended_tests(candidates, ambiguities, octahedral):
    """
    Gera proximos testes recomendados a partir das incertezas detectadas.

    A regra usa conjuntos para evitar duplicidade e retorna lista ordenada para
    garantir reproducibilidade em testes automatizados e JSON de auditoria.
    """
    tests = {"FTIR", "padrao de po randomico", "validacao por especialista"}
    windows = {row.get("window") for row in ambiguities}
    if windows & {"7 A", "14 A"}:
        tests.update({"aquecimento controlado 400/550 C", "pico 060"})
    # Moore & Reynolds: 14 A nao separa sozinho clorita, vermiculita,
    # esmectita Mg/Ca ou C/S. Glicerol, K-saturacao e aquecimento moderado
    # ajudam a testar colapso/expansao operacional da vermiculita.
    if "14 A" in windows:
        tests.update({"glicerol", "K-saturacao", "aquecimento 300 C por 1 h"})
    # Moore & Reynolds: 3.34 A e 1.54 A podem ser quartzo. A recomendacao
    # força checagem do padrao de quartzo antes de usar esses picos como ilita
    # ou d060 trioctaedrico.
    if windows & {"3.33-3.34 A", "d060/quartz 1.54 A"}:
        tests.update({"verificar padrao de quartzo 4.26/3.34/1.82 A", "usar quartzo como padrao interno se presente"})
    if "7 A" in windows:
        tests.update({"verificar clorita 003/004", "formamida ou DMSO para haloisita/caulinita quando necessario"})
    if octahedral.get("octahedral_type") == "unknown":
        tests.add("medir/refinar reflexao 060")
    labels = {candidate.get("label") for candidate in candidates}
    if labels & {"stevensite", "saponite", "kerolite", "kerolite_stevensite_mixed_layer"}:
        tests.update({"quimica Mg-Al-Fe", "saturacao Mg/K", "modelagem de interestratificados"})
    if labels & {"sepiolite", "palygorskite", "halloysite_10a", "serpentine"}:
        tests.add("microscopia/morfologia")
    return sorted(tests)


def interpret_ngc(peaks, metadata=None, empirical_ranges=None):
    """
    Executa a engine completa de interpretacao N/G/C.

    Args:
        peaks: Dicionario de picos separados por preparacao ("N", "G", "C").
        metadata: Metadados opcionais, incluindo d060, contexto, morfologia e
            quimica.
        empirical_ranges: Faixas empiricas locais opcionais para comparacao com
            literatura e dataset Pre-Sal.

    Returns:
        dict: Payload com chave "diagnostic_interpretation", pronto para o
        painel DRX e para serializacao InvenioRDM.

    Fluxo de execucao:
        1. interpreta comportamento N/G/C;
        2. avalia picos companheiros;
        3. classifica d060;
        4. calcula ambiguidades;
        5. compara faixas literatura/empirico/Pre-Sal;
        6. detecta interestratificados;
        7. monta candidatos;
        8. pontua confianca;
        9. serializa saida explicavel.

    Looping e complexidade:
        os dois loops principais percorrem listas pequenas de
        interestratificados e candidatos. Nao ha loop constante em background;
        cada chamada e independente e termina apos processar a amostra recebida.

    Meunier neste fluxo:
        a referencia aparece nos dados de literatura, na classificacao 060,
        nos candidatos magnesianos/fibrosos e nos interestratificados. O retorno
        preserva isso em octahedral_classification, mixed_layer_candidates,
        provenance e references.
    """
    metadata = metadata or {}
    # Camada 1: comportamento fisico entre tratamentos, base da decisao.
    behavior = interpret_treatments(peaks, metadata=metadata)
    # Camada 2: picos companheiros reduzem falsos positivos por pico isolado.
    peak_sets = evaluate_peak_sets(behavior["peaks"])
    # Camada 3: Meunier aplicado diretamente; d060 auxilia
    # dioctaedrico/trioctaedrico, sem confirmar especie.
    explicit_d060 = metadata.get("d060")
    inferred_d060 = None if explicit_d060 is not None else _infer_d060_from_peaks(behavior)
    octahedral = classify_octahedral(explicit_d060 if explicit_d060 is not None else (inferred_d060 or {}).get("d"), candidate=None)
    if inferred_d060 and explicit_d060 is None:
        octahedral["source"] = "inferred_from_ngc_peak_window"
        octahedral["preparation"] = inferred_d060.get("preparation")
        octahedral["intensity"] = inferred_d060.get("intensity")
        octahedral.setdefault("warnings", []).append("d060 inferred from a peak in 1.485-1.555 A; verify with random powder mount and quartz interference check.")
    # Camada 4: janelas problematicas sao explicitadas ao usuario.
    ambiguities = evaluate_ambiguities(behavior["peaks"], behavior["behaviors"], metadata)
    # Camada 5: compara referencias. Os registros com meunier_2005 trazem
    # estrutura, d060 e expansibilidade, mas match de faixa continua hipotese.
    range_comparison = compare_ranges(behavior["peaks"], empirical=empirical_ranges or {})
    # Camada 6: Meunier fornece componentes estruturais e Lanson trata ordem;
    # interestratificados entram como candidatos proprios, nao como soma simples
    # de minerais puros.
    mixed_layers = detect_mixed_layers(behavior["peaks"], behavior["behaviors"], metadata)
    candidates = _build_candidates(behavior, peak_sets, octahedral, metadata)
    # Loop finito sobre interestratificados detectados para inseri-los na mesma
    # esteira de pontuacao dos demais candidatos.
    for mixed in mixed_layers:
        candidates.append(_candidate(
            mixed["mixed_layer_candidate"],
            "mixed_layer",
            0.8 if mixed["confidence"] == "high" else 0.6,
            0.5,
            0.4,
            0.5,
            0.6,
            [evidence("mixed_layer_engine", "mixed_layer", mixed["explanation"], 0.6)],
            mixed["explanation"],
            warnings=["Mixed-layer candidate: do not report a pure mineral without alert."],
        ))
    scored = []
    # Loop finito sobre candidatos. O motor de confianca bloqueia confianca alta
    # quando falta tratamento, ha poucos picos ou existe ambiguidade severa.
    for candidate in candidates:
        contraindications = []
        stats = score_candidate(candidate, behavior["input_completeness"], ambiguities=ambiguities, contradictions=contraindications)
        candidate = {**candidate, **stats}
        candidate["score"] = round(candidate["score"] / 100.0, 3)
        scored.append(candidate)
    scored.sort(key=lambda row: row.get("score", 0), reverse=True)
    combined = scored[:8]
    warnings = list(range_comparison.get("warnings") or [])
    if any(row.get("window") == "d060/quartz 1.54 A" for row in ambiguities):
        warnings.append("Moore & Reynolds: pico perto de d060 ~1.54 A pode incluir quartzo; verificar reflexoes de quartzo antes de usar 060 como suporte trioctaedrico.")
    if any(row.get("window") == "3.33-3.34 A" for row in ambiguities):
        warnings.append("Moore & Reynolds: 3.33-3.34 A pode ser quartzo; ilita/mica requer 10 A e preferencialmente 5 A persistentes.")
    if any(row.get("window") == "14 A" for row in ambiguities):
        warnings.append("Moore & Reynolds: 14 A exige resposta a glicol/glicerol/K/aquecimento para separar clorita, vermiculita, esmectita e interestratificados.")
    warnings.append("Diagnostico confirmado apenas no escopo das regras DRX N/G/C da Argiloteca; casos ambiguos ainda exigem verificacao mineralogica complementar.")
    # Capitulo 7 aplicado como base de conhecimento executavel:
    # - get_chapter7_knowledge fornece contagens e metadados de proveniencia;
    # - chapter7_rule_index cria um dicionario rule_id -> regra para o painel
    #   responder "qual regra do livro originou esta decisao?";
    # - chapter7_profile retorna o perfil mineralogico do candidato, com
    #   reflexoes, comportamento, d060, intensidades e interferencias.
    # O loop abaixo percorre apenas os candidatos combinados finais, portanto
    # nao altera a pontuacao: ele so anexa explicabilidade e auditoria.
    chapter7_knowledge = get_chapter7_knowledge()
    chapter7_rules = chapter7_rule_index()
    chapter7_profiles = {
        candidate["label"]: chapter7_profile(candidate["label"])
        for candidate in combined
        if chapter7_profile(candidate["label"])
    }
    # Contrato publico da engine. Esta estrutura e consumida pelo painel,
    # exportadores JSON e serializador InvenioRDM.
    interpretation = {
        "policy": POLICY,
        "policy_scope": "rule_based_confirmation_within_argiloteca_ngc_engine",
        "diagnostic_labels": ["confirmed_by_rules", "probable_by_rules", "possible_by_rules"],
        "engine_version": ENGINE_VERSION,
        "method": "literature_empirical_presalt_flow_meunier_chapter7_ngc_behavior",
        "input_summary": behavior["input_completeness"],
        "literature_candidates": range_comparison["literature_matches"],
        "empirical_candidates": range_comparison["empirical_matches"],
        "presalt_candidates": range_comparison["presalt_matches"],
        "peak_set_candidates": peak_sets,
        "behavior_candidates": _behavior_candidates(behavior),
        "octahedral_classification": octahedral,
        "mixed_layer_candidates": mixed_layers,
        "combined_candidates": combined,
        "confidence_scores": {candidate["label"]: {"score": candidate["score"], "confidence": candidate["confidence"]} for candidate in combined},
        "competitors": [competitor for candidate in combined for competitor in candidate.get("competitors", [])],
        "ambiguities": ambiguities,
        "warnings": warnings,
        "recommended_next_tests": _recommended_tests(combined, ambiguities, octahedral),
        "provenance": {
            "reference_files": ["textos/flow.pdf", "textos/Clays_Meunier.pdf", "textos/MooreandReynolds.pdf", "textos/Adobe Scan 14 de mai. de 2026.pdf", "/home/invenio/Downloads/analises.pdf"],
            "references": REFERENCES,
            "presalt_reference_source": PRESALT_REFERENCE_DATASET["source"],
            "chapter7_source_id": CHAPTER7_SOURCE_ID,
            "chapter7_knowledge_counts": {
                "entities": len(chapter7_knowledge["entities"]),
                "diagnostic_rules": len(chapter7_knowledge["diagnostic_rules"]),
                "behavior_rules": len(chapter7_knowledge["behavior_rules"]),
                "d060_rules": len(chapter7_knowledge["d060_rules"]),
                "intensity_rules": len(chapter7_knowledge["intensity_rules"]),
                "mineral_profiles": len(chapter7_knowledge["mineral_profiles"]),
            },
        },
        "references": list(REFERENCES.values()),
        # Estruturas consumidas pela secao "Regra-fonte" da interface e pelo
        # exportador InvenioRDM. Elas preservam titulo da obra, capitulo,
        # pagina, tabela/figura e explicacao curta da regra.
        "source_rule_index": chapter7_rules,
        "source_mineral_profiles": chapter7_profiles,
        "range_comparison": range_comparison,
        "behavior_interpretation": behavior,
        "diagnostic_graph": build_diagnostic_graph(behavior["relations"], combined),
    }
    interpretation["invenio_rdm"] = serialize_for_invenio(interpretation)
    return {"diagnostic_interpretation": interpretation}
