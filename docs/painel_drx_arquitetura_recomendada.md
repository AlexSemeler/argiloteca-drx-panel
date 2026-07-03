# Painel DRX - Arquitetura Recomendada

## Objetivo

Este documento define a arquitetura recomendada para evoluir o Painel de
Comparacao DRX/XRD da Argiloteca sem reescrita total e sem alterar regras
cientificas em refatoracoes estruturais. A diretriz central e manter calculo
cientifico critico no backend Python e deixar o frontend responsavel por
visualizacao, interacao e explicacao.

## Fluxo Ideal

```text
Entrada
-> validacao de arquivo/metadados
-> parsing padronizado
-> modelo Diffractogram
-> preprocessamento opcional e auditavel
-> deteccao de picos
-> normalizacao de picos
-> agrupamento N/G/C
-> comparacao entre tratamentos
-> regras mineralogicas explicaveis
-> resultado interpretativo versionado
-> visualizacao
-> exportacao/persistencia InvenioRDM
```

## Principios Arquiteturais

- O backend Python deve executar parsing, geometria, peak-picking, comparacao
  N/G/C e regras mineralogicas.
- O frontend deve renderizar curvas, tooltips, tabelas, badges e explicacoes
  recebidas do backend.
- Toda hipotese mineralogica deve carregar fonte, regra, pagina, tabela/figura
  quando disponivel, limitacoes e status nao confirmatorio.
- Dados brutos, processados e exibidos devem ser distinguidos por metadados.
- Nenhum modulo deve assumir Cu K-alpha ou qualquer comprimento de onda de modo
  silencioso.
- Refatoracao estrutural e mudanca cientifica devem ocorrer em commits
  separados.

## Camadas Recomendadas

| Camada | Responsabilidade | Modulos atuais | Modulos futuros |
| --- | --- | --- | --- |
| Entrada/parsing | Ler RAW/CSV/XY/TXT/DAT, validar extensao, limite e checksum | `services/drx.py`, `argiloteca_drx_core/curves.py` | `argiloteca_drx_core/parsers.py` |
| Modelo de dados | Representar amostra, arquivo, preparo, curva, pico, evidencia e hipotese | `argiloteca_drx_core/diffractogram.py`, contratos dispersos | `argiloteca_drx_core/models.py` |
| Pre-processamento | Baseline, suavizacao, normalizacao, decimacao e QC | `services/drx_analysis.py`, `argiloteca_drx_core/processing.py` | Pipeline versionado em `argiloteca_drx_core/pipeline.py` |
| Geometria | Bragg, 2theta, d-spacing, lambda, eixo, d060 e incertezas | `argiloteca_drx/geometry`, `argiloteca_drx_core/geometry.py` | Adaptador unico de geometria para API |
| Picos | Deteccao, FWHM, area, SNR, origem do pico | `argiloteca_drx_core/peak_detector.py`, `argiloteca_drx_core/peaks.py` | Contrato unico `Peak` em todo payload |
| Comparacao N/G/C | Agrupar por amostra e comparar trajetorias N, G e C | `services/drx_ngc_workflow.py`, `argiloteca_drx_core/ngc.py` | Backend como unica fonte de agrupamento cientifico |
| Regras mineralogicas | Cap. 7/8, ambiguidades, interestratificados, d060 auxiliar | `argiloteca_drx/diagnostics` | Catalogo de regras versionado e validado |
| API/backend | Expor endpoints finos e estaveis | `views.py` | Blueprint DRX dedicado |
| Visualizacao | Plotly/SVG, tooltips, tabelas, filtros e exportacao visual | `drx-comparacao.js` | JS modular: data, chart, panels, exports |
| Persistencia | Runs, relatorios, metadados InvenioRDM e artefatos JSON | `drx_runs.py`, `drx_selection_report.py` | Serializadores InvenioRDM versionados |
| Testes | Unitarios, contratos, integracao e regressao | `tests/test_drx*.py` | Fixtures sinteticas e smoke tests de frontend |

## Contratos De Dados Minimos

Os contratos devem representar:

- `Sample`: amostra cientifica e vinculo com registro.
- `XrdFile`: arquivo de origem, formato, checksum e proveniencia.
- `Treatment`: preparo N/G/C e forma de inferencia.
- `Diffractogram`: curva, eixo, intensidade, metadados e contagens.
- `Peak`: pico observado ou calculado, sem assumir d-spacing.
- `Evidence`: evidencia rastreavel usada por uma hipotese.
- `MineralHypothesis`: hipotese mineralogica nao confirmatoria.
- `NgcComparison`: comparacao estrutural entre tratamentos.

Esses contratos devem ser serializaveis, preservar `None`, permitir lacunas no
difratograma e nao executar regras cientificas durante a serializacao.

## Estrategia Incremental De Commits

1. `docs: mapeia fluxo atual do painel DRX`
2. `model: adiciona contratos internos do pipeline DRX`
3. `test: cobre contratos de difratograma pico e NGC`
4. `refactor: extrai helpers puros do frontend sem mudar comportamento`
5. `refactor: centraliza agrupamento NGC remanescente no backend`
6. `test: cobre workflow NGC para uploads externos`
7. `ui: reduz duplicacao da interpretacao mineralogica assistida`
8. `docs: documenta regras Cap 3 7 8 e provenance`

## Estrategia De Testes

### Unitarios

- Parser: RAW legado, RAW101, CSV, XY, separadores, arquivo vazio e extensao
  invalida.
- Geometria: `2theta -> theta -> d`, ausencia de lambda, lambda invalido e
  resultado nao finito.
- Modelos: serializacao, `from_dict`, lacunas, eixos desalinhados e ausencia de
  dependencias externas.
- Picos: gaussianas sinteticas, SNR, FWHM, NaN, intensidade negativa e series
  grandes.

### Integracao

- `/api/argiloteca/drx/difratogramas/<id>`
- `/api/argiloteca/drx/externo/curva`
- `/api/argiloteca/drx/workflows/ngc`
- `/api/argiloteca/drx/runs`

### Regressao Cientifica

- Manter `test_drx_v3_engine.py` como suite minima para Cap. 7/8, d060,
  ambiguidades e interestratificados.
- Nao atualizar expectativas de score ou politica sem justificar mudanca
  cientifica em commit separado.

### Frontend

- Validar sintaxe com `node --check`.
- Adicionar smoke tests quando houver harness adequado.
- Cobrir tooltip, `connectgaps: false`, marcadores por 2theta e estados sem
  lambda.

## Recomendacoes Para InvenioRDM

- Persistir runs DRX como artefatos versionados com hash de entrada,
  parametros, versao do pipeline e fontes de regras.
- Separar metadados do arquivo bruto, curva processada e interpretacao
  mineralogica.
- Registrar `validation_status` para resultados exploratorios, insuficientes ou
  dependentes de revisao.
- Preservar referencias bibliograficas e paginas em `source_rules`.
- Evitar persistir arquivos temporarios de `instance/` no Git.

## Evolucao Do Frontend

O frontend deve caminhar para quatro responsabilidades claras:

1. carregar e selecionar itens;
2. renderizar curvas e interacoes;
3. mostrar explicacoes recebidas do backend;
4. exportar o que foi exibido com metadados visiveis.

Logica cientifica remanescente em `drx-comparacao.js` deve ser removida apenas
quando houver contrato backend equivalente, testes de regressao e comparacao de
payloads antes/depois.

## Criterios De Aceite Da Arquitetura

- Modelos internos serializaveis existem e nao dependem de bibliotecas pesadas.
- O backend continua sendo a fonte de verdade para N/G/C.
- Nenhum comportamento visual ou cientifico muda durante a introducao dos
  contratos.
- Documentacao descreve o fluxo atual e o fluxo desejado.
- Testes de contrato passam e podem ser usados como base para refatoracoes
  futuras.
