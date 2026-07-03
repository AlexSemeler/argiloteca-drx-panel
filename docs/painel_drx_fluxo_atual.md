# Painel DRX - Fluxo Atual

## Resumo Executivo

O painel de comparacao DRX/XRD da Argiloteca funciona hoje como uma aplicacao
de comparacao com ampla cobertura funcional. Ele carrega difratogramas internos,
itens do snapshot geral de RAWs processados e arquivos externos temporarios nos
formatos `.raw`, `.csv`, `.txt`, `.xy` e `.dat`. O fluxo tambem infere preparo
N/G/C, le curvas `2theta x intensidade`, aplica processamento ALS e
peak-picking, monta workflow N/G/C no backend, exibe interpretacao mineralogica
assistida e exporta relatorios.

O ponto mais forte da implementacao atual e a existencia de bases cientificas
modulares em Python:

- `argiloteca_drx`
- `argiloteca_drx_core`
- `argiloteca/services/drx_ngc_workflow.py`

O ponto mais fragil e a concentracao de responsabilidades no frontend
`argiloteca/static/js/drx-comparacao.js`. Esse arquivo ainda mistura
renderizacao, agrupamento N/G/C, logica auxiliar de picos, calculos de
visualizacao, montagem de evidencias, interpretacao textual e exportacao.

Nenhuma identificacao mineralogica exibida pelo painel deve ser tratada como
certeza absoluta. Os resultados sao hipoteses assistidas, dependentes dos
tratamentos disponiveis, da qualidade da curva, do peak-picking, da
rastreabilidade das regras e da validacao especializada.

## Fluxo Atual Obrigatorio

```text
Usuario
-> /drx/comparacao
-> template drx_comparacao.html
-> drx-comparacao.js
-> API registros / snapshot / upload externo
-> parser DRX
-> curva 2theta/intensidade
-> processamento ALS + picos
-> pre-classificacao N/G/C
-> build_ngc_workflow()
-> interpretacao Cap. 3/7/8
-> grafico Plotly/SVG + painel de evidencias
-> exportacao JSON/CSV/SVG/PDF / runs
```

## Mapa Por Etapa

| Etapa | Entrada | Processamento | Saida | Arquivos e funcoes |
| --- | --- | --- | --- | --- |
| Pagina | Navegador em `/drx/comparacao` | Renderiza o shell e injeta URLs das APIs em `data-*` | HTML do painel | `views.py::drx_comparacao`, `templates/semantic-ui/argiloteca/drx_comparacao.html` |
| Selecao interna | Filtros, `record_id`, snapshot | Lista registros, pacotes analiticos e RAWs processados | Itens DRX selecionaveis | `views.py::api_drx_registros`, `views.py::api_drx_raw_snapshot`, `services/drx.py::list_records_with_drx`, `services/drx.py::list_raw_snapshot_items` |
| Sugestoes | Snapshot RAW filtrado | Agrupa por amostra, preparo e candidatos | Sugestoes de comparacao | `views.py::api_drx_raw_snapshot_sugestoes`, `services/drx.py::build_raw_snapshot_comparison_suggestions` |
| Upload externo | Arquivo `.raw/.csv/.txt/.xy/.dat` | Valida tamanho/extensao, calcula SHA-256, persiste temporario, parseia curva, infere preparo | Curva temporaria e metadados | `views.py::api_drx_externo_curva`, `parse_diffractogram_bytes`, `_persist_drx_temp_upload` |
| Curva por id | `diffractogram_id` | Carrega RAW do snapshot ou sidecar importado, aplica alinhamento classificado quando configurado, decima | `two_theta`, `intensity`, `metadata` | `views.py::api_drx_difratograma`, `services/drx.py::load_diffractogram_data`, `services/drx.py::decimate_series` |
| Processamento | Curva e metadados | ALS, baseline, suavizacao, picos, FWHM, evidencias basais | `advanced_processing`, `advanced_curve`, `advanced_summary` | `services/drx_analysis.py::build_drx_analysis_run`, `argiloteca_drx_core/peak_detector.py`, `argiloteca_drx_core/processing.py` |
| Pre-classificacao externa | Arquivo externo processado | Monta item temporario com picos, preparo, SHA-256 e d060 auxiliar quando possivel | `external_raw_preclassification` | `views.py::_external_curve_preclassification_item`, `views.py::_infer_external_curve_d060` |
| N/G/C backend | Itens selecionados ou ids | Agrupa por `sample_base`, normaliza preparo, agrega picos, chama engine diagnostica | Grupos N/G/C e candidatos | `views.py::api_drx_ngc_workflow`, `services/drx_ngc_workflow.py::build_ngc_workflow` |
| Regras cientificas | Picos por preparo, d060, metadados | Aplica conhecimento Cap. 3, Cap. 7 e Cap. 8, ambiguidades e interestratificados | Hipoteses explicaveis | `argiloteca_drx/diagnostics/*`, `argiloteca_drx/geometry/*`, `rules_catalog.yaml` |
| Visualizacao | Payloads de curva e workflow | Renderiza Plotly/SVG, tooltips, picos, ranking, evidencias e exportacoes | Interface interativa | `static/js/drx-comparacao.js` |
| Persistencia | Run, relatorio, selecao | Grava artefato JSON versionado | Historico de analise | `views.py::api_drx_runs`, `services/drx_runs.py`, `services/drx_selection_report.py` |

## Pontos Fortes

- Ha separacao crescente da base cientifica em Python.
- O workflow N/G/C principal ja existe no backend.
- O painel distingue curvas externas temporarias de registros persistidos.
- O endpoint de difratograma informa contagens de pontos e estado de
  decimacao.
- O fluxo atual ja evita assumir d-spacing em algumas etapas quando nao ha
  comprimento de onda explicito.
- A base Cap. 3/7/8 melhora rastreabilidade de regras, tabelas e figuras.

## Problemas Tecnicos

- `views.py` ainda concentra muitas rotas de dominios diferentes: DRX,
  geoquimica, relatorios, jobs externos, pacotes analiticos e snapshots.
- `drx-comparacao.js` mistura estado, renderizacao, regras auxiliares,
  agrupamento N/G/C, fallback de picos, texto interpretativo e exportacao.
- Parte da logica N/G/C existe tanto no backend quanto no frontend.
- O upload externo executa muitas operacoes dentro do request HTTP:
  parsing, ALS, picos, similaridade, pre-classificacao e registro de job
  externo.
- Algumas verificacoes de frontend ainda sao cobertas por testes estaticos que
  procuram strings, nao por testes de comportamento real.

## Pontos De Acoplamento

- O frontend depende de muitos campos opcionais do payload sem contrato unico.
- O mesmo conceito pode aparecer como `peaks`, `advanced_peaks`,
  `detected_peaks`, `fit_results` ou `targeted_basal_peaks`.
- O preparo aparece como `treatment`, `preparation`, label textual ou inferido
  pelo nome do arquivo.
- A visualizacao ainda precisa conhecer detalhes de regras N/G/C para montar
  evidencias e mensagens.
- O eixo exibido pode ser bruto, alinhado ou classificado; esse estado depende
  de metadados que precisam permanecer explicitos.

## Riscos Cientificos

- Pico isolado pode sugerir mineral errado quando ha sobreposicao entre
  caulinita, clorita, serpentina, ilita, quartzo e interestratificados.
- d060 inferido de RAW externo e apenas evidencia auxiliar; depende de faixa
  angular, montagem, interferencias e qualidade do pico.
- Intensidade relativa depende de preparo, orientacao preferencial, background,
  largura instrumental e sobreposicao.
- Falta de tratamento G ou C reduz a confiabilidade para argilas expansivas ou
  colapsaveis.
- Comportamento parcial pode indicar interestratificacao, defeitos, mistura
  fisica ou problemas instrumentais; nao deve ser resolvido automaticamente.

## Diretriz De Continuidade

A evolucao deve manter compatibilidade com o painel atual. A prioridade e
formalizar contratos de dados, mover gradualmente calculos cientificos para
Python testavel, reduzir duplicacao visual e preservar rastreabilidade das
decisoes cientificas.
