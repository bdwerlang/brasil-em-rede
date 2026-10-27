# carf_tax_appeals — CARF tax appeals

Cadastrar acórdãos e eventos públicos do CARF distinguindo contencioso administrativo de processos judiciais.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `carf_tax_appeals`.
- Ordem topológica: **110**; onda de execução: **6**; prioridade temática inicial: 6.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://carf.economia.gov.br/dados-abertos](https://carf.economia.gov.br/dados-abertos).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Identificador e situação real da fonte; atualizar apenas após implementação e carga comprovadas.
- [etl/src/bracc_etl/base.py](../../../etl/src/bracc_etl/base.py): Contrato Pipeline.extract/transform/load e rastreamento IngestionRun.
- [etl/src/bracc_etl/loader.py](../../../etl/src/bracc_etl/loader.py): Carga por lotes, MERGE e repetição de falhas.
- [scripts/bootstrap_all/adapters/registry.py](../../../scripts/bootstrap_all/adapters/registry.py): Aquisição por script_download ou file_manifest; blocked_external/blocked_credentials explícitos.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato de entradas e preparação a ampliar.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Labels, constraints e índices existentes; incluir migração para labels propostos.
- [etl/src/bracc_etl/pipelines/stj_dados_abertos.py](../../../etl/src/bracc_etl/pipelines/stj_dados_abertos.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://carf.economia.gov.br/dados-abertos](https://carf.economia.gov.br/dados-abertos) | Página legada oficial de dados abertos e ligação para dados gerenciais/pesquisa de acórdãos. | Página consultada se identifica como Antigo Site do CARF; atualização da origem precisa ser descoberta. |

- **Método:** Resolver site atual gov.br, datasets de acórdãos e arquivos gerenciais; separar estatísticas agregadas de decisões nominais; PDF exige parser com documento bruto.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** CSV/XLSX gerencial e metadados/inteiro teor de acórdãos conforme recurso localizado
- **Partições e backfill:** Ano × turma/câmara × data de sessão ou publicação
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- Página consultada é do site antigo do CARF; distribuição atual pendente. Bases gerenciais podem ser agregadas e omitir contribuinte/inteiro teor.

## Contrato de ingestão

**Entrada esperada:** data/carf_tax_appeals/raw/<partição>/ com bytes originais e manifest.json; processo administrativo, acórdão, colegiado, sessão, resultado e identificação pública da parte quando publicada; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** tax_appeal_id=CARF+numero_processo; decisao=numero_acordao+data_sessao+versao

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `TaxAppealCase` | case_id | proposed |
| `TaxAppealDecision` | decision_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `TaxAppealCase` → `HAS_DECISION` → `TaxAppealDecision` | número processo administrativo oficial | Cada versão de acórdão com situação e data. | proposed |
| `Company` → `PARTY_TO` → `TaxAppealCase` | CNPJ integral publicamente fornecido | Contencioso não comprova infração ou dívida exigível. | proposed |
| `TaxAppealCase` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_carf_tax_appeals.py`
- `etl/src/bracc_etl/pipelines/carf_tax_appeals.py`
- `etl/src/bracc_etl/schemas/carf_tax_appeals.py`
- `etl/tests/test_carf_tax_appeals_pipeline.py`
- `docs/source-runbooks/carf_tax_appeals.md`

Tarefas específicas, em ordem:

1. Inventariar exportações e schema atual; testar se dados gerenciais incluem contribuinte/documento ou apenas totais.
1. Criar TaxAppealCase próprio; registrar acórdãos anulados/retificados e PDFs com checksum; não usar JudicialCase sem tipo administrativo explícito.
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
- [ ] Acórdão retificado mantém versão anterior e relação de substituição; número administrativo não recebe formatação CNJ.
- [ ] Base gerencial agregada não cria Company-PARTY_TO; apenas CNPJ integral publicado permite vínculo nominal.

## Riscos e decisões pendentes

- Dados fiscais ou partes podem ser omitidos; não completar por homônimo.

## Evidências e referências

- [https://carf.economia.gov.br/dados-abertos](https://carf.economia.gov.br/dados-abertos)
- `docs/source_registry_br_v1.csv`
- `etl/src/bracc_etl/pipelines/stj_dados_abertos.py`
- [https://acordaos.economia.gov.br/](https://acordaos.economia.gov.br/)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
