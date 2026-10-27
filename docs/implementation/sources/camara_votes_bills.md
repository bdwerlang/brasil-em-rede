# camara_votes_bills — Camara votes and bills

Cadastrar proposições, autoria, tramitação e votos nominais da Câmara com IDs legislativos e papel exato de cada votação.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `camara_votes_bills`.
- Ordem topológica: **28**; onda de execução: **3**; prioridade temática inicial: 3.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [camara](camara.md)
- Contrato de acesso catalogado: [https://dadosabertos.camara.leg.br/api/v2](https://dadosabertos.camara.leg.br/api/v2).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Identificador e situação real da fonte; atualizar apenas após implementação e carga comprovadas.
- [etl/src/bracc_etl/base.py](../../../etl/src/bracc_etl/base.py): Contrato Pipeline.extract/transform/load e rastreamento IngestionRun.
- [etl/src/bracc_etl/loader.py](../../../etl/src/bracc_etl/loader.py): Carga por lotes, MERGE e repetição de falhas.
- [scripts/bootstrap_all/adapters/registry.py](../../../scripts/bootstrap_all/adapters/registry.py): Aquisição por script_download ou file_manifest; blocked_external/blocked_credentials explícitos.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato de entradas e preparação a ampliar.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Labels, constraints e índices existentes; incluir migração para labels propostos.
- [etl/src/bracc_etl/pipelines/camara.py](../../../etl/src/bracc_etl/pipelines/camara.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dadosabertos.camara.leg.br/swagger/api.html](https://dadosabertos.camara.leg.br/swagger/api.html) | Swagger oficial da API v2 com proposicoes/votacoes/votos. | Documentação oficial consultada e nota oficial de cobertura/dados de votação. |
| [https://dadosabertos.camara.leg.br/api/v2](https://dadosabertos.camara.leg.br/api/v2) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** GET API v2 seguindo links de paginação; histórico por arquivos anuais de votações/votos quando oferecidos; buscar detalhe/autores/tramitações incrementalmente.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** JSON API e CSV anual público
- **Partições e backfill:** Ano × proposição/votação; janelas de publicação para incremento; detalhe pelo ID
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial daily; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- Somente votos nominais registrados/publicáveis podem ser atribuídos a deputados; IDs/objetos de votação podem refletir inconsistências manuais documentadas.

## Contrato de ingestão

**Entrada esperada:** data/camara_votes_bills/raw/<partição>/ com bytes originais e manifest.json; IDs proposição/votação/deputado, tipo/ano, data, orientação, voto, autoria e resultado; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** bill_id=CAMARA+id_proposicao; voting_id=CAMARA+id_votacao; voto=voting_id+id_deputado+registro_oficial

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
| `Parliamentarian` → `CAST_VOTE` → `LegislativeVote` | ID deputado+ID votação | Ausência de voto não significa ausência na sessão; sem voto individual inferido em simbólica. | proposed |
| `LegislativeVote` → `AFFECTS_BILL` → `LegislativeBill` | ID proposição expressamente retornado | Guardar papel objeto/afetada/possível objeto. | proposed |
| `Parliamentarian` → `IDENTIFIED_AS` → `Person` | idDeputado→CPF oficial | Somente resolução exata com origem. | proposed |
| `LegislativeBill` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_camara_votes_bills.py`
- `etl/src/bracc_etl/pipelines/camara_votes_bills.py`
- `etl/src/bracc_etl/schemas/camara_votes_bills.py`
- `etl/tests/test_camara_votes_bills_pipeline.py`
- `docs/source-runbooks/camara_votes_bills.md`

Tarefas específicas, em ordem:

1. Mapear /proposicoes, /votacoes, /votacoes/{id}/votos e autores; distinguir proposição objeto, afetada e possível objeto.
1. Reusar mapa idDeputado→CPF do pipeline camara; nome/partido não resolvem parlamentar; separar orientações partidárias de voto individual.
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
- [ ] Proposição objeto, afetada e possível objeto são papéis distintos; voto não informado não vira ausência.
- [ ] ID deputado resolve Person somente via CPF oficial; orientação de liderança não gera voto individual.

## Riscos e decisões pendentes

- Uma votação pode afetar várias proposições e ter objeto apenas presumido; conservar o papel informado.
- Voto não registrado e votação simbólica não significam ausência; deduplicação por IDs deve respeitar inconsistências documentadas da origem.

## Evidências e referências

- [https://dadosabertos.camara.leg.br/swagger/api.html](https://dadosabertos.camara.leg.br/swagger/api.html)
- `docs/source_registry_br_v1.csv`
- `etl/src/bracc_etl/pipelines/camara.py`
- [https://dadosabertos.camara.leg.br/howtouse/2020-02-07-dados-votacoes.html](https://dadosabertos.camara.leg.br/howtouse/2020-02-07-dados-votacoes.html)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
