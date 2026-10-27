# anatel_telecom_licenses — ANATEL licenses

Cadastrar prestadoras, autorizações de serviço e licenças de estação como entidades regulatórias distintas.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `anatel_telecom_licenses`.
- Ordem topológica: **40**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dados.gov.br/dados/conjuntos-dados/anatel](https://dados.gov.br/dados/conjuntos-dados/anatel).

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
| [https://www.gov.br/anatel/pt-br/dados](https://www.gov.br/anatel/pt-br/dados) | Entrada oficial de dados da Anatel a resolver para painel/catálogo atual. | Página oficial Dados consultada em 26/10/2026; menu de dados/painéis/outorga existe. Ligação oficial Acesso à Informação→Dados Abertos retornou 404; recurso de exportação continua não validado. |
| [https://dados.gov.br/dados/conjuntos-dados/anatel](https://dados.gov.br/dados/conjuntos-dados/anatel) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Descobrir no portal oficial o catálogo de outorgas/prestadoras e licenças; validar os recursos e seus dicionários; não tratar dados de acessos como relação de licenças.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** CSV/ZIP de prestadoras/outorgas/estações conforme descoberta
- **Partições e backfill:** Serviço (SCM/SMP/STFC etc.) × snapshot × UF para estações
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- Link oficial Dados Abertos retornou 404; recurso de licenças/outorgas não validado. Painéis de acessos não substituem atos/licenças.

## Contrato de ingestão

**Entrada esperada:** data/anatel_telecom_licenses/raw/<partição>/ com bytes originais e manifest.json; ato/licença, tipo de serviço, CNPJ público da prestadora, estação/código, situação e vigência; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** telecom_license_id=ANATEL+servico+numero_ato/licenca+estacao_quando_aplicavel

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `TelecomAuthorization` | authorization_id | proposed |
| `TelecomStation` | station_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `HOLDS_TELECOM_AUTHORIZATION` → `TelecomAuthorization` | CNPJ integral publicado | Não usar quantidade municipal de acessos para inferir usuários. | proposed |
| `TelecomAuthorization` → `LICENSES_STATION` → `TelecomStation` | ID licença/estação oficial | Apenas associação explicitamente fornecida. | proposed |
| `TelecomAuthorization` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_anatel_telecom_licenses.py`
- `etl/src/bracc_etl/pipelines/anatel_telecom_licenses.py`
- `etl/src/bracc_etl/schemas/anatel_telecom_licenses.py`
- `etl/tests/test_anatel_telecom_licenses_pipeline.py`
- `docs/source-runbooks/anatel_telecom_licenses.md`

Tarefas específicas, em ordem:

1. Resolver índice de dados Anatel e identificar conjuntos exatos de outorgas e licenças; manter bloqueio de publicação enquanto não houver arquivo piloto.
1. Distinguir outorga de radiodifusão do MCom, licença de estação da Anatel e autorização de telecomunicação; registrar sucessão/transferência.
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
- [ ] Fixture distingue autorização de serviço, licença de estação e quantidade de acessos; acessos não viram licença.
- [ ] Link 404 não fica implementado; aquisição só libera após recurso real e dicionário registrados.

## Riscos e decisões pendentes

- Portal dadosabertos.anatel.gov.br não pôde ser consultado pela ferramenta; origem genérica do catálogo precisa ser substituída após descoberta.
- Link https://www.gov.br/anatel/pt-br/acesso-a-informacao/dados-abertos retornou 404 nesta consulta; descobrir distribuição atual pelos links de dados/painéis/outorga.

## Evidências e referências

- [https://www.gov.br/anatel/pt-br/dados](https://www.gov.br/anatel/pt-br/dados)
- `docs/source_registry_br_v1.csv`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
