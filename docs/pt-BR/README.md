# Brasil em Rede

**Infraestrutura aberta para baixar, cadastrar e conectar dados públicos brasileiros.**

[English](../../README.md) · [Plano das fontes](../implementation/README.md) · [Roteiro do projeto](../project/README.md)

Continuação independente do br/acc Open Graph, com licença AGPL e créditos
preservados. Consulte [origem e modificações](../../NOTICE.md).

## Estado atual

A base de código tem API FastAPI, grafo Neo4j, ETL Python e interface React.
O catálogo possui **169 fontes**, sendo **168 no universo público de
planejamento**, e existem **47 módulos de pipeline**. Cada fonte possui um
plano individual para aquisição, cadastro, ligações e aceite.

Esses números descrevem o repositório. Não comprovam conectores funcionando,
portais disponíveis ou banco carregado. Estados `loaded` herdados são metadados
históricos até uma execução validada neste projeto.

A primeira entrega será um piloto reproduzível **CNPJ → sanções → contratos
públicos**, com evidência de origem e data. O trabalho começa pela fundação
registrada no [roteiro](../project/README.md). Ainda não há serviço de produção.

## O Que Esta Incluido Neste Repositorio Publico

- Código da API, interface, ETL, esquema Neo4j e fixtures sintéticas.
- [Cadastro das fontes](../source_registry_br_v1.csv) e [resumo do catálogo](../data-sources.md).
- [169 fichas individuais](../implementation/README.md), [matriz de implementação](../implementation/source_matrix.csv) e [21 planos de cruzamentos](../implementation/crossings.md).
- [Plano estruturado](../../config/source_implementation_plan.json), gerador e verificações.
- [Backlog inicial](../../config/github_backlog.json) e CI de código, segurança e catálogo.

## O Que Nao Esta Incluido Por Padrao

Não são distribuídos dados em massa, credenciais, backups de produção ou grafo
nacional pré-carregado. Portais de descoberta, bases derivadas e sistemas
restritos têm requisitos próprios; consulte a ficha de cada fonte.

## O Que E Reproduzivel Localmente Hoje

As verificações abaixo usam Python 3.12 e não baixam bases externas. Execute na
raiz do repositório:

```bash
python3 scripts/generate_source_implementation_plan.py --check
python3 scripts/generate_data_sources_summary.py --check
python3 scripts/check_public_claims.py --repo-root .
python3 scripts/check_pipeline_contracts.py
python3 scripts/check_pipeline_inputs.py
```

Para desenvolver, instale Python 3.12, uv e Node.js 22:

```bash
(cd api && uv sync --locked --extra dev)
(cd etl && uv sync --locked --extra dev)
(cd frontend && npm ci)
```

Depois execute `make check` e `make neutrality`. Os testes de integração com
banco são separados da suíte padrão. O Compose e a carga sintética herdados
servem como ponto de partida; alinhamento de configuração e validação completa
são tarefas de fundação. Esta publicação não certifica bootstrap de todas as fontes.

As contagens em [métricas de referência](../reference_metrics.md) descrevem um
**snapshot de referencia de producao** herdado, não o banco deste projeto.

## Por onde começar

1. Corrigir IDs das fontes, documentos, migração e constraints.
2. Tornar aquisição, escrita e ligações verificáveis e retomáveis.
3. Alinhar orquestração, dimensões e ambiente; entregar o piloto de ponta a ponta.
4. Executar as oito ondas de expansão, aprovando fonte por fonte.

Download, carga e cruzamentos precisam de evidências distintas. Homônimos e
documentos parciais não viram uma identidade comum por inferência. Consulte a
[arquitetura e os critérios de aceite](../implementation/architecture.md).

## Contribuição e licença

Veja o [guia de contribuição](CONTRIBUTING.md) e o [roteiro](../project/README.md).
As automações anteriores de deploy, releases, imagens e cargas agendadas foram
[arquivadas](../history/workflows/README.md).

O código mantém a licença [AGPL-3.0-or-later](../../LICENSE); as referências
importadas do Brazil Visible mantêm o [aviso MIT](../catalogs/brazil_visible_LICENSE.txt).
Documentos de políticas herdados são uma base para revisão antes de operar um
serviço. Uma ligação em registros públicos não estabelece irregularidade.
