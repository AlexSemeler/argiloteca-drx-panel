# Painel DRX da Argiloteca

Este recorte documenta o painel DRX/XRD da Argiloteca para publicação em Git. O
objetivo é versionar o código da interface, as rotas Flask/InvenioRDM, os
serviços de leitura/comparação e a geração de métricas, sem incluir arquivos RAW
pesados nem relatórios gerados.

## Projeto

O projeto desenvolve um módulo em Python para comparar arquivos .raw de DRX
aplicados a argilominerais, preservando dados brutos e registrando etapas de
processamento. O sistema reconstrói curvas 2θ versus intensidade, calcula
d-spacing pela Lei de Bragg, corrige linha de base, normaliza sinais, detecta
picos e estima FWHM, áreas, intensidades relativas e qualidade. Também compara
difratogramas com artigos, teses, dissertações, relatórios e dados científicos
organizados por metadados geológicos e analíticos. O objetivo é ranquear
referências semelhantes e gerar hipóteses rastreáveis, sem confirmar
automaticamente minerais, fortalecendo reprodutibilidade, curadoria científica e
reuso de dados em Geoquímica, e apoiando coleções e laboratórios universitários.

## Estado atual

Auditoria de referência: `2026-06-18`.

Este repositório representa a tela integrada da Argiloteca em
`/drx/comparacao`. Essa tela é diferente da bancada local Streamlit localizada
no checkout principal em `povoamento/visualizacao-drx`: a bancada local serve
para explorar lotes, triagens Diffract/WebMineral, qualidade e revisão
operacional; a tela integrada é o painel de comparação publicado dentro da
Argiloteca/InvenioRDM.

O documento
[`EXPLICACAO_PAINEL_DRX_COMPARACAO.md`](EXPLICACAO_PAINEL_DRX_COMPARACAO.md)
descreve a lógica científica e a relação entre esses dois usos.

## Componentes principais

- `argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/drx_comparacao.html`:
  página de comparação de difratogramas.
- `argiloteca/argiloteca_custom/argiloteca/static/js/drx-comparacao.js`:
  lógica de seleção, gráfico, comparação N/G/C, painel mineralógico, RAW
  temporário, similaridade, XRDNet contextual e exportação.
- `argiloteca/argiloteca_custom/argiloteca/static/css/drx-comparacao.css`:
  estilos do painel de comparação.
- `argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/analises_index.html`:
  visão geral dos RAW processados.
- `argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/pacote_analitico.html`:
  pacote analítico de um registro.
- `argiloteca/argiloteca_custom/argiloteca/static/js/pacote-analitico.js`:
  tabela, filtros, exportação e visualização de curvas no pacote analítico.
- `argiloteca/argiloteca_custom/argiloteca/static/css/pacote-analitico.css`:
  estilos compartilhados do painel de análise.
- `argiloteca/argiloteca_custom/argiloteca/services/drx.py`:
  leitura de snapshots RAW, enriquecimento DRX, seleção por mineral e ligação com
  registros.
- `argiloteca/argiloteca_custom/argiloteca/services/analytical_packages.py`:
  leitura de manifestos analíticos e comparação de RAW externo com pacotes DRX.
- `argiloteca/argiloteca_custom/argiloteca/services/raw_snapshot_links.py`:
  ponte opcional entre snapshots gerais de RAW e registros públicos da Argiloteca.
- `povoamento/drx/gerar_metricas_painel_drx.py`:
  geração de métricas portáveis do painel.
- `povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_argilominerais_vocabulario.json`:
  JSON de referência usado pelo classificador mineralógico.
- `povoamento/visualizacao-drx/saida_argiloteca_drx/webmineral_xray_referencia.json`:
  cache WebMineral legado usado como fallback.
- `povoamento/visualizacao-drx/webmineral/webmineral_argilominerais_vocabulario_manifest.json`:
  manifesto/rastreabilidade da referência WebMineral local.

## O que o painel faz

- Sobrepõe difratogramas RAW processados em modo absoluto, normalizado ou
  empilhado.
- Seleciona RAWs vindos do snapshot geral ou de pacotes analíticos por registro.
- Compara tratamentos Natural/Glicolado/Calcinado e calcula leitura N/G/C
  assistida.
- Agrega candidatos mineralógicos, picos de suporte, reflexões ausentes,
  conflitos e recomendações.
- Compara RAW temporário com pacotes DRX já indexados sem gravar o arquivo como
  registro.
- Mostra XRDNet apenas como evidência contextual quando há RAW semelhante ou
  carregado como semelhante.
- Exporta CSV e PDF da comparação.

Todas as interpretações são preliminares e exigem revisão curatorial.

## Relação com `visualizacao-drx`

O diretório local `povoamento/visualizacao-drx` é uma bancada de trabalho do
projeto maior da Argiloteca. Ele pode conter RAWs, snapshots, saídas Diffract,
saídas WebMineral/CMS e um painel Streamlit de lote. Esse material não é
publicado integralmente neste repositório.

Na prática:

- `/drx/comparacao` é a interface integrada publicada neste recorte;
- `visualizacao-drx` é a área de processamento, diagnóstico e revisão de lote;
- os RAWs e snapshots completos devem permanecer fora do Git;
- os JSONs WebMineral de referência podem ser versionados porque apoiam a
  classificação e não são resultado classificado dos RAWs;
- métricas agregadas e documentação explicativa podem ser versionadas.

## Métricas

Gere um JSON de métricas a partir de um checkout com os artefatos locais
disponíveis:

```bash
cd argiloteca-drx-panel
python3 povoamento/drx/gerar_metricas_painel_drx.py --stdout
```

Saída padrão:

```text
reports/drx_panel_metrics.json
```

O relatório inclui:

- total de linhas no snapshot mineralógico RAW;
- status dos RAW;
- total de RAW com candidatos minerais;
- total de RAW com picos detectados;
- distribuição por tratamento;
- minerais candidatos mais frequentes;
- buckets de score mineralógico;
- quantidade de manifestos DRX;
- quantidade de itens em pacotes analíticos;
- itens com resultados avançados, ajustes e `record_id` válido.

Se os snapshots e pacotes analíticos estiverem fora dos caminhos padrão, use
`--raw-snapshot`, `--treatment-snapshot` e `--packages-dir` para apontar para os
artefatos locais. Sem esses dados, o script continua executando, mas as métricas
ficam vazias ou parciais.

## Publicação no Linux

Para enviar o recorte atualizado ao servidor local:

```bash
cd /Users/argilas/argilas/repos/argiloteca-drx-panel
./enviar_painel_para_linux_192_168_0_16.sh
```

O script envia somente arquivos permitidos, aplica no runtime Linux, reinicia a
Argiloteca local quando possível e confere se `/drx/comparacao` está servindo a
versão esperada do HTML/JS.

Para baixar e aplicar diretamente no Linux, use no servidor:

```bash
cd /home/invenio/invenio-project
./linux_baixar_e_atualizar_painel_argiloteca.sh
```

## Dados que não devem ir para Git

Não versionar:

- arquivos `.raw` ou `.RAW`;
- snapshots completos muito grandes quando forem produto de processamento local;
- JSONs derivados da classificação de RAW, como `classificacao_*`,
  `publicacao_painel_drx.json`, inventários e resumos de processamento;
- PDFs/HTMLs de auditoria gerados;
- `__pycache__`, `.pytest_cache`, logs e saídas temporárias;
- diretórios de execução local ou deploy.

Os JSONs WebMineral de referência do classificador são exceção: eles são
versionados para tornar a comparação mineralógica reprodutível.

## Fluxos validados

- `/drx/comparacao`: comparação geral de difratogramas.
- `/drx/comparacao?argilomineral=<slug>`: abre a comparação e carrega
  automaticamente um difratograma com o argilomineral informado, quando houver
  item compatível no snapshot.
- `/drx/comparacao?record_id=<record_id>&source=package`: abre a comparação
  contextualizada por pacote analítico.
- `/analises/`: visão geral rastreável dos RAW processados.
- `/analises/<record_id>`: pacote analítico de um registro.
- `/argilominerais/<slug>`: página do argilomineral com atalho para o painel DRX.

## Camadas auxiliares

- Comparação N/G/C: usa Natural, Glicolado e Calcinado como trajetória
  diagnóstica assistida.
- Reflexões confirmatórias: cruza picos observados com janelas esperadas para
  argilominerais como esmectita/montmorilonita, ilita/mica, clorita, caulinita e
  vermiculita.
- Similaridade RAW: combina metadados, forma da curva, picos e candidatos
  mineralógicos para encontrar RAWs já existentes em pacotes.
- XRDNet contextual: aparece apenas em cartões de similaridade, como evidência
  neural auxiliar.
- Fila do geólogo: quando os JSONs derivados existem, ajuda a priorizar revisão
  humana.

## Validação rápida

```bash
python3 -m py_compile \
  argiloteca/argiloteca_custom/argiloteca/services/drx.py \
  argiloteca/argiloteca_custom/argiloteca/services/analytical_packages.py \
  argiloteca/argiloteca_custom/argiloteca/services/raw_snapshot_links.py \
  povoamento/drx/gerar_metricas_painel_drx.py

node --check argiloteca/argiloteca_custom/argiloteca/static/js/drx-comparacao.js
node --check argiloteca/argiloteca_custom/argiloteca/static/js/pacote-analitico.js
```

Antes de publicar, confira:

```bash
git status --short
git diff --check
git ls-files '*.raw' '*.RAW' '*.rar' '*.zip' 'var/*' 'reports/*'
```

O último comando deve retornar vazio para dados brutos e artefatos locais.

## Observação científica

O painel produz interpretação preliminar. Os scores e classificações são
assistivos: dependem da qualidade do difratograma, preparo, sobreposição de
picos, curadoria das referências e validação mineralógica complementar.
