# mapbiomas_alertas — MapBiomas Alerta

Ingerir alertas publicados e laudos com geometria, versão e cruzamentos ambientais explícitos.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `mapbiomas_alertas`.
- Ordem topológica: **104**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Acesso condicionado / restrito**; complexidade relativa: **XL**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://alerta.mapbiomas.org/api](https://alerta.mapbiomas.org/api).

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
| [https://plataforma.alerta.mapbiomas.org/api/docs/index.html](https://plataforma.alerta.mapbiomas.org/api/docs/index.html) | Documentação oficial GraphQL V2 e exportação alertReport. | Documentação consultada confirma endpoint /api/v2/graphql, conta verificada e Bearer Token; V1 descontinuada. |
| [https://alerta.mapbiomas.org/api](https://alerta.mapbiomas.org/api) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Usar GraphQL V2: alerts para índice paginado e alert por alertCode; preferir exportação documentada para carga histórica; cachear laudos e geometrias.
- **Autenticação:** Conta MapBiomas Alerta com email verificado e Bearer Token obtido pelo mecanismo documentado; não há conta de serviço segundo documentação.
- **Formato bruto:** JSON GraphQL bruto + CSV/SHP exportado quando disponibilizado
- **Partições e backfill:** Publicação mensal/semanal × UF/território × página; usar data de publicação além da data de detecção
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- GraphQL V2 exige conta verificada e Bearer Token; não há conta de serviço documentada. Default de 100 registros por página; máximo/quotas efetivos ainda a medir.

## Contrato de ingestão

**Entrada esperada:** data/mapbiomas_alertas/raw/<partição>/ com bytes originais e manifest.json; alertCode, detecção, publicação, área, geometria/CRS, situação e CARs/UCs explicitamente cruzados; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** environmental_alert_id=MAPBIOMAS+alertCode; versão=publicado/statusAt+checksum

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `EnvironmentalAlert` | alert_id | proposed |
| `RuralParcel` | parcel_id | proposed |
| `ProtectedArea` | protected_area_id | proposed |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `EnvironmentalAlert` → `INTERSECTS_PARCEL` → `RuralParcel` | código CAR publicado ou interseção geométrica calculada | Relação espacial com área/CRS/data/método; não atribui autoria do desmate. | proposed |
| `EnvironmentalAlert` → `INTERSECTS_PROTECTED_AREA` → `ProtectedArea` | ID CNUC ou crosswalk oficial | Conservar área sobreposta e versões das geometrias. | proposed |
| `EnvironmentalAlert` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_mapbiomas_alertas.py`
- `etl/src/bracc_etl/pipelines/mapbiomas_alertas.py`
- `etl/src/bracc_etl/schemas/mapbiomas_alertas.py`
- `etl/tests/test_mapbiomas_alertas_pipeline.py`
- `docs/source-runbooks/mapbiomas_alertas.md`

Tarefas específicas, em ordem:

1. Configurar conta/token fornecido legitimamente sem gravar segredo; validar query mínima e token expirado.
1. Distinguir republicação, remoção e novo alerta; guardar referência de laudo e métricas de interseção com CAR/UC/embargo.
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
- [ ] Token ausente/expirado gera blocked_credentials; segredo não aparece em manifesto/log.
- [ ] Republicação preserva alertCode e versões; interseção guarda área/CRS/método e não atribui infrator.

## Riscos e decisões pendentes

- Aquisição autenticada aguarda token; acesso à API não foi exercido.
- Alerta e sobreposição não demonstram infrator ou ilegalidade.

## Evidências e referências

- [https://plataforma.alerta.mapbiomas.org/api/docs/index.html](https://plataforma.alerta.mapbiomas.org/api/docs/index.html)
- `docs/source_registry_br_v1.csv`
- [https://plataforma.alerta.mapbiomas.org/api/v2/graphql](https://plataforma.alerta.mapbiomas.org/api/v2/graphql)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
