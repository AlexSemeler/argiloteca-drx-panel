# Explicacao do painel DRX - Comparacao

Este documento explica a logica do painel `DRX > Comparacao`, especialmente os blocos de interpretacao mineralogica, comparacao N/G/C, reflexoes confirmatorias e scores exibidos na interface.

O ponto central e: o painel gera hipoteses assistidas para curadoria. Ele nao confirma mineral automaticamente. A confirmacao depende da leitura tecnica do difratograma, qualidade do preparo, comparacao entre tratamentos e possiveis sobreposicoes de picos.

## Projeto

O projeto desenvolve um módulo em Python para comparar arquivos .raw de DRX aplicados a argilominerais, preservando dados brutos e registrando etapas de processamento. O sistema reconstrói curvas 2θ versus intensidade, calcula d-spacing pela Lei de Bragg, corrige linha de base, normaliza sinais, detecta picos e estima FWHM, áreas, intensidades relativas e qualidade. Também compara difratogramas com artigos, teses, dissertações, relatórios e dados científicos organizados por metadados geológicos e analíticos. O objetivo é ranquear referências semelhantes e gerar hipóteses rastreáveis, sem confirmar automaticamente minerais, fortalecendo reprodutibilidade, curadoria científica e reuso de dados em Geoquímica, e apoiando coleções e laboratórios universitários.

## 1. O que a interface compara

A tela de comparacao DRX permite selecionar difratogramas RAW e observar:

- a curva DRX de cada amostra;
- os picos detectados;
- o preparo/tratamento de cada arquivo;
- candidatos mineralogicos vindos do classificador;
- leitura comparativa Natural/Glicolado/Calcinado;
- reflexoes confirmatorias esperadas para argilominerais principais;
- alertas, ausencias e recomendacoes de revisao.

A tela integrada tambem permite:

- adicionar RAWs do snapshot geral ou de um pacote analitico;
- carregar conjuntos sugeridos N/G/C;
- abrir a fila do geologo quando houver triagens derivadas;
- comparar RAW temporario sem gravar o arquivo como registro;
- carregar RAW semelhante encontrado por similaridade;
- mostrar evidencia neural XRDNet apenas como contexto auxiliar quando existir RAW semelhante ou carregado como semelhante;
- exportar CSV e PDF da comparacao.

Os tratamentos usados no painel sao:

| Tratamento | Significado |
|---|---|
| Natural | amostra natural, tambem lida como AD/Natural |
| Glicolado | amostra apos glicolacao, tambem lida como EG/Glicolado |
| Calcinado | amostra aquecida/calcinada, tambem lida como H/Calcinado |
| Indeterminado | o sistema nao conseguiu inferir o preparo |

## 2. Classificacao do preparo N/G/C

O classificador de preparo usa principalmente o nome do arquivo RAW.

Opcoes geradas:

| Campo | Opcoes |
|---|---|
| `treatment` | `natural`, `glicolado`, `calcinado`, `indeterminado` |
| `confidence` | `alta` ou `baixa` |
| `status` | `ok` ou `erro` |
| `review_note` | nota de revisao sobre completude N/G/C |

Regras principais:

- arquivo terminando em `N`, `-N` ou `_N` vira `natural`;
- arquivo terminando em `G`, `-G` ou `_G` vira `glicolado`;
- arquivo terminando em `C`, `-C` ou `_C` vira `calcinado`;
- nomes com `CAL`, `CALC`, `AQUEC`, `HEAT`, `550`, `500`, `350` ou `300` tambem tendem a `calcinado`;
- sem marcador reconhecido, o preparo fica `indeterminado`.

A confianca e `alta` quando o preparo foi identificado pelo nome. Se nao houver marcador N/G/C, a confianca fica `baixa`.

## 3. Janelas diagnosticas em d-spacing

O sistema procura picos em janelas diagnosticas expressas em `d` angstrom. Esses valores nao sao graus `2theta`: o painel mostra o eixo em `2theta`, mas as regras mineralogicas trabalham com `d-spacing`, calculado pela lei de Bragg quando necessario.

Faixas atualmente registradas no vocabulario WebMineral local e no comparador. O JSON completo usado como referencia de comparacao esta em [`povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_argilominerais_vocabulario.json`](povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_argilominerais_vocabulario.json), com os 81 argilominerais, linhas `d/I`, faixas diagnosticas, fontes e metadados usados pelo classificador:

| Regra | Preparo | Janela d (A) | Uso interpretativo |
|---|---|---:|---|
| `RANGE_ILITA_10A` | qualquer | 9,70-10,40 | pico 001 de ilita/mica; estabilidade entre tratamentos reforca hipotese nao expansiva |
| `RANGE_CAULINITA_7A` | qualquer | 6,90-7,80 | pico de caulinita 7 A; sobrepoe com clorita 002 |
| `RANGE_ESMECTITA_N` | Natural | 13,00-16,50 | basal de esmectita em amostra natural |
| `RANGE_ESMECTITA_G` | Glicolado | 16,60-18,60 | expansao apos glicolacao, criterio central para esmectita expansiva |
| `RANGE_ESMECTITA_C` | Calcinado | 9,40-10,40 | colapso termico de esmectita apos aquecimento |
| `RANGE_CLORITA_14A` | qualquer | 13,70-14,60 | pico basal 001 de clorita; deve ser lido com estabilidade termica e ausencia de expansao em EG |
| `RANGE_QUARTZO_101` | qualquer | 3,24-3,44 | pico principal 101 do quartzo; fase nao argilosa que pode dominar a curva |
| `RANGE_QUARTZO_100` | qualquer | 4,23-4,35 | pico secundario 100 do quartzo |

Constantes operacionais atuais:

```python
RANGE_ILITA_10A = (9.7, 10.4)
RANGE_CAULINITA_7A = (6.9, 7.8)

RANGE_ESMECTITA_N = (13.0, 16.5)
RANGE_ESMECTITA_G = (16.6, 18.6)
RANGE_ESMECTITA_C = (9.4, 10.4)

RANGE_CLORITA_14A = (13.7, 14.6)

RANGE_QUARTZO_101 = (3.24, 3.44)
RANGE_QUARTZO_100 = (4.23, 4.35)
```

Esses valores ficam sincronizados em tres pontos principais:

- `argiloteca/argiloteca_custom/argiloteca/services/drx.py`, constante `DRX_DIAGNOSTIC_D_RANGES`;
- `povoamento/drx/classificar_minerais_raw.py`, constantes `RANGE_*` usadas na reclassificacao de lote;
- `povoamento/drx/baixar_webmineral_argilominerais.py` e `povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_argilominerais_vocabulario.json`, vocabulario local usado como referencia auxiliar.

JSONs de apoio versionados para classificacao:

- `povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_argilominerais_vocabulario.json`: cache principal passado em `--cache-referencia`, com 81 registros do vocabulario de argilominerais e linhas de referencia `d/I`;
- `povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_xray_referencia.json`: cache legado usado como fallback por `load_reference()` quando o cache principal nao esta disponivel;
- `povoamento/visualizacao-drx/webmineral/webmineral_argilominerais_vocabulario_manifest.json`: manifesto/rastreabilidade da copia WebMineral usada como referencia.

JSONs de classificacao de RAW, como `classificacao_mineralogica_raw.json`, `classificacao_mineralogica_resumo.json`, `classificacao_tratamento_raw.json` e `publicacao_painel_drx.json`, continuam fora do Git porque sao saidas derivadas de processamento.

Essas janelas nao confirmam mineral sozinhas. Elas ajudam a montar a trajetoria entre os tratamentos.

### Eixo 2theta e deslocamento N/G/C

Quando o RAW glicolado ou calcinado vem com o eixo `2theta` deslocado em relacao ao Natural da mesma amostra, o sistema pode alinhar o eixo antes de classificar e antes de mostrar a curva no painel.

A ordem e:

1. usar correcao manual quando existir em `correcoes_eixo_2theta.json`;
2. se nao houver correcao manual, procurar o quartzo 101 em torno de `3,34 A` para calcular uma calibracao absoluta do eixo;
3. quando houver trio N/G/C, calibrar o Natural pelo quartzo quando possivel e ancorar G/C no inicio corrigido do Natural do mesmo grupo;
4. aplicar o deslocamento N/G/C apenas quando a diferenca for maior que `0,05` grau `2theta`; a calibracao por quartzo usa limiar menor, de `0,02` grau `2theta`;
5. registrar no metadado `two_theta_offset_applied` e marcar a curva como `classificacao_mineralogica_raw_com_eixo_ajustado`.

Na exibicao, quando existe eixo classificado/corrigido, o painel usa esse eixo corrigido para a curva, background, curva corrigida e marcadores de pico. O objetivo e evitar que um RAW glicolado deslocado cerca de 1 grau para a direita seja interpretado visualmente pelo eixo bruto original.

## 4. Classificador mineralogico geral

O classificador mineralogico compara os picos observados do RAW com linhas de referencia mineralogica.

### Como a intensidade do pico e medida

No classificador de lote, a intensidade usada para ordenar e casar picos e a altura relativa do pico, nao a area integrada. A rotina:

1. suaviza a curva;
2. estima o fundo como percentil 10 da curva suavizada;
3. calcula a amplitude util como `maximo_suavizado - fundo`;
4. aceita maximos locais acima de `fundo + 1% da amplitude`;
5. calcula a intensidade relativa:

```text
Irel = 100 * (pico_suavizado - fundo) / (maximo_suavizado - fundo)
```

O campo `intensity` guarda a altura original do ponto no RAW. O campo `relative_intensity` guarda a altura relativa normalizada em porcentagem.

No processamento avancado ALS usado no painel, a curva passa por suavizacao, remocao de background ALS, correcao positiva e normalizacao pelo maior pico corrigido. Nessa rota, `intensity` e a altura corrigida do pico e `relative_intensity` e a altura corrigida normalizada. Area integrada e FWHM tambem podem ser calculados para apoio, mas hoje nao sao o criterio principal da classificacao.

Para clorita, ha uma protecao especifica: se o peak-picking geral nao destacou um pico em `13,70-14,60 A`, o classificador procura o ponto mais forte dentro dessa janela basal 001 e so o aceita se a intensidade relativa for pelo menos `18%`.

Opcoes geradas:

| Campo | Significado |
|---|---|
| `status` | `ok` quando o RAW foi processado; `erro` quando houve falha de leitura |
| `candidates` | lista de minerais candidatos |
| `score` | nota entre 0 e 1 para cada candidato |
| `confidence` | `alta`, `media` ou `baixa` |
| `matched_lines` | numero de linhas de referencia encontradas |
| `reference_lines` | numero total de linhas esperadas para o mineral |
| `coverage` | proporcao de linhas encontradas |

### Como o score mineralogico e calculado

Para cada mineral de referencia, o sistema:

1. le os picos observados no RAW;
2. percorre as linhas esperadas do mineral, com valores de `d` e intensidade de referencia;
3. verifica se algum pico observado esta dentro da tolerancia em `d` ou em `2theta`;
4. calcula a proximidade entre pico observado e linha esperada;
5. pesa mais as linhas de maior intensidade da referencia;
6. aplica uma penalizacao se poucas linhas esperadas foram encontradas.

A formula conceitual e:

```text
score = qualidade_dos_casamentos * penalizacao_por_cobertura
```

No codigo:

```text
score = (weighted_score / total_weight) * (0.55 + 0.45 * coverage)
```

Onde:

- `weighted_score / total_weight` mede a qualidade dos picos casados;
- `coverage` mede quantas linhas esperadas do mineral apareceram;
- uma unica linha muito boa ainda recebe score limitado, porque falta confirmacao por outras reflexoes.

### Como a confianca mineralogica e definida

| Confianca | Regra |
|---|---|
| `alta` | score >= 0,72, coverage >= 0,66 e pelo menos 2 linhas casadas |
| `media` | score >= 0,45 e pelo menos 2 linhas casadas |
| `baixa` | qualquer caso abaixo disso |

Assim, um mineral com score baixo e uma unica ocorrencia deve ser lido como hipotese fraca.

## 5. Painel mineralogico

O painel mineralogico agrega os candidatos encontrados nos difratogramas selecionados.

Campos exibidos:

| Campo | Como ler |
|---|---|
| Mineral sugerido | nome do candidato gerado pelo classificador |
| Grupo | grupo mineralogico quando informado na referencia |
| Tratamentos onde apareceu | em quais preparos o candidato surgiu |
| Confianca | melhor confianca observada para aquele mineral |
| Melhor score | maior score daquele mineral entre as amostras selecionadas |
| Ocorrencias | quantas vezes o mineral apareceu como candidato |
| Amostras | arquivos/amostras que sustentam a hipotese |
| Picos que sustentam | picos observados que casaram com linhas esperadas |
| Picos ausentes importantes | reflexoes esperadas que nao foram observadas |
| Reflexoes fora da faixa medida | reflexoes que nao podiam ser avaliadas pela faixa do difratograma |
| Conflitos | alertas de sobreposicao ou falta de regra diagnostica |
| Limitacoes | limites registrados para aquela interpretacao |
| Recomendacao | orientacao para revisao curatorial |

O campo `ocorrencias` nao e confirmacao. Ele apenas mostra quantas vezes o candidato apareceu. Um mineral pode ter varias ocorrencias e ainda assim ser fraco se os scores forem baixos ou se faltarem reflexoes diagnosticas.

## 6. Exemplo: leitura de Stilpnomelane

Exemplo de saida:

```text
Mineral sugerido: Stilpnomelane
Tratamentos onde apareceu: Glicolado
Confianca: baixa
Melhor score: 0,223
Ocorrencias: 1
```

Leitura correta:

- o mineral apareceu apenas como candidato geral;
- apareceu em um unico tratamento;
- o score e baixo;
- nao ha regra diagnostica especifica cadastrada para ele no painel;
- a recomendacao e tratar como hipotese fraca ate haver picos diagnosticos compativeis.

Neste caso, `Stilpnomelane` nao deve ser usado como interpretacao final sem revisao manual.

## 7. Comparacao N/G/C

A comparacao N/G/C avalia a trajetoria entre:

```text
Natural -> Glicolado -> Calcinado
```

Ela procura padroes de expansao, colapso e estabilidade de picos basais.

Opcoes geradas:

| Campo | Opcoes |
|---|---|
| Status | `trio completo`, `trio incompleto`, `indeterminado` |
| Confianca | `alta`, `media`, `baixa` |
| Hipotese assistida | lista de hipoteses mineralogicas conservadoras |

Hipoteses possiveis:

| Hipotese | Condicao geral |
|---|---|
| compativel com esmectita/montmorilonita expansiva | expansao no glicolado e colapso no calcinado |
| compativel com argilomineral expansivo | ha expansao em EG, mas falta parte da trajetoria |
| compativel com ilita/mica por estabilidade em ~10 A | pico ~10 A estavel entre tratamentos |
| compativel com clorita/vermiculita | pico basal de clorita em 13,70-14,60 A ou pico ~14 A estavel, sem expansao clara em EG |
| compativel com caulinita/clorita | pico ~7 A presente, com risco de sobreposicao |
| evidencia insuficiente | faltam picos ou tratamentos para hipotese consistente |

### Score N/G/C

O score N/G/C tambem vai de 0 a 1.

Componentes:

| Componente | Peso | O que mede |
|---|---:|---|
| completude dos tratamentos | 0,20 | se existem Natural, Glicolado e Calcinado |
| expansao N->G | 0,25 | se o basal expande apos glicolacao |
| colapso G->C | 0,20 | se o basal colapsa apos calcinacao |
| estabilidade | 0,20 | estabilidade em ~10 A, ~14 A ou ~7 A |
| melhor sinal diagnostico | 0,15 | reforco do melhor componente observado |

Formula:

```text
score =
0.20 * completude_tratamentos
+ 0.25 * expansao_n_g
+ 0.20 * colapso_g_c
+ 0.20 * estabilidade
+ 0.15 * melhor_sinal_diagnostico
```

Confianca:

| Confianca | Regra |
|---|---|
| alta | score >= 0,75 e sem tratamento ausente |
| media | score >= 0,45 |
| baixa | score abaixo de 0,45 |

Mesmo com score alto, a interpretacao continua preliminar e precisa de curadoria.

## 8. Comparacao por reflexoes confirmatorias

Esta tabela cruza os picos observados com reflexoes diagnosticas esperadas para alguns argilominerais.

Minerais avaliados explicitamente:

- Esmectita/montmorilonita;
- Ilita/mica;
- Clorita;
- Caulinita;
- Quartzo como fase nao argilosa de controle;
- Vermiculita.

Status possiveis:

| Status | Significado |
|---|---|
| `compativel` | ha multiplas reflexoes ou trajetoria diagnostica coerente |
| `parcial` | ha apenas parte da evidencia |
| `nao conclusivo` | nao ha evidencia suficiente |

Confiancas possiveis:

- `baixa`;
- `baixa/media`;
- `media`;
- `media/alta`.

### Regras diagnosticas usadas

| Mineral | Reflexoes/janelas esperadas |
|---|---|
| Esmectita/montmorilonita | Natural 13,00-16,50 A; EG/Glicolado 16,60-18,60 A; Calcinado 9,40-10,40 A |
| Ilita/mica | 001 em 9,70-10,40 A; estabilidade entre tratamentos reforca a hipotese |
| Clorita | 001 basal em 13,70-14,60 A; leitura reforcada por permanencia apos aquecimento e ausencia de expansao como esmectita em EG |
| Caulinita | 001 em 6,90-7,80 A; deve ser diferenciada da clorita 002 por tratamento e picos de suporte |
| Quartzo | 101 em 3,24-3,44 A; 100 em 4,23-4,35 A; nao e argilomineral, mas pode dominar picos e mascarar fases argilosas |
| Vermiculita | pico proximo de 14 A com permanencia em EG e possivel colapso aquecido; continua como hipotese conservadora quando faltam criterios completos |

### Como o status e definido

Regra geral:

- 2 ou mais reflexoes observadas: `compativel`, confianca `media`;
- 1 reflexao observada: `parcial`, confianca `baixa/media`;
- nenhuma reflexao observada: `nao conclusivo`, confianca `baixa`.

Excecoes importantes:

- Esmectita/montmorilonita com expansao em EG e colapso aquecido: `compativel`, confianca `media/alta`;
- Esmectita/montmorilonita com apenas expansao em EG: `parcial`, confianca `media`;
- Vermiculita com 14 A estavel no natural e glicolado mais colapso aquecido: `compativel`, confianca `media`;
- Vermiculita com 14 A estavel mas sem evidencia termica: `parcial`, confianca `baixa/media`.

## 9. Completude diagnostica

O painel tambem pode avaliar se o conjunto selecionado e adequado para interpretacao assistida.

Status possiveis:

| Status | Regra |
|---|---|
| `completa` | tem Natural, Glicolado e Calcinado, pelo menos 6 picos e sem flags ruins |
| `parcial` | tem pelo menos 2 tratamentos e pelo menos 3 picos |
| `fraca` | tem menos de 3 picos |
| `revisar` | caso intermediario ou com alerta de qualidade |

Recomendacoes:

| Status | Recomendacao |
|---|---|
| completa | conjunto adequado para interpretacao assistida, mantendo revisao manual |
| parcial | completar tratamentos ausentes e revisar picos basais |
| fraca/revisar | reprocessar/validar RAW e revisar qualidade do difratograma |

## 10. Similaridade entre RAWs

Quando a interface compara um RAW externo com RAWs ja existentes em pacote analitico, ela usa outro score, de similaridade de curva.

Status possiveis:

| Status | Significado |
|---|---|
| `igual` | o RAW parece ja existir no pacote, geralmente por coincidencia exata de nome/codigo |
| `muito_parecido` | score de similaridade alto |
| `parecido` | encontrou semelhanca parcial |
| `sem_semelhante_forte` | nao achou RAW suficientemente semelhante |

Componentes do score de similaridade:

- metadados;
- forma completa da curva;
- picos detectados;
- candidatos mineralogicos.

Quando existe curva comparavel, a composicao e:

```text
score = 0.18 * metadados
+ 0.32 * curva
+ 0.35 * picos
+ 0.15 * candidatos
```

Quando nao ha curva completa comparavel, o sistema usa:

```text
score = 0.25 * metadados
+ 0.55 * picos
+ 0.20 * candidatos
```

## 11. Como interpretar o painel com criterio DRX

Leitura recomendada:

1. Verificar se ha trio N/G/C completo.
2. Observar se ha expansao apos glicolacao.
3. Observar se ha colapso apos calcinacao.
4. Checar estabilidade em ~10 A, ~14 A e ~7 A.
5. Conferir se as reflexoes confirmatorias aparecem em mais de uma linha.
6. Tratar picos isolados como hipotese fraca.
7. Dar atencao especial a sobreposicoes: caulinita/clorita, quartzo/feldspatos, 14 A ambiguo.
8. Usar o score como triagem, nao como laudo.

## 12. Resumo curto

| Bloco do painel | Pergunta que ele responde |
|---|---|
| Classificacao de preparo | Este arquivo e N, G, C ou indeterminado? |
| Classificador mineralogico | Quais minerais da biblioteca parecem com os picos observados? |
| Painel mineralogico | Quais candidatos se repetem e quais picos sustentam? |
| Comparacao N/G/C | A trajetoria entre tratamentos e mineralogicamente coerente? |
| Reflexoes confirmatorias | Os picos diagnosticos esperados aparecem? |
| Completude diagnostica | O conjunto e adequado para interpretacao assistida? |
| Similaridade RAW | Este RAW se parece com outro ja indexado? |
| Evidencia neural XRDNet contextual | Existe predicao auxiliar para um RAW semelhante carregado? |
| Fila do geologo | Quais curvas/hipoteses derivadas devem ser revisadas primeiro? |

Interpretacao final: o painel organiza evidencias para revisao. A decisao mineralogica deve considerar preparo, qualidade do difratograma, picos ausentes, sobreposicoes e coerencia entre tratamentos.

## 13. O que o painel local `visualizacao-drx` mostra hoje

O painel Streamlit em `povoamento/visualizacao-drx/codigo-drx/src/dashboard/app.py` esta voltado para operacao de lote. Ele possui as paginas:

- `Visao geral`: contagem de RAW classificados, curvas Diffract geradas, pendencias e erros controlados;
- `Explorador de amostras`: filtros por origem, amostra, arquivo e mineral, com resumo por origem e tabela de curvas;
- `Visualizador de difratogramas`: uma curva por vez, com picos detectados e candidatos por referencia DRX;
- `Resultados avancados`: qualidade, cobertura de faixa 2theta, curvas sem candidato e metricas tecnicas;
- `Painel mineralogico`: agregacao simples por mineral principal, ocorrencias, score medio, melhor score e distribuicao de confianca;
- `Diffract argilominerais`: triagem WebMineral/CMS, candidatos, linhas casadas, linhas ausentes, qualidade e avisos;
- `Revisao`: baixa confianca, curvas sem candidato, faixa parcial e erros.

Ele nao substitui a tela integrada `/drx/comparacao` para:

- sobrepor varias curvas selecionadas na mesma tela de comparacao integrada;
- montar o mesmo relatorio visual completo usado no PDF da Argiloteca;
- mostrar, em uma unica pagina, painel mineralogico + N/G/C + reflexoes confirmatorias + completude diagnostica + similaridade RAW;
- gravar ou publicar registros no InvenioRDM.

O projeto `visualizacao-drx`, porem, contem o nucleo cientifico que alimenta parte desses blocos:

- `src/drx/comparison_ngc.py` infere Natural/Glicolado/Calcinado por nome de arquivo;
- `src/argiloteca/drx/comparison/basal_tracking.py` rastreia trajetoria basal 001;
- `src/argiloteca/drx/minerals/diagnostic_rules.py` aplica regras conservadoras de evidencia por d-spacing;
- `src/argiloteca/drx/minerals/characterization.py` agrega picos de suporte, ausencias, reflexoes fora da faixa, conflitos, limitacoes e recomendacoes;
- `povoamento/drx/processar_curva_drx_avancado.py` gera JSONs com picos, ajuste, QC, basal tracking, evidencias e caracterizacao.

Portanto, se a avaliacao estiver olhando apenas para o painel Streamlit local, a resposta e: ele esta coerente com a politica cientifica do documento, mas nao esta funcionalmente completo em relacao ao painel integrado descrito aqui. A documentacao correta deve trata-lo como bancada auxiliar, nao como a propria tela `/drx/comparacao`.

## 14. Camadas auxiliares recentes

### Evidencia neural XRDNet contextual

O painel integrado pode carregar um resumo XRDNet a partir de `static/data/xrdnet_argilominerais_v1/panel_summary.json`. Essa evidencia aparece apenas quando o item selecionado foi carregado como RAW semelhante ou quando a similaridade com pacote analitico encontrou um RAW comparavel.

A leitura correta e:

- XRDNet e auxiliar;
- aparece como contexto, nao como decisao mineralogica;
- deve ser comparado com picos, preparo N/G/C e interpretacao mineralogica;
- ausencia de JSON neural correspondente nao invalida a comparacao DRX.

### Fila do geologo

Quando disponiveis, os arquivos derivados em `static/data/drx_geologist_review_20260616/` adicionam uma fila de revisao e sugestoes de similaridade. Essa camada serve para priorizar curadoria, especialmente em baixa confianca, curvas sem candidato, similaridades relevantes ou hipoteses que exigem revisao humana.

Ela tambem nao confirma mineral automaticamente.

## 15. Rotinas operacionais de reclassificacao e publicacao

As rotinas atuais ficam em `povoamento/drx/` e foram separadas em duas etapas para reduzir risco operacional:

| Script | Papel | O que altera |
|---|---|---|
| `povoamento/drx/reclassificar_minerais_raw.sh` | apaga classificacoes derivadas antigas e reclassifica os RAWs com os padroes atuais | recria `classificacao_mineralogica_raw.json`, `classificacao_mineralogica_resumo.json` e `classificacao_mineralogica_raw.csv` |
| `povoamento/drx/publicar_resultado_painel_argiloteca.sh` | valida o snapshot novo, gera manifesto/metricas e reinicia o HTTPS local para o painel ler a versao nova | cria/atualiza `publicacao_painel_drx.json` e `reports/drx_panel_metrics.json`; nao altera RAWs |

O script de reclassificacao nao mexe nos arquivos `.raw`. Ele remove apenas os arquivos derivados de classificacao mineralogica:

```text
povoamento/visualizacao-drx/saida_argiloteca_drx/classificacao_mineralogica_raw.json
povoamento/visualizacao-drx/saida_argiloteca_drx/classificacao_mineralogica_resumo.json
povoamento/visualizacao-drx/saida_argiloteca_drx/classificacao_mineralogica_raw.csv
```

Fluxo recomendado:

```bash
cd /Users/argilas/argilas

povoamento/drx/reclassificar_minerais_raw.sh
povoamento/drx/publicar_resultado_painel_argiloteca.sh
```

Durante a reclassificacao, o script imprime:

- quantos RAWs encontrou;
- qual pasta RAW esta usando;
- qual vocabulario WebMineral local esta usando;
- quantos candidatos por amostra serao calculados;
- as faixas diagnosticas ativas lidas diretamente do codigo da Argiloteca.

Durante a publicacao, o script:

1. valida se `classificacao_mineralogica_raw.json`, resumo, CSV e vocabulario existem;
2. confere se o vocabulario contem as faixas diagnosticas atuais;
3. grava `povoamento/visualizacao-drx/saida_argiloteca_drx/publicacao_painel_drx.json`;
4. atualiza `reports/drx_panel_metrics.json`;
5. reinicia `https://127.0.0.1:5443` para limpar cache em memoria do painel;
6. consulta `/api/argiloteca/drx/raw-snapshot?limit=1` para confirmar que a API voltou a responder.

Para validar/publicar sem reiniciar o servidor local:

```bash
cd /Users/argilas/argilas
povoamento/drx/publicar_resultado_painel_argiloteca.sh --no-restart
```

Depois de publicar, abrir:

```text
https://127.0.0.1:5443/drx/comparacao
```

Se o servidor ja estava aberto antes da reclassificacao, o restart e importante porque algumas leituras JSON do servico DRX usam cache em memoria. Sem reiniciar, a pagina pode continuar mostrando dados antigos ate o processo local ser reiniciado.
