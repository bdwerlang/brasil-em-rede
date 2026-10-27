# senado_votes_bills — Senado votes and bills

Cadastrar processos legislativos e votos do Senado com transição dos endpoints de matéria legados para o modelo atual.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `senado_votes_bills`.
- Ordem topológica: **32**; onda de execução: **3**; prioridade temática inicial: 3.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [senado](senado.md)
- Contrato de acesso catalogado: [https://legis.senado.leg.br/dadosabertos](https://legis.senado.leg.br/dadosabertos).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Identificador e situação real da fonte; atualizar apenas após implementação e carga comprovadas.
- [etl/src/bracc_etl/base.py](../../../etl/src/bracc_etl/base.py): Contrato Pipeline.extract/transform/load e rastreamento IngestionRun.
- [etl/src/bracc_etl/loader.py](../../../etl/src/bracc_etl/loader.py): Carga por lotes, MERGE e repetição de falhas.
- [scripts/bootstrap_all/adapters/registry.py](../../../scripts/bootstrap_all/adapters/registry.py): Aquisição por script_download ou file_manifest; blocked_external/blocked_credentials explícitos.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato de entradas e preparação a ampliar.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Labels, constraints e índices existentes; incluir migração para labels propostos.
- [etl/src/bracc_etl/pipelines/senado.py](../../../etl/src/bracc_etl/pipelines/senado.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://legis.senado.leg.br/dadosabertos/api-docs/swagger-ui/index.html](https://legis.senado.leg.br/dadosabertos/api-docs/swagger-ui/index.html) | OpenAPI oficial de processos/votações legislativas. | Swagger consultado: serviços /materia e plenario antigos marcados deprecated; /processo e /votacao são atuais. |
| [https://legis.senado.leg.br/dadosabertos](https://legis.senado.leg.br/dadosabertos) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Usar endpoints atuais /processo e /votacao conforme parâmetros do OpenAPI; adotar legados só para lacunas históricas com crosswalk documentado.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** JSON/XML conforme serviço; preservar schema e versão de endpoint
- **Partições e backfill:** Período × processo legislativo × votação; comissões separadas do plenário
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial daily; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- Múltiplos endpoints matéria/plenario estão deprecated; cobertura histórica no modelo processo/votacao deve ser comprovada.

## Contrato de ingestão

**Entrada esperada:** data/senado_votes_bills/raw/<partição>/ com bytes originais e manifest.json; ID processo, códigos de matéria legada quando presentes, parlamentar, votação, data, voto e resultado; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** bill_id=SENADO+id_processo; voting_id=SENADO+ID_votacao_oficial; voto=votacao+codigo_parlamentar

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `LegislativeBill` | bill_id | proposed |
| `LegislativeVote` | vote_id | proposed |
| `Parliamentarian` | parliamentarian_id | proposed |
| `Person` | cpf | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Parliamentarian` → `CAST_VOTE` → `LegislativeVote` | código parlamentar+votação | Manter data e exercício de mandato. | proposed |
| `LegislativeVote` → `AFFECTS_BILL` → `LegislativeBill` | ID oficial processo/matéria mapeado | Não unir com proposição da Câmara só por número/ementa. | proposed |
| `Parliamentarian` → `IDENTIFIED_AS` → `Person` | mapeamento oficial código→CPF | CPF parcial/nome não autoriza fusão. | proposed |
| `LegislativeBill` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_senado_votes_bills.py`
- `etl/src/bracc_etl/pipelines/senado_votes_bills.py`
- `etl/src/bracc_etl/schemas/senado_votes_bills.py`
- `etl/tests/test_senado_votes_bills_pipeline.py`
- `docs/source-runbooks/senado_votes_bills.md`

Tarefas específicas, em ordem:

1. Fixar schema atual e identificar campos de paginação/filtro; construir crosswalk matéria→processo quando oferecido.
1. Reusar códigos de senadores, mapear titular/suplente e mandato em cada data; distinguir plenário, comissões, vetos e orientação de bancada.
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
- [ ] Fixture mapeia matéria legada→processo atual sem unir apenas por número; endpoints atuais são padrão.
- [ ] Titular/suplente conservam códigos e mandato em cada data; votação simbólica não gera voto nominal.

## Riscos e decisões pendentes

- Remodelagem legislativa depreca múltiplos endpoints; validar cobertura histórica.

## Evidências e referências

- [https://legis.senado.leg.br/dadosabertos/api-docs/swagger-ui/index.html](https://legis.senado.leg.br/dadosabertos/api-docs/swagger-ui/index.html)
- `docs/source_registry_br_v1.csv`
- `etl/src/bracc_etl/pipelines/senado.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
