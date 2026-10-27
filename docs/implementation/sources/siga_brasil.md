# siga_brasil — SIGA Brasil

Cadastrar execução orçamentária federal com trilha LOA/emenda/ação e estágios financeiros reconciliados.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `siga_brasil`.
- Ordem topológica: **21**; onda de execução: **2**; prioridade temática inicial: 2.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **XL**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://www12.senado.leg.br/orcamento/sigabrasil](https://www12.senado.leg.br/orcamento/sigabrasil).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Identificador e situação real da fonte; atualizar apenas após implementação e carga comprovadas.
- [etl/src/bracc_etl/base.py](../../../etl/src/bracc_etl/base.py): Contrato Pipeline.extract/transform/load e rastreamento IngestionRun.
- [etl/src/bracc_etl/loader.py](../../../etl/src/bracc_etl/loader.py): Carga por lotes, MERGE e repetição de falhas.
- [scripts/bootstrap_all/adapters/registry.py](../../../scripts/bootstrap_all/adapters/registry.py): Aquisição por script_download ou file_manifest; blocked_external/blocked_credentials explícitos.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato de entradas e preparação a ampliar.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Labels, constraints e índices existentes; incluir migração para labels propostos.
- [etl/src/bracc_etl/pipelines/siop.py](../../../etl/src/bracc_etl/pipelines/siop.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.
- [etl/src/bracc_etl/pipelines/tesouro_emendas.py](../../../etl/src/bracc_etl/pipelines/tesouro_emendas.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www12.senado.leg.br/orcamento/sigabrasil](https://www12.senado.leg.br/orcamento/sigabrasil) | Página oficial de acesso público ao SIGA Brasil Painéis/Relatórios. | Página consultada informa atualização para SAP BusinessObjects BI 2025 em 27/07/2026 e acesso público/especialista na mesma base. |

- **Método:** Descobrir exportação pública suportada na versão atual; fixar consulta/universo/filtros de extração; aceitar CSV de relatório público manual enquanto não houver exportação automatizável documentada.
- **Autenticação:** Acesso público sem perfil especialista; se exportação exigir conta, manter bloqueio documentado e importação pública manual.
- **Formato bruto:** CSV/XLSX exportado de relatório e definição de consulta
- **Partições e backfill:** Exercício LOA × universo × período execução × UO/UG; restos a pagar separados
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- SAP BO migrou em 27/07/2026; exportação suportada precisa de descoberta. Limite de linhas/universo/filtro pode truncar relatório; comprovar completude.

## Contrato de ingestão

**Entrada esperada:** data/siga_brasil/raw/<partição>/ com bytes originais e manifest.json; dimensões orçamentárias, período, estágio, valor e parâmetros da consulta; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** budget_execution_id=exercicio+esfera+UO+UG+programa+acao+localizador+fonte+natureza+RP+autor/emenda_quando_existir+periodo+estagio

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
| `BudgetExecution` | execution_id | proposed |
| `Amendment` | amendment_id | existing |
| `PublicBody` | public_body_id | proposed |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `BudgetExecution` → `EXECUTED_BY` → `PublicBody` | UG/UO oficial+esfera+exercício | Sem substituir UG por nome. | proposed |
| `Amendment` → `HAS_EXECUTION` → `BudgetExecution` | código oficial emenda+exercício | Somente em níveis com identificador comum; agregados não viram contrato. | proposed |
| `BudgetExecution` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_siga_brasil.py`
- `etl/src/bracc_etl/pipelines/siga_brasil.py`
- `etl/src/bracc_etl/schemas/siga_brasil.py`
- `etl/tests/test_siga_brasil_pipeline.py`
- `docs/source-runbooks/siga_brasil.md`

Tarefas específicas, em ordem:

1. Inventariar universos e exportação após migração BI 2025; produzir consulta reexecutável de um exercício/órgão e documentar limites de linhas.
1. Conciliar empenhado/liquidado/pago e RAP com siop/tesouro_emendas; não somar fontes espelho como despesas adicionais.
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
- [ ] Totais empenhado, liquidado, pago e RAP por UG/exercício conferem com exportação oficial de mesmos filtros/data-base.
- [ ] Truncamento é detectado por contagem/totalizador; dividir consulta e comprovar completude antes de fechar partição.

## Riscos e decisões pendentes

- SAP BO atualizado em julho/2026; receita antiga de scraping pode estar incompatível.
- Granularidade varia por universo e relatório.

## Evidências e referências

- [https://www12.senado.leg.br/orcamento/sigabrasil](https://www12.senado.leg.br/orcamento/sigabrasil)
- `docs/source_registry_br_v1.csv`
- `etl/src/bracc_etl/pipelines/siop.py`
- `etl/src/bracc_etl/pipelines/tesouro_emendas.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
