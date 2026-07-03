# Migracao do agrupamento N/G/C para backend

## Resumo

O painel DRX ainda mantem parte do agrupamento N/G/C em
`drx-comparacao.js`, enquanto o backend ja possui o workflow versionado
`build_ngc_workflow(items)`. Essa duplicidade aumenta o risco de divergencia
entre o que o painel mostra e o que a engine Python calcula, principalmente
quando RAWs externos, snapshots e registros internos usam payloads levemente
diferentes.

Esta rodada cria apenas um contrato estrutural no backend. Nenhuma regra
mineralogica, score, texto cientifico ou fluxo visual deve mudar.

## Estado Atual

Funcoes JavaScript ainda envolvidas:

- `buildNgcGroups(items)`: agrupa itens por amostra-base e separa preparos em
  `natural`, `glicolada`, `calcinada` e `indeterminado`.
- `buildNgcInterpretations(items)`: usa os grupos JS, picos em faixas basais e
  trajetorias N/G/C para montar linhas interpretativas de apresentacao.
- `buildNgcSummary(items)`: resume completude do trio, duplicatas, evidencias e
  candidatos para o painel de analises automatizadas.

Chamadas principais observadas em `drx-comparacao.js`:

- `buildNgcGroups(items)` e usado em paineis de selecao, trajetorias basais,
  pre-classificacao e relatorios.
- `buildNgcInterpretations(items)` alimenta cards e resumo textual.
- `buildNgcSummary(items)` alimenta a tabela de analises automatizadas.

Campos de item consumidos no JS:

- `treatment`
- `sampleCode`
- `sample.sample_code`
- `metadata.original_filename`
- `metadata.sample_code`
- `id`
- `peaks`, `advanced_peaks`, `detected_peaks`

Backend existente:

- endpoint: `/argiloteca/drx/workflows/ngc`
- funcao central: `build_ngc_workflow(items)`
- normalizacao interna: `_item_from_payload(item)`
- interpretacao por grupo: `_interpret_group(sample_base, rows)`

Partes ja existentes no payload backend:

- `groups`
- `ngc_behavior`
- `clay_interpretation`
- `diagnostic_interpretation`
- `external_curve_preclassification`
- `external_raw_preclassification`
- `ngc_candidate_peak_windows`
- `interpretation_policy`

## Plano Incremental

1. Criar contrato backend equivalente para agrupamento estrutural:
   `backend_grouping`.
2. Cobrir o contrato com fixtures sinteticas N/G/C.
3. Em rodada futura, fazer o frontend preferir
   `ngc_workflow.backend_grouping` quando existir.
4. Manter `buildNgcGroups`, `buildNgcInterpretations` e `buildNgcSummary` como
   fallback por uma versao.
5. Remover agrupamento cientifico do JS apenas depois de equivalencia testada
   e validacao visual.

## Criterios Cientificos

- Nenhuma regra mineralogica muda.
- Nenhuma inferencia mineral nova e criada pelo contrato.
- Nenhum score e recalculado.
- Evidencias e interpretacoes continuam vindo do workflow existente.
- Toda decisao cientifica deve preservar `rule_id`, fonte, capitulo, pagina,
  tabela ou figura quando disponivel.
- Resultados continuam auxiliares, nao confirmatorios.

## Contrato Backend Criado

`build_ngc_backend_grouping_contract(items)` retorna:

```json
{
  "version": "argiloteca.drx.ngc.backend_grouping.v1",
  "policy": "argiloteca_rule_based_diagnostic",
  "status": "available",
  "groups": [],
  "warnings": []
}
```

Esse contrato agrupa estruturalmente itens por `sample_base`, lista preparos
disponiveis, preserva nomes de arquivo, origem dos metadados e contagem de
picos. Ele nao calcula d-spacing, nao detecta picos e nao classifica minerais.

