# if_data — BCB IF data indicators

Ingerir indicadores trimestrais de instituições e conglomerados do IFData com sua unidade e nível de consolidação.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `if_data`.
- Ordem topológica: **64**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dadosabertos.bcb.gov.br/dataset/if-data](https://dadosabertos.bcb.gov.br/dataset/if-data).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Identificador e situação real da fonte; atualizar apenas após implementação e carga comprovadas.
- [etl/src/bracc_etl/base.py](../../../etl/src/bracc_etl/base.py): Contrato Pipeline.extract/transform/load e rastreamento IngestionRun.
- [etl/src/bracc_etl/loader.py](../../../etl/src/bracc_etl/loader.py): Carga por lotes, MERGE e repetição de falhas.
- [scripts/bootstrap_all/adapters/registry.py](../../../scripts/bootstrap_all/adapters/registry.py): Aquisição por script_download ou file_manifest; blocked_external/blocked_credentials explícitos.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato de entradas e preparação a ampliar.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Labels, constraints e índices existentes; incluir migração para labels propostos.
- [etl/src/bracc_etl/pipelines/bcb.py](../../../etl/src/bracc_etl/pipelines/bcb.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dadosabertos.bcb.gov.br/dataset/ifdata---dados-selecionados-de-instituies-financeiras](https://dadosabertos.bcb.gov.br/dataset/ifdata---dados-selecionados-de-instituies-financeiras) | Catálogo oficial corrigido do IFData; links para Swagger e OData. | Catálogo oficial consultado; slug if-data do registro local não é o conjunto localizado. |
| [https://dadosabertos.bcb.gov.br/dataset/if-data](https://dadosabertos.bcb.gov.br/dataset/if-data) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Descobrir endpoint OData pelo recurso do catálogo; guardar metadados de instituições, relatórios e lista de contas antes dos valores.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** JSON OData bruto com metadados/relatórios
- **Partições e backfill:** Trimestre × relatório × tipo de instituição/consolidação; páginas conforme serviço
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial quarterly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- Publicação trimestral com defasagem 60 dias, dezembro 90; instituição individual e conglomerado são recortes distintos e precisam de metadados do relatório.

## Contrato de ingestão

**Entrada esperada:** data/if_data/raw/<partição>/ com bytes originais e manifest.json; data-base, código de instituição/conglomerado, relatório, conta, unidade, valor; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** ifdata_observation_id=data_base+tipo_consolidacao+codigo_instituicao+codigo_relatorio+codigo_conta

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `FinancialInstitution` | institution_id | proposed |
| `InstitutionIndicator` | indicator_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `FinancialInstitution` → `HAS_INDICATOR` → `InstitutionIndicator` | código IFData+nível+data_base | Indicador não é operação financeira nominal. | proposed |
| `FinancialInstitution` → `REPRESENTS` → `Company` | CNPJ oficial integral | Não usar nome do conglomerado como CNPJ de uma instituição. | proposed |
| `FinancialInstitution` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_if_data.py`
- `etl/src/bracc_etl/pipelines/if_data.py`
- `etl/src/bracc_etl/schemas/if_data.py`
- `etl/tests/test_if_data_pipeline.py`
- `docs/source-runbooks/if_data.md`

Tarefas específicas, em ordem:

1. Seguir links oficiais de OData/Swagger e fixar o schema em fixture; testar uma instituição individual e um conglomerado.
1. Criar dimensão própria para conglomerado; somente associar Company quando crosswalk oficial fornecer CNPJ.
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
- [ ] Instituição individual e conglomerado do mesmo trimestre têm chaves distintas e não são somados sem regra metodológica.
- [ ] Um relatório/conta/trimestre reproduz IFData com unidade, zero, ausência e versão da publicação.

## Riscos e decisões pendentes

- Misturar conglomerado e instituição individual duplica valores; manter nível de consolidação na chave.
- Slug legado if-data não resolve o catálogo localizado; o endpoint OData final ainda deve ser validado.

## Evidências e referências

- [https://dadosabertos.bcb.gov.br/dataset/ifdata---dados-selecionados-de-instituies-financeiras](https://dadosabertos.bcb.gov.br/dataset/ifdata---dados-selecionados-de-instituies-financeiras)
- `docs/source_registry_br_v1.csv`
- `etl/src/bracc_etl/pipelines/bcb.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
