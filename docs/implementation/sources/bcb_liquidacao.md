# bcb_liquidacao — BCB bank liquidation acts

Registrar atos e vigências de regimes especiais das instituições financeiras, distinguindo intervenção, liquidação e RAET.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `bcb_liquidacao`.
- Ordem topológica: **46**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **M**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dadosabertos.bcb.gov.br/dataset/intervencao-e-liquidacao](https://dadosabertos.bcb.gov.br/dataset/intervencao-e-liquidacao).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Identificador e situação real da fonte; atualizar apenas após implementação e carga comprovadas.
- [etl/src/bracc_etl/base.py](../../../etl/src/bracc_etl/base.py): Contrato Pipeline.extract/transform/load e rastreamento IngestionRun.
- [etl/src/bracc_etl/loader.py](../../../etl/src/bracc_etl/loader.py): Carga por lotes, MERGE e repetição de falhas.
- [scripts/bootstrap_all/adapters/registry.py](../../../scripts/bootstrap_all/adapters/registry.py): Aquisição por script_download ou file_manifest; blocked_external/blocked_credentials explícitos.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato de entradas e preparação a ampliar.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Labels, constraints e índices existentes; incluir migração para labels propostos.
- [etl/src/bracc_etl/pipelines/bcb.py](../../../etl/src/bracc_etl/pipelines/bcb.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.bcb.gov.br/estabilidadefinanceira/consulta_regesp](https://www.bcb.gov.br/estabilidadefinanceira/consulta_regesp) | Consulta oficial de instituições sob regimes de resolução com opções CSV e JSON. | Página oficial localizada; recurso final do botão CSV/JSON ainda não testado. |
| [https://dadosabertos.bcb.gov.br/dataset/intervencao-e-liquidacao](https://dadosabertos.bcb.gov.br/dataset/intervencao-e-liquidacao) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Resolver a exportação pública e coletar situação atual; complementar atos/histórico apenas por arquivos oficiais vinculados.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** CSV ou JSON exportado + atos oficiais quando públicos
- **Partições e backfill:** Snapshot de instituições e evento por CNPJ/data/ato
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- CSV/JSON de posição atual foi identificado na consulta, mas recurso final e cobertura completa de atos históricos ainda não foram validados.

## Contrato de ingestão

**Entrada esperada:** data/bcb_liquidacao/raw/<partição>/ com bytes originais e manifest.json; CNPJ, nome, regime, início, encerramento e situação; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** resolution_regime_id=CNPJ+tipo_regime+data_inicio+numero_ato_se_publicado

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `ResolutionRegime` | regime_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `SUBJECT_TO_REGIME` → `ResolutionRegime` | CNPJ integral | Vínculo por ato e intervalo; sem inferir condenação ou culpa de administradores. | proposed |
| `ResolutionRegime` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_bcb_liquidacao.py`
- `etl/src/bracc_etl/pipelines/bcb_liquidacao.py`
- `etl/src/bracc_etl/schemas/bcb_liquidacao.py`
- `etl/tests/test_bcb_liquidacao_pipeline.py`
- `docs/source-runbooks/bcb_liquidacao.md`

Tarefas específicas, em ordem:

1. Mapear exportações e localizar o identificador/data do ato; conferir um regime encerrado e uma mudança de regime.
1. Preservar intervalos e situação sem converter regime de resolução em sanção por corrupção.
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
- [ ] Mudança de intervenção para liquidação preserva dois atos/intervalos; regime encerrado não aparece como vigente após a data final.
- [ ] Nenhuma aresta de sanção/condenação é criada apenas pela existência de regime de resolução.

## Riscos e decisões pendentes

- Snapshot atual pode não conter todos os atos históricos.

## Evidências e referências

- [https://www.bcb.gov.br/estabilidadefinanceira/consulta_regesp](https://www.bcb.gov.br/estabilidadefinanceira/consulta_regesp)
- `docs/source_registry_br_v1.csv`
- `etl/src/bracc_etl/pipelines/bcb.py`
- [https://www.bcb.gov.br/estabilidadefinanceira/resolucao](https://www.bcb.gov.br/estabilidadefinanceira/resolucao)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
