# antt_transport_concessions — ANTT concessions

Cadastrar concessões rodoviárias e ferroviárias com contratos, concessionárias e vigência.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `antt_transport_concessions`.
- Ordem topológica: **43**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dados.gov.br/dados/conjuntos-dados/antt](https://dados.gov.br/dados/conjuntos-dados/antt).

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
| [https://dados.antt.gov.br/group/rodovias](https://dados.antt.gov.br/group/rodovias) | Catálogo oficial ANTT do tema rodovias; descobrir também concessões ferroviárias. | Catálogo localizado; novos projetos ainda não licitados não equivalem a contratos vigentes. |
| [https://dados.gov.br/dados/conjuntos-dados/antt](https://dados.gov.br/dados/conjuntos-dados/antt) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Enumerar datasets de contratos de concessão e municípios/trechos; usar arquivos por tema e dicionário; complementar documentos contratuais oficiais.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** CSV/ZIP e PDFs de contratos quando vinculados
- **Partições e backfill:** Modal × contrato/concessão × snapshot ou ano
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- Tema rodovias não substitui ferrovias; dataset de novos projetos contém casos sem licitação/contrato vigente.

## Contrato de ingestão

**Entrada esperada:** data/antt_transport_concessions/raw/<partição>/ com bytes originais e manifest.json; contrato, concessionária/CNPJ publicado, trecho/ativo, datas e situação; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** transport_concession_id=ANTT+modal+numero_contrato+ano+titular_original

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `TransportConcession` | concession_id | proposed |
| `TransportAsset` | asset_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `HOLDS_CONCESSION` → `TransportConcession` | CNPJ integral do titular | Datas de transferência e aditivos próprios. | proposed |
| `TransportConcession` → `COVERS_ASSET` → `TransportAsset` | ID trecho/lote/ferrovia oficial | Vínculo geográfico não indica contratação local. | proposed |
| `TransportConcession` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_antt_transport_concessions.py`
- `etl/src/bracc_etl/pipelines/antt_transport_concessions.py`
- `etl/src/bracc_etl/schemas/antt_transport_concessions.py`
- `etl/tests/test_antt_transport_concessions_pipeline.py`
- `docs/source-runbooks/antt_transport_concessions.md`

Tarefas específicas, em ordem:

1. Separar contratos vigentes, encerrados, relicitação e projetos não licitados; conferir titular e número no documento contratual.
1. Mapear rodovia/trecho/km e ferrovia com identificadores oficiais; não somar investimentos autorizados como pagamentos.
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
- [ ] Projeto não licitado não cria concessão vigente; contrato com vários trechos conserva uma concessão e múltiplos ativos.
- [ ] Aditivo/troca de concessionária preserva base contratual e datas; km/rodovia/ferrovia têm referência oficial explícita.

## Riscos e decisões pendentes

- Novos projetos não licitados não possuem contrato vigente; não tratá-los como concessões contratadas.
- Catálogo de rodovias não cobre automaticamente ferrovias; arquivos de investimentos e contratos podem ter chaves diferentes.

## Evidências e referências

- [https://dados.antt.gov.br/group/rodovias](https://dados.antt.gov.br/group/rodovias)
- `docs/source_registry_br_v1.csv`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
