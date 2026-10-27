# cnciai_improbidade — CNIAI improbidade

Integrar condenações públicas por improbidade e inelegibilidade com situação processual e vigência das penas.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `cnciai_improbidade`.
- Ordem topológica: **111**; onda de execução: **6**; prioridade temática inicial: 6.
- Tipo de trabalho: **Acesso condicionado / restrito**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://www.cnj.jus.br/sistemas/cnciai/](https://www.cnj.jus.br/sistemas/cnciai/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Identificador e situação real da fonte; atualizar apenas após implementação e carga comprovadas.
- [etl/src/bracc_etl/base.py](../../../etl/src/bracc_etl/base.py): Contrato Pipeline.extract/transform/load e rastreamento IngestionRun.
- [etl/src/bracc_etl/loader.py](../../../etl/src/bracc_etl/loader.py): Carga por lotes, MERGE e repetição de falhas.
- [scripts/bootstrap_all/adapters/registry.py](../../../scripts/bootstrap_all/adapters/registry.py): Aquisição por script_download ou file_manifest; blocked_external/blocked_credentials explícitos.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato de entradas e preparação a ampliar.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Labels, constraints e índices existentes; incluir migração para labels propostos.
- [etl/src/bracc_etl/pipelines/datajud.py](../../../etl/src/bracc_etl/pipelines/datajud.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.cnj.jus.br/programas-e-acoes/combate-a-corrupcao-enccla/cadastro-nacional-de-condenados-por-crimes-de-improbidade-administrativa/](https://www.cnj.jus.br/programas-e-acoes/combate-a-corrupcao-enccla/cadastro-nacional-de-condenados-por-crimes-de-improbidade-administrativa/) | Página oficial atual do cadastro e consultas públicas. | CNJ confirma consultas por processo, nome e CPF/CNPJ; não foi localizada API pública de carga em massa. |
| [https://www.cnj.jus.br/sistemas/cnciai/](https://www.cnj.jus.br/sistemas/cnciai/) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Gate de descoberta: verificar exportação pública e documentar licença, captcha e cobertura; aceitar importação de arquivo oficial obtido legitimamente. Se exigir desafio humano, manter aquisição manual e bloqueio explícito.
- **Autenticação:** Consulta pública pode conter captcha; acesso de alimentação é restrito. Não automatizar captcha nem usar perfil de magistrado.
- **Formato bruto:** A confirmar: exportação oficial estruturada; HTML/PDF de consulta somente com rastreio
- **Partições e backfill:** Tribunal × ano de julgamento × snapshot/exportação autorizada
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- Nenhuma API pública de lote foi comprovada; consulta pode exigir desafio humano. Se houver captcha, manter aquisição manual e blocked_external, sem contorno.

## Contrato de ingestão

**Entrada esperada:** data/cnciai_improbidade/raw/<partição>/ com bytes originais e manifest.json; ID/processo, órgão, parte pública, tipo de decisão, penas e datas; não presumir trânsito em julgado; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** conviction_id=ID_oficial_do_cadastro; fallback processo+órgão+tipo_decisao+data+parte_identificada

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `JudicialConviction` | conviction_id | proposed |
| `JudicialCase` | judicial_case_id | existing |
| `Person` | cpf | existing |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `JudicialConviction` → `IN_CASE` → `JudicialCase` | número CNJ integral ou ID do processo com tribunal | Não unificar números antigos sem tabela oficial. | proposed |
| `Person` → `SUBJECT_OF` → `JudicialConviction` | CPF integral publicado | Sem resolver identidade por nome. | proposed |
| `Company` → `SUBJECT_OF` → `JudicialConviction` | CNPJ integral publicado | Preservar pena e vigência individual. | proposed |
| `JudicialConviction` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_cnciai_improbidade.py`
- `etl/src/bracc_etl/pipelines/cnciai_improbidade.py`
- `etl/src/bracc_etl/schemas/cnciai_improbidade.py`
- `etl/tests/test_cnciai_improbidade_pipeline.py`
- `docs/source-runbooks/cnciai_improbidade.md`

Tarefas específicas, em ordem:

1. Validar acesso público atual e se existe lote/exportação; registrar endpoint não validado e evidência do bloqueio quando houver.
1. Distinguir condenação de primeiro grau/colegiada/trânsito, suspensão, recursos e fim de inelegibilidade; preparar importador mesmo com captura manual.
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
- [ ] Sem bypass de desafios; sem transformar consulta sem resultado em certidão de inexistência de condenação.
- [ ] Decisão colegiada e trânsito em julgado permanecem distintos; pena expirada/suspensa não vira proibição vigente.
- [ ] Nome/documento parcial não resolve Person; captcha/indisponibilidade vira bloqueio, sem afirmar carga concluída.

## Riscos e decisões pendentes

- Aquisição em massa não comprovada; endpoint antigo do catálogo não validado.

## Evidências e referências

- [https://www.cnj.jus.br/programas-e-acoes/combate-a-corrupcao-enccla/cadastro-nacional-de-condenados-por-crimes-de-improbidade-administrativa/](https://www.cnj.jus.br/programas-e-acoes/combate-a-corrupcao-enccla/cadastro-nacional-de-condenados-por-crimes-de-improbidade-administrativa/)
- `docs/source_registry_br_v1.csv`
- `etl/src/bracc_etl/pipelines/datajud.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
