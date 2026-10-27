# Etapas de implementação da unificação

Gerado de `config/unification_plan.json`. Estado: **planejamento**.

F00 ([issue #1](https://github.com/bdwerlang/brasil-em-rede/issues/1)) trata as dependências antes da introdução dos novos serviços e de release. Inventário e desenho podem ocorrer em paralelo.

As dependências definem a ordem; trabalhos independentes podem ocorrer em paralelo conforme equipe e recursos. M/L/XL expressam esforço relativo, sem compromisso de datas. Papéis são propostos, ainda sem pessoas atribuídas.

| Etapa | Depende de | Papel responsável | Esforço |
|---|---|---|---|
| [U01 — Inventário e contratos](#u01) | Inventário inicial | engenharia de dados | M |
| [U02 — Identidade e modelo canônico](#u02) | U01 | dados e backend | L |
| [U03 — Persistência e catálogo operacional](#u03) | U01 | infraestrutura e dados | L |
| [U04 — Aquisição e normalização comuns](#u04) | U02, U03 | engenharia de dados | XL |
| [U05 — Observações, fatos e histórico](#u05) | U02, U03 | dados e domínio | L |
| [U06 — Resolução e reconciliação entre fontes](#u06) | U04, U05 | dados e revisão de domínio | XL |
| [U07 — Projeção Neo4j compatível](#u07) | U05, U06 | dados e backend | L |
| [U08 — Piloto de entidades e vínculos](#u08) | U04, U07 | dados e domínio | L |
| [U09 — Piloto de séries e geografia](#u09) | U04, U05, U06 | dados e análise de domínio | M |
| [U10 — API e interface unificadas](#u10) | U08, U09 | backend e frontend | L |
| [U11 — Migração, publicação e recuperação](#u11) | U10 | infraestrutura e backend | XL |
| [U12 — Expansão das 169 fontes e operação](#u12) | U11 | dados, backend e operação | XL |

<a id="u01"></a>

## U01 — Inventário e contratos

Backlog existente: [F01 / #2](https://github.com/bdwerlang/brasil-em-rede/issues/2), [F10 / #11](https://github.com/bdwerlang/brasil-em-rede/issues/11).

Trabalho:

- Inventariar arquivos, bancos, volumes, versões, chaves e estados reais sem iniciar cargas.
- Mapear os IDs das 169 fontes aos aliases e identificar os 47 adaptadores existentes.
- Fixar granularidade, chave de negócio, partição, cobertura, acesso e atualização de cada dataset.

Entregáveis propostos:

- `config/source_aliases.json`
- `config/source_contracts/`
- `audit-results/unification/inventory.json`

Evidência atual:

- [docs/source_registry_br_v1.csv](../../docs/source_registry_br_v1.csv)
- [etl/src/bracc_etl/runner.py](../../etl/src/bracc_etl/runner.py)

Critérios de aceite:

- [ ] 169 IDs cobertos uma vez; nenhum alias ambíguo.
- [ ] Cada dataset piloto tem contrato e partição verificáveis; bloqueios têm causa explícita.

<a id="u02"></a>

## U02 — Identidade e modelo canônico

Backlog existente: [F02 / #3](https://github.com/bdwerlang/brasil-em-rede/issues/3), [F03 / #4](https://github.com/bdwerlang/brasil-em-rede/issues/4), [F09 / #10](https://github.com/bdwerlang/brasil-em-rede/issues/10).

Trabalho:

- Definir IDs opacos persistentes e identificadores com namespace.
- Separar cadastro por raiz, estabelecimento completo, pessoa, observação de sócio e órgão.
- Especificar crosswalks de território, CNAE, códigos de órgão e identificadores de eventos.

Entregáveis propostos:

- `etl/src/bracc_etl/identity/`
- `config/unification/identity_rules.json`
- `etl/tests/test_canonical_identity.py`

Evidência atual:

- [etl/src/bracc_etl/transforms/document_formatting.py](../../etl/src/bracc_etl/transforms/document_formatting.py)
- [etl/src/bracc_etl/pipelines/cnpj.py](../../etl/src/bracc_etl/pipelines/cnpj.py)

Critérios de aceite:

- [ ] Zeros e letras preservados; raiz não fabrica CNPJ completo.
- [ ] Filiais distintas e homônimos com máscara igual permanecem separados.
- [ ] IDs públicos continuam estáveis quando a projeção é reconstruída.

<a id="u03"></a>

## U03 — Persistência e catálogo operacional

Backlog existente: [F04 / #5](https://github.com/bdwerlang/brasil-em-rede/issues/5), [F05 / #6](https://github.com/bdwerlang/brasil-em-rede/issues/6), [F10 / #11](https://github.com/bdwerlang/brasil-em-rede/issues/11).

Trabalho:

- Introduzir PostgreSQL para catálogo de datasets/artefatos, execuções, identidade e releases.
- Definir volumes de bruto e Parquet com caminhos imutáveis e política de acesso.
- Implementar leases por partição, outbox e controle de publicação concorrente.
- Separar schema de aplicação para usuários/investigações/anotações do controle de ingestão; definir migração e backup sem expor hashes ou identificadores sensíveis.

Entregáveis propostos:

- `infra/postgres/migrations/`
- `etl/src/bracc_etl/control/`
- `infra/storage/README.md`

Evidência atual:

- [docker-compose.yml](../../docker-compose.yml)
- [etl/src/bracc_etl/base.py](../../etl/src/bracc_etl/base.py)

Critérios de aceite:

- [ ] Migrations e restore do controle ensaiados; versões fixadas após triagem F00.
- [ ] Dois workers não publicam a mesma partição em concorrência.
- [ ] Arquivo órfão ou outbox pendente não muda a release consultável.

<a id="u04"></a>

## U04 — Aquisição e normalização comuns

Backlog existente: [F05 / #6](https://github.com/bdwerlang/brasil-em-rede/issues/6), [F06 / #7](https://github.com/bdwerlang/brasil-em-rede/issues/7), [F08 / #9](https://github.com/bdwerlang/brasil-em-rede/issues/9).

Trabalho:

- Adaptar os módulos ao contrato adquirir, validar e normalizar sem escrita direta no grafo ativo.
- Gravar bruto íntegro e Parquet tipado com proveniência por registro e rejeições separadas.
- Retomar paginação/partições e aplicar evolução de esquema explícita.

Entregáveis propostos:

- `etl/src/bracc_etl/acquisition/`
- `etl/src/bracc_etl/normalization/`
- `etl/tests/test_normalized_partitions.py`

Evidência atual:

- [etl/src/bracc_etl/base.py](../../etl/src/bracc_etl/base.py)
- [scripts/bootstrap_all/adapters/registry.py](../../scripts/bootstrap_all/adapters/registry.py)

Critérios de aceite:

- [ ] Reexecução do mesmo conteúdo e versão do parser não duplica observações.
- [ ] Leitura reconciliada em aceitos, duplicatas e rejeições; dados vazios inesperados falham.
- [ ] Mudança incompatível de esquema bloqueia a partição, preservando a release anterior.

<a id="u05"></a>

## U05 — Observações, fatos e histórico

Backlog existente: [F04 / #5](https://github.com/bdwerlang/brasil-em-rede/issues/5), [F07 / #8](https://github.com/bdwerlang/brasil-em-rede/issues/8).

Trabalho:

- Separar registro da fonte, versão de observação, evento de negócio e entidade canônica.
- Preservar vigência do fato, data de observação e revisões divergentes.
- Definir evidência de atributos e relações, incluindo localização no artefato original.

Entregáveis propostos:

- `config/unification/fact_contracts/`
- `etl/src/bracc_etl/evidence/`
- `etl/tests/test_fact_revisions.py`

Evidência atual:

- [etl/src/bracc_etl/pipelines/senado_cpis.py](../../etl/src/bracc_etl/pipelines/senado_cpis.py)
- [etl/src/bracc_etl/pipelines/tse.py](../../etl/src/bracc_etl/pipelines/tse.py)

Critérios de aceite:

- [ ] Toda afirmação publicada resolve para fonte, versão, artefato e registro.
- [ ] Duas receitas eleitorais ou contratos distintos não colapsam por mesmo par/ano/valor.
- [ ] Correções e retrações são versionadas; ausência de linha não equivale a revogação.

<a id="u06"></a>

## U06 — Resolução e reconciliação entre fontes

Backlog existente: [F07 / #8](https://github.com/bdwerlang/brasil-em-rede/issues/8), [F09 / #10](https://github.com/bdwerlang/brasil-em-rede/issues/10).

Trabalho:

- Resolver documentos íntegros e IDs oficiais em namespaces definidos.
- Tratar candidatos probabilísticos, conflitos e crosswalks de contratos como estados auditáveis.
- Reconciliar fontes sobrepostas preservando todas as observações e o grão dos fatos.

Entregáveis propostos:

- `etl/src/bracc_etl/identity/resolver.py`
- `config/unification/reconciliation_rules.json`
- `etl/tests/test_cross_source_resolution.py`

Evidência atual:

- [etl/src/bracc_etl/entity_resolution/linker.py](../../etl/src/bracc_etl/entity_resolution/linker.py)
- [etl/src/bracc_etl/pipelines/mides.py](../../etl/src/bracc_etl/pipelines/mides.py)

Critérios de aceite:

- [ ] Homônimo, CPF parcial, geoproximidade e igualdade de valor não geram identidade confirmada.
- [ ] PNCP, Comprasnet e MiDES contam um mesmo contrato somente com chave/crosswalk demonstrado.
- [ ] Cada decisão de ligação pode ser revisada e revertida sem apagar evidência.

<a id="u07"></a>

## U07 — Projeção Neo4j compatível

Backlog existente: [F04 / #5](https://github.com/bdwerlang/brasil-em-rede/issues/5), [F06 / #7](https://github.com/bdwerlang/brasil-em-rede/issues/7).

Trabalho:

- Unificar constraints e manter a projeção derivada de datasets aprovados.
- Projetar entidades e relações canônicas com chaves explícitas e evidência.
- Confirmar transações, propagar falhas e reconciliar contadores sem confundir linhas com nós criados.
- Fazer writers e coordenador de freeze adquirirem o mesmo guard transacional no grafo, verificando estado/epoch/token sob lock antes de gravar; adaptar QSA canônico à raiz LegalEntity.

Entregáveis propostos:

- `infra/neo4j/migrations/`
- `etl/src/bracc_etl/projection/`
- `etl/tests/integration/test_unified_projection.py`

Evidência atual:

- [etl/src/bracc_etl/loader.py](../../etl/src/bracc_etl/loader.py)
- [infra/neo4j/init.cypher](../../infra/neo4j/init.cypher)
- [api/src/bracc/queries/schema_init.cypher](../../api/src/bracc/queries/schema_init.cypher)

Critérios de aceite:

- [ ] Inicialização limpa e atualização dão esquema equivalente.
- [ ] Falha no último lote impede promoção; retry não duplica fatos.
- [ ] Rebuild a partir dos manifestos mantém IDs e resultados do recorte.
- [ ] Worker atrasado após revogação/freeze não confirma escrita; transação iniciada antes da barreira é drenada ou abortada de forma verificável.

<a id="u08"></a>

## U08 — Piloto de entidades e vínculos

Backlog existente: [P01 / #12](https://github.com/bdwerlang/brasil-em-rede/issues/12), [P02 / #13](https://github.com/bdwerlang/brasil-em-rede/issues/13), [P03 / #14](https://github.com/bdwerlang/brasil-em-rede/issues/14).

Trabalho:

- Selecionar recorte público delimitado com estabelecimentos, sanções e contratos.
- Adquirir recursos de contratos/fornecedores, distinguindo publicação de licitação.
- Validar os vínculos positivos e negativos e medir recursos antes de ampliar.

Entregáveis propostos:

- `audit-results/unification/pilot/`
- `etl/tests/integration/test_company_sanction_contract.py`

Evidência atual:

- [etl/src/bracc_etl/pipelines/cnpj.py](../../etl/src/bracc_etl/pipelines/cnpj.py)
- [etl/src/bracc_etl/pipelines/sanctions.py](../../etl/src/bracc_etl/pipelines/sanctions.py)
- [etl/src/bracc_etl/pipelines/pncp.py](../../etl/src/bracc_etl/pipelines/pncp.py)

Critérios de aceite:

- [ ] CNPJ a sanção e fornecedor a contrato reproduzidos com origem e datas.
- [ ] Filiais diferentes e mesmo contrato espelhado exercitados.
- [ ] Bytes, pico de memória, tempo, cobertura e rejeições medidos por partição.
- [ ] QSA por raiz aparece no cadastro correto, sem replicar uma sociedade como fatos independentes de todas as filiais.

<a id="u09"></a>

## U09 — Piloto de séries e geografia

Backlog existente: [F09 / #10](https://github.com/bdwerlang/brasil-em-rede/issues/10), [E01 / #16](https://github.com/bdwerlang/brasil-em-rede/issues/16).

Trabalho:

- Escolher dimensão IBGE e uma série agregada do catálogo com competência explícita.
- Consultar Parquet com DuckDB e ligar métricas ao território/dimensão sem inventar entidades nominais.
- Definir CRS, unidades, versões territoriais e revisões de série.

Entregáveis propostos:

- `etl/src/bracc_etl/analytics/`
- `config/unification/dimensions/`
- `etl/tests/integration/test_territorial_series.py`

Evidência atual:

- [etl/src/bracc_etl/pipelines/siconfi.py](../../etl/src/bracc_etl/pipelines/siconfi.py)
- [etl/src/bracc_etl/pipelines/rais.py](../../etl/src/bracc_etl/pipelines/rais.py)

Critérios de aceite:

- [ ] Agregação reproduz soma/contagem/unidade da fonte no grão correto.
- [ ] Mudança territorial e competência revisada não duplicam série.
- [ ] Mesmo nome de município ou valor de indicador não produz ligação nominal.

<a id="u10"></a>

## U10 — API e interface unificadas

Backlog existente: [P04 / #15](https://github.com/bdwerlang/brasil-em-rede/issues/15), [F02 / #3](https://github.com/bdwerlang/brasil-em-rede/issues/3), [F10 / #11](https://github.com/bdwerlang/brasil-em-rede/issues/11).

Trabalho:

- Servir empresa, fatos, evidências, séries e cobertura pela mesma API com queries parametrizadas.
- Migrar IDs e serializers sem depender de elementId ou da ordem dos labels.
- Fixar release e versão de resolução no início de cada requisição; separar acesso público e restrito.
- Migrar serviços de usuário/investigação/anotação para schema app e manter release nos cursores/expansões, com ordenação estável e expiração explícita.

Entregáveis propostos:

- `api/src/bracc/services/unified_data.py`
- `api/src/bracc/routers/data_releases.py`
- `api/tests/integration/test_unified_release.py`

Evidência atual:

- [api/src/bracc/routers/public.py](../../api/src/bracc/routers/public.py)
- [api/src/bracc/services/intelligence_provider.py](../../api/src/bracc/services/intelligence_provider.py)
- [frontend/src/](../../frontend/src/)

Critérios de aceite:

- [ ] Resposta nunca mistura entidades/arestas de releases distintas.
- [ ] URLs por ID público sobrevivem a rebuild; aliases antigos têm transição testada.
- [ ] Busca, navegação, ausência de resultado, conflito e origem/data funcionam no fluxo de usuário.
- [ ] Paginação atravessa promoção sem trocar bundle; release retirada retorna 410 e reinicia o contexto. Login e edições não escrevem no grafo congelado.

<a id="u11"></a>

## U11 — Migração, publicação e recuperação

Backlog existente: [F03 / #4](https://github.com/bdwerlang/brasil-em-rede/issues/4), [F08 / #9](https://github.com/bdwerlang/brasil-em-rede/issues/9), [F10 / #11](https://github.com/bdwerlang/brasil-em-rede/issues/11).

Trabalho:

- Inventariar e exportar o legado em modo controlado, sem fabricar proveniência ausente.
- Ensaiar backup offline e restore em instância/volume separado.
- Publicar bundle imutável por compare-and-swap e manter rollback para bundle anterior.
- Ensaiar preservação do estado mutável da aplicação e barreira de writers; reter destinos enquanto houver cursores e janela de rollback válidos.

Entregáveis propostos:

- `infra/scripts/migrate-unification.sh`
- `infra/scripts/restore-unification.sh`
- `audit-results/unification/rehearsal/`

Evidência atual:

- [infra/scripts/backup-neo4j.sh](../../infra/scripts/backup-neo4j.sh)
- [docker-compose.yml](../../docker-compose.yml)

Critérios de aceite:

- [ ] Falhas antes/depois da confirmação do grafo e do ponteiro recuperam sem sucesso falso.
- [ ] Restore e rollback preservam IDs, relações e release consultada.
- [ ] Gates e relatório de diferença aprovados antes de qualquer corte de produção.
- [ ] Rebuild e rollback mantêm investigações/anotações e não reativam writers legados sem guard.

<a id="u12"></a>

## U12 — Expansão das 169 fontes e operação

Backlog existente: [E01 / #16](https://github.com/bdwerlang/brasil-em-rede/issues/16).

Trabalho:

- Executar oito ondas existentes com contratos e mapas individuais desta unificação.
- Separar descoberta, acesso condicionado, fontes derivadas e ingestão factual.
- Habilitar os 21 cruzamentos apenas após dependências, evidências e testes de endpoint.

Entregáveis propostos:

- `config/unification/source_readiness.json`
- `audit-results/unification/coverage/`
- `docs/unification/operations.md`

Evidência atual:

- [docs/implementation/source_matrix.csv](../../docs/implementation/source_matrix.csv)
- [config/source_implementation_plan.json](../../config/source_implementation_plan.json)

Critérios de aceite:

- [ ] 169 fontes têm destino e estado explícitos; acesso restrito não vira cobertura pública.
- [ ] Nenhuma fonte pronta sem download, carga e vínculos demonstrados separadamente.
- [ ] Freshness, não resolvidos, falhas, custos e capacidade são acompanhados por fonte e partição.
