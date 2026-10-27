# ana_water_grants — ANA water grants

Ingerir outorgas de uso de água, pontos de interferência, usos e titulares publicados, distinguindo domínio federal e estadual.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `ana_water_grants`.
- Ordem topológica: **72**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dados.gov.br/dados/conjuntos-dados/ana](https://dados.gov.br/dados/conjuntos-dados/ana).

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
| [https://www.snirh.gov.br/portal/snirh-1/acesso-tematico/regulacao-e-fiscalizacao](https://www.snirh.gov.br/portal/snirh-1/acesso-tematico/regulacao-e-fiscalizacao) | Índice oficial SNIRH para outorgas federais, estaduais, mapa, metadados e planilhas. | Página oficial consultada; planilha/serviço geográfico final a resolver. |
| [https://dados.gov.br/dados/conjuntos-dados/ana](https://dados.gov.br/dados/conjuntos-dados/ana) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Seguir dados abertos/planilha de outorgas; descobrir serviço geográfico pelo metadado; usar exportação pública e evitar plataforma de solicitação autenticada.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** CSV/XLSX e dados geoespaciais conforme recurso
- **Partições e backfill:** Autoridade emissora/domínio × UF × snapshot
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- ANA federal não cobre todas as outorgas estaduais; plataforma de solicitação Gov.br não é fonte pública de terceiros.

## Contrato de ingestão

**Entrada esperada:** data/ana_water_grants/raw/<partição>/ com bytes originais e manifest.json; autoridade, ato, usuário público/documento quando liberado, uso, vazão, ponto, vigência e CRS; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** water_grant_id=autoridade+numero_ato+ano+ponto_interferencia; preservar ID original CNARH quando público

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `WaterGrant` | grant_id | proposed |
| `WaterUsePoint` | point_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `HOLDS_WATER_GRANT` → `WaterGrant` | CNPJ integral publicado | Sem acesso a dados não públicos do requerimento. | proposed |
| `WaterGrant` → `APPLIES_TO_POINT` → `WaterUsePoint` | ID oficial do ponto+autoridade | Interseção espacial não prova domínio do imóvel. | proposed |
| `WaterGrant` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_ana_water_grants.py`
- `etl/src/bracc_etl/pipelines/ana_water_grants.py`
- `etl/src/bracc_etl/schemas/ana_water_grants.py`
- `etl/tests/test_ana_water_grants_pipeline.py`
- `docs/source-runbooks/ana_water_grants.md`

Tarefas específicas, em ordem:

1. Resolver planilha de outorgas emitidas e recursos estaduais; documentar cobertura de cada autoridade.
1. Distinguir preventiva, direito de uso e DRDH; normalizar vazões/unidades e pontos múltiplos do mesmo ato.
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
- [ ] Ponto com CRS/coordenada inválidos é rejeitado; L/s e m³/s permanecem unidades explicitadas.
- [ ] Número igual de outorga federal/estadual não colide; usuário sem documento integral publicado permanece não resolvido.

## Riscos e decisões pendentes

- ANA não representa todas as outorgas estaduais; não declarar cobertura nacional completa sem inventário.

## Evidências e referências

- [https://www.snirh.gov.br/portal/snirh-1/acesso-tematico/regulacao-e-fiscalizacao](https://www.snirh.gov.br/portal/snirh-1/acesso-tematico/regulacao-e-fiscalizacao)
- `docs/source_registry_br_v1.csv`
- [https://www.gov.br/ana/pt-br/assuntos/regulacao-e-fiscalizacao/outorga/solicite-sua-outorga](https://www.gov.br/ana/pt-br/assuntos/regulacao-e-fiscalizacao/outorga/solicite-sua-outorga)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
