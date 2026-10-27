# ans_health_plans — ANS operators

Cadastrar operadoras ativas/canceladas e sua trajetória regulatória pelo registro ANS e CNPJ.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `ans_health_plans`.
- Ordem topológica: **3**; onda de execução: **1**; prioridade temática inicial: 1.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **M**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dados.gov.br/dados/conjuntos-dados/ans](https://dados.gov.br/dados/conjuntos-dados/ans).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Identificador e situação real da fonte; atualizar apenas após implementação e carga comprovadas.
- [etl/src/bracc_etl/base.py](../../../etl/src/bracc_etl/base.py): Contrato Pipeline.extract/transform/load e rastreamento IngestionRun.
- [etl/src/bracc_etl/loader.py](../../../etl/src/bracc_etl/loader.py): Carga por lotes, MERGE e repetição de falhas.
- [scripts/bootstrap_all/adapters/registry.py](../../../scripts/bootstrap_all/adapters/registry.py): Aquisição por script_download ou file_manifest; blocked_external/blocked_credentials explícitos.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato de entradas e preparação a ampliar.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Labels, constraints e índices existentes; incluir migração para labels propostos.
- [etl/src/bracc_etl/pipelines/datasus.py](../../../etl/src/bracc_etl/pipelines/datasus.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude_ativas/](https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude_ativas/) | Diretório oficial com Relatorio_cadop.csv e dicionário. | Listagem oficial consultada; arquivo de ativas atualizado em 26/10/2026. |
| [https://dados.gov.br/dados/conjuntos-dados/ans](https://dados.gov.br/dados/conjuntos-dados/ans) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Baixar CADOP e descobrir diretório de canceladas; guardar snapshot para histórico; indicadores assistenciais/financeiros são subproduto separado.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** CSV CADOP e PDF de dicionário
- **Partições e backfill:** Snapshot × situação (ativa/cancelada)
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- CADOP de ativas é snapshot, não histórico completo; canceladas exigem recurso complementar e registro ANS é chave distinta do CNPJ.

## Contrato de ingestão

**Entrada esperada:** data/ans_health_plans/raw/<partição>/ com bytes originais e manifest.json; Registro ANS, CNPJ, razão social, modalidade, UF e data de registro/cancelamento quando disponível; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** operator_id=ANS+registro_ANS; snapshot_id=operator_id+data_base

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `HealthPlanOperator` | operator_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `HealthPlanOperator` → `REPRESENTS` → `Company` | CNPJ integral CADOP | Preservar registro ANS como chave distinta do CNPJ. | proposed |
| `HealthPlanOperator` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_ans_health_plans.py`
- `etl/src/bracc_etl/pipelines/ans_health_plans.py`
- `etl/src/bracc_etl/schemas/ans_health_plans.py`
- `etl/tests/test_ans_health_plans_pipeline.py`
- `docs/source-runbooks/ans_health_plans.md`

Tarefas específicas, em ordem:

1. Mapear CADOP e canceladas e validar unicidade do registro; tratar mudanças de razão social e endereço como histórico.
1. Associar Company pelo CNPJ integral; nenhum nó de beneficiário de plano deve ser criado a partir de agregados.
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
- [ ] Registro ANS e CNPJ são chaves distintas; cadastro ativo/cancelado não duplica operador.
- [ ] Cancelamento exige evidência e data; desaparecer de um snapshot não basta para cancelar operador.

## Riscos e decisões pendentes

- Snapshot de operadoras ativas não informa sozinho o histórico de cancelamentos; obter distribuição complementar.
- Registro ANS não é CNPJ; múltiplos cadastros podem exigir relação temporal e tabela oficial de correspondência.

## Evidências e referências

- [https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude_ativas/](https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude_ativas/)
- `docs/source_registry_br_v1.csv`
- `etl/src/bracc_etl/pipelines/datasus.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
