# Auditoria visual e runtime do painel DRX N/G/C

Este documento registra a etapa de estabilizacao antes de remover logica legada
do frontend. A meta e confirmar que os contratos backend ja alimentam o painel
sem mudar ciencia, texto interpretativo, pontuacao ou aparencia.

## Escopo validado

- O painel `/drx/comparacao` deve continuar abrindo sem erro HTTP.
- O JavaScript `drx-comparacao.js` deve continuar sintaticamente valido.
- A API N/G/C deve retornar `backend_grouping`, `ngc_evidence_summary` e
  `ngc_source_rule_summary`.
- O frontend deve preferir esses contratos quando presentes.
- O frontend deve manter fallback legado para agrupamento, resumo, interpretacoes,
  evidencias e Regra-fonte.
- A secao `Resumo das evidências N-G-C` deve continuar existindo.
- A secao `Regra-fonte` deve continuar imprimindo regras aplicadas e dados das
  tabelas quando o backend fornecer esses dados.

## Verificacoes automatizadas desta etapa

- Teste estatico de renderizadores N/G/C:
  `test_drx_ngc_frontend_renderer_contracts.py`.
- Validacao de sintaxe JS com `node --check`.
- Testes de contratos backend ja existentes para agrupamento, evidencias e
  Regra-fonte.

## Resultado esperado

Esta etapa nao remove codigo legado. Ela apenas cria uma barreira de regressao
para que a proxima rodada possa reduzir duplicacao no JS com menor risco.

## Riscos residuais

- Este teste nao substitui validacao DOM/browser real.
- Sem harness Playwright/Puppeteer no projeto, a verificacao visual continua
  dependendo de teste manual no navegador ou auditoria HTTP/API.
- Dados reais sem candidatos estruturados podem retornar `ngc_source_rule_summary`
  vazio; isso e aceitavel quando o workflow nao produziu candidatos para aquele
  conjunto.

## Proximo passo seguro

Executar uma validacao manual no navegador com amostras N/G/C reais. Depois,
remover duplicacao no JS em pequenas etapas, mantendo fallback ate haver cobertura
DOM suficiente.
