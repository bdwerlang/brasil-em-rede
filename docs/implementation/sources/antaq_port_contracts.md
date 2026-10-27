# antaq_port_contracts — ANTAQ contracts

Cadastrar arrendamentos, concessões e autorizações portuárias com instalação, titular e histórico contratual.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `antaq_port_contracts`.
- Ordem topológica: **42**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dados.gov.br/dados/conjuntos-dados/antaq](https://dados.gov.br/dados/conjuntos-dados/antaq).

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
| [https://www.gov.br/antaq/pt-br/acesso-a-informacao/dados-abertos](https://www.gov.br/antaq/pt-br/acesso-a-informacao/dados-abertos) | Portal oficial ANTAQ com bases programadas para abertura e dados de instalações/outorgas. | Página oficial consultada; recurso estruturado específico de contratos ainda precisa ser localizado. |
| [https://dados.gov.br/dados/conjuntos-dados/antaq](https://dados.gov.br/dados/conjuntos-dados/antaq) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Descobrir recursos públicos em bases do PDA e painéis de portos/instalações; registrar quais tabelas são contratos, termos de autorização e estatística aquaviária.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** CSV/XLSX público ou metadados+PDF conforme inventário; formato final pendente
- **Partições e backfill:** Tipo de instrumento × instalação × snapshot/ano
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- PDA/portal não é API de contratos; conjunto de arrendamento/concessão/autorização e seu recurso de lote ainda devem ser localizados.

## Contrato de ingestão

**Entrada esperada:** data/antaq_port_contracts/raw/<partição>/ com bytes originais e manifest.json; número instrumento, tipo, instalação, titular, datas, objeto e situação; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** port_instrument_id=ANTAQ+tipo+numero+ano+instalacao_oficial

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `PortInstrument` | instrument_id | proposed |
| `PortFacility` | facility_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `HOLDS_PORT_INSTRUMENT` → `PortInstrument` | CNPJ contratual integral | Natureza e período conforme documento. | proposed |
| `PortInstrument` → `COVERS_FACILITY` → `PortFacility` | código oficial instalação+porto | Movimentação de carga não gera vínculo contratual. | proposed |
| `PortInstrument` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_antaq_port_contracts.py`
- `etl/src/bracc_etl/pipelines/antaq_port_contracts.py`
- `etl/src/bracc_etl/schemas/antaq_port_contracts.py`
- `etl/tests/test_antaq_port_contracts_pipeline.py`
- `docs/source-runbooks/antaq_port_contracts.md`

Tarefas específicas, em ordem:

1. Inventariar bases de arrendamento, concessão e autorização; registrar URL final e schema antes de habilitar coleta.
1. Validar empresa e vigência no instrumento; distinguir operador portuário, arrendatário, terminal privado e autoridade portuária.
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
- [ ] Piloto demonstra número/tipo/titular/instalação; sem recurso nominal a aquisição permanece pendente, sem carga fictícia.
- [ ] Arrendamento, autorização e concessão mantêm tipos distintos; movimentação de carga não gera relação contratual.

## Riscos e decisões pendentes

- Dataset genérico do catálogo não é endpoint de consulta; extração depende de descoberta do recurso correto.

## Evidências e referências

- [https://www.gov.br/antaq/pt-br/acesso-a-informacao/dados-abertos](https://www.gov.br/antaq/pt-br/acesso-a-informacao/dados-abertos)
- `docs/source_registry_br_v1.csv`
- [https://www.gov.br/antaq/pt-br/acesso-a-informacao/dados-abertos/disponibilizacao-das-bases-de-dados-programadas-para-abertura-no-pda](https://www.gov.br/antaq/pt-br/acesso-a-informacao/dados-abertos/disponibilizacao-das-bases-de-dados-programadas-para-abertura-no-pda)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
