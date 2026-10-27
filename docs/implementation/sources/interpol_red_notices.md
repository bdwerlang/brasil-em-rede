# interpol_red_notices — Interpol red notices

Registrar apenas notices vermelhas publicadas para acesso público, com situação e proveniência, sem inferir culpa ou identidade brasileira por nome.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `interpol_red_notices`.
- Ordem topológica: **116**; onda de execução: **6**; prioridade temática inicial: 6.
- Tipo de trabalho: **Acesso condicionado / restrito**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://www.interpol.int/How-we-work/Notices/Red-Notices](https://www.interpol.int/How-we-work/Notices/Red-Notices).

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
| [https://www.interpol.int/How-we-work/Notices/Red-Notices](https://www.interpol.int/How-we-work/Notices/Red-Notices) | Descrição oficial e acesso à lista de notices públicas. | Página oficial consultada; red notice é alerta a pedido de país/tribunal, não mandado de prisão internacional; interface de lote não validada. |

- **Método:** Gate de aquisição: revisar termos e existência de exportação/API pública documentada; usar importador de arquivo público autorizado se não houver contrato de lote. Não usar rede policial I-24/7, endpoints privados ou contornar WAF/captcha.
- **Autenticação:** Somente conteúdo público; acesso policial restrito excluído.
- **Formato bruto:** A confirmar: JSON/exportação pública ou metadados HTML com URL e checksum
- **Partições e backfill:** País/nacionalidade publicada × snapshot; nunca presumir que o subconjunto público representa todas as notices
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial weekly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- Não comprovada API/exportação pública de lote; notices públicas são subconjunto. Excluir rede policial e contorno de WAF/captcha.

## Contrato de ingestão

**Entrada esperada:** data/interpol_red_notices/raw/<partição>/ com bytes originais e manifest.json; notice_id, país requisitante, nome original, nacionalidade pública, nascimento público, natureza/status e URL; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** interpol_notice_id=identificador oficial público; não nome/data_nascimento

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `PublicNotice` | notice_id | proposed |
| `NoticeSubject` | subject_id | proposed |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `NoticeSubject` → `SUBJECT_OF_NOTICE` → `PublicNotice` | ID oficial público de notice/sujeito | Não criar Person.cpf nem apontar candidato/servidor por semelhança nominal. | proposed |
| `PublicNotice` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_interpol_red_notices.py`
- `etl/src/bracc_etl/pipelines/interpol_red_notices.py`
- `etl/src/bracc_etl/schemas/interpol_red_notices.py`
- `etl/tests/test_interpol_red_notices_pipeline.py`
- `docs/source-runbooks/interpol_red_notices.md`

Tarefas específicas, em ordem:

1. Validar termos e mecanismo público de aquisição; documentar ausência de API suportada como bloqueio e não prometer download completo.
1. Modelar NoticeSubject por ID de origem; atualizar retirada/cancelamento, impedir busca nominal automática em pessoas brasileiras.
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
- [ ] Retirada/cancelamento refletida na visão corrente; nenhuma fusão automática com Person por nome.
- [ ] Sem contrato público de aquisição validado, a ficha permanece bloqueada; lista pública não é rotulada como todas as notices existentes.

## Riscos e decisões pendentes

- Lote/API pública não comprovada; WAF pode impedir automação.
- Publicação é parcial e uma notice não equivale a condenação.

## Evidências e referências

- [https://www.interpol.int/How-we-work/Notices/Red-Notices](https://www.interpol.int/How-we-work/Notices/Red-Notices)
- `docs/source_registry_br_v1.csv`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
