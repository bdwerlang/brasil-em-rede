# anac_aviation_concessions — ANAC concessions

Cadastrar concessões aeroportuárias, blocos, aeroportos e respectivas concessionárias e aditivos.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `anac_aviation_concessions`.
- Ordem topológica: **39**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dados.gov.br/dados/conjuntos-dados/anac](https://dados.gov.br/dados/conjuntos-dados/anac).

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
| [https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/certificacao-e-outorga/dados-gerais-das-concessoes-de-aeroportos](https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/certificacao-e-outorga/dados-gerais-das-concessoes-de-aeroportos) | Metadados oficiais do conjunto de concessões e ligação CSV/JSON. | Página localizada; recurso final de distribuição a descobrir e validar. |
| [https://dados.gov.br/dados/conjuntos-dados/anac](https://dados.gov.br/dados/conjuntos-dados/anac) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Resolver recurso CSV/JSON de dados gerais; complementar contratos publicados na área de concessões; evitar AECO administrativo autenticado.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** CSV/JSON e PDFs contratuais públicos
- **Partições e backfill:** Rodada/bloco × contrato × aeroporto × snapshot
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- Página de metadados localizada é de 2022; URL CSV/JSON ainda depende de piloto. AECO administrativo não é endpoint público de lote.

## Contrato de ingestão

**Entrada esperada:** data/anac_aviation_concessions/raw/<partição>/ com bytes originais e manifest.json; contrato, concessionária/CNPJ publicado, rodada/bloco, aeroportos, vigência e situação; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** airport_concession_id=ANAC+numero_contrato+ano; airport_id=ICAO oficial

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `AirportConcession` | concession_id | proposed |
| `Airport` | airport_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `HOLDS_CONCESSION` → `AirportConcession` | CNPJ contratual integral | Aditivos e transferências com vigência. | proposed |
| `AirportConcession` → `COVERS_AIRPORT` → `Airport` | código ICAO oficial | Não assumir relação um contrato/um aeroporto. | proposed |
| `AirportConcession` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_anac_aviation_concessions.py`
- `etl/src/bracc_etl/pipelines/anac_aviation_concessions.py`
- `etl/src/bracc_etl/schemas/anac_aviation_concessions.py`
- `etl/tests/test_anac_aviation_concessions_pipeline.py`
- `docs/source-runbooks/anac_aviation_concessions.md`

Tarefas específicas, em ordem:

1. Seguir recurso estruturado e validar schema atual; descobrir lista de aeroportos concedidos e contratos oficiais.
1. Modelar um contrato para vários aeroportos do bloco; distinguir relicitação e troca de operador de duplicação de concessão.
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
- [ ] Contrato de bloco liga vários aeroportos ICAO sem replicar valor global para somatório por aeroporto.
- [ ] Uma relicitação/troca de operador preserva versão e titular; recurso legado indisponível mantém gate de descoberta.

## Riscos e decisões pendentes

- Página de 2022 pode apontar recurso legado; API não testada.

## Evidências e referências

- [https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/certificacao-e-outorga/dados-gerais-das-concessoes-de-aeroportos](https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/certificacao-e-outorga/dados-gerais-das-concessoes-de-aeroportos)
- `docs/source_registry_br_v1.csv`
- [https://www.gov.br/anac/pt-br/assuntos/concessoes](https://www.gov.br/anac/pt-br/assuntos/concessoes)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
