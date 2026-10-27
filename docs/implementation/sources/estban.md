# estban — BCB ESTBAN balances

Registrar saldos bancários por município, instituição/agência e rubrica como observações agregadas.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `estban`.
- Ordem topológica: **61**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://dadosabertos.bcb.gov.br/dataset/estban](https://dadosabertos.bcb.gov.br/dataset/estban).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Identificador e situação real da fonte; atualizar apenas após implementação e carga comprovadas.
- [etl/src/bracc_etl/base.py](../../../etl/src/bracc_etl/base.py): Contrato Pipeline.extract/transform/load e rastreamento IngestionRun.
- [etl/src/bracc_etl/loader.py](../../../etl/src/bracc_etl/loader.py): Carga por lotes, MERGE e repetição de falhas.
- [scripts/bootstrap_all/adapters/registry.py](../../../scripts/bootstrap_all/adapters/registry.py): Aquisição por script_download ou file_manifest; blocked_external/blocked_credentials explícitos.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato de entradas e preparação a ampliar.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Labels, constraints e índices existentes; incluir migração para labels propostos.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.bcb.gov.br/estatisticas/estatisticabancariamunicipios](https://www.bcb.gov.br/estatisticas/estatisticabancariamunicipios) | Publicação ESTBAN com arquivos por município e agência. | Página oficial BCB localizada; periodicidade e defasagem documentadas; URL final dos arquivos a resolver. |
| [https://dadosabertos.bcb.gov.br/dataset/estban](https://dadosabertos.bcb.gov.br/dataset/estban) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Enumerar arquivos mensais da página e guardar leiaute COSIF/4500; implementar adaptador por versão de leiaute.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** Arquivos oficiais compactados/tabulares conforme leiaute a confirmar
- **Partições e backfill:** Data-base mensal × tipo (município ou agência)
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Mensal, revisitando os seis últimos meses; confirmar disponibilidade do histórico.

Limites e pré-condições:

- Defasagem documentada 60 dias, dezembro 90; revisões dos seis meses publicados; agregado municipal e detalhe por agência não são dados aditivos.

## Contrato de ingestão

**Entrada esperada:** data/estban/raw/<partição>/ com bytes originais e manifest.json; data_base, rubrica, saldo, código de instituição, código territorial e tipo de relatório; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** estban_id=source_id+data_base+tipo+código_instituição/agência+código_município+rubrica

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.
- Projetar dimensões comuns conforme F09: Territory.territory_id=sistema:tipo:codigo:versao_territorial; EconomicActivity.activity_id=classificacao:versao:codigo; PublicBody.public_body_id=jurisdicao:sistema:identificador:versao. Aplicar somente as dimensões usadas nesta fonte, preservar códigos originais e validar crosswalks; município é Territory, sem dimensão paralela incompatível.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `BankingObservation` | observation_id | proposed |
| `Territory` | territory_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `BankingObservation` → `OBSERVED_IN` → `Territory` | crosswalk oficial BCB→IBGE | Sem inferir cliente ou correntista individual. | proposed |
| `BankingObservation` → `REPORTED_BY` → `Company` | código BCB→CNPJ por tabela oficial | Somente quando a dimensão de instituição trouxer CNPJ exato. | proposed |
| `BankingObservation` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_estban.py`
- `etl/src/bracc_etl/pipelines/estban.py`
- `etl/src/bracc_etl/schemas/estban.py`
- `etl/tests/test_estban_pipeline.py`
- `docs/source-runbooks/estban.md`

Tarefas específicas, em ordem:

1. Resolver recursos de município e de agência e baixar um exemplar de cada; documentar códigos territoriais BCB e correspondência IBGE.
1. Mapear mudança de rubricas/leiaute; impedir soma simultânea de agregado municipal e detalhe por agência.
1. Implementar aquisição com timeout, backoff para 429/5xx, escrita atômica e manifesto por partição (URL final, parâmetros, retrieved_at, ETag/Last-Modified quando presentes, SHA-256, tamanho e cobertura). Guardar segredos apenas no ambiente.
1. Implementar validação e quarentena com motivo por linha; adaptar Pipeline e Neo4jBatchLoader, preservar SourceDocument/IngestionRun e separar tempo do fato, publicação e captura.
1. Adicionar constraints/índices das chaves propostas e atualizar mapeamento de entidades/consultas da API para os novos labels e relações antes de considerá-los navegáveis; preservar distinção entre vínculos exatos e referências pendentes.
1. Registrar no runner, contrato bootstrap e catálogo; criar fixtures pequenas representativas, caso de retomada e dupla carga; liberar carga histórica só após reconciliação do piloto.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto de uma partição com cobertura declarada, contagem de entrada = aceitas + rejeitadas e rejeições justificadas.
- [ ] Duas cargas do mesmo bruto não duplicam nós/arestas; interrupção retomada sem perda; alteração legítima preserva histórico.
- [ ] Arestas nominais exigem documento integral ou ID oficial resolvido; nome ou documento parcial geram apenas pendência de resolução.
- [ ] Saldo por município/rubrica reproduz arquivo oficial; agências e municípios não são contados duas vezes.
- [ ] Uma agência e agregado municipal da mesma data-base permanecem recortes distintos; soma analítica não inclui as duas tabelas simultaneamente.

## Riscos e decisões pendentes

- ESTBAN contém agregados, não lista de beneficiários de crédito.

## Evidências e referências

- [https://www.bcb.gov.br/estatisticas/estatisticabancariamunicipios](https://www.bcb.gov.br/estatisticas/estatisticabancariamunicipios)
- `docs/source_registry_br_v1.csv`
- [https://www.bcb.gov.br/content/estabilidadefinanceira/cosif_leiautes/4500V1.pdf](https://www.bcb.gov.br/content/estabilidadefinanceira/cosif_leiautes/4500V1.pdf)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
