# Escopo do repositório

Este repositório contém o recorte publicável do painel DRX da Argiloteca.

## Incluído

- Código da comparação DRX.
- Código do painel de análises e pacotes analíticos.
- Serviços Python de leitura, enriquecimento, comparação e ligação com registros.
- Scripts de métricas, reclassificação, publicação local e atualização Linux do painel.
- JSONs WebMineral de referência/fallback usados pelo classificador mineralógico.
- Testes relacionados ao painel DRX.
- Documentação técnica e explicativa.

## Não incluído

- Arquivos `.RAW`.
- Snapshots completos gerados localmente.
- Relatórios PDF/HTML/JSON gerados.
- JSONs derivados de classificação de RAW, inventários e publicações locais do painel.
- Dados de runtime do InvenioRDM.
- Outros módulos da Argiloteca sem relação direta com o painel DRX.

## Dependência esperada

Este recorte é extraído de um módulo maior da Argiloteca/InvenioRDM. O script de
métricas roda de forma independente sobre arquivos JSON locais. A interface
completa depende do ambiente Argiloteca para registrar rotas, templates e
serviços Flask/InvenioRDM.
