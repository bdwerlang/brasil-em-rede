# icmbio_cnuc — ICMBio CNUC units

Cadastrar unidades de conservação do CNUC, seus órgãos gestores, atos e limites oficiais por versão.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `icmbio_cnuc`.
- Ordem topológica: **94**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://www.icmbio.gov.br/portal/faunabrasileira/cadastro-nacional-de-unidades-de-conservacao](https://www.icmbio.gov.br/portal/faunabrasileira/cadastro-nacional-de-unidades-de-conservacao).

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
| [https://dados.mma.gov.br/dataset/unidadesdeconservacao](https://dados.mma.gov.br/dataset/unidadesdeconservacao) | Catálogo oficial MMA com CSV, polígonos e dicionários CNUC. | Catálogo consultado contém recursos 2026_03/2026_07; CNUC é gerido pelo MMA e inclui esferas além do ICMBio. |
| [https://www.icmbio.gov.br/portal/faunabrasileira/cadastro-nacional-de-unidades-de-conservacao](https://www.icmbio.gov.br/portal/faunabrasileira/cadastro-nacional-de-unidades-de-conservacao) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Enumerar recursos CSV e SHP da mesma data-base; complementar plataforma cnuc.mma.gov.br quando necessário; preservar conjuntos anteriores.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** CSV + ZIP com SHP e dicionários
- **Partições e backfill:** Data-base × esfera/categoria; parear atributos e geometrias da mesma edição
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- CSV e SHP podem ter edições diferentes; apenas parear mesma data-base. Snapshot de UCs ativas não cobre automaticamente unidades extintas.

## Contrato de ingestão

**Entrada esperada:** data/icmbio_cnuc/raw/<partição>/ com bytes originais e manifest.json; código CNUC, nome, categoria, esfera, órgão gestor, ato, data e geometria; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** protected_area_id=código CNUC; versão=data_base+checksum

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
| `ProtectedArea` | protected_area_id | proposed |
| `PublicBody` | public_body_id | proposed |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `PublicBody` → `MANAGES_PROTECTED_AREA` → `ProtectedArea` | código de órgão gestor e ato na origem | Gestão não equivale a propriedade. | proposed |
| `ProtectedArea` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_icmbio_cnuc.py`
- `etl/src/bracc_etl/pipelines/icmbio_cnuc.py`
- `etl/src/bracc_etl/schemas/icmbio_cnuc.py`
- `etl/tests/test_icmbio_cnuc_pipeline.py`
- `docs/source-runbooks/icmbio_cnuc.md`

Tarefas específicas, em ordem:

1. Corrigir descoberta para MMA/CNUC; confirmar código estável e correspondência CSV/SHP; não tratar todas UCs como federais.
1. Validar CRS/área, atos de criação/alteração e situação; disponibilizar interseções com alertas, CAR e ANM como relações espaciais propostas.
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
- [ ] Cada polígono corresponde ao código e edição do CSV; divergência de data-base bloqueia cruzamentos espaciais.
- [ ] UC estadual/municipal não é atribuída automaticamente ao ICMBio; órgão gestor e ato devem coincidir com origem.

## Riscos e decisões pendentes

- CSV e SHP podem ter datas diferentes; pareamento incorreto gera falsas interseções.

## Evidências e referências

- [https://dados.mma.gov.br/dataset/unidadesdeconservacao](https://dados.mma.gov.br/dataset/unidadesdeconservacao)
- `docs/source_registry_br_v1.csv`
- [https://www.gov.br/mma/pt-br/assuntos/biodiversidade-e-biomas/areas-protegidas/plataforma-cnuc-1](https://www.gov.br/mma/pt-br/assuntos/biodiversidade-e-biomas/areas-protegidas/plataforma-cnuc-1)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
