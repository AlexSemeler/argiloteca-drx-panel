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

Auditoria de referência: `2026-06-25`.

Este repositório representa a tela integrada da Argiloteca em
`/drx/comparacao`. Essa tela é diferente da bancada local Streamlit localizada
no checkout principal em `povoamento/visualizacao-drx`: a bancada local serve
para explorar lotes, triagens Diffract/WebMineral, qualidade e revisão
operacional; a tela integrada é o painel de comparação publicado dentro da
Argiloteca/InvenioRDM.

O documento
[`EXPLICACAO_PAINEL_DRX_COMPARACAO.md`](EXPLICACAO_PAINEL_DRX_COMPARACAO.md)
descreve a lógica científica e a relação entre esses dois usos.

A documentação técnica completa do painel está em
[`argiloteca/argiloteca_custom/docs/painel_drx_documentacao.md`](argiloteca/argiloteca_custom/docs/painel_drx_documentacao.md).
Esse documento detalha funções, classes, objetos, regras mineralógicas, fontes
bibliográficas, estruturas JSON, payloads do painel, XAI e proveniência.

## Base científica e literatura

O painel foi ampliado para tratar a interpretação de DRX como um processo
rastreável, baseado em geometria, preparo da amostra, padrões 00l completos,
comportamento entre tratamentos e literatura mineralógica. A política atual da
engine N/G/C é `argiloteca_rule_based_diagnostic`: a Argiloteca pode registrar
diagnóstico assistido baseado em regras quando há evidência convergente, mas não
confirma mineral por pico isolado.

Referências e bases de conhecimento usadas na documentação e nas regras:

- `X-Ray Diffraction and the Identification and Analysis of Clay Minerals`,
  Capítulo 7, `Identification of Clay Minerals and Associated Minerals`: base
  executável para ilita/mica, caulinita, clorita, esmectita, vermiculita,
  minerais associados, reflexões 00l, comportamento N/G/C, d060 auxiliar,
  tabelas diagnósticas, limitações e ambiguidades.
- `X-Ray Diffraction and the Identification and Analysis of Clay Minerals`,
  Capítulo 8, `Identification of Mixed-Layered Clay Minerals`: base conceitual
  para argilominerais interestratificados, incluindo illite/smectite,
  chlorite/smectite, corrensite, kaolinite/smectite, serpentine/chlorite,
  mica/vermiculite, hydrobioite, Reichweite, ordenamento R0/R1/R3,
  superestruturas, mistura física versus interestratificação e comparação com
  padrões calculados.
- Capítulo `Diffraction I: Geometry`: base físico-geométrica para Lei de
  Bragg, separação rigorosa entre θ e 2θ, d-spacing, Laue, rede recíproca,
  esfera de Ewald, métodos Laue/cristal rotativo/pó, difratômetro,
  espectrômetro, unidades e condições não ideais.
- Anexo de modelagem 1D e cálculo de intensidade 00l da ilita: base para
  estrutura de camada, fator de estrutura de camada `G(θ)`, função de
  interferência, Lorentz-polarização, orientação preferencial, parâmetros
  instrumentais, intercamadas, defect broadening, distribuição de tamanho de
  cristalito e comparação observado × calculado.
- Brindley & Brown (1980), Bailey (1980/1988), Moore & Reynolds (1989/1997),
  Drits & Tchoubar (1990), Lanson & Bouchet (1995), Meunier, *Clays* (2005),
  fluxograma USGS de identificação de argilominerais por DRX e referências
  empíricas Pre-Sal UFRGS/Petrobras.

Os PDFs locais usados como fontes de extração ficam fora deste recorte Git. Os
caminhos locais documentados durante a curadoria foram:

- `/home/invenio/Downloads/analises.pdf`;
- `/home/invenio/invenio-project/textos/capitulo8.pdf`;
- `/home/invenio/invenio-project/textos/difracao-geomentria.pdf`;
- `/home/invenio/invenio-project/textos/capitulo3-ilita.pdf`;
- `/home/invenio/invenio-project/textos/lanson-1995-bull-centres-rech-ep-19-91.pdf`;
- `/home/invenio/invenio-project/Clays_Meunier.pdf`.

O repositório versiona somente fragmentos curtos de proveniência, estruturas
derivadas, regras e documentação técnica. Ele não redistribui os livros ou PDFs.

## Motores e regras incorporados

- Motor N/G/C: compara Natural, Glicolado e Calcinado como trajetória
  mineralógica, preservando incerteza quando falta preparo ou quando há
  sobreposição.
- Motor de geometria DRX: aplica a Lei de Bragg com θ = 2θ/2, calcula
  d-spacing, valida radiação/comprimento de onda e registra limitações
  geométricas.
- Motor de picos: normaliza curvas, detecta máximos, estima FWHM, intensidade,
  área, largura e qualidade, sem transformar pico isolado em diagnóstico final.
- Base executável do Capítulo 7:
  `argiloteca/argiloteca_custom/argiloteca_drx/diagnostics/chapter7_knowledge.py`
  e JSONs derivados em
  `argiloteca/argiloteca_custom/argiloteca_drx/diagnostics/data/generated/`.
- Motor de interestratificados:
  `argiloteca/argiloteca_custom/argiloteca_drx/diagnostics/mixed_layer_engine.py`,
  com hipóteses para corrensite, I/S, C/S, K/S e T/S quando aparecem expansão
  parcial, ombros, bandas largas ou sequências N/G/C compatíveis.
- Comparador de literatura, empírico e Pre-Sal: separa `literature_matches`,
  `empirical_matches` e `presalt_matches`, preservando proveniência e impedindo
  que dataset local substitua regra bibliográfica.
- XAI e proveniência: cada interpretação deve indicar regra, fonte, preparo,
  evidência a favor, evidência contra, ambiguidade, dados ausentes e próximos
  testes recomendados.
- Simulação 1D e observado × calculado: documentada como módulo de evolução do
  painel para testar se padrões 00l calculados são compatíveis com o padrão
  observado em posição, intensidade, largura, forma e comportamento entre
  tratamentos.

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
- `argiloteca/argiloteca_custom/docs/painel_drx_documentacao.md`:
  documentação técnica completa do painel, incluindo literatura, regras,
  módulos, classes, funções, JSONs e XAI.
- `argiloteca/argiloteca_custom/argiloteca_drx/diagnostics/chapter7_knowledge.py`:
  base executável rastreável do Capítulo 7.
- `argiloteca/argiloteca_custom/argiloteca_drx/diagnostics/mixed_layer_engine.py`:
  hipóteses de argilominerais interestratificados e alertas de perfis 00l
  complexos.
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
- Calcula e exibe relações 2θ, θ e d-spacing usando a Lei de Bragg quando os
  metadados de radiação permitem.
- Agrega candidatos mineralógicos, picos de suporte, reflexões ausentes,
  conflitos e recomendações.
- Emite hipóteses para argilominerais interestratificados quando o padrão 00l,
  os tratamentos e a largura/forma dos picos sugerem comportamento misto.
- Mostra regra-fonte, política de interpretação, evidências e ambiguidades para
  revisão curatorial.
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
- Geometria DRX: separa 2θ de θ, calcula d-spacing e evita interpretação de
  picos sem radiação, unidade e preparo.
- Reflexões confirmatórias: cruza picos observados com janelas esperadas para
  argilominerais como esmectita/montmorilonita, ilita/mica, clorita, caulinita e
  vermiculita.
- Interestratificados: registra hipóteses como illite/smectite,
  chlorite/smectite, corrensite, kaolinite/smectite, mica/vermiculite e
  kerolite/stevensite quando o padrão não deve ser forçado para mineral puro.
- Capítulo 7: fornece entidades, regras diagnósticas, regras de comportamento,
  regras d060, intensidade auxiliar, perfis minerais e tabelas de reflexão.
- Capítulo 8: fornece o modelo conceitual de mixed-layer, Reichweite, R0/R1/R3,
  superestruturas, Δ2θ, alargamento de linhas e distinção entre mistura física e
  interestratificação.
- Simulação 1D: documenta como testar hipóteses por padrão calculado, fator de
  estrutura de camada, função de interferência, correções instrumentais e
  resíduos observado × calculado.
- Similaridade RAW: combina metadados, forma da curva, picos e candidatos
  mineralógicos para encontrar RAWs já existentes em pacotes.
- XRDNet contextual: aparece apenas em cartões de similaridade, como evidência
  neural auxiliar.
- Fila do geólogo: quando os JSONs derivados existem, ajuda a priorizar revisão
  humana.

## Validação rápida

```bash
PYTHONPATH="$PWD:$PWD/argiloteca/argiloteca_custom" \
  /home/invenio/invenio-project/argiloteca-local/venvs/app-py310-l3/bin/python \
  -m unittest discover \
  -s argiloteca/argiloteca_custom/tests \
  -p test_drx_v3_engine.py

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
