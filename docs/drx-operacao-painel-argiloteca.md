# Operacao do Painel DRX da Argiloteca

Este guia descreve o fluxo operacional local para classificar arquivos RAW de
DRX, atualizar o painel da Argiloteca, consultar evidencias auxiliares e acionar
os adapters GSAS-II/DARA. Os caminhos abaixo correspondem a esta maquina Linux.

## Principios

- O painel DRX gera hipoteses assistidas, nao confirmacao mineralogica.
- Arquivos RAW originais devem permanecer fora do Git.
- DiffractGPT, XRDNet, evidencia neural, CIF/COD/RRUFF, GSAS-II e DARA sao
  camadas auxiliares ate revisao curatorial.
- GSAS-II/DARA rodam via worker offline, nunca dentro da request Flask.
- Artefatos derivados devem manter parametros, hashes e versoes.

## Caminhos Principais

Projeto:

```bash
/home/invenio/invenio-project
```

Argiloteca local:

```bash
/home/invenio/invenio-project/argiloteca-local
```

RAWs classificados:

```bash
/home/invenio/invenio-project/argiloteca-local/data/drx/raw-classificados
```

Saidas DRX usadas pelo painel:

```bash
/home/invenio/invenio-project/argiloteca-local/data/drx/saida_argiloteca_drx
```

DiffractGPT/Diffract:

```bash
/home/invenio/difract
```

Painel:

```text
http://127.0.0.1:5000/drx/comparacao
```

## Iniciar a Argiloteca

Use o script local:

```bash
cd /home/invenio/invenio-project
./iniciar_argiloteca.sh
```

Em outra janela, valide:

```bash
curl -fsS -o /tmp/argiloteca_health.html -w '%{http_code}\n' http://127.0.0.1:5000/
curl -fsS 'http://127.0.0.1:5000/api/argiloteca/drx/raw-snapshot?limit=1'
```

## Classificar RAWs e Atualizar o Painel

O script principal e:

```bash
/home/invenio/invenio-project/rodar_drx_diffractgpt_publicar_argiloteca.sh
```

Ele pode executar:

- reclassificacao dos RAWs;
- diagnostico N/G/C de grupos quando houver tratamentos Natural/Glicolado/
  Calcinado;
- metricas do painel;
- DiffractGPT/JARVIS experimental;
- dataset e adaptador Diffract N/G/C auxiliar, quando configurado;
- reconstrucao do indice neural auxiliar;
- restart da Argiloteca;
- validacao das APIs.

### Rodar fluxo completo

Use quando quiser reprocessar tudo:

```bash
cd /home/invenio/invenio-project
ALLOW_HF_NETWORK=1 \
ALLOW_JARVIS_DOWNLOAD=1 \
./rodar_drx_diffractgpt_publicar_argiloteca.sh
```

Saidas principais:

```text
argiloteca-local/data/drx/saida_argiloteca_drx/classificacao_mineralogica_raw.json
argiloteca-local/data/drx/saida_argiloteca_drx/classificacao_mineralogica_raw.csv
argiloteca-local/data/drx/saida_argiloteca_drx/classificacao_mineralogica_resumo.json
argiloteca-local/data/drx/saida_argiloteca_drx/classificacao_mineralogica_ngc_groups.json
argiloteca-local/data/drx/saida_argiloteca_drx/classificacao_mineralogica_ngc_groups.csv
argiloteca-local/reports/drx_panel_metrics.json
argiloteca-local/instance/argiloteca_drx_neural/neural_evidence_index.json
/home/invenio/difract/datasets/argiloteca_ngc_training/ngc_training_samples.jsonl
/home/invenio/difract/datasets/argiloteca_ngc_training/ngc_training_labels.csv
/home/invenio/difract/outputs/diffractgpt_real_argilominerais_<data>
```

Quando existir trio N/G/C completo, o painel deve usar
`classificacao_mineralogica_ngc_groups.json` como leitura principal. O arquivo
`classificacao_mineralogica_raw.json` continua util, mas seus candidatos por
RAW isolado sao evidencias secundarias.

### Rodar apenas reclassificacao RAW

Use quando voce mudou ou adicionou RAWs:

```bash
cd /home/invenio/invenio-project
RUN_RECLASSIFICATION=1 \
RUN_DIFRACTGPT=0 \
BUILD_NEURAL_INDEX=0 \
RESTART_ARGILOTECA=1 \
CHECK_API=1 \
./rodar_drx_diffractgpt_publicar_argiloteca.sh
```

### Rodar reclassificacao com Diffract N/G/C auxiliar

Use quando quiser atualizar a classificacao, o indice N/G/C de grupos, o dataset
Diffract e o adaptador multi-label auxiliar sem baixar dados externos:

```bash
cd /home/invenio/invenio-project
RUN_RECLASSIFICATION=1 \
RUN_DIFRACTGPT=0 \
BUILD_NEURAL_INDEX=1 \
RUN_NGC_RECLASSIFICATION=1 \
RUN_DIFRACT_NGC_ADAPTER=1 \
VALIDATE_NGC_INTERPRETATION=1 \
RESTART_ARGILOTECA=1 \
CHECK_API=1 \
STRICT=0 \
./rodar_drx_diffractgpt_publicar_argiloteca.sh
```

O adaptador Diffract N/G/C usa os grupos gerados pelo painel como labels
auxiliares. Ele nao deve substituir revisao mineralogica e nao transforma
DiffractGPT em fonte confirmatoria.

### Recriar apenas indice neural auxiliar

Use quando os dados pre-computados em `/home/invenio/difract` mudaram:

```bash
cd /home/invenio/invenio-project
RUN_RECLASSIFICATION=0 \
RUN_DIFRACTGPT=0 \
BUILD_NEURAL_INDEX=1 \
RESTART_ARGILOTECA=1 \
CHECK_API=1 \
./rodar_drx_diffractgpt_publicar_argiloteca.sh
```

O indice neural e compacto e evita varrer milhares de diretorios durante cada
request do painel.

## Regras N/G/C Usadas pelo Painel

As regras versionadas ficam em:

```text
argiloteca-local/app/argiloteca_custom/argiloteca/data/diagnostic_rules_ngc.json
```

O workflow backend que aplica as regras fica em:

```text
argiloteca-local/app/argiloteca_custom/argiloteca/services/drx_ngc_workflow.py
```

Faixas operacionais principais:

| Alvo | Faixa |
| --- | --- |
| Quartzo 101 | 3.24-3.44 A, alvo 3.34 A |
| Quartzo 100 | 4.23-4.35 A |
| Ilita/mica | 9.7-10.4 A, com companheiros ~5 A e ~3.33 A |
| Caulinita | 6.9-7.8 A no scan; regra seletiva 6.90-7.30 A |
| Esmectita N | 13.0-16.5 A no script; regra ampla 12.0-16.5 A |
| Esmectita G | 16.6-18.6 A |
| Esmectita C | 9.4-10.4 A no script; regra seletiva 9.8-10.4 A |
| Clorita | 13.7-15.3 A, com companheiros ~7, ~4.72 e ~3.53 A |

O painel tambem executa `targeted_basal_peak_scan`, que procura picos basais
fracos dentro dessas janelas mesmo quando eles nao aparecem entre os maiores
picos globais. A classificacao N/G/C sempre deve ser lida como evidencia
auxiliar.

As regras tambem carregam referencias RRUFF/ODR locais como picos auxiliares em
`rruff_odr_reference`. Esses picos ajudam a conferir companheiros e
sobreposicoes:

- caulinita/dickita: ~7.131 A e ~3.570 A;
- clorita: ~14.193, ~7.060, ~4.719 e ~3.530 A;
- esmectita natural: ~14.590, ~13.743 e ~13.091 A;
- ilita/micas: ~9.985, ~4.968 e ~3.335 A.

RRUFF/ODR nao substitui a regra N/G/C. Ele deve aparecer como referencia
auxiliar, nao como confirmacao mineralogica.

## Diagnostico N/G/C em Lote com ALS e Calibracao por Quartzo

Existe tambem um script de bancada para processar grupos Natural/Glicolado/
Calcinado diretamente a partir de RAW/TXT/XY/DAT/CSV. Ele aplica filtro
Savitzky-Golay, subtracao de background ALS, auto-calibracao opcional pelo pico
do quartzo, deteccao de picos, calculo de d-spacing/FWHM/area/Scherrer e regras
diagnosticas N/G/C para ilita, esmectita, caulinita, clorita e quartzo.

Script:

```bash
/home/invenio/invenio-project/argiloteca-local/app/argiloteca_custom/scripts/batch_ngc_raw_diagnostics.py
```

Rodar em uma pasta pequena de entrada:

```bash
cd /home/invenio/invenio-project
/home/invenio/invenio-project/argiloteca-local/venvs/drx-science-py310/bin/python \
  /home/invenio/invenio-project/argiloteca-local/app/argiloteca_custom/scripts/batch_ngc_raw_diagnostics.py \
  --input-dir /caminho/para/input_files \
  --output-dir /caminho/para/output_files
```

Rodar nas pastas RAW classificadas, limitando para teste:

```bash
/home/invenio/invenio-project/argiloteca-local/venvs/drx-science-py310/bin/python \
  /home/invenio/invenio-project/argiloteca-local/app/argiloteca_custom/scripts/batch_ngc_raw_diagnostics.py \
  --input-dir /home/invenio/invenio-project/argiloteca-local/data/drx/raw-classificados \
  --output-dir /home/invenio/invenio-project/argiloteca-local/instance/argiloteca_drx_batch_ngc \
  --limit 10
```

Saidas:

```text
batch_ngc_raw_diagnostics.json
batch_ngc_peaks.csv
<Mineral>/Grafico_Espectro_<amostra>.png
```

Por seguranca, o script nao copia RAWs por padrao. Para rotear/copiar os RAWs
para subpastas por mineral detectado, use explicitamente:

```bash
--copy-raw
```

Esse diagnostico e auxiliar e nao deve ser publicado como confirmacao
mineralogica sem revisao.

### Rodar DiffractGPT experimental

Use somente como evidencia experimental. O gate de revisao decide se algo pode
ser integrado ao painel:

```bash
cd /home/invenio/invenio-project
RUN_RECLASSIFICATION=0 \
RUN_DIFRACTGPT=1 \
ALLOW_HF_NETWORK=1 \
ALLOW_JARVIS_DOWNLOAD=1 \
BUILD_NEURAL_INDEX=1 \
RESTART_ARGILOTECA=1 \
CHECK_API=1 \
./rodar_drx_diffractgpt_publicar_argiloteca.sh
```

Verifique o gate:

```bash
cat /home/invenio/difract/outputs/diffractgpt_real_argilominerais_$(date +%Y%m%d)/09_panel_integration_review_gate.json
```

Se `integration_allowed` for `false`, nada estrutural deve ser publicado como
identificacao confirmatoria.

## Usar o Painel DRX

Abra:

```text
http://127.0.0.1:5000/drx/comparacao
```

Fluxos uteis:

```text
/drx/comparacao
/drx/comparacao?argilomineral=kaolinite
/drx/comparacao?record_id=<record_id>&source=package
/analises/
/analises/<record_id>
```

No painel:

- selecione uma amostra/curva carregada do snapshot;
- use o grafico Plotly para inspecionar 2theta versus intensidade;
- compare tratamentos N/G/C quando existirem;
- leia primeiro a secao de interpretacao N/G/C quando houver trio completo;
- consulte candidatos minerais por RAW isolado apenas como evidencia secundaria;
- use "Picos basais direcionados" para conferir faixas fracas de clorita,
  caulinita, ilita e esmectita;
- leia a secao "Evidencia neural auxiliar" quando existir;
- exporte resultados quando necessario.

## Upload Temporario de Difratograma

O painel aceita upload temporario para analise/comparacao sem transformar o
arquivo em registro publicado. Use formatos simples quando possivel:

- `.csv`
- `.txt`
- `.xy`
- `.dat`
- `.raw` quando o parser local reconhecer o formato

O upload temporario deve ser usado para triagem. Para publicacao na Argiloteca,
o arquivo precisa entrar no fluxo curado de registro/dados, com metadados,
licenca, proveniencia e revisao.

## Publicar/Enviar Para a Argiloteca

Existem dois sentidos diferentes de "publicar":

1. Atualizar o painel local com snapshots e indices derivados.
2. Publicar dados como registros/artefatos curados na Argiloteca/InvenioRDM.

O script `rodar_drx_diffractgpt_publicar_argiloteca.sh` atualiza o painel local
e os artefatos de consulta. Ele nao deve ser tratado como publicacao cientifica
confirmatoria.

Para registros curados, use o fluxo da Argiloteca/InvenioRDM:

- conferir metadados da amostra;
- anexar ou referenciar RAW original;
- anexar artefatos derivados versionados;
- registrar parametros de analise;
- preservar hash SHA-256;
- incluir relatorio tecnico;
- revisar interpretacao mineralogica antes de divulgar.

Endpoints uteis para artefatos DRX:

```bash
curl -fsS 'http://127.0.0.1:5000/api/argiloteca/drx/runs?limit=5'
curl -fsS 'http://127.0.0.1:5000/api/argiloteca/drx/references?limit=5'
curl -fsS 'http://127.0.0.1:5000/api/argiloteca/drx/raw-snapshot?limit=5'
```

## CIF/COD/RRUFF

RRUFF/ODR ja e lido como indice de referencia quando o manifesto esta presente.

Para indexar uma pasta curada de CIFs:

```bash
cd /home/invenio/invenio-project
CIF_SOURCE_DIR=/caminho/para/cifs \
SOURCE=COD \
MAX_FILES=5000 \
RESTART_ARGILOTECA=1 \
CHECK_API=1 \
./indexar_cif_cod_argiloteca.sh
```

O script nao copia CIFs grandes para dentro da Argiloteca. Ele gera um manifesto
com caminho local, hash, picos simulados via `pymatgen` e proveniencia:

```text
argiloteca-local/instance/argiloteca_drx_references/cif_cod_reference_index.json
```

Validar:

```bash
curl -fsS 'http://127.0.0.1:5000/api/argiloteca/drx/references?source=COD&limit=5'
```

## GSAS-II e DARA

Instalacoes locais:

```text
GSAS-II source: argiloteca-local/tools/GSAS-II
GSAS-II venv:   argiloteca-local/venvs/drx-science-py310
DARA source:    argiloteca-local/tools/DARA
DARA venv:      argiloteca-local/venvs/dara-xrd-py310
BGMN:           argiloteca-local/venvs/dara-xrd-py310/lib/python3.10/site-packages/dara/bgmn/BGMNwin/bgmn
```

Adapters configurados no env:

```text
ARGILOTECA_DRX_GSAS2_COMMAND=.../scripts/gsas2_external_adapter.sh
ARGILOTECA_DRX_DARA_COMMAND=.../scripts/dara_external_adapter.sh
```

Criar job GSAS-II:

```bash
curl -fsS -H 'Content-Type: application/json' \
  -d '{"engine":"gsas2","diffractogram_id":"minha-amostra"}' \
  http://127.0.0.1:5000/api/argiloteca/drx/jobs/external
```

Criar job DARA:

```bash
curl -fsS -H 'Content-Type: application/json' \
  -d '{"engine":"dara","diffractogram_id":"minha-amostra"}' \
  http://127.0.0.1:5000/api/argiloteca/drx/jobs/external
```

Processar jobs offline:

```bash
cd /home/invenio/invenio-project
set -a
. /home/invenio/invenio-project/argiloteca-local/secrets/l3-local.env
set +a
/home/invenio/invenio-project/argiloteca-local/venvs/app-py310-l3/bin/python \
  /home/invenio/invenio-project/argiloteca-local/app/argiloteca_custom/scripts/run_drx_external_jobs.py \
  --limit 10
```

Consultar jobs:

```bash
curl -fsS 'http://127.0.0.1:5000/api/argiloteca/drx/jobs/external?limit=10'
curl -fsS 'http://127.0.0.1:5000/api/argiloteca/drx/jobs/external/<job_id>'
```

Os adapters atuais validam a instalacao e gravam artefatos. Eles nao executam
refinamento real sem entradas curadas como:

- curva/padrao DRX em arquivo;
- CIFs/fases candidatas;
- perfil instrumental;
- radiacao/comprimento de onda;
- parametros de refinamento versionados;
- revisao curatorial.

## Relatorios e Runs

Runs DRX ficam em:

```text
argiloteca-local/instance/argiloteca_drx_runs
```

Jobs externos ficam em:

```text
argiloteca-local/instance/argiloteca_drx_jobs
```

Endpoints:

```bash
curl -fsS 'http://127.0.0.1:5000/api/argiloteca/drx/runs?limit=5'
curl -fsS 'http://127.0.0.1:5000/api/argiloteca/drx/runs/<run_id>'
```

Relatorios HTML:

```text
/argiloteca/drx/reports/technical/<diffractogram_id>.html
/argiloteca/drx/reports/selection/<run_id>.html
```

PDF depende de biblioteca disponivel; quando nao houver suporte, o endpoint
retorna fallback controlado.

## Validacao Rapida

Sintaxe Python:

```bash
cd /home/invenio/invenio-project
/home/invenio/invenio-project/argiloteca-local/venvs/app-py310-l3/bin/python -m py_compile \
  argiloteca-local/app/argiloteca_custom/argiloteca/services/drx_external_jobs.py \
  argiloteca-local/app/argiloteca_custom/scripts/run_drx_external_jobs.py \
  argiloteca-local/app/argiloteca_custom/scripts/gsas2_external_adapter.py \
  argiloteca-local/app/argiloteca_custom/scripts/dara_external_adapter.py
```

Testes DRX:

```bash
cd /home/invenio/invenio-project/argiloteca-local/app
/home/invenio/invenio-project/argiloteca-local/venvs/app-py310-l3/bin/python \
  -m unittest argiloteca_custom.tests.test_drx
```

Saude do painel:

```bash
curl -fsS -o /tmp/argiloteca_health.html -w '%{http_code}\n' http://127.0.0.1:5000/
curl -fsS 'http://127.0.0.1:5000/api/argiloteca/drx/references?limit=3'
curl -fsS 'http://127.0.0.1:5000/api/argiloteca/drx/raw-snapshot?limit=1'
```

## Problemas Comuns

### Porta 5000 recusada

Reinicie:

```bash
cd /home/invenio/invenio-project
./iniciar_argiloteca.sh
```

Veja logs:

```bash
tail -n 120 /tmp/argiloteca_restart.log
```

### API nao enxerga indice CIF/COD atualizado

O processo Flask pode estar com cache antigo. Reinicie a Argiloteca e consulte:

```bash
curl -fsS 'http://127.0.0.1:5000/api/argiloteca/drx/references?source=COD&limit=5'
```

### DARA avisa sobre Matplotlib config

Os wrappers definem:

```bash
MPLCONFIGDIR=/tmp/argiloteca_mplconfig
```

Se executar DARA manualmente, use a mesma variavel.

### DiffractGPT nao liberado para integracao

Consulte o arquivo `09_panel_integration_review_gate.json`. Enquanto
`integration_allowed` for `false`, mantenha os resultados como experimentais e
nao confirmatorios.

## Politica Cientifica

Nenhuma camada isolada confirma mineralogia. A decisao final exige avaliacao
conjunta de preparo, qualidade do difratograma, picos diagnosticos, tratamento
N/G/C, referencias, contexto geologico, possiveis fases sobrepostas e revisao
humana.
