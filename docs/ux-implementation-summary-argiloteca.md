# Implementação P0/P1 da auditoria UX da Argiloteca

Data: 2026-05-20

## 1. Resumo das melhorias implementadas

Foram implementadas melhorias incrementais P0/P1 para padronizar a experiência das páginas científicas da Argiloteca, sem reescrever a aplicação e sem alterar contratos existentes de APIs de forma destrutiva.

Principais entregas:

- Criação de macros compartilhadas para cabeçalho científico, breadcrumbs, navegação entre módulos, links relacionados e estados.
- Criação de CSS base para tokens e componentes científicos reutilizáveis.
- Criação da rota e página índice `/analises/`.
- Padronização de cabeçalhos, breadcrumbs e rótulos de navegação nas páginas de mapa, catálogo, geoquímica, DRX e pacote analítico.
- Ajustes de acessibilidade: `aria-label`, `aria-live`, foco visível e redução de múltiplos `h1` nos módulos atualizados.
- Melhorias específicas em DRX, pacote analítico, mapa e atlas geoquímico.

## 2. Arquivos alterados

- `argiloteca/argiloteca_custom/argiloteca/views.py`
- `argiloteca/argiloteca_custom/argiloteca/services/geoquimica.py`
- `argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/mapa_argilominerais.html`
- `argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/catalogo_autorizado_argilominerais.html`
- `argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/geoquimica_rede.html`
- `argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/geoquimica_agregada.html`
- `argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/drx_comparacao.html`
- `argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/pacote_analitico.html`
- `argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argilo_map_components.html`
- `argiloteca/templates/semantic-ui/argilo_map_components.html`
- `argiloteca/argiloteca_custom/argiloteca/static/js/drx-comparacao.js`
- `argiloteca/argiloteca_custom/argiloteca/static/js/pacote-analitico.js`
- `argiloteca/argiloteca_custom/tests/test_drx.py`
- `docs/ux-audit-argiloteca.md`

## 3. Novos arquivos criados

- `argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/_scientific_page.html`
- `argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/analises_index.html`
- `argiloteca/argiloteca_custom/argiloteca/static/css/argiloteca-scientific.css`
- `docs/ux-implementation-summary-argiloteca.md`

## 4. Rotas adicionadas

- `/analises/`, endpoint `analises_index`

A rota renderiza sem `record_id` e funciona como porta de entrada para:

- Comparação DRX
- Atlas químico
- Rede geoquímica
- Mapa de argilominerais
- Catálogo de nomes
- Registros com dados DRX, quando a API local responde

## 5. Componentes/macros criados

Arquivo: `argiloteca/argiloteca_custom/argiloteca/templates/semantic-ui/argiloteca/_scientific_page.html`

Macros:

- `render_scientific_header(...)`
- `render_module_nav(...)`
- `render_breadcrumb(...)`
- `render_related_links(...)`
- `render_empty_state(...)`
- `render_loading_state(...)`
- `render_error_state(...)`

## 6. Melhorias de acessibilidade aplicadas

- Breadcrumb com `aria-label`.
- Navegação científica com `aria-label`.
- Estados dinâmicos com `aria-live="polite"` em áreas de status.
- Botões de alternância existentes preservados com `aria-pressed`.
- Página `/analises/` com cards de entrada e seção de registros analíticos com estado vazio seguro.
- Pacote analítico passou a ter `h1` curto no cabeçalho comum e `h2` interno, evitando título de registro muito longo como título principal.
- DRX recebeu texto orientativo inicial quando aberto sem contexto.

## 7. Melhorias de responsividade aplicadas

- Navegação científica compartilhada com quebra em múltiplas linhas.
- Navegação científica ajustada para uma única camada principal, sem botão "Comunidades" e sem botões de ação duplicados no cabeçalho.
- Navegação científica revisada novamente para remover o botão "Análises" da faixa global e usar a ordem: Mapa, Catálogo de nomes, Rede geoquímica, Atlas químico e Comparação DRX.
- Paleta do cabeçalho científico alinhada ao marrom padrão já usado na página inicial da Argiloteca.
- Seção de introdução da página inicial padronizada com os mesmos rótulos de navegação científica.
- Menus internos duplicados removidos/ocultados em mapa, catálogo, rede, atlas e DRX; controles operacionais do mapa foram preservados.
- A comparação DRX sem `record_id` passou a ler o snapshot geral de arquivos RAW do módulo DRX. A seleção carrega metadados do snapshot e busca a curva RAW sob demanda.
- Botões da navegação científica padronizados no mesmo modelo da introdução: barra clara, botões retangulares bege, texto marrom e ativo/hover em marrom com destaque inferior.
- Painel do mapa padronizado com os demais painéis: removida a faixa interna marrom sólida, adotado cabeçalho claro com borda suave e botões operacionais retangulares bege/marrom.
- Página `/analises/` expandida para funcionar como visão geral do snapshot RAW do módulo DRX, com filtros, estatísticas e lista inicial de arquivos processados, reaproveitando a mesma API usada pela comparação.
- Painel `/analises/` reestruturado com o mesmo padrão visual de `/analises/<record_id>`: cabeçalho `argilo-package`, fluxo em etapas, métodos, métricas, filtros e tabela analítica, lendo o snapshot geral em vez de um registro específico.
- Cards da página `/analises/` com grid responsivo.
- Toolbars DRX agrupadas por Seleção, Visualização e Exportação.
- Tabelas e componentes existentes preservados com menor risco; ajustes mais profundos de visualização responsiva ficaram para P2.

## 8. Pendências P2/P3 não implementadas

- Customização profunda de `/communities/`, porque depende de templates globais do InvenioRDM e deve ser feita com uma inspeção visual específica da listagem real.
- Alternativa tabular completa para todos os nós e arestas da rede geoquímica; nesta fase foi criado um container semântico inicial, sem refatorar o JavaScript da rede.
- Redesenho responsivo completo das tabelas largas.
- Consolidação total dos CSS específicos dos módulos em um design system único.
- Revisão visual em navegador real, pois o ambiente local previamente apresentou bloqueio/indisponibilidade em `https://127.0.0.1:5443`.

## 9. Como testar manualmente

Com a aplicação local ativa, acessar:

- `https://127.0.0.1:5443/analises/`
- `https://127.0.0.1:5443/drx/comparacao`
- `https://127.0.0.1:5443/geoquimica/rede`
- `https://127.0.0.1:5443/geoquimica/composicao-global`
- `https://127.0.0.1:5443/mapa-argilominerais`
- `https://127.0.0.1:5443/catalogo-autorizado-de-nomes-para-argilominerais`
- `https://127.0.0.1:5443/analises/<record_id>`

Verificar:

- Existência de breadcrumb no topo.
- Navegação científica com rótulos legíveis.
- `/analises/` renderizando sem `record_id`.
- DRX com estado inicial orientativo.
- Pacote analítico com H1 curto e título do registro em metadados.
- Mapa com rótulo "Composição química global" e microtexto de legenda.

## 10. Comandos executados

```bash
PYTHONPYCACHEPREFIX=/tmp/argilo_pycache python3 -m py_compile argiloteca/argiloteca_custom/argiloteca/views.py argiloteca/argiloteca_custom/argiloteca/services/geoquimica.py
node --check argiloteca/argiloteca_custom/argiloteca/static/js/drx-comparacao.js
node --check argiloteca/argiloteca_custom/argiloteca/static/js/pacote-analitico.js
/Users/argilas/venvs/argiloteca-rdm12/bin/python - <<'PY'
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader([
    'argiloteca/argiloteca_custom/argiloteca/templates',
    'argiloteca/templates',
]))
for name in [
    'semantic-ui/argiloteca/_scientific_page.html',
    'semantic-ui/argiloteca/mapa_argilominerais.html',
    'semantic-ui/argiloteca/catalogo_autorizado_argilominerais.html',
    'semantic-ui/argiloteca/geoquimica_rede.html',
    'semantic-ui/argiloteca/geoquimica_agregada.html',
    'semantic-ui/argiloteca/drx_comparacao.html',
    'semantic-ui/argiloteca/analises_index.html',
    'semantic-ui/argiloteca/pacote_analitico.html',
    'semantic-ui/argilo_map_components.html',
]:
    env.get_template(name)
PY
/Users/argilas/venvs/argiloteca-rdm12/bin/python -m unittest tests.test_drx.AnalyticalPackageTest.test_analises_index_route_renders_without_record_id
/Users/argilas/venvs/argiloteca-rdm12/bin/python -m unittest tests.test_drx
/Users/argilas/argilas/argiloteca/start_local_5443.sh
```

Resultado:

- Compilação Python: OK.
- Verificação JavaScript: OK.
- Parse dos templates Jinja alterados: OK.
- Teste específico da nova rota: OK.
- Suíte `tests.test_drx`: 32 testes OK.
- Inicialização local: não concluída porque a porta `5443` já estava ocupada por outro processo; não houve traceback novo da aplicação nesta tentativa.
