"""
Argiloteca DRX V3 - hipoteses de argilominerais interestratificados.

Autor: Alexandre Ribas Semeler
E-mail: alexandre.semeler@ufrgs.br

Referencia aplicada:
    Lanson, B. & Bouchet, A. (1995). Identification des mineraux argileux
    par diffraction des rayons X: apport du traitement numerique.
    Bull. Centres Rech. Explor.-Prod. Elf Aquitaine, 19(1), 91-118.
    Arquivo local: /home/invenio/invenio-project/textos/
    lanson-1995-bull-centres-rech-ep-19-91.pdf

Como a logica da referencia esta aplicada neste arquivo:
    - detect_mixed_layers aplica a recomendacao de nao tratar bandas 00l
      largas, ombros, deslocamentos intermediarios e respostas parciais como
      minerais puros.
    - A funcao cria candidatos de interestratificados quando a resposta N/G/C
      e complexa, coerente com a discussao de Lanson & Bouchet sobre defeitos
      cristalinos, dominios coerentes pequenos e linhas 00l largas/irracionais.
    - Corrensita e tratada como entidade C/S ordenada quando ha sequencia longa
      coerente, e I/S, C/S, K/S e T/S sao retornados como hipoteses com alerta.

Referencia estrutural aplicada:
    Meunier, Clays, 2005.
    Arquivo local: /home/invenio/invenio-project/Clays_Meunier.pdf

Como a logica de Meunier esta aplicada neste arquivo:
    - Os componentes illite/smectite, chlorite/smectite,
      kerolite/stevensite e talc/smectite sao tratados como arquiteturas de
      camadas 2:1 e 2:1:1 interestratificadas, nao como soma simples de fases.
    - Corrensita e reconhecida como entidade C/S regular quando a sequencia
      N/G/C e compativel.
    - K/S e T/S usam a familia magnesiana talco-kerolita-estevensita como
      hipotese contextual auxiliar.

Capitulo 8 aplicado:
    Identification of Mixed-Layered Clay Minerals, da obra
    X-Ray Diffraction and the Identification and Analysis of Clay Minerals.

Como a logica do Capitulo 8 esta aplicada:
    - respostas N/G/C parciais, bandas largas, ombros e deslocamentos
      intermediarios geram candidatos interestratificados, nao mineral puro;
    - corrensita e tratada como chlorite/smectite ordenado quando ha reflexao
      longa em ~29 A, expansao com glicol para ~31-32 A e suporte termico;
    - I/S, C/S, K/S e T/S sao mantidos como hipoteses com `order` R1,
      R0|unknown ou unknown, porque o painel ainda nao faz modelagem 00l
      NEWMOD-like suficiente para resolver Reichweite por completo;
    - mistura fisica e interestratificacao permanecem separadas por alerta:
      a engine retorna hipotese e evidencia, mas nao confirma sequencia
      estrutural sem padrao 00l completo e comparacao observado-calculado.

Padrao de engenharia:
    modulo puro, sem estado global mutavel e sem loop residente. A funcao
    percorre apenas listas de picos da amostra recebida e retorna JSON
    estruturado para a arvore decisoria.


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

from .evidences import find_peak


def detect_mixed_layers(peaks_by_preparation, behaviors=None, metadata=None):
    """
    Detecta candidatos de interestratificados a partir dos picos e comportamentos.

    Args:
        peaks_by_preparation: Dicionario com picos normalizados em N, G e C.
        behaviors: Marcadores gerados por treatment_interpreter, incluindo
            partial_expansion_with_glycol e broad_or_shoulder.
        metadata: Contexto geologico e quimica, usado como reforco auxiliar.

    Returns:
        list[dict]: Candidatos de interestratificados, cada um com ordem,
        componentes, evidencias, explicacao e confianca.

    Aplicacao direta do Capitulo 8:
        a funcao materializa a regra "nao identificar interestratificados por
        pico isolado". Ela exige comportamento entre preparos, reflexoes de
        baixa angulacao, ombros/largura ou coexistencia de componentes antes de
        emitir uma hipotese mixed-layer.

    Objetos onde Lanson & Bouchet 1995 esta materializado:
        - mixed_layer_candidate: evita colapsar banda complexa em mineral puro;
        - order: expressa R1, R0 ou unknown quando a ordem nao pode ser
          resolvida por picos simples;
        - evidence: registra bandas largas, ombros, expansao parcial ou
          sequencia racional;
        - explanation: comunica ao painel por que a interpretacao e auxiliar.

    Objetos onde Meunier, Clays, 2005 esta materializado:
        - components: explicita os blocos estruturais 2:1/2:1:1 avaliados;
        - mixed_layer_candidate: preserva corrensita, K/S e T/S como entidades
          ou hipoteses interestratificadas;
        - order: separa sequencia regular de resposta parcial/indefinida.
    """
    behaviors = set(behaviors or [])
    n = (peaks_by_preparation or {}).get("N") or []
    g = (peaks_by_preparation or {}).get("G") or []
    c = (peaks_by_preparation or {}).get("C") or []
    context = set((metadata or {}).get("context") or [])
    chemistry = (metadata or {}).get("chemistry") or {}
    out = []

    # Corrensita/C-S regular: Meunier fornece a leitura estrutural como
    # interestratificado clorita/esmectita; Lanson reforca que a sequencia
    # longa N/G/C deve ser relatada como entidade, nao mistura simples.
    if find_peak(n, 28.5, 29.8) and find_peak(g, 30.8, 32.2):
        out.append({
            "mixed_layer_candidate": "corrensite",
            "order": "R1",
            "components": ["chlorite", "smectite"],
            "evidence": ["29 A in N expands to 31-32 A in G", "flow diagram ordered C/S rule"],
            "explanation": "Regular chlorite/smectite sequence supports corrensite as its own entity.",
            "confidence": "high" if find_peak(c, 23.5, 24.8) else "medium",
        })
    # Aplicacao direta de Lanson & Bouchet: expansao parcial, bandas largas ou
    # ombros indicam perfis complexos e possivelmente nao-racionais. A engine
    # retorna mixed-layer em vez de forcar ilita ou esmectita pura.
    if "partial_expansion_with_glycol" in behaviors or "broad_or_shoulder" in behaviors:
        out.append({
            "mixed_layer_candidate": "illite_smectite_or_random_mixed_layer",
            "order": "R0|unknown",
            "components": ["illite", "smectite"],
            "evidence": sorted(behaviors),
            "explanation": "Partial expansion, broad peaks or shoulders should be treated as mixed-layer evidence.",
            "confidence": "medium",
        })
    # C/S nao ordenado ou parcialmente ordenado: coexistencia de componente
    # cloritico 2:1:1 (~14 A) e componente esmectitico 2:1 expansivo (~17 A),
    # conforme a leitura estrutural de Meunier.
    if find_peak(n, 13.7, 14.8) and find_peak(g, 16.0, 17.8):
        out.append({
            "mixed_layer_candidate": "chlorite_smectite",
            "order": "R0|unknown",
            "components": ["chlorite", "smectite"],
            "evidence": ["14 A component with expandable component"],
            "explanation": "Chlorite-like and smectite-like responses coexist.",
            "confidence": "medium",
        })
    # Interestratificados magnesianos K/S: Meunier sustenta a relacao
    # kerolita/estevensita como hipotese estrutural magnesiana. O pico 9-10 A
    # e o contexto Mg/Pre-Sal nao confirmam mineral puro; geram hipotese a ser
    # validada por modelagem.
    if find_peak(n, 9.3, 10.0) and (find_peak(g, 16.0, 17.8) or "presalt" in context or chemistry.get("Mg")):
        out.append({
            "mixed_layer_candidate": "kerolite_stevensite_mixed_layer",
            "order": "unknown",
            "components": ["kerolite", "stevensite"],
            "evidence": ["9-10 A magnesian peak", "partial/contextual expandable component"],
            "explanation": "K/S hypothesis requires Mg chemistry and preferably modeling.",
            "confidence": "medium",
        })
    # T/S: associacao de reflexao talco/kerolita-like com componente expansivo.
    # Mantida como interestratificado por coerencia com Meunier e com a regra
    # de Lanson de nao forcar fase pura em perfis mistos.
    if find_peak(n, 9.3, 9.5) and find_peak(g, 16.0, 17.8):
        out.append({
            "mixed_layer_candidate": "talc_smectite",
            "order": "unknown",
            "components": ["talc_or_kerolite", "smectite"],
            "evidence": ["9.34 A talc-like peak plus expandable component"],
            "explanation": "T/S hypothesis; do not report pure talc or smectite without warning.",
            "confidence": "medium",
        })
    return out
