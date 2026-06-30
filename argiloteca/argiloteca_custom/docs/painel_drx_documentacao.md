# Painel DRX Argiloteca - Documentacao Tecnica

Autoria cientifica e curadoria: Alexandre Ribas Semeler.  
E-mail: alexandre.semler@ufrgs.br.

Este painel e fundamentado nas referencias cientificas revisadas: Brindley & Brown (1980), Bailey (1980/1988), Moore & Reynolds (1989/1997), Drits & Tchoubar (1990), Lanson & Bouchet (1995), Meunier, Clays (2005), fluxograma USGS de identificacao de argilominerais por DRX e referencias empiricas Pre-Sal UFRGS/Petrobras.

Politica cientifica: `argiloteca_rule_based_diagnostic`. O painel pode confirmar um argilomineral no escopo das regras N/G/C da Argiloteca quando ha evidencias convergentes suficientes. A confirmacao nunca deve vir de pico isolado, intensidade isolada ou match simples de faixa; ela combina comportamento N/G/C, picos companheiros, d060, ambiguidades, contexto, proveniencia e confianca.

Rotulos diagnosticos de saida:

| Rotulo | Significado |
|---|---|
| `confirmed_by_rules` | Confirmado pelas regras N/G/C da Argiloteca para o conjunto de dados disponivel. |
| `probable_by_rules` | Provavel pelas regras, mas com alguma evidencia complementar ausente ou ambiguidade moderada. |
| `possible_by_rules` | Possivel pelas regras, geralmente por dados incompletos, pico isolado, baixa coocorrencia ou ambiguidade forte. |

## Uso da Lei de Bragg

O Painel DRX usa a lei de Bragg para converter entre angulo difratometrico `2θ` e espacamento interplanar `d-spacing`.

Formula usada:

`nλ = 2d sinθ`

No codigo, a aplicacao operacional assume `n = 1`, usa por padrao radiacao Cu Kα com `λ ≈ 1.5406 Å`, e considera que o eixo do difratograma esta em `2θ`; portanto o calculo usa `θ = 2θ / 2`.

| Funcao | Arquivo | O que faz |
|---|---|---|
| `_two_theta_to_d_spacing` | `argiloteca/services/drx.py` | Converte `2θ` observado em `d-spacing` para enriquecer picos, diagnosticos e saidas do painel. |
| `_d_spacing_to_two_theta` | `argiloteca/services/drx.py` | Converte `d-spacing` de referencia em `2θ`, usado em comparacoes, calibracao e janelas teoricas. |
| `calculate_d_spacing` | `argiloteca_drx_core/curves.py` | Funcao reutilizavel do nucleo DRX para converter `2θ -> d`. |
| `calculate_two_theta` | `argiloteca_drx_core/curves.py` | Funcao reutilizavel do nucleo DRX para converter `d -> 2θ`. |
| `Diffractogram.d_spacing_axis` | `argiloteca_drx_core/diffractogram.py` | Calcula o eixo auxiliar `d-spacing` da curva carregada, preservando `2θ` como eixo experimental medido. |
| `Diffractogram.visualization_summary` | `argiloteca_drx_core/diffractogram.py` | Resume pontos, dominios, comprimento de onda, regra geometrica e avisos para o painel. |
| `braggDSpacing` | `argiloteca/static/js/drx-comparacao.js` | Conversao no frontend para exibicao/interacao no painel. |
| `braggTwoTheta` | `argiloteca/static/js/drx-comparacao.js` | Conversao no frontend para projetar referencias em `2θ`. |

Essas conversoes sao instrumentais: elas permitem comparar picos observados, picos companheiros e referencias em uma mesma escala. A conversao por Bragg nao confirma mineral sozinha; ela apenas fornece a base fisica para a avaliacao auxiliar N/G/C.

## Base Executavel do Capitulo 3

Fonte local: `/home/invenio/invenio-project/textos/difracao-geomentria.pdf`.

Capitulo: `Diffraction I: Geometry`.

O Capitulo 3 foi organizado no mesmo padrao do Capitulo 7 no modulo:

`argiloteca_drx/diagnostics/chapter3_geometry_knowledge.py`

Esse arquivo registra:

| Camada | Conteudo | Uso no motor |
|---|---|---|
| Fonte bibliografica | `CHAPTER3_SOURCE`, `SOURCE_ID` e PDF local | Proveniencia de calculos geometricos. |
| Entidades | `2θ`, `θ`, `λ`, `d-spacing`, Lei de Bragg, Laue, rede reciproca, esfera de Ewald e metodos | `CHAPTER3_ENTITIES` organiza a ontologia fisico-geometrica. |
| Equacoes | Bragg, primeira ordem, condicao `λ < 2d`, Laue e equacao cubica | `EQUATIONS` rastreia calculos de d-spacing e posicao esperada. |
| Regras geometricas | convencao θ/2θ, `2θ -> d`, `d -> 2θ`, limite geometrico e alargamento nao ideal | `GEOMETRY_RULES` explica calculos usados por Python e JavaScript. |
| Perfis de metodo | po, Laue e espectrometro de raios X | `METHOD_PROFILES` documenta geometria experimental. |
| Ontologia e schemas | classes fisicas, calculos, incertezas e schema de regra/equacao | `ONTOLOGY` e `SCHEMAS` apoiam indexacao e auditoria. |

Funcoes publicas:

| Funcao | Uso |
|---|---|
| `get_chapter3_geometry_knowledge()` | Retorna a base completa em copia profunda. |
| `chapter3_rule_index()` | Indexa regras geometricas por `rule_id`. |
| `chapter3_equation_index()` | Indexa equacoes por `equation_id`. |

## Base Executavel do Capitulo 8

Fonte local: `/home/invenio/invenio-project/textos/capitulo8.pdf`.

Capitulo: `Identification of Mixed-Layered Clay Minerals`.

O Capitulo 8 foi organizado no mesmo padrao do Capitulo 7 no modulo:

`argiloteca_drx/diagnostics/chapter8_mixed_layer_knowledge.py`

Esse arquivo registra:

| Camada | Conteudo | Uso no motor |
|---|---|---|
| Fonte bibliografica | `CHAPTER8_SOURCE`, `SOURCE_ID` e PDF local | Proveniencia das regras de interestratificados. |
| Entidades | mixed-layer, interstratification, Reichweite, R0/R1/R3, superestrutura, mistura fisica e sistemas minerais | `CHAPTER8_ENTITIES` organiza a semantica dos interestratificados. |
| Nomenclatura | componentes, proporcao e ordenamento | `NOMENCLATURE_RULES` preserva significado de nomes como R1 I/S. |
| Principios de Mering | reflexoes compostas, migracao, alargamento e superestrutura | `MERING_RULES` impede diagnostico por pico isolado. |
| Ordenamento | R0, R1 e R3 | `ORDERING_RULES` documenta uso de superestrutura e sequencia. |
| Comportamento entre tratamentos | corrensita, expansao parcial e C/S versus C/V | `TREATMENT_BEHAVIOR_RULES` alimenta hipoteses N/G/C. |
| Diagnostico diferencial | mistura fisica versus interestratificacao | `DIFFERENTIAL_RULES` preserva ambiguidades. |
| Perfis mixed-layer | corrensita, I/S, C/S e K/S | `MIXED_LAYER_PROFILES` explica componentes e evidencia minima. |
| Ontologia e schemas | classes mixed-layer, tratamento, reflexao e regra | `ONTOLOGY` e `SCHEMAS` apoiam JSON, InvenioRDM e OpenSearch. |

Funcoes publicas:

| Funcao | Uso |
|---|---|
| `get_chapter8_mixed_layer_knowledge()` | Retorna a base completa em copia profunda. |
| `chapter8_rule_index()` | Indexa regras de interestratificados por `rule_id`. |
| `chapter8_profile(profile_id)` | Retorna perfil de sistema mixed-layer. |

Exportacao da base do Capitulo 3:

```bash
/home/invenio/invenio-project/argiloteca-local/venvs/app-py310-l3/bin/python \
  argiloteca/argiloteca_custom/scripts/export_chapter3_geometry_knowledge.py
```

Exportacao da base do Capitulo 8:

```bash
/home/invenio/invenio-project/argiloteca-local/venvs/app-py310-l3/bin/python \
  argiloteca/argiloteca_custom/scripts/export_chapter8_mixed_layer_knowledge.py
```

Saida padrao:

`argiloteca_drx/diagnostics/data/generated/`

Arquivos exportados principais:

| Arquivo gerado | Conteudo |
|---|---|
| `chapter3_geometry_knowledge_complete.json` | Base geometrica completa. |
| `chapter3_geometry_export_manifest.json` | Manifesto da exportacao do Capitulo 3. |
| `chapter3_geometry_equations.json` | Equacoes e usos computacionais. |
| `chapter3_geometry_rules.json` | Regras de Bragg, convencao angular e limitacoes. |
| `chapter8_mixed_layer_knowledge_complete.json` | Base completa de interestratificados. |
| `chapter8_mixed_layer_export_manifest.json` | Manifesto da exportacao do Capitulo 8. |
| `chapter8_mering_rules.json` | Principios de Mering estruturados. |
| `chapter8_ordering_rules.json` | Regras R0/R1/R3. |
| `chapter8_treatment_behavior_rules.json` | Comportamento entre preparacoes. |
| `chapter8_mixed_layer_profiles.json` | Perfis por sistema mixed-layer. |

## Núcleo Reutilizável `argiloteca_drx_core`

Os scripts em `argiloteca_drx_core` foram ampliados para consumir a logica dos
Capitulos 3, 7 e 8 por uma API leve, sem dependencia direta de Flask/Invenio.

| Arquivo | Funcao | Capitulo aplicado |
|---|---|---|
| `argiloteca_drx_core/geometry.py` | Calcula Bragg com explicacao auditavel, valida `2θ -> θ -> d` e projeta `d -> 2θ`. | Capitulo 3 |
| `argiloteca_drx_core/diffractogram.py` | Define a classe `Diffractogram`, modelo canonico de curva 1D para visualizacao, dominios, normalizacao e metadados geometricos. | Capitulo 3 |
| `argiloteca_drx_core/peaks.py` | Normaliza picos de ALS, lmfit, scripts de lote e JSONs para o contrato N/G/C. | Capitulos 3, 7 e 8 |
| `argiloteca_drx_core/knowledge.py` | Expoe `get_scientific_knowledge()`, `get_rule_indexes()` e resumo de fontes. | Capitulos 3, 7 e 8 |
| `argiloteca_drx_core/curves.py` | Mantem parsing de curvas e funcoes Bragg basicas com docstrings do Capitulo 3. | Capitulo 3 |

Novas funcoes publicas:

| Funcao | Uso |
|---|---|
| `Diffractogram(...)` | Representa uma curva 1D `2θ/intensidade` validada para visualizacao e auditoria. |
| `Diffractogram.from_curve_data(curve)` | Converte `CurveData` do parser RAW/texto para o modelo canonico de difratograma. |
| `Diffractogram.to_visualization_payload(...)` | Gera payload com `metadata.visualization`, eixo `2θ`, intensidade, opcionalmente intensidade normalizada e eixo `d-spacing`. |
| `bragg_from_two_theta(two_theta, wavelength)` | Retorna `BraggCalculation` com `theta`, `d`, status e `rule_id`. |
| `two_theta_from_d_spacing(d, wavelength)` | Projeta reflexoes em Å para o eixo 2θ. |
| `geometry_explanation(...)` | Gera explicacao XAI curta para calculos geometricos. |
| `normalize_peak(row)` | Converte campos heterogeneos de pico para `two_theta`, `d`, intensidade, FWHM e flags de largura. |
| `group_peaks_for_ngc(items)` | Agrupa picos por `N`, `G` e `C` no formato esperado pela engine. |
| `get_scientific_knowledge(chapter)` | Retorna bases executaveis dos Capitulos 3, 7 ou 8. |
| `get_rule_indexes()` | Retorna indices de regras/equacoes para XAI e auditoria. |

## Base Executavel do Capitulo 7

Fonte OCR local: `/home/invenio/Downloads/analises.pdf`.

Obra completa: `X-Ray Diffraction and the Identification and Analysis of Clay Minerals`.

Capitulo: `Identification of Clay Minerals and Associated Minerals`.

O capitulo foi tratado como base de conhecimento executavel, nao apenas como texto descritivo. A extracao foi incorporada no modulo:

`argiloteca_drx/diagnostics/chapter7_knowledge.py`

Esse arquivo registra:

| Camada | Conteudo | Uso no motor |
|---|---|---|
| Entidades | minerais, grupos, reflexoes, tratamentos e minerais associados | `CHAPTER7_ENTITIES` alimenta auditoria semantica. |
| Tabelas | 060, sepiolita/paligorsquita e caulinita/polimorfos | `REFLECTION_TABLES` preserva linhas estruturadas por pagina/tabela. |
| Regras diagnosticas | series OOl, clorita, caulinita, esmectita, vermiculita, ilita/mica, minerais fibrosos e quartzo | `DIAGNOSTIC_RULES` fornece `rule_id`, condicoes, explicacao e fonte. |
| Comportamento entre tratamentos | Natural, glicolada, calcinada, glicerol, K-saturacao e aquecimento | `BEHAVIOR_RULES` complementa `treatment_interpreter.py`. |
| Reflexao 060 | classificacao dioctaedrica/trioctaedrica e aviso de interferencia por quartzo | `D060_RULES` complementa `octahedral_classifier.py`. |
| Razoes de intensidade | I003/I005, I002/I003 e razoes de clorita/esmectita | `INTENSITY_RULES` documenta uso auxiliar e limitacoes. |
| Perfis mineralogicos | clorita, grupo da caulinita, esmectita, vermiculita e ilita/mica | `MINERAL_PROFILES` responde quais evidencias sustentam cada candidato. |
| Ontologia | Mineral, Grupo, Especie, Reflexao, Tratamento, Evidencia, Regra e Diagnostico | `ONTOLOGY` organiza a semantica exportavel. |

Arquivos JSON de contrato criados:

| Arquivo | Funcao |
|---|---|
| `argiloteca_drx/diagnostics/data/argiloteca_rule_schema.json` | Schema de regra diagnostica rastreavel. |
| `argiloteca_drx/diagnostics/data/argiloteca_mineral_schema.json` | Schema de perfil mineralogico. |
| `argiloteca_drx/diagnostics/data/argiloteca_behavior_schema.json` | Schema de comportamento entre tratamentos. |
| `argiloteca_drx/diagnostics/data/chapter7_knowledge_base_manifest.json` | Manifesto versionado da base extraida do capitulo. |

Exportacao completa da base para JSON:

```bash
/home/invenio/invenio-project/argiloteca-local/venvs/app-py310-l3/bin/python \
  argiloteca-local/app/argiloteca_custom/scripts/export_chapter7_knowledge.py
```

Saida padrao:

`argiloteca_drx/diagnostics/data/generated/`

Arquivos exportados principais:

| Arquivo gerado | Conteudo |
|---|---|
| `chapter7_knowledge_complete.json` | Base completa em uma estrutura JSON unica. |
| `chapter7_reflection_tables.json` | Tabelas 7.3, 7.4, 7.6 e 7.8 a 7.15 estruturadas. |
| `chapter7_diagnostic_rules.json` | Regras diagnosticas rastreaveis. |
| `chapter7_behavior_rules.json` | Regras de comportamento entre tratamentos. |
| `chapter7_d060_rules.json` | Regras auxiliares de reflexao 060. |
| `chapter7_intensity_rules.json` | Regras de razoes de intensidade e limitacoes. |
| `chapter7_mineral_profiles.json` | Perfis mineralogicos usados para explicar candidatos. |
| `argiloteca_mineralogy_ontology.json` | Ontologia mineralogica resumida. |

Aplicacao direta no codigo:

| Funcao/classe | Arquivo | Aplicacao |
|---|---|---|
| `CHAPTER7_SOURCE` | `chapter7_knowledge.py` | Objeto bibliografico raiz com a obra completa, capitulo, PDF local, OCR e policy. |
| `source_ref` | `chapter7_knowledge.py` | Funcao que normaliza pagina, tabela, figura e fragmento curto para toda regra-fonte. |
| `CHAPTER7_ENTITIES` | `chapter7_knowledge.py` | Lista minerais, grupos, reflexoes e conceitos do capitulo com pagina/paragrafo. |
| `REFLECTION_TABLES` | `chapter7_knowledge.py` | Converte tabelas 7.3, 7.4, 7.6 e 7.8 a 7.15 para objetos JSON em memoria. |
| `DIAGNOSTIC_RULES` | `chapter7_knowledge.py` | Codifica series OOl, clorita, caulinita, esmectita, vermiculita, ilita/mica, fibrosos e quartzo como regras auditaveis. |
| `BEHAVIOR_RULES` | `chapter7_knowledge.py` | Codifica comportamento entre tratamentos: permanece, expande, colapsa, desaparece, reduz ou aumenta. |
| `D060_RULES` | `chapter7_knowledge.py` | Registra d060 como discriminador auxiliar dioctaedrico/trioctaedrico com alerta de interferencia por quartzo. |
| `INTENSITY_RULES` | `chapter7_knowledge.py` | Documenta razoes I003/I005, I002/I003 e limitacoes; intensidade nao confirma mineral sozinha. |
| `MINERAL_PROFILES` | `chapter7_knowledge.py` | Agrupa reflexoes, comportamento, d060, intensidades e interferencias para explicar cada candidato. |
| `ONTOLOGY` | `chapter7_knowledge.py` | Organiza Mineral, Grupo, Especie, Reflexao, Tratamento, Evidencia, Regra e Diagnostico. |
| `get_chapter7_knowledge` | `chapter7_knowledge.py` | Retorna copia profunda da base para evitar mutacao acidental por chamadores. |
| `chapter7_rule_index` | `chapter7_knowledge.py` | Cria indice `rule_id -> regra`, usado no painel e no JSON final. |
| `chapter7_profile` | `chapter7_knowledge.py` | Busca o perfil mineralogico de um candidato. |
| `interpret_treatments` | `treatment_interpreter.py` | Detecta expansao, colapso, persistencia, desaparecimento, reducao forte em 7 A e aumento/persistencia em 14 A. |
| `_behavior_candidates` | `diagnostic_decision_tree.py` | Liga behaviors detectados a IDs do Capitulo 7 como `chapter7_kaolin_heat_loss` e `chapter7_chlorite_heat_intensity`. |
| `_build_candidates` | `diagnostic_decision_tree.py` | Converte comportamentos N/G/C em candidatos sem identificar por pico isolado. |
| `interpret_ngc` | `diagnostic_decision_tree.py` | Injeta `source_rule_index`, `source_mineral_profiles` e contagens da base no payload final. |
| `serialize_for_invenio` | `serializers.py` | Preserva regra-fonte e perfis mineralogicos na exportacao InvenioRDM. |
| `export_chapter7_knowledge` | `scripts/export_chapter7_knowledge.py` | Materializa a base executavel em JSON versionado. |
| `write_json` | `scripts/export_chapter7_knowledge.py` | Grava cada camada da base em UTF-8 com ordenacao estavel. |
| `main` | `scripts/export_chapter7_knowledge.py` | Entrada CLI para exportacao manual ou automatizada. |
| `sourceRuleTargets` | `argiloteca/static/js/drx-comparacao.js` | Mapeia candidato exibido para os alvos das regras do Capitulo 7. |
| `renderSourceRulePanel` | `argiloteca/static/js/drx-comparacao.js` | Mostra no painel regra, pagina, tabela/figura e explicacao curta. |
| `renderDiagnosticV3Block` | `argiloteca/static/js/drx-comparacao.js` | Mostra no painel a secao recolhivel `Regra-fonte` para cada candidato N/G/C. |
| `renderNgcEvidenceMatrix` | `argiloteca/static/js/drx-comparacao.js` | Mostra matriz por hipotese mineral com N, G, C, evidencias a favor, conflitos, status e regra-fonte dos Capitulos 3/7/8. |
| `compactRuleSourceText` | `argiloteca/static/js/drx-comparacao.js` | Resume regra-fonte como `Cap. 3 Bragg/2θ→d`, `Cap. 7 N-G-C` e `Cap. 8 interestratificados` quando aplicavel. |

Perguntas respondidas pela estrutura:

| Pergunta | Onde responder |
|---|---|
| Por que foi interpretado como clorita? | `combined_candidates`, `source_mineral_profiles.chlorite`, `source_rule_index.chapter7_chlorite_ool`. |
| Por que nao e caulinita? | `ambiguities`, `competitors`, comportamento termico e ausencia/presenca dos picos 14/4.74/3.53 A. |
| Quais evidencias sustentam esmectita? | `behavior_candidates`, `source_mineral_profiles.smectite`, regra `chapter7_smectite_ngc`. |
| Qual regra do livro originou a decisao? | `source_rule_index` com `source.page`, `source.table`, `source.figure` e `rule_id`. |

## Visualizacao Canonica do Difratograma

Foi criada a classe `Diffractogram` em:

`argiloteca_drx_core/diffractogram.py`

Objetivo: fornecer um modelo unico de curva 1D para melhorar a visualizacao do difratograma sem misturar desenho grafico com interpretacao mineralogica. A classe trabalha com o eixo experimental `2θ` e intensidade, calcula metadados geometricos do Capitulo 3 e gera um payload estavel para o painel.

Responsabilidades:

| Metodo | Funcao |
|---|---|
| `cleaned_points()` | Remove pares nao finitos e preserva a ordem da curva original. |
| `validation()` | Verifica pontos suficientes, tamanho compativel entre eixo/intensidade, monotonicidade e comprimento de onda. |
| `x_domain()` | Retorna dominio do eixo `2θ` para enquadramento do grafico. |
| `y_domain()` | Retorna dominio de intensidade observado. |
| `normalized_intensity()` | Normaliza intensidade para escala `0-100`, usada em sobreposicoes visuais. |
| `d_spacing_axis()` | Calcula eixo auxiliar em Å pela Lei de Bragg, com `θ = 2θ/2`. |
| `decimated(max_points)` | Reduz a quantidade de pontos para renderizacao sem alterar a curva original em disco. |
| `visualization_summary()` | Produz resumo auditavel: pontos, dominios, `λ`, regra geometrica e avisos. |
| `to_visualization_payload()` | Serializa a curva no contrato consumido pelo painel. |

Integracao atual:

| Local | Como aplica |
|---|---|
| `argiloteca/services/drx.py` | `load_diffractogram_data()` passa as curvas carregadas por `_diffractogram_visualization_response()`, que usa `Diffractogram`. |
| API de curva | Mantem as chaves historicas `two_theta`, `intensity` e `metadata`, evitando quebra no JavaScript. |
| `metadata.visualization` | Novo bloco com `points`, `x_domain`, `y_domain`, `wavelength_angstrom`, `geometry_rule_id`, `geometry_explanation` e `warnings`. |
| Testes | `test_diffractogram_visualization_model` valida dominios, normalizacao, eixo `d-spacing` e payload. |

Contrato novo anexado ao retorno do difratograma:

```json
{
  "metadata": {
    "visualization": {
      "curve_id": "id-da-curva",
      "status": "valid",
      "points": 1234,
      "x_domain": {"min": 3.0, "max": 70.0, "unit": "degree_2theta"},
      "y_domain": {"min": 0.0, "max": 10000.0, "unit": "counts_or_relative"},
      "wavelength_angstrom": 1.5406,
      "geometry_rule_id": "chapter3_two_theta_to_d_spacing",
      "geometry_explanation": "2θ e o eixo medido; d-spacing e calculado com θ = 2θ/2 pela Lei de Bragg.",
      "warnings": []
    }
  },
  "two_theta": [],
  "intensity": []
}
```

Politica: `Diffractogram` nao confirma mineralogia. Ele apenas prepara a curva para visualizacao, calculo geometrico e auditoria. A interpretacao continua nos motores N/G/C, regras do Capitulo 7 e regras de interestratificados do Capitulo 8.

## Matriz de Evidencias N-G-C no Painel

O bloco **Resumo das evidencias N-G-C** da **Interpretacao Mineralogica Assistida** foi ampliado. Alem dos cards de comportamento, agora o painel renderiza uma matriz por hipotese mineralogica usando o payload `clay_interpretation.candidates`.

Colunas da matriz:

| Coluna | Conteudo |
|---|---|
| Hipotese | Nome do grupo, serie ou hipotese ambigua. |
| N | Pico(s) da preparacao natural, com `d`, `2θ` e FWHM quando disponiveis. |
| G | Pico(s) da preparacao glicolada, com expansao ou estabilidade. |
| C | Pico(s) da preparacao calcinada/aquecida, com colapso, persistencia ou perda. |
| A favor | Evidencias que sustentam a hipotese. |
| Contra/conflito | Evidencias contra, sobreposicoes ou sinais de ambiguidade. |
| Status | `provavel`, `possivel`, `ambiguo` e score auxiliar. |
| Regra-fonte | Citacao curta dos Capitulos 3, 7 e 8 quando aplicavel. |

Aplicacao das fontes:

| Fonte | Quando aparece |
|---|---|
| Cap. 3 `Bragg/2θ→d` | Quando a hipotese usa pico medido em `2θ` ou `d-spacing`. |
| Cap. 7 `N-G-C` | Sempre que a hipotese vem da interpretacao por Natural/Glicolado/Calcinado. |
| Cap. 8 `interestratificados` | Quando ha mistura/interestratificado, expansao parcial, ombro, pico largo, vermiculita/corrensita ou ambiguidade preservada. |

Funcoes JavaScript adicionadas ou ampliadas:

| Funcao | Uso |
|---|---|
| `renderNgcEvidenceMatrix()` | Constroi a tabela compacta por hipotese mineralogica. |
| `peakCellForPreparation(candidate, preparation)` | Extrai evidencias de picos por preparo N/G/C. |
| `compactRuleSourceText(candidate)` | Gera resumo de regra-fonte Cap. 3/7/8. |
| `clayCandidateAsSourceTarget(candidate)` | Mapeia candidatos do backend para alvos de regras bibliograficas. |
| `sourceChapterLabel(source)` | Resolve o titulo do capitulo a partir de `chapter` ou `source_id`. |

Estilos adicionados:

| Classe CSS | Uso |
|---|---|
| `.argilo-drx__ngc-matrix-wrap` | Permite rolagem horizontal quando a matriz ficar larga. |
| `.argilo-drx__ngc-matrix` | Tabela compacta de evidencias N/G/C. |

Essa matriz nao altera a decisao do backend. Ela apenas torna explicito o caminho:

`pico medido -> d calculado -> comportamento N/G/C -> evidencia a favor/contra -> status -> regra-fonte`.

## Catalogo Unico de Picos Diagnosticos

Os valores de picos usados pela leitura do difratograma foram centralizados em:

`argiloteca/static/data/diagnostic_peak_rules_catalog.json`

Esse arquivo e o ponto de edicao recomendado para atualizar janelas de `d-spacing` sem alterar varios arquivos Python e JavaScript. Ele guarda `policy = argiloteca_rule_based_diagnostic`, unidade em Angstrom, nome completo da fonte `X-Ray Diffraction and the Identification and Analysis of Clay Minerals` e, para cada faixa, o campo `rule_source`.

Modulo carregador:

`argiloteca_drx/diagnostics/diagnostic_peak_rules.py`

| Funcao | O que faz |
|---|---|
| `load_peak_rule_catalog` | Carrega e valida o JSON central. |
| `named_range` | Retorna `(d_min, d_max)` de uma faixa nomeada. |
| `range_target` | Retorna alvo teorico quando existe, por exemplo quartzo 101 em `3.34 A`. |
| `mapped_ranges` | Converte secoes de compatibilidade para constantes historicas do codigo. |
| `targeted_basal_ranges` | Monta as faixas usadas no peak-picking basal e preserva `rule_source`. |
| `simple_analysis_ranges` | Alimenta a analise simples de regras DRX. |
| `peak_sets` | Alimenta conjuntos de picos companheiros por grupo mineral. |
| `frontend_rules_payload` | Expõe o subconjunto usado pelo JavaScript do painel. |

Mapa de arquivos que antes repetiam valores de picos:

| Arquivo | Valores agora carregados do catalogo | Regra vinculada |
|---|---|---|
| `argiloteca/services/drx.py` | `DRX_DIAGNOSTIC_D_RANGES`, `TARGETED_BASAL_PEAK_RANGES`, quartzo 101 para calibracao | `chapter7_smectite_ngc`, `chapter7_kaolinite_chlorite_resolution`, `chapter7_chlorite_ool`, `chapter7_illite_glauconite_mica`, `chapter7_quartz_internal_standard` |
| `argiloteca/services/drx_ngc_workflow.py` | `DIAGNOSTIC_RANGES`, `SCRIPT_INTERVAL_RANGES`, `TARGETED_BASAL_RANGES` | mesmas regras N/G/C e picos companheiros do Capitulo 7 |
| `scripts/batch_ngc_raw_diagnostics.py` | `RANGES`, `TARGETED_BASAL_RANGES`, `DEFAULT_QUARTZ_SEARCH_D`, `DEFAULT_TARGET_QUARTZ_D` | mesmas regras N/G/C e quartzo interno |
| `argiloteca/services/drx_analysis.py` | `DIAGNOSTIC_D_RANGES` | caulinita/clorita 7 A, ilita/mica 10 A, clorita/vermiculita 14 A e esmectita glicolada |
| `argiloteca_drx/diagnostics/peak_sets.py` | `PEAK_SETS` | picos companheiros de ilita/mica, caulinita, clorita, esmectita, sepiolita, paligorsquita, kerolita/talco e corrensita |
| `argiloteca/static/js/drx-comparacao.js` | `SEM_TITULO_NGC_DIAGNOSTIC_RANGES` e `mineralReflectionRules` | regras de exibicao e triagem no navegador, hidratadas por `diagnostic_peak_rules_catalog.json` |

Regras principais do catalogo:

| Faixa | Janela principal | Regra-fonte |
|---|---:|---|
| Ilita/mica 10 A | `9.73-10.38 A` | `chapter7_illite_glauconite_mica` |
| Caulinita 7 A | `6.96-7.42 A` | `chapter7_kaolinite_chlorite_resolution` |
| Caulinita 3.57 A | `3.52-3.62 A` | `chapter7_kaolinite_chlorite_resolution` |
| Esmectita N | `13.46-16.86 A` | `chapter7_smectite_ngc` |
| Esmectita G | `16.06-18.31 A` | `chapter7_smectite_ngc` |
| Esmectita C | `9.65-10.37 A` | `chapter7_smectite_ngc` |
| Clorita 14 A | `13.58-14.87 A` | `chapter7_chlorite_ool` |
| Clorita 7/4.72/3.53 A | `6.90-7.40`, `4.60-4.85`, `3.45-3.65 A` | `chapter7_chlorite_ool` |
| Quartzo 101 | busca `3.24-3.44 A`, alvo `3.34 A` | `chapter7_quartz_internal_standard` |
| Sepiolita e paligorsquita | `12.00-12.50 A`, `10.30-10.50 A` | `chapter7_fibrous_channel_minerals` |
| Kerolita | `9.35-9.50 A` | `presalt_magnesian_clays_reference` |
| Corrensita | `29 A`, `31-32 A`, `24 A` | `flow_pdf_corrensite` |

Observacao de manutencao: alterar o JSON central muda as faixas usadas por backend, batch e frontend apos recarregar a aplicacao ou atualizar os assets. Regras bibliograficas completas e perfis explicativos continuam em `chapter7_knowledge.py` e `literature_ranges.py`; o catalogo central serve como camada operacional editavel para as janelas de pico usadas pelo painel.

## Uso do GSAS-II na Argiloteca

O GSAS-II e integrado como motor externo auxiliar para leitura, validacao e preparacao de artefatos DRX. Ele nao substitui a interpretacao mineralogica N/G/C da Argiloteca e nao confirma argilomineral automaticamente.

Politica do GSAS-II: motor externo tecnico de leitura/validacao; a confirmacao mineralogica continua sendo emitida apenas pela engine N/G/C da Argiloteca com `argiloteca_rule_based_diagnostic`.

### O que o GSAS-II faz no painel

| Capacidade | Uso na Argiloteca | Arquivos/rotas |
|---|---|---|
| Leitura de formatos de po | Valida ou complementa leitura de `.raw`, `.brml`, `.xy`, `.xye`, `.csv`, `.fxye` e padroes compativeis. | `scripts/gsas2_external_adapter.py`, `/api/argiloteca/drx/gsas2/validate-pattern` |
| Geracao de projeto GPX | Cria um `.gpx` auditavel por job externo. | `project_gpx` no `result.json` do job |
| Resumo de histograma | Retorna numero de pontos, faixa x, intensidade maxima, media e posicao do maximo. | `histogram_summary` |
| Comparacao Argiloteca x GSAS-II | Compara numero de pontos, faixa x e intensidade maxima entre parser local e GSAS-II. | `argiloteca/services/drx_gsas2_bridge.py`, `/api/argiloteca/drx/gsas2/compare-job/<job_id>` |
| Picos semeados e ajuste | Pode receber `seed_peaks` e tentar `refine_peaks()` quando houver parametros instrumentais. | `allow_peak_refinement`, `seed_peaks` |
| Fases CIF | Importa fases com `add_phase()` e salva no GPX; refinamento de fase fica bloqueado sem receita curada. | `phase_paths`, `phase_summaries` |

### O que o GSAS-II nao faz automaticamente

- nao confirma caulinita, clorita, ilita, esmectita, kerolita, estevensita ou qualquer argilomineral;
- nao substitui especialista;
- nao substitui a regra N/G/C;
- nao executa Rietveld, Le Bail ou Pawley sem parametros instrumentais, fases CIF e receita curada;
- nao roda dentro da request Flask.

### Arquitetura operacional

O painel registra um job externo. O worker executa o adaptador GSAS-II fora do Flask:

`Painel DRX -> fila de jobs -> worker -> GSAS-II -> GPX/result.json/log -> painel`

Arquivos principais:

| Arquivo | Funcao |
|---|---|
| `argiloteca/services/drx_gsas2_bridge.py` | Ponte segura entre API Flask e worker GSAS-II; consulta status, registra jobs e compara parsers. |
| `argiloteca/services/drx_external_jobs.py` | Fila local de jobs externos e execucao do adaptador configurado. |
| `scripts/gsas2_external_adapter.py` | Executa no Python do GSAS-II, importa padroes, fases CIF, salva GPX e gera JSON estruturado. |
| `scripts/gsas2_external_adapter.sh` | Wrapper com `ARGILOTECA_GSAS2_ROOT`, `ARGILOTECA_GSAS2_PYTHON` e `PYTHONPATH`. |
| `scripts/run_drx_external_jobs.py` | Worker offline para processar jobs pendentes. |
| `rodar_gsas2_em_pasta.sh` | Batch para processar uma pasta de arquivos DRX com GSAS-II. |

### Requisitos

Instalacao local esperada:

`/home/invenio/invenio-project/tools/g2main_rhel`

Variaveis aceitas:

| Variavel | Finalidade |
|---|---|
| `ARGILOTECA_GSAS2_ROOT` | Raiz da instalacao GSAS-II. |
| `ARGILOTECA_GSAS2_PYTHON` | Python do GSAS-II. |
| `ARGILOTECA_GSAS2_PYTHONPATH` | Caminho do fonte GSAS-II. |
| `ARGILOTECA_DRX_GSAS2_COMMAND` | Wrapper chamado pelo worker externo. |
| `ARGILOTECA_DRX_JOBS_DIR` | Diretorio local dos jobs e artefatos. |
| `ARGILOTECA_GSAS2_INSTRUMENT_PATH` | Arquivo `.PRM` ou `.instprm` curado usado como parametro instrumental padrao para importacao e ajuste de picos. |

Status:

`GET /api/argiloteca/drx/gsas2/status`

Validacao de padrao por caminho local:

`POST /api/argiloteca/drx/gsas2/validate-pattern`

Payload minimo:

```json
{
  "pattern_path": "/caminho/amostra.xy",
  "instrument_path": null,
  "phase_paths": [],
  "allow_peak_refinement": false,
  "allow_phase_refinement": false
}
```

### Batch de pasta

Uso:

```bash
./rodar_gsas2_em_pasta.sh /caminho/entrada /caminho/saida
```

O script busca `.raw`, `.RAW`, `.brml`, `.xy`, `.xye`, `.csv` e `.fxye`, registra jobs GSAS-II, roda o worker e gera:

`/caminho/saida/gsas2_batch_index.json`

Para gerar resumo completo em formatos que exigem parametros instrumentais:

```bash
ARGILOTECA_GSAS2_INSTRUMENT_PATH=/caminho/instrumento.PRM \
./rodar_gsas2_em_pasta.sh /caminho/entrada /caminho/saida
```

### Upload temporario RAW e GSAS-II

Quando um arquivo temporario e enviado pelo botao `Comparar arquivo temporario`, a Argiloteca agora:

1. le a curva com o parser local;
2. calcula evidencias N/G/C e similaridade com registros;
3. grava uma copia efemera em `instance/argiloteca_drx_temp_uploads`;
4. registra um job GSAS-II externo com `pattern_path`;
5. usa `ARGILOTECA_GSAS2_INSTRUMENT_PATH` quando configurado;
6. envia picos detectados como `seed_peaks` quando o ajuste de picos e permitido;
7. mostra a secao `Validacao GSAS-II do RAW externo` no painel mesclado.

O job continua assíncrono: ele fica na fila ate o worker `scripts/run_drx_external_jobs.py` ser executado. A interface exibe o `job_id`, o instrumento curado usado e os avisos. O resultado GSAS-II permanece auxiliar e nao altera automaticamente a interpretacao mineralogica.

### Receita de refinamento curada

A receita inicial registrada no JSON e:

`argiloteca.gsas2.refinement.curated_placeholder.v1`

Ela permite somente:

- importacao;
- geracao de GPX;
- ajuste de picos semeados quando houver `instrument_path`.

Continuam bloqueados por padrao:

- Le Bail;
- Pawley;
- Rietveld.

Esses modos exigem fase CIF curada, parametros instrumentais, limites de refinamento, autorizacao explicita e revisao por especialista.

### Referencia e licenca

Referencia obrigatoria:

Toby, B. H., & Von Dreele, R. B. (2013). GSAS-II: the genesis of a modern open-source all purpose crystallography software package. Journal of Applied Crystallography, 46(2), 544-549. doi:10.1107/S0021889813003531.

Aviso de licenca registrado nos JSONs:

`This product includes software produced by UChicago Argonne, LLC under Contract No. DE-AC02-06CH11357 with the Department of Energy.`

## Quadros de Regras Aplicadas ao Codigo

As tabelas abaixo documentam como cada referencia cientifica revisada foi traduzida em codigo. Todas as regras foram aplicadas como evidencia auxiliar, aviso, ambiguidade, recomendacao de teste, range bibliografico ou regra de comportamento N/G/C. Nenhuma regra promove identificacao confirmatoria por pico isolado.

### Brindley & Brown (1980)

| Regra Brindley & Brown | Onde foi aplicada | Como foi aplicada |
|---|---|---|
| Caulinita, dickita e nacrita compartilham reflexoes basais proximas de 7 A e 3.57 A. | `argiloteca_drx/diagnostics/literature_ranges.py`, `peak_sets.py`, `diagnostic_decision_tree.py` | Os ranges 001/002 entram como evidencia do `kaolin_group`; a engine nao separa especie sem hkl/morfologia/contexto. |
| O grupo da caulinita perde ou reduz fortemente a reflexao basal apos aquecimento. | `treatment_interpreter.py`, `diagnostic_decision_tree.py` | A regra N/G/C exige 7 A estavel em N/G e ausente/reduzido em C para favorecer `kaolin_group`. |
| Picos de 7 A devem competir com clorita, serpentina e haloisita. | `ambiguity_rules.py`, `confidence_engine.py` | A janela `7 A` gera ambiguidade e bloqueia confianca alta quando os dados nao resolvem picos companheiros e resposta termica. |

### Bailey (1980/1988)

| Regra Bailey | Onde foi aplicada | Como foi aplicada |
|---|---|---|
| d060 auxilia a separar estruturas dioctaedricas e trioctaedricas. | `octahedral_classifier.py`, `diagnostic_decision_tree.py`, `literature_ranges.py` | Os campos `octahedral_type` e `d060_range` alimentam `classify_octahedral` e refinam candidatos como clorita, biotita, esmectita trioctaedrica e caulinitas. |
| Cloritas e micas exigem suporte estrutural adicional para interpretacao especifica. | `literature_ranges.py`, `peak_sets.py`, `diagnostic_decision_tree.py` | A engine exige persistencia N/G/C e picos companheiros; especies ou politipos ficam como hipoteses auxiliares. |
| Reflexoes 060 e politipos devem ser avaliados em padrao de po/randomico quando necessario. | `diagnostic_decision_tree.py`, `docs/painel_drx_documentacao.md` | `recommended_next_tests` inclui `pico 060` e `padrao de po randomico` quando a classificacao estrutural permanece incerta. |

### Moore & Reynolds (1989/1997)

Arquivo lido: `/home/invenio/invenio-project/textos/MooreandReynolds.pdf`.

| Regra Moore & Reynolds | Onde foi aplicada | Como foi aplicada |
|---|---|---|
| Quartzo e comum na fracao argila, tem picos invariantes e pode servir como padrao interno. | `argiloteca_drx/diagnostics/treatment_interpreter.py` | Quando aparecem picos em ~4.26 A e ~3.34 A, o behavior `quartz_internal_standard_pattern` e registrado como marcador auxiliar. |
| Pico 3.33-3.34 A pode ser quartzo e nao deve confirmar ilita/mica sozinho. | `argiloteca_drx/diagnostics/ambiguity_rules.py`, `diagnostic_decision_tree.py` | A ambiguidade `3.33-3.34 A` recomenda verificar 10 A, 5 A e padrao de quartzo 4.26/3.34/1.82 A; a engine adiciona warning no payload. |
| Quartzo em d~1.542 A pode interferir com a reflexao 060. | `argiloteca_drx/diagnostics/octahedral_classifier.py`, `ambiguity_rules.py` | A janela d060 ~1.54 A adiciona aviso para checar picos companheiros de quartzo antes de usar 060 como suporte trioctaedrico. |
| Caulinita e clorita podem se sobrepor em 7 A; aquecimento e picos companheiros sao necessarios. | `argiloteca_drx/diagnostics/ambiguity_rules.py`, `diagnostic_decision_tree.py` | A ambiguidade `7 A` recomenda clorita 003/004, desaparecimento em 550 C e formamida/DMSO quando haloisita/caulinita permanecerem nao resolvidas. |
| Vermiculita, esmectita, clorita e interestratificados competem em 14 A. | `argiloteca_drx/diagnostics/ambiguity_rules.py`, `diagnostic_decision_tree.py` | A ambiguidade `14 A` recomenda glicerol, K-saturacao, aquecimento a 300 C por 1 h, persistencia em 550 C e expansao/colapso N/G/C. |
| Picos largos e largura de reflexoes ajudam a reconhecer mistura, baixa cristalinidade ou interestratificacao. | `argiloteca_drx/diagnostics/treatment_interpreter.py`, `mixed_layer_engine.py` | Picos `broad`, `asymmetric` ou `fwhm > 0.5` mantem behavior `broad_or_shoulder`, que alimenta candidatos interestratificados e reduz conclusao por mineral puro. |
| Sepiolita e paligorsquita podem ser confundidas com fases expansivas e exigem morfologia/reflexoes adicionais. | `argiloteca_drx/diagnostics/ambiguity_rules.py`, `diagnostic_decision_tree.py` | Ambiguidades em 10 A e 12 A continuam recomendando morfologia fibrosa/tubular, hkl adicionais e trajetoria N/G/C. |

### Drits & Tchoubar (1990)

| Regra Drits & Tchoubar | Onde foi aplicada | Como foi aplicada |
|---|---|---|
| Desordem, defeitos e interestratificacao podem deslocar, alargar ou assimetrizar reflexoes 00l. | `treatment_interpreter.py`, `mixed_layer_engine.py`, `confidence_engine.py` | Picos largos/ombros geram `broad_or_shoulder`, candidatos de mixed-layer e reducao de confianca para mineral puro. |
| Sequencias racionais e nao racionais devem ser tratadas como evidencias estruturais, nao como simples match de faixa. | `mixed_layer_engine.py`, `diagnostic_graph.py` | Corrensita e outros interestratificados carregam `order`, `components`, `evidence` e relacoes explicaveis no grafo. |
| Modelagem e contexto sao necessarios para resolver interestratificados complexos. | `diagnostic_decision_tree.py` | `recommended_next_tests` adiciona `modelagem de interestratificados` quando aparecem K/S, C/S, T/S ou respostas parciais. |

### Lanson & Bouchet (1995)

| Regra Lanson & Bouchet | Onde foi aplicada | Como foi aplicada |
|---|---|---|
| Bandas largas, ombros e expansao parcial nao devem ser forcados como mineral puro. | `treatment_interpreter.py`, `mixed_layer_engine.py` | Esses sinais geram `partial_expansion_with_glycol` ou `broad_or_shoulder`, retornando candidatos interestratificados com alerta. |
| Interestratificados precisam ser reportados como hipoteses proprias quando a resposta N/G/C e mista. | `mixed_layer_engine.py`, `diagnostic_decision_tree.py` | I/S, C/S, K/S, T/S e corrensita entram em `mixed_layer_candidates` e depois em `combined_candidates`. |
| Padroes de minerais puros nao modelam adequadamente perfis interestratificados. | `literature_ranges.py`, `range_comparator.py` | Ranges de mixed-layer tem `notes` restritivas; `compare_ranges` retorna apenas hipotese auxiliar. |

### Meunier, Clays (2005)

| Regra Meunier | Onde foi aplicada | Como foi aplicada |
|---|---|---|
| Classificar argilominerais por tipo estrutural 1:1, 2:1, 2:1:1 e fibroso/canal. | `literature_ranges.py`, `diagnostic_decision_tree.py` | Os candidatos carregam `family`, `octahedral_type`, comportamento e competidores coerentes com cada tipo estrutural. |
| d060 auxilia a separar dioctaedrico, intermediario e trioctaedrico. | `octahedral_classifier.py`, `diagnostic_decision_tree.py` | `classify_octahedral` retorna `dioctahedral`, `intermediate`, `trioctahedral` ou `unknown`, sempre com aviso de uso auxiliar. |
| Esmectitas expandem, micas/cloritas nao expandem, vermiculitas podem responder parcialmente. | `treatment_interpreter.py`, `diagnostic_decision_tree.py`, `ambiguity_rules.py` | A trajetoria N/G/C e priorizada sobre ranges: expansao para ~17 A, colapso para ~10 A, persistencia de 10/14 A e colapsos parciais. |
| Argilominerais magnesianos como saponita, estevensita, kerolita e K/S exigem quimica/contexto. | `diagnostic_decision_tree.py`, `presalt_reference_dataset.py`, `mixed_layer_engine.py` | Contexto `Mg`, `presalt`, `lacustrine` ou `evaporitic` reforca candidatos, mas nao confirma especie sem quimica/modelagem. |

### Fluxograma USGS de Identificacao de Argilominerais por DRX

| Regra do fluxograma USGS | Onde foi aplicada | Como foi aplicada |
|---|---|---|
| A identificacao operacional deve seguir resposta entre natural, glicolada e aquecida. | `treatment_interpreter.py`, `diagnostic_decision_tree.py`, `drx_ngc_workflow.py` | O workflow monta grupos N/G/C e a engine interpreta expansao, persistencia, colapso e desaparecimento. |
| Clorita, caulinita, ilita/mica, esmectita e vermiculita devem ser testadas por trajetorias e picos companheiros. | `peak_sets.py`, `diagnostic_decision_tree.py` | Conjuntos 14/7/4.72/3.53, 7/3.57, 10/5/3.33 e 12-17-10 A alimentam candidatos e confianca. |
| Corrensita/C-S regular deve ser reconhecida como entidade interestratificada. | `treatment_interpreter.py`, `mixed_layer_engine.py` | N ~29 A, G ~31-32 A e C ~24 A geram `corrensite` ou C/S regular, nao clorita + esmectita simples. |
| Dados incompletos nao podem produzir alta confianca. | `confidence_engine.py`, `diagnostic_decision_tree.py` | `input_completeness` bloqueia alta confianca quando falta tratamento, ha poucos picos ou ambiguidade severa. |

### Referencias empiricas Pre-Sal UFRGS/Petrobras

| Regra Pre-Sal UFRGS/Petrobras | Onde foi aplicada | Como foi aplicada |
|---|---|---|
| Kerolita deve ser considerada em picos ~9.35-9.45 A nao expansivos em contexto magnesiano. | `presalt_reference_dataset.py`, `literature_ranges.py`, `diagnostic_decision_tree.py` | `kerolite` entra como candidato auxiliar quando ha ~9.4 A estavel e contexto Mg/Pre-Sal reforca a hipotese. |
| Estevensita e saponita sao esmectitas trioctaedricas magnesianas com expansao para ~17 A. | `presalt_reference_dataset.py`, `diagnostic_decision_tree.py` | Esmectita expansiva com d060/contexto Mg pode gerar `saponite` ou `stevensite`, com competidores e recomendacao de quimica Mg-Al-Fe. |
| Corrensita e K/S devem ser tratados como entidades/interestratificados relevantes no Pre-Sal. | `mixed_layer_engine.py`, `presalt_reference_dataset.py`, `diagnostic_decision_tree.py` | C/S regular, K/S kerolita-estevensita e T/S aparecem como `mixed_layer_candidates`, exigindo modelagem/validacao. |
| O dataset empirico local deve ser separado da literatura. | `presalt_reference_dataset.py`, `range_comparator.py`, `serializers.py` | Matches Pre-Sal aparecem em `presalt_matches`, separados de `literature_matches` e `empirical_matches`, preservando proveniencia. |

## Tabela de Arquivos

| Arquivo | O que faz |
|---|---|
| `argiloteca/services/drx.py` | Nucleo de importacao, parsing, alinhamento, enriquecimento e snapshots de difratogramas DRX. |
| `argiloteca/services/drx_analysis.py` | Construcao de runs analiticos versionados, hashes de configuracao e matches diagnosticos. |
| `argiloteca/services/drx_cif_simulation.py` | Entrada para simulacao DRX a partir de CIF e normalizacao de parametros. |
| `argiloteca/services/drx_external_jobs.py` | Fila simples de jobs externos para motores DRX isolados e adaptadores locais. |
| `argiloteca/services/drx_ngc_workflow.py` | Workflow N/G/C backend que monta grupos natural/glicolado/calcinado e chama a engine V3. |
| `argiloteca/services/drx_reference_index.py` | Indice local de referencias DRX, manifestos e curvas padrao. |
| `argiloteca/services/drx_references.py` | Parser e comparador de padroes de referencia JSON/texto/CIF. |
| `argiloteca/services/drx_report.py` | Relatorio tecnico HTML/JSON para uma curva DRX carregada. |
| `argiloteca/services/drx_runs.py` | Persistencia e consulta de runs DRX em arquivos JSON locais. |
| `argiloteca/services/drx_science_engine.py` | Ponte com ambiente cientifico isolado para simulacao, deteccao e ajuste de picos. |
| `argiloteca/services/drx_selection_report.py` | Relatorio reproduzivel para conjunto selecionado no painel. |
| `argiloteca_drx/diagnostics/__init__.py` | Exporta a engine diagnostica explicavel N/G/C. |
| `argiloteca_drx/diagnostics/ambiguity_rules.py` | Regras obrigatorias de ambiguidade em janelas 7, 10, 12, 14 e 3.33 A. |
| `argiloteca_drx/diagnostics/confidence_engine.py` | Pontuacao de confianca e bloqueios de alta confianca em dados incompletos. |
| `argiloteca_drx/diagnostics/demo_rule_engine.py` | Exemplo minimo de chamada da engine V3. |
| `argiloteca_drx/diagnostics/diagnostic_behavior_rules.py` | Constantes de versao e politica da engine. |
| `argiloteca_drx/diagnostics/diagnostic_decision_tree.py` | Arvore decisoria N/G/C explicavel com candidatos, interestratificados e confianca. |
| `argiloteca_drx/diagnostics/diagnostic_graph.py` | Grafo de evidencias, regras e relacoes diagnosticas. |
| `argiloteca_drx/diagnostics/empirical_builder.py` | Construtor de ranges empiricos a partir de padroes validados por especialista. |
| `argiloteca_drx/diagnostics/empirical_ranges.py` | Loader de ranges empiricos locais. |
| `argiloteca_drx/diagnostics/evidences.py` | Helpers para normalizar picos, localizar janelas e registrar evidencias. |
| `argiloteca_drx/diagnostics/literature_ranges.py` | Catalogo de faixas bibliograficas e comportamento mineralogico auxiliar. |
| `argiloteca_drx/diagnostics/matcher.py` | API publica para match de pico contra literatura, empirico e Pre-Sal. |
| `argiloteca_drx/diagnostics/mixed_layer_engine.py` | Detector de interestratificados I/S, C/S, K/S, T/S e corrensita. |
| `argiloteca_drx/diagnostics/octahedral_classifier.py` | Classificador auxiliar d060 dioctaedrico/intermediario/trioctaedrico. |
| `argiloteca_drx/diagnostics/peak_sets.py` | Avaliador de conjuntos de picos companheiros. |
| `argiloteca_drx/diagnostics/presalt_reference_dataset.py` | Dataset empirico local de argilas magnesianas do Pre-Sal. |
| `argiloteca_drx/diagnostics/range_comparator.py` | Comparador de picos observados com ranges de literatura, empiricos e Pre-Sal. |
| `argiloteca_drx/diagnostics/schema.py` | Validador leve do payload diagnostico V3. |
| `argiloteca_drx/diagnostics/serializers.py` | Serializacao do diagnostico para campos customizados InvenioRDM. |
| `argiloteca_drx/diagnostics/treatment_interpreter.py` | Interpretador de comportamento entre tratamentos N/G/C. |
| `argiloteca_drx_core/__init__.py` | Namespace de compatibilidade para nucleo DRX reutilizavel. |
| `argiloteca_drx_core/contracts.py` | Contratos e schemas versionados do nucleo DRX. |
| `argiloteca_drx_core/curves.py` | Parser reutilizavel de curvas RAW/texto e funcoes Bragg. |
| `argiloteca_drx_core/diffractogram.py` | Classe canonica `Diffractogram` para curva 1D, dominios, normalizacao, d-spacing e payload de visualizacao. |
| `argiloteca_drx_core/ngc.py` | Wrapper de compatibilidade para workflow N/G/C. |
| `argiloteca_drx_core/processing.py` | Wrappers de compatibilidade para processamento ALS avancado. |
| `argiloteca/static/js/drx-comparacao.js` | Aplicacao frontend do painel: estado, renderizacao, upload RAW, comparacao, N/G/C e exportacoes. |
| `argiloteca/static/css/drx-comparacao.css` | Estilos responsivos do painel DRX, grafico, tabelas, cards e relatorios. |
| `argiloteca/templates/semantic-ui/argiloteca/drx_comparacao.html` | Template Jinja que injeta endpoints, contexto e estrutura DOM do painel. |
| `scripts/batch_ngc_raw_diagnostics.py` | Processamento batch N/G/C de arquivos RAW/texto com diagnostico e relatorios. |
| `scripts/build_drx_neural_evidence_index.py` | Gera indice compacto de evidencias neurais auxiliares consumido pelo painel. |
| `scripts/run_drx_external_jobs.py` | Worker CLI para executar jobs externos DRX pendentes. |

## Inventario de Funcoes, Classes e Objetos Executaveis

A tabela abaixo foi extraida do codigo atual. Funcoes internas prefixadas por `_` sao auxiliares privadas do modulo. Arquivos CSS/HTML/YAML nao declaram funcoes executaveis e aparecem com essa observacao.

### `argiloteca/services/drx.py`

Nucleo de importacao, parsing, alinhamento, enriquecimento e snapshots de difratogramas DRX.

| Tipo | Nome | Descricao |
|---|---|---|
| classe | `RawParseError` | Raised when a RAW file cannot be converted into a 1D diffractogram. |
| classe | `DiffractogramData` | In-memory 1D diffractogram parsed from RAW bytes. |
| funcao | `utc_now_iso` | Return a compact UTC timestamp for manifests and import records. |
| funcao | `_read_float32_series` | Read one little-endian float32 intensity vector from a RAW layout. |
| funcao | `_build_axis` | Build the 2theta axis from header start/step metadata. |
| funcao | `parse_raw_bytes` | Parse supported RAW byte layouts into 2theta/intensity arrays. |
| funcao | `_parse_text_curve_number` | Parse one numeric cell from CSV/TXT/XY text without locale side effects. |
| funcao | `_text_curve_columns` | Return candidate numeric tokens from one delimited or whitespace row. |
| funcao | `parse_text_curve_bytes` | Parse a simple two-column 2theta/intensity text curve. |
| funcao | `parse_diffractogram_bytes` | Parse an uploaded diffractogram by extension, with RAW/text fallbacks. |
| funcao | `parse_raw_file` | Parse a RAW file path into a diffractogram object. |
| funcao | `infer_diffractogram_sample_base` | Infer the N/G/C sample base by removing treatment suffixes from names. |
| funcao | `load_two_theta_axis_corrections` | Load optional manual 2theta offsets keyed by filename/path/sample code. |
| funcao | `_axis_correction_keys` | Generate lookup keys for manual 2theta corrections. |
| funcao | `_axis_offset_from_corrections` | Return a manual offset when any filename/path/sample key matches. |
| funcao | `apply_two_theta_axis_alignment` | Shift parsed 2theta values by manual, quartz or Natural-anchor offset. |
| funcao | `align_raw_curve_for_classified_display` | Apply the classifier N/G/C axis correction before a curve is displayed. |
| funcao | `_shift_numeric_value` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `shift_observed_two_theta_fields` | Shift observed 2theta fields from processed metadata to the classified axis. |
| funcao | `align_compact_advanced_curve_to_classified_axis` | Make an advanced compact curve use the same 2theta axis shown in the chart. |
| funcao | `_finite_float` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_finite_curve_pairs` | Return finite 2theta/intensity pairs sorted for numeric processing. |
| funcao | `_round_series` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_moving_average` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_smooth_savgol_compatible` | Return Savitzky-Golay-like smoothing without making SciPy mandatory. |
| funcao | `_d_spacing_to_two_theta` | Convert d-spacing to 2theta with Bragg's law for the configured wavelength. |
| funcao | `calculate_quartz_axis_offset` | Find quartz 101 and return an absolute 2theta shift for axis calibration. |
| funcao | `_second_difference_penalty_diagonals` | Build the smoothness penalty diagonals used by the ALS fallback solver. |
| funcao | `_solve_pentadiagonal` | Solve a five-diagonal linear system produced by ALS baseline smoothing. |
| funcao | `_als_baseline_stdlib` | Compute ALS baseline without SciPy, using the pentadiagonal solver. |
| funcao | `_als_baseline` | Compute ALS baseline, preferring SciPy and falling back to stdlib. |
| funcao | `_normalize_positive` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_two_theta_to_d_spacing` | Convert 2theta to d-spacing with Bragg's law. |
| funcao | `_interpolate_x` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_peak_fwhm` | Estimate peak FWHM directly from a corrected curve. |
| funcao | `_integrated_peak_area` | Integrate a local peak window above a small baseline-relative threshold. |
| funcao | `_select_advanced_peaks` | Pick local maxima for advanced ALS evidence, keeping peaks separated. |
| funcao | `_select_advanced_peaks_with_engine` | Prefer scipy.signal.find_peaks from the isolated science engine. |
| funcao | `_advanced_fit_rows` | Build peak and fit-result rows consumed by the package/similarity UI. |
| funcao | `_safe_slice` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_is_local_maximum` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_targeted_quality` | Classify targeted basal evidence without treating it as confirmation. |
| funcao | `targeted_basal_peak_scan` | Scan diagnostic basal windows for weak clay-mineral peaks. |
| funcao | `process_advanced_als_curve` | Build the advanced ALS processing payload used by the DRX comparator. |
| funcao | `advanced_als_summary` | Return a compact count/status summary for an advanced ALS payload. |
| funcao | `compact_advanced_als_curve` | Return the curve channels needed by the browser, bounded by point count. |
| funcao | `_load_index` | Load the local import index; invalid/missing files become an empty index. |
| funcao | `_load_json_payload` | Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática. |
| funcao | `_snapshot_id_for_path` | Create the same stable id used to expose RAW snapshot rows via the API. |
| funcao | `_iter_raw_snapshot_rows` | Iterate classification rows from the module-wide RAW snapshot. |
| funcao | `_load_treatment_snapshot_index` | Index N/G/C treatment snapshot rows by path, filename and sample code. |
| funcao | `_sha256_file` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_package_alias_targets` | Return canonical package ids that should win duplicate enrichment ties. |
| funcao | `_has_fwhm` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_has_package_fwhm` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_package_candidate_sort_key` | Prefer canonical packages, FWHM-rich entries and existing advanced output. |
| funcao | `_add_package_index_candidate` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_normalized_lookup_text` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_path_lookup_keys` | Build raw and resolved path keys for cross-machine manifest matching. |
| funcao | `_add_advanced_index_candidate` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_read_jsonl_rows` | Read JSONL rows while ignoring malformed lines from generated manifests. |
| funcao | `_read_advanced_result_payload` | Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática. |
| funcao | `_compact_advanced_fit_results` | Keep only fit fields that the API contract exposes to the browser. |
| funcao | `_compact_advanced_peaks` | Trim advanced peak rows to the fields useful in DRX comparison. |
| funcao | `_compact_targeted_basal_peaks` | Trim targeted basal scan rows for API/UI contracts. |
| funcao | `_advanced_summary_from_payload` | Summarize an advanced processing payload plus manifest provenance. |
| funcao | `_advanced_result_fields` | Load selected advanced ALS evidence for one enrichment candidate. |
| funcao | `_load_advanced_drx_enrichment_index` | Index module-wide advanced DRX results for snapshot enrichment. |
| funcao | `_load_package_drx_enrichment_index` | Index package DRX metadata used to enrich the module-wide RAW snapshot. |
| funcao | `_package_candidates_for_snapshot` | Find package manifest candidates that may describe one snapshot RAW. |
| funcao | `_snapshot_raw_sha` | Resolve a SHA-256 for a snapshot RAW when safe local access exists. |
| funcao | `_select_package_match` | Choose the best package enrichment candidate for a snapshot item. |
| funcao | `_enrich_snapshot_item_from_package` | Attach package-level FWHM/ALS fields to a module-wide snapshot item. |
| funcao | `_enrich_snapshot_item_from_raw_link` | Attach public Argiloteca record links from the curated RAW link table. |
| funcao | `_advanced_candidates_for_snapshot` | Find advanced processing outputs by path first, then filename/sample keys. |
| funcao | `_enrich_snapshot_item_from_advanced_processing` | Attach module-wide advanced ALS output when no package field already wins. |
| funcao | `_treatment_for_snapshot_row` | Resolve N/G/C treatment from snapshot, treatment index or filename rules. |
| funcao | `_compact_webmineral_features` | Reduce WebMineral enrichment to scientific fields shown by the panel. |
| funcao | `_candidate_feature_groups` | Return classifier feature group labels used for traceability chips. |
| funcao | `_snapshot_candidates` | Normalize classifier mineral candidates from one RAW snapshot row. |
| funcao | `_manual_override_candidate` | Normalize one curated candidate without making it look automatic. |
| funcao | `_manual_override_match_keys` | Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica. |
| funcao | `_load_manual_mineral_overrides` | Load optional curated mineral overrides keyed by sample/file/path/hash. |
| funcao | `_manual_override_keys_for_item` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_manual_override_haystack` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_matching_manual_overrides` | Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica. |
| funcao | `_apply_manual_mineral_overrides` | Prepend curated candidates and mark traceability/policy on the item. |
| funcao | `_snapshot_item_from_row` | Build the public API item for one module-wide RAW snapshot row. |
| funcao | `_attach_ngc_group_classification_to_snapshot_item` | Attach group-level N/G/C classification to snapshot RAW items when available. |
| funcao | `_normalized_raw_snapshot_filters` | Normalize API filter inputs for snapshot list and suggestion endpoints. |
| funcao | `_raw_snapshot_mineral_key` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_candidate_matches_mineral_filter` | Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica. |
| funcao | `_raw_snapshot_item_matches_argilomineral_filter` | Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica. |
| funcao | `_raw_snapshot_item_matches_filters` | Apply query, status, preparation and mineral filters to a snapshot item. |
| funcao | `_candidate_score` | Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica. |
| funcao | `_raw_snapshot_mineral_rank` | Rank mineral-filtered rows by whether the target is the top candidate. |
| funcao | `_filtered_raw_snapshot_pairs` | Return raw rows plus enriched/filter-matching snapshot item pairs. |
| funcao | `_snapshot_row_by_id` | Find the backing snapshot row for an API diffractogram id. |
| funcao | `_snapshot_natural_axis_start` | Find the natural curve start angle used to align G/C companions. |
| funcao | `_save_index` | Persist the local import index atomically. |
| funcao | `_relative_to_instance` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_is_safe_local_raw_path` | Ensure local RAW access stays inside approved import/snapshot roots. |
| funcao | `_resolve_snapshot_raw_path` | Resolve snapshot paths across original and current workspace layouts. |
| funcao | `build_diffractogram_record` | Create an index entry and sidecar curve JSON for an imported RAW. |
| funcao | `import_raw_path` | Import a local RAW file and associate it with an Argiloteca record id. |
| funcao | `import_raw_upload` | Import a Flask/Werkzeug upload object and associate it with a record id. |
| funcao | `record_exists` | Return True when the target record is visible in the published record service. |
| funcao | `record_import_error` | Record a failed import attempt so the API can report it consistently. |
| funcao | `load_drx_index` | Expose the local DRX import index to routes/tests. |
| funcao | `_diffractogram_visualization_response` | Monta resposta de curva preservando `two_theta`/`intensity` e anexando `metadata.visualization` via classe `Diffractogram`. |
| funcao | `load_diffractogram_data` | Load curve data for either snapshot-backed or locally imported DRX ids. |
| funcao | `list_raw_snapshot_items` | Return RAW files from the module-wide DRX snapshot, not tied to records. |
| funcao | `_comparison_candidate_match` | Trim a classifier match to comparison-suggestion fields. |
| funcao | `_comparison_candidate` | Trim one mineral candidate for the suggestion API. |
| funcao | `_comparison_suggestion_item` | Return the compact item payload used in comparison suggestions. |
| funcao | `_add_comparison_suggestion` | Append a comparison suggestion when at least two unique items exist. |
| funcao | `build_raw_snapshot_comparison_suggestions` | Build comparison groups over the full RAW snapshot without loading curves. |
| funcao | `_unique_texts` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_classification_lookup_keys` | Generate robust lookup keys for filenames, stems and sample codes. |
| funcao | `_load_mineral_classification_index` | Load the derived classifier snapshot as an item lookup index. |
| funcao | `_load_ngc_group_classification_index` | Load group-level N/G/C classification generated by the batch diagnostic script. |
| funcao | `_normalize_ngc_group_candidate` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_ngc_group_classification_for_item` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_mineral_classification_for_item` | Return classifier peaks/candidates for one imported or snapshot item. |
| funcao | `infer_diffractogram_treatment` | Infer the XRD preparation from common local RAW filename suffixes. |
| funcao | `_sample_contexts` | Index record sample metadata by sample code for imported DRX rows. |
| funcao | `_analysis_contexts` | Index record analysis metadata by sample code. |
| funcao | `_mineral_contexts` | Index curated mineral context by sample code, with record-level fallback. |
| funcao | `_record_description` | Collect record metadata used to contextualize DRX diffractograms. |
| funcao | `_enrich_diffractogram` | Attach sample, analysis and classifier context to an imported DRX item. |
| funcao | `list_records_with_drx` | Return records that have at least one imported DRX entry. |
| funcao | `decimate_series` | Keep browser payloads bounded while preserving the full converted file. |

### `argiloteca/services/drx_analysis.py`

Construcao de runs analiticos versionados, hashes de configuracao e matches diagnosticos.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `_config_hash` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_finite_float` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_diagnostic_peak_matches` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `build_drx_analysis_run` | Run reusable DRX processing and return a versioned analysis contract. |

### `argiloteca/services/drx_cif_simulation.py`

Entrada para simulacao DRX a partir de CIF e normalizacao de parametros.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `_normalise_wavelength_label` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `build_cif_simulation_payload` | Simulate a powder XRD pattern from CIF bytes via the isolated engine. |

### `argiloteca/services/drx_external_jobs.py`

Fila simples de jobs externos para motores DRX isolados e adaptadores locais.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `_jobs_dir` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_job_path` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_job_artifact_dir` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_write_job` | Gera artefatos derivados, relatórios ou saídas serializadas com parâmetros e proveniência para auditoria posterior. |
| funcao | `submit_external_job` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `get_external_job` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `list_external_jobs` | List persisted jobs from the bounded jobs directory. |
| funcao | `claim_next_external_job` | Move the oldest queued job to running for an offline worker. |
| funcao | `complete_external_job` | Persist a terminal or intermediate status for one external DRX job. |
| funcao | `_adapter_command` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_write_input_manifest` | Gera artefatos derivados, relatórios ou saídas serializadas com parâmetros e proveniência para auditoria posterior. |
| funcao | `run_external_job_adapter` | Execute one claimed external job through a configured command adapter. |

### `argiloteca/services/drx_ngc_workflow.py`

Workflow N/G/C backend que monta grupos natural/glicolado/calcinado e chama a engine V3.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `_finite_float` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_d_from_two_theta` | Converte posição angular 2θ em espaçamento interplanar d pela Lei de Bragg. |
| funcao | `_preparation_key` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_sample_base` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_peak_d` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_peak_intensity` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_compact_peak` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_strongest_peak` | Seleciona o pico mais intenso dentro de uma janela diagnóstica em Å. |
| funcao | `_item_from_payload` | Normaliza um difratograma recebido da UI para o contrato interno N/G/C. |
| funcao | `_compact_targeted_rows` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_script_peak_tables` | Return script-like peak tables per preparation for panel display. |
| funcao | `_script_report` | Expose the batch-script style output in the versioned workflow payload. |
| funcao | `_range_peak` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_interval_peak_intensity` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_interval_observation` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_diagnostic_observation` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_companion_peak_set` | Retorna reflexoes companheiras usadas para evitar pico isolado. |
| funcao | `_peak_present` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_ngc_behavior` | Summarize N/G/C response for the mineral rules shown in the panel. |
| funcao | `_mixed_layer_warnings` | Gera avisos para respostas que devem ser revisadas como misturas. |
| funcao | `_script_interval_diagnostics` | Reproduz a lógica do script de bancada para diagnóstico comparativo N/G/C. |
| funcao | `_candidate_hint` | Return True when curated/classifier candidates already suggest a target. |
| funcao | `_observation_intensity` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_screening_entry` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_targeted_clay_screening` | Triar argilominerais-alvo combinando faixas basais e comportamento N/G/C. |
| funcao | `_evidence` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_best_by_preparation` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_confidence` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_candidate` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `load_diagnostic_rules_ngc` | Load versioned N/G/C diagnostic rules kept separate from WebMineral. |
| funcao | `load_webmineral_vocabulary_summary` | Load compact WebMineral vocabulary metadata for family/category context. |
| funcao | `_obs_peak` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_obs_d` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_format_peak_text` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_normalise_score` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_candidate_status` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_candidate_interpretation` | Monta um candidato mineralógico no contrato público da API N/G/C. |
| funcao | `_observations_for_clay_rules` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `_matched_peak` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `interpret_clay_minerals_ngc` | Interpreta argilominerais a partir do comportamento entre N, G e C. |
| funcao | `_interpret_group` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `build_ngc_workflow` | Agrupa difratogramas selecionados e executa o workflow N/G/C versionado. |

### `argiloteca/services/drx_reference_index.py`

Indice local de referencias DRX, manifestos e curvas padrao.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `_normalise_key` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_compact_peak` | Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar. |
| funcao | `_rruff_manifest_path` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_cif_cod_manifest_path` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_source_entry` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_reference_search_key` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_load_cif_cod_rows` | Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática. |
| funcao | `load_reference_index` | Build a compact cached reference index from curated/static manifests. |
| funcao | `search_reference_index` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `reference_pattern_from_index` | Return one indexed reference as a reference-pattern compatible payload. |

### `argiloteca/services/drx_references.py`

Parser e comparador de padroes de referencia JSON/texto/CIF.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `_finite_float` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `two_theta_to_d` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `d_to_two_theta` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_normalise_reference_peaks` | Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar. |
| funcao | `_parse_json_reference` | Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática. |
| funcao | `_split_text_row` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_parse_text_reference` | Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática. |
| funcao | `_parse_cif_reference` | Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática. |
| funcao | `parse_reference_pattern_bytes` | Parse a reference peak list from JSON/text, or metadata from CIF. |
| funcao | `compare_reference_pattern` | Match observed DRX peaks against one parsed reference pattern. |

### `argiloteca/services/drx_report.py`

Relatorio tecnico HTML/JSON para uma curva DRX carregada.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `_qc_messages` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_candidate_summary` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_peak_summary` | Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar. |
| funcao | `build_drx_technical_report` | Build a compact, versioned report payload for one DRX analysis. |
| funcao | `_cell` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_table` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `render_drx_technical_report_html` | Render a backend HTML view from a versioned DRX technical report. |

### `argiloteca/services/drx_runs.py`

Persistencia e consulta de runs DRX em arquivos JSON locais.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `_runs_dir` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_safe_run_id` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_run_path` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_hash_payload` | Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática. |
| funcao | `persist_drx_run` | Persist a versioned DRX run artifact under instance/argiloteca_drx_runs. |
| funcao | `get_drx_run` | Load one persisted DRX run artifact. |
| funcao | `list_drx_runs` | List run artifacts without opening unrelated directories. |

### `argiloteca/services/drx_science_engine.py`

Ponte com ambiente cientifico isolado para simulacao, deteccao e ajuste de picos.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `science_python_path` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `cif_simulator_path` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `scipy_peak_detector_path` | Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar. |
| funcao | `lmfit_peak_fitter_path` | Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar. |
| funcao | `_engine_env` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_last_json_line` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_run_engine` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `simulate_cif_pattern` | Simulate powder XRD peaks for CIF bytes using the isolated engine. |
| funcao | `detect_peaks_scipy` | Detect peaks with scipy.signal.find_peaks in the isolated engine. |
| funcao | `fit_peaks_lmfit` | Fit selected peaks with lmfit PseudoVoigtModel in the isolated engine. |
| funcao | `science_engine_status` | Return a compact status payload for the isolated scientific engine. |

### `argiloteca/services/drx_selection_report.py`

Relatorio reproduzivel para conjunto selecionado no painel.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `_config_hash` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_first` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_compact_peak` | Processa picos DRX e grandezas cristalográficas, relacionando 2θ, d-spacing e intensidade para apoiar triagem mineralógica auxiliar. |
| funcao | `render_drx_selection_report_html` | Render a printable backend HTML report from a selection contract. |
| funcao | `_compact_item` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `_ngc_summary` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `build_drx_selection_report` | Build a reproducible report for the selected DRX comparison set. |

### `argiloteca_drx/diagnostics/__init__.py`

Exporta a engine diagnostica explicavel N/G/C.

Este arquivo nao declara funcoes/classes executaveis; fornece template, estilo, constantes ou configuracao consumida pelo painel.

### `argiloteca_drx/diagnostics/ambiguity_rules.py`

Regras obrigatorias de ambiguidade em janelas 7, 10, 12, 14 e 3.33 A.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `evaluate_ambiguities` | Executa uma etapa auxiliar do fluxo do Painel DRX. |

### `argiloteca_drx/diagnostics/confidence_engine.py`

Pontuacao de confianca e bloqueios de alta confianca em dados incompletos.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `confidence_label` | Calcula pontuacao ou nivel de confianca auxiliar. |
| funcao | `score_candidate` | Calcula pontuacao ou nivel de confianca auxiliar. |

### `argiloteca_drx/diagnostics/demo_rule_engine.py`

Exemplo minimo de chamada da engine V3.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `demo` | Executa uma etapa auxiliar do fluxo do Painel DRX. |

### `argiloteca_drx/diagnostics/diagnostic_behavior_rules.py`

Constantes de versao e politica da engine.

Este arquivo nao declara funcoes/classes executaveis; fornece template, estilo, constantes ou configuracao consumida pelo painel.

### `argiloteca_drx/diagnostics/diagnostic_decision_tree.py`

Arvore decisoria N/G/C explicavel com candidatos, interestratificados e confianca.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `_candidate` | Cria um candidato mineralogico padronizado. |
| funcao | `_peak_set_score` | Recupera a pontuacao de um conjunto de picos companheiros. |
| funcao | `_context_has` | Verifica contexto e quimica textual para reforcos auxiliares. |
| funcao | `_build_candidates` | Converte comportamentos N/G/C em candidatos mineralogicos. |
| funcao | `_recommended_tests` | Gera proximos testes recomendados a partir das incertezas detectadas. |
| funcao | `interpret_ngc` | Executa a engine completa de interpretacao N/G/C. |

### `argiloteca_drx/diagnostics/diagnostic_graph.py`

Grafo de evidencias, regras e relacoes diagnosticas.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `build_diagnostic_graph` | Monta payload, relatorio, indice ou estrutura derivada para consumo posterior. |

### `argiloteca_drx/diagnostics/empirical_builder.py`

Construtor de ranges empiricos a partir de padroes validados por especialista.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `_percentile` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao | `_provenance_hash` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao | `build_empirical_ranges` | Monta payload, relatorio, indice ou estrutura derivada para consumo posterior. |

### `argiloteca_drx/diagnostics/empirical_ranges.py`

Loader de ranges empiricos locais.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `load_empirical_ranges` | Carrega dados locais ou configuracao usada pelo painel. |

### `argiloteca_drx/diagnostics/evidences.py`

Helpers para normalizar picos, localizar janelas e registrar evidencias.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `prep_key` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao | `number` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao | `normalize_peaks` | Normaliza valores para comparacao e exibicao consistentes. |
| funcao | `find_peak` | Processa, seleciona ou descreve picos de difratograma. |
| funcao | `has_peak` | Processa, seleciona ou descreve picos de difratograma. |
| funcao | `evidence` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao | `relation` | Executa uma etapa auxiliar do fluxo do Painel DRX. |

### `argiloteca_drx/diagnostics/literature_ranges.py`

Catalogo de faixas bibliograficas e comportamento mineralogico auxiliar.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `peak` | Cria um objeto de faixa diagnostica bibliografica. |
| funcao | `get_literature_ranges` | Retorna o catalogo bibliografico usado pela engine DRX V3. |

### `argiloteca_drx/diagnostics/matcher.py`

API publica para match de pico contra literatura, empirico e Pre-Sal.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `match_peak` | Compara observacoes com referencias, candidatos ou regras. |

### `argiloteca_drx/diagnostics/mixed_layer_engine.py`

Detector de interestratificados I/S, C/S, K/S, T/S e corrensita.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `detect_mixed_layers` | Detecta candidatos de interestratificados a partir dos picos e comportamentos. |

### `argiloteca_drx/diagnostics/octahedral_classifier.py`

Classificador auxiliar d060 dioctaedrico/intermediario/trioctaedrico.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `classify_octahedral` | Classifica d060 segundo as janelas estruturais auxiliares de Meunier. |

### `argiloteca_drx/diagnostics/peak_sets.py`

Avaliador de conjuntos de picos companheiros.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `evaluate_peak_sets` | Avalia picos companheiros por familia. |

### `argiloteca_drx/diagnostics/presalt_reference_dataset.py`

Dataset empirico local de argilas magnesianas do Pre-Sal.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `load_presalt_reference_dataset` | Carrega dados locais ou configuracao usada pelo painel. |

### `argiloteca_drx/diagnostics/range_comparator.py`

Comparador de picos observados com ranges de literatura, empiricos e Pre-Sal.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `compare_ranges` | Executa comparacao por ranges. |

### `argiloteca_drx/diagnostics/schema.py`

Validador leve do payload diagnostico V3.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `validate_diagnostic_payload` | Valida ou protege entrada contra valores invalidos. |

### `argiloteca_drx/diagnostics/serializers.py`

Serializacao do diagnostico para campos customizados InvenioRDM.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `serialize_for_invenio` | Executa uma etapa auxiliar do fluxo do Painel DRX. |

### `argiloteca_drx/diagnostics/treatment_interpreter.py`

Interpretador de comportamento entre tratamentos N/G/C.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `interpret_treatments` | Interpreta o comportamento dos picos entre Natural, Glicolado e Calcinado. |

### `argiloteca_drx_core/__init__.py`

Namespace de compatibilidade para nucleo DRX reutilizavel.

Este arquivo nao declara funcoes/classes executaveis; fornece template, estilo, constantes ou configuracao consumida pelo painel.

### `argiloteca_drx_core/contracts.py`

Contratos e schemas versionados do nucleo DRX.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `auxiliary_policy` | Return the standard non-confirmatory interpretation policy. |

### `argiloteca_drx_core/curves.py`

Parser reutilizavel de curvas RAW/texto e funcoes Bragg.

| Tipo | Nome | Descricao |
|---|---|---|
| classe | `CurveParseError` | Raised when a diffractogram curve cannot be parsed. |
| classe | `CurveData` | In-memory 1D diffractogram curve. |
| funcao | `_read_float32_series` | Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática. |
| funcao | `_build_axis` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `parse_raw_bytes` | Parse supported Bruker/EVA-like RAW byte layouts. |
| funcao | `_parse_number` | Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática. |
| funcao | `_text_curve_columns` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `parse_text_curve_bytes` | Parse a simple two-column 2theta/intensity text curve. |
| funcao | `parse_curve_bytes` | Parse an uploaded diffractogram by extension, with RAW/text fallbacks. |
| funcao | `normalize_max` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `normalize_area` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `calculate_d_spacing` | Convert 2theta to d-spacing with Bragg's law. |
| funcao | `calculate_two_theta` | Convert d-spacing to 2theta with Bragg's law. |

### `argiloteca_drx_core/diffractogram.py`

Modelo canonico de difratograma para visualizacao e auditoria geometrica.

| Tipo | Nome | Descricao |
|---|---|---|
| classe | `Diffractogram` | Representa curva 1D `2θ/intensidade`, valida pontos, calcula dominios, normaliza intensidade, calcula d-spacing e gera payload para o painel. |
| funcao | `_finite_float` | Converte valores heterogeneos em numero finito ou `None`. |
| funcao | `_round_or_none` | Arredonda valores opcionais preservando ausencia de dado. |
| metodo | `from_curve_data` | Cria `Diffractogram` a partir de `CurveData`. |
| metodo | `from_payload` | Cria `Diffractogram` a partir do JSON historico do painel. |
| metodo | `cleaned_points` | Retorna pares finitos `2θ/intensidade`. |
| metodo | `validation` | Retorna status de validade, numero de pontos e avisos da curva. |
| metodo | `x_domain` | Calcula intervalo do eixo `2θ`. |
| metodo | `y_domain` | Calcula intervalo de intensidade. |
| metodo | `normalized_intensity` | Converte intensidade para escala visual `0-100`. |
| metodo | `d_spacing_axis` | Calcula eixo auxiliar em Å pela Lei de Bragg. |
| metodo | `decimated` | Reduz pontos para renderizacao preservando amostragem regular. |
| metodo | `visualization_summary` | Gera metadados de visualizacao com regra geometrica do Capitulo 3. |
| metodo | `to_visualization_payload` | Serializa curva para o contrato `metadata`, `two_theta`, `intensity`. |

### `argiloteca_drx_core/ngc.py`

Wrapper de compatibilidade para workflow N/G/C.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `build_ngc_workflow` | Delegate to the current service implementation while core API stabilizes. |

### `argiloteca_drx_core/processing.py`

Wrappers de compatibilidade para processamento ALS avancado.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `process_advanced_als_curve` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `advanced_als_summary` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `compact_advanced_als_curve` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |

### `argiloteca/static/js/drx-comparacao.js`

Aplicacao frontend do painel: estado, renderizacao, upload RAW, comparacao, N/G/C e exportacoes.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao JS | `parseAuthorizedMineralSlugs` | Interpreta entrada externa e converte para estrutura interna do painel. |
| funcao JS | `parseAuthorizedMineralAliases` | Interpreta entrada externa e converte para estrutura interna do painel. |
| funcao JS | `currentRecordId` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `hasRecordContext` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `currentArgilomineralSlug` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `currentArgilomineralLabel` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `escapeHtml` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `formatNumber` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `fetchJson` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `fetchOptionalJson` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `uploadRawFormData` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `queryUrl` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `fillSelect` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `loadRecords` | Carrega dados locais ou configuracao usada pelo painel. |
| funcao JS | `renderTags` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `treatmentLabel` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `inferExternalTreatment` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `inferExternalSampleBase` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `shiftPeakAxisFields` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `shiftAdvancedCurveAxis` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `applyAxisOffsetToExternalItem` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `applyExternalSingleRawAxisFallback` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `applyExternalNgcAxisAlignment` | Opera grupos ou evidencias Natural/Glicolado/Calcinado. |
| funcao JS | `treatmentBadge` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `diffractogramContext` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `sampleLabel` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `analysisLabel` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `formatScore` | Calcula pontuacao ou nivel de confianca auxiliar. |
| funcao JS | `renderScoreBreakdown` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderMatchedPeaks` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `percent` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `recordUrl` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `recordButton` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderRelatedRecordMatches` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `mineralSlug` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `resolveMineralSlug` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `mineralLink` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `mineralListLinks` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `linkKnownMineralText` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `escapeRegExp` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `evidenceSummary` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `mineralRuleAlias` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `ruleAppliesToMineral` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `readableMatchPeak` | Compara observacoes com referencias, candidatos ou regras. |
| funcao JS | `stageMatches` | Compara observacoes com referencias, candidatos ou regras. |
| funcao JS | `diagnosticProfileForMineral` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `confidenceFromMineral` | Calcula pontuacao ou nivel de confianca auxiliar. |
| funcao JS | `htmlEvidenceList` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderRecordList` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `diffractogramUrl` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `neuralEvidenceUrl` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `technicalReportUrl` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `referenceCompareUrl` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `compactNgcPeaks` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `ngcWorkflowItemPayload` | Opera grupos ou evidencias Natural/Glicolado/Calcinado. |
| funcao JS | `ngcWorkflowSelectionKey` | Opera grupos ou evidencias Natural/Glicolado/Calcinado. |
| funcao JS | `refreshNgcWorkflow` | Opera grupos ou evidencias Natural/Glicolado/Calcinado. |
| funcao JS | `firstStoredSelectedItem` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `compareReferenceForSelected` | Compara observacoes com referencias, candidatos ou regras. |
| funcao JS | `loadNeuralEvidenceForItem` | Carrega dados locais ou configuracao usada pelo painel. |
| funcao JS | `packageCurveUrl` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `packageUrl` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `legacyPackageUrl` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `fetchPackageJson` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `tryUrl` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `packageDisplayLabel` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `addPackageCurve` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `addSnapshotRaw` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `suggestionPreparation` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `suggestionHasCompleteNgcTrio` | Opera grupos ou evidencias Natural/Glicolado/Calcinado. |
| funcao JS | `bestNgcSuggestionForMineral` | Opera grupos ou evidencias Natural/Glicolado/Calcinado. |
| funcao JS | `suggestionAutoloadLabel` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `suggestionItemSnapshotId` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `addSnapshotSuggestionItems` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `loadSingleMineralSnapshotFromUrl` | Carrega dados locais ou configuracao usada pelo painel. |
| funcao JS | `loadMineralNgcSelectionFromUrl` | Carrega dados locais ou configuracao usada pelo painel. |
| funcao JS | `loadMineralSelectionFromUrl` | Carrega dados locais ou configuracao usada pelo painel. |
| funcao JS | `addExternalRaw` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `addExternalRawFiles` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `loadPackageSelectionFromUrl` | Carrega dados locais ou configuracao usada pelo painel. |
| funcao JS | `renderRawPickerItems` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `rruffOdrCurveLabel` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `isValidRruffOdrChecksum` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `isConfirmedRruffOdrCurve` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `rruffOdrPolicyText` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `rruffOdrCurveMineralSlug` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `rruffOdrCurveMatchesSlug` | Compara observacoes com referencias, candidatos ou regras. |
| funcao JS | `rruffOdrCurvesForSlug` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `rruffOdrActiveTarget` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `setRruffOdrTargetMineral` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `syncRruffOdrTypeToTarget` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `rruffOdrFilteredCurves` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `rruffOdrPreferredCurveIndex` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `populateRruffOdrSelect` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `selectedRruffOdrCurve` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `rruffOdrNormalizedY` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderRruffOdrMeta` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderRruffOdrStatus` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderRruffOdrAbsenceRule` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `rruffOdrScale` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `rruffOdrLinePath` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `rruffOdrTicks` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderRruffOdrSvgChart` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderRruffOdrPlot` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `loadRruffOdrCurves` | Carrega dados locais ou configuracao usada pelo painel. |
| funcao JS | `showRruffOdrPanel` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `syncRruffOdrWithActivePanelMineral` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `staticManifestUrl` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `loadStaticManifest` | Carrega dados locais ou configuracao usada pelo painel. |
| funcao JS | `loadPackageItems` | Carrega dados locais ou configuracao usada pelo painel. |
| funcao JS | `fetchSnapshotPage` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `fetchPage` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `itemMatchesRawPickerFilters` | Compara observacoes com referencias, candidatos ou regras. |
| funcao JS | `rawPickerPayloadFromStaticManifest` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `fetchRawPickerPayload` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `loadRawPickerItems` | Carrega dados locais ou configuracao usada pelo painel. |
| funcao JS | `loadSuggestionItems` | Carrega dados locais ou configuracao usada pelo painel. |
| funcao JS | `loadSuggestionPayload` | Carrega dados locais ou configuracao usada pelo painel. |
| funcao JS | `buildComparisonSuggestions` | Monta payload, relatorio, indice ou estrutura derivada para consumo posterior. |
| funcao JS | `renderSuggestions` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `comparisonSuggestionRank` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `prioritizeComparisonSuggestions` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `indexGeologistTriage` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `triageQueueFromSnapshotSuggestions` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `loadGeologistTriage` | Carrega dados locais ou configuracao usada pelo painel. |
| funcao JS | `loadGeologistSimilarityReview` | Carrega dados locais ou configuracao usada pelo painel. |
| funcao JS | `renderEvidenceChips` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `geologistQueueOrder` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `geologistQueueTitle` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderGeologistQueueItem` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderGeologistTriageQueue` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `loadGeologistTriageQueue` | Carrega dados locais ou configuracao usada pelo painel. |
| funcao JS | `addTriageCandidate` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `loadComparisonSuggestions` | Carrega dados locais ou configuracao usada pelo painel. |
| funcao JS | `addSuggestion` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `toggleSelection` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `transformedSeries` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `curveArea` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `showSvgChart` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `showPlotlyChart` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `extent` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `niceTicks` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `firstNonEmptySeries` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `numericSeries` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `alignedNumericSeries` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `svgNumber` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `hasFiniteSeriesValue` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `usesClassifiedAxis` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `advancedScriptSeries` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `advancedScriptChartData` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `paddedDomain` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `scriptLinePoints` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `nearestArrayPoint` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `mapAdvancedPeak` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `advancedScriptPeaks` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `pushScriptPanelGrid` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `pushScriptLegend` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderScriptStyleAdvancedChart` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderChart` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderPlotlyMainChart` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `nearestSeriesPoint` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderPeakMarkers` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `showTooltip` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `compareByCandidateScore` | Compara observacoes com referencias, candidatos ou regras. |
| funcao JS | `candidateMatchesMineralSlug` | Compara observacoes com referencias, candidatos ou regras. |
| funcao JS | `bestScoredClayCandidate` | Calcula pontuacao ou nivel de confianca auxiliar. |
| funcao JS | `renderBestScoredClayCandidate` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `geologistTriageForItem` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `candidatePeakEvidence` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `qcEvidenceForItem` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderCandidateEvidenceBlock` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderGeologistEvidencePanel` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `backendNgcGroups` | Opera grupos ou evidencias Natural/Glicolado/Calcinado. |
| funcao JS | `hasBackendNgcCompleteGroup` | Opera grupos ou evidencias Natural/Glicolado/Calcinado. |
| funcao JS | `bestNgcDiagnosticCandidate` | Opera grupos ou evidencias Natural/Glicolado/Calcinado. |
| funcao JS | `renderDiagnosticV3Block` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `sourceRuleTargets` | Mapeia candidatos exibidos para alvos das bases dos Capitulos 7 e 8. |
| funcao JS | `sourceChapterLabel` | Resolve o capitulo/titulo da fonte usada em `Regra-fonte`. |
| funcao JS | `renderSourceRulePanel` | Renderiza regras aplicadas, perfil mineralogico e regras geometricas do Capitulo 3. |
| funcao JS | `clayCandidateAsSourceTarget` | Converte candidatos N/G/C do backend para alvos bibliograficos. |
| funcao JS | `compactRuleSourceText` | Resume a regra-fonte da matriz N/G/C citando Cap. 3, Cap. 7 e Cap. 8 quando aplicavel. |
| funcao JS | `peakCellForPreparation` | Mostra evidencias de pico por preparo Natural, Glicolado e Calcinado. |
| funcao JS | `renderNgcEvidenceMatrix` | Renderiza a matriz N/G/C por hipotese mineralogica. |
| funcao JS | `renderBackendNgcPrimarySummary` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `isExternalRawItem` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderExternalRawFileRows` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `externalSimilarityEntries` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderExternalSimilarityLinks` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderExternalNgcCandidateEvidenceFromBackend` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderExternalNgcCandidateEvidenceLocal` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderExternalRawMergedNgcPanel` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderSelectedClayEvidence` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `compareByMineralRowScore` | Compara observacoes com referencias, candidatos ou regras. |
| funcao JS | `clayMineralsFromAssembly` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `bestClayMineralFromAssembly` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `activePanelArgilomineral` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderRruffOdrReviewLink` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `interpretationStrengthLabel` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `alternativeClayMinerals` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `alternativeClayMineralsHtml` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `selectedNgcCurveComparisonText` | Opera grupos ou evidencias Natural/Glicolado/Calcinado. |
| funcao JS | `renderSelectedNgcCompleteSummary` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderReferenceComparisonBlock` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderNgcBackendWorkflowBlock` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderObservationValues` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderSelectedSummary` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `aggregateMinerals` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderMineralPanel` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderMineralPanelReport` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `xrdnetPercent` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `xrdnetPredictionBadges` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `neuralEvidenceCandidateRows` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `neuralEvidenceQualityLine` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `neuralEvidenceBinsHtml` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderNeuralEvidenceBlock` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `xrdnetNormalize` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `xrdnetBasename` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `xrdnetTerms` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `xrdnetRowTerms` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `xrdnetItemTerms` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `xrdnetTermsMatch` | Compara observacoes com referencias, candidatos ou regras. |
| funcao JS | `xrdnetPredictionForItem` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `shouldShowXrdnetForItem` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `ensureXrdnetSummary` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderXrdnetContextBlock` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `isMineralPanelFullscreen` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `syncMineralPanelFullscreenButton` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `toggleMineralPanelFullscreen` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `updateStatus` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderAll` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `exportCsv` | Exporta resultado em arquivo, HTML, CSV, JSON ou documento. |
| funcao JS | `exportJson` | Exporta resultado em arquivo, HTML, CSV, JSON ou documento. |
| funcao JS | `exportSvg` | Exporta resultado em arquivo, HTML, CSV, JSON ou documento. |
| funcao JS | `mineralDescription` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `uniqueMineralCandidates` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `braggDSpacing` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `braggTwoTheta` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `mineralSlugName` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `mineralClass` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `mineralGeologicalRole` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `confidenceRank` | Calcula pontuacao ou nivel de confianca auxiliar. |
| funcao JS | `confidenceLabel` | Calcula pontuacao ou nivel de confianca auxiliar. |
| funcao JS | `statusFromEvidence` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `allCandidateRows` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `buildMineralAssembly` | Monta payload, relatorio, indice ou estrutura derivada para consumo posterior. |
| funcao JS | `classifyAssemblyByClass` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `generalInterpretationConfidence` | Calcula pontuacao ou nivel de confianca auxiliar. |
| funcao JS | `relativeIntensityAt` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `simplePeakPicking` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `observedPeaks` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `isDiagnosticPeak` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `isDiagnosticPeakDSpacing` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `hasDiagnosticCandidate` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `isDiagnosticPeakTwoTheta` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `matchObservedDSpacing` | Compara observacoes com referencias, candidatos ou regras. |
| funcao JS | `matchObservedTwoTheta` | Compara observacoes com referencias, candidatos ou regras. |
| funcao JS | `candidateHasDiagnosticRangePeak` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `matchPeakToCandidate` | Compara observacoes com referencias, candidatos ou regras. |
| funcao JS | `diagnosticObservation` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `buildPeakRows` | Monta payload, relatorio, indice ou estrutura derivada para consumo posterior. |
| funcao JS | `methodPayload` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `peakDetectionDescription` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `renderMethodologyLimitations` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `mainEvidences` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `interpretationUncertainties` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `recommendationsFor` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `interpretationPeakEvidenceRows` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `treatmentCoverageText` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `interpretationNgcEvidenceRows` | Opera grupos ou evidencias Natural/Glicolado/Calcinado. |
| funcao JS | `interpretationHtmlList` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `interpretationRelationRow` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderInterpretationRelationRows` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `abundanceClass` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `geologicalInterpretationText` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `geologicalInterpretationHtml` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `isAuthorizedClayMineral` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `otherMineralsSummary` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `reportRows` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `truncateReportText` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `reportSampleSummary` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `styledReportSvg` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `reportCurveData` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `lowAngleReportSvg` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `xScale` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `yScale` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `htmlList` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `htmlListLinked` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderExecutiveSummary` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `sampleBaseForNgc` | Opera grupos ou evidencias Natural/Glicolado/Calcinado. |
| funcao JS | `buildNgcGroups` | Monta payload, relatorio, indice ou estrutura derivada para consumo posterior. |
| funcao JS | `preparationStage` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `stageLabelForCell` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `formatPeakCell` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `buildBasalTrajectoryRows` | Monta payload, relatorio, indice ou estrutura derivada para consumo posterior. |
| funcao JS | `mineralReflectionRules` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `buildConfirmatoryReflectionRows` | Monta payload, relatorio, indice ou estrutura derivada para consumo posterior. |
| funcao JS | `buildConfirmatoryMineralComparison` | Monta payload, relatorio, indice ou estrutura derivada para consumo posterior. |
| funcao JS | `renderConfirmatoryReflectionPanel` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `buildDiagnosticCompletenessRows` | Monta payload, relatorio, indice ou estrutura derivada para consumo posterior. |
| funcao JS | `strongestPeakInDRange` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `semTituloRangeLabel` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `semTituloPeakIntensity` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `strongestSemTituloPeak` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `semTituloPeak` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `semTituloPeakEvidence` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `semTituloNgcStatus` | Opera grupos ou evidencias Natural/Glicolado/Calcinado. |
| funcao JS | `diagnoseSemTituloNgcGroup` | Detecta evidencias ou hipoteses diagnosticas auxiliares. |
| funcao JS | `renderSemTituloNgcDiagnosticPanel` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `peakEvidenceText` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `stabilityScore` | Calcula pontuacao ou nivel de confianca auxiliar. |
| funcao JS | `buildNgcTrajectoryScore` | Monta payload, relatorio, indice ou estrutura derivada para consumo posterior. |
| funcao JS | `renderNgcScoreDetails` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `buildNgcInterpretations` | Monta payload, relatorio, indice ou estrutura derivada para consumo posterior. |
| funcao JS | `renderNgcInterpretationPanel` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `buildNgcSummary` | Monta payload, relatorio, indice ou estrutura derivada para consumo posterior. |
| funcao JS | `basalEvidenceSummary` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderAutomatedAnalysesSection` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `normalizeReportSeries` | Normaliza valores para comparacao e exibicao consistentes. |
| funcao JS | `backgroundReportSvg` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderBackgroundSection` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderBasalTrajectoryTable` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderConfirmatoryReflectionTable` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderDiagnosticCompletenessTable` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderPeakTable` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderDiagnosticCriteria` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `seen` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `renderAssemblyTable` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderAbundanceSection` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderShortMineralCards` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderFacts` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderTechnicalBlocks` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderSourceBlocks` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `renderMineralReport` | Renderiza HTML ou bloco visual a partir de dados estruturados. |
| funcao JS | `fetchMineralReportSummaries` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `buildPdfHtml` | Monta payload, relatorio, indice ou estrutura derivada para consumo posterior. |
| funcao JS | `exportPdfReport` | Exporta resultado em arquivo, HTML, CSV, JSON ou documento. |
| funcao JS | `download` | Exporta resultado em arquivo, HTML, CSV, JSON ou documento. |
| funcao JS | `items` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `peaks` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `candidates` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `rows` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `selectedRows` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `diffractograms` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `item` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `sx` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `sy` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `points` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `add` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `topCandidate` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `evidence` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `reviewCounts` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `visible` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `step` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `finite` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `padding` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `explicit` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `syUpper` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `syLower` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `x` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `matches` | Compara observacoes com referencias, candidatos ou regras. |
| funcao JS | `flags` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `web` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `xrd` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `clayCandidate` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `evidences` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `competitors` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `behavior` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `peakSets` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `mixed` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `ambiguities` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `tests` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `warnings` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `minerals` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `diagnostics` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `screenings` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `filename` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `related` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `bestClay` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `diagnosticRows` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `peak` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `screeningRows` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `groups` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `intervalDiagnostics` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `scriptMinerals` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `scriptDiagnostics` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `scriptPeakTables` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `peakRows` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `targetScreening` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `clayWarnings` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `missingPreparations` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `clayCandidates` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `evidenceFor` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `evidenceAgainst` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `overlaps` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `mixedWarnings` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `targetedRows` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `labels` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `thetaRadians` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `relative` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `sourcePeaks` | Processa, seleciona ou descreve picos de difratograma. |
| funcao JS | `clayMinerals` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `hypotheses` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `completeness` | Controla ciclo de vida de jobs externos. |
| funcao JS | `score` | Calcula pontuacao ou nivel de confianca auxiliar. |
| funcao JS | `numeric` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `xValues` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `qc` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `selected` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `references` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `selectedBlocks` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `occurrenceFacts` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `nextWidth` | Executa uma etapa auxiliar do fluxo do Painel DRX. |
| funcao JS | `delta` | Executa uma etapa auxiliar do fluxo do Painel DRX. |

### `argiloteca/static/css/drx-comparacao.css`

Estilos responsivos do painel DRX, grafico, tabelas, cards e relatorios.

Este arquivo nao declara funcoes/classes executaveis; fornece template, estilo, constantes ou configuracao consumida pelo painel.

### `argiloteca/templates/semantic-ui/argiloteca/drx_comparacao.html`

Template Jinja que injeta endpoints, contexto e estrutura DOM do painel.

Este arquivo nao declara funcoes/classes executaveis; fornece template, estilo, constantes ou configuracao consumida pelo painel.

### `scripts/batch_ngc_raw_diagnostics.py`

Processamento batch N/G/C de arquivos RAW/texto com diagnostico e relatorios.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `read_curve` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `baseline_als` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `safe_savgol` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `calculate_quartz_offset` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `intensity_in_range` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `targeted_quality` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `targeted_basal_peak_scan` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `merge_targeted_peaks` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `diagnose_clays` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `process_spectrum` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `infer_treatment` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `discover_samples` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `plot_sample` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `safe_dir_name` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `route_raw_files` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `process_sample` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `diagnostic_score_for_mineral` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `group_classification_candidates` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `best_treatment_summary` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `build_ngc_group_classification_payload` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `write_ngc_group_csv` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `write_csv` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `load_manual_offsets` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `parse_args` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |
| funcao | `main` | Avalia evidências minerais em séries N/G/C usando d-spacing, comportamento entre tratamentos e ressalvas científicas para evitar identificação automática indevida. |

### `scripts/build_drx_neural_evidence_index.py`

Gera indice compacto de evidencias neurais auxiliares consumido pelo painel.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `utc_now_iso` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `load_json` | Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática. |
| funcao | `normalize_key` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `basename_key` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `path_suffix_keys` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `snapshot_id_for_path` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `compact_number` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `compact_match` | Calcula correspondências e pontuações auxiliares entre amostras, vocabulários ou padrões de referência, sem promover o resultado a confirmação mineralógica. |
| funcao | `compact_candidate` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `compact_quality` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `compact_bins` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `xrdnet_row_keys` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `load_xrdnet_lookup` | Carrega e valida dados de entrada usados pelo fluxo, preservando rastreabilidade e tratando formatos heterogêneos sem assumir validade científica automática. |
| funcao | `evidence_keys` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `find_xrdnet` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `build_index` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |
| funcao | `main` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |

### `scripts/run_drx_external_jobs.py`

Worker CLI para executar jobs externos DRX pendentes.

| Tipo | Nome | Descricao |
|---|---|---|
| funcao | `main` | Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca. |

## Regras de Comentario e Manutencao

- Manter cabecalho cientifico em arquivos Python, JavaScript, CSS e templates do painel.
- Preservar `policy = argiloteca_rule_based_diagnostic` nas saidas diagnosticas da engine N/G/C.
- Usar `confirmed_by_rules`, `probable_by_rules` e `possible_by_rules` como rotulos de saida.
- Comentarios devem explicar regra mineralogica, contrato de dados, loop ou decisao de interface quando a intencao nao for obvia.
- Nao transformar range bibliografico em confirmacao; matches sao hipoteses auxiliares.
- Ao adicionar funcao nova, atualizar esta documentacao ou regenerar o inventario.
