# susep_insurance_market — SUSEP insurance market

Cadastrar supervisionadas SUSEP e estatísticas públicas de seguros por companhia/período, mantendo dados internos fora do escopo.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `susep_insurance_market`.
- Ordem topológica: **71**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dados.gov.br/dados/conjuntos-dados/susep](https://dados.gov.br/dados/conjuntos-dados/susep).

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
| [https://www.gov.br/susep/pt-br/acesso-a-informacao/dados-abertos](https://www.gov.br/susep/pt-br/acesso-a-informacao/dados-abertos) | Página oficial de conjuntos de dados e PDA vigente. | Página oficial consultada, modificada em 30/09/2026; PDA 2026–2028 indicado. |
| [https://dados.gov.br/dados/conjuntos-dados/susep](https://dados.gov.br/dados/conjuntos-dados/susep) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Descobrir cadastro de supervisionadas e extrações públicas de estatística; confirmar se dado tem identificação empresarial ou apenas agregado de mercado.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** CSV/ZIP/XLSX público conforme conjunto; dicionários de códigos SUSEP
- **Partições e backfill:** Snapshot cadastral × companhia × competência × ramo/indicador
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- PDA não comprova disponibilidade de cada dataset; SAPIEMS interno não pode ser tratado como distribuição aberta.

## Contrato de ingestão

**Entrada esperada:** data/susep_insurance_market/raw/<partição>/ com bytes originais e manifest.json; código SUSEP, CNPJ publicado, situação; indicadores com período, ramo e unidade; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** insurer_id=SUSEP+codigo_supervisionada; indicador=companhia+periodo+ramo+codigo_indicador+unidade

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Insurer` | insurer_id | proposed |
| `InsuranceObservation` | observation_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Insurer` → `REPRESENTS` → `Company` | CNPJ integral oficial | Código regulatório preservado. | proposed |
| `Insurer` → `HAS_OBSERVATION` → `InsuranceObservation` | código SUSEP+período | Nenhum segurado individual inferido de agregado. | proposed |
| `Insurer` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_susep_insurance_market.py`
- `etl/src/bracc_etl/pipelines/susep_insurance_market.py`
- `etl/src/bracc_etl/schemas/susep_insurance_market.py`
- `etl/tests/test_susep_insurance_market_pipeline.py`
- `docs/source-runbooks/susep_insurance_market.md`

Tarefas específicas, em ordem:

1. Mapear conjuntos efetivamente abertos no PDA 2026–2028; não presumir acesso ao SAPIEMS interno.
1. Baixar cadastro e um período de estatística pública; distinguir seguradora, ressegurador, previdência aberta e capitalização.
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
- [ ] Companhia/ramo/indicador/período reproduz extrato com unidade; agregado de mercado não cria segurado.
- [ ] Base só prevista no PDA permanece descoberta pendente; código SUSEP resolve CNPJ apenas por correspondência oficial.

## Riscos e decisões pendentes

- PDA histórico distingue SAPIEMS interno de bases abertas; disponibilidade de cada extração deve ser comprovada.

## Evidências e referências

- [https://www.gov.br/susep/pt-br/acesso-a-informacao/dados-abertos](https://www.gov.br/susep/pt-br/acesso-a-informacao/dados-abertos)
- `docs/source_registry_br_v1.csv`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
