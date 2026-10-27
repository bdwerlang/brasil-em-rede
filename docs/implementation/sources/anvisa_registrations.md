# anvisa_registrations — ANVISA products

Cadastrar registros públicos de medicamentos, produtos para saúde e demais classes selecionadas, com titular e situação regulatória.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `anvisa_registrations`.
- Ordem topológica: **80**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dados.gov.br/dados/conjuntos-dados/anvisa](https://dados.gov.br/dados/conjuntos-dados/anvisa).

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
| [https://dados.anvisa.gov.br/dados/](https://dados.anvisa.gov.br/dados/) | Diretório oficial com medicamentos, produtos para saúde, restrições e dicionários. | Listagem oficial consultada; DADOS_ABERTOS_MEDICAMENTOS.csv e TA_PRODUTO_SAUDE_SITE.csv encontrados. |
| [https://dados.gov.br/dados/conjuntos-dados/anvisa](https://dados.gov.br/dados/conjuntos-dados/anvisa) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Enumerar explicitamente arquivos de registro por classe; não carregar toda a pasta sem classificar finalidade, sobretudo notificações sanitárias.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** CSV por classe e documentação correspondente
- **Partições e backfill:** Classe de produto × snapshot; arquivo grande lido em chunks
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- Diretório reúne registros e notificações de finalidades diferentes; arquivos de modelos podem exceder 1GB e precisam de leitura em chunks.

## Contrato de ingestão

**Entrada esperada:** data/anvisa_registrations/raw/<partição>/ com bytes originais e manifest.json; registro, processo, classe, produto, titular/documento publicado, situação e datas; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** product_registration_id=ANVISA+classe+registro+apresentacao/modelo_se_integrar_a_chave

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `ProductRegistration` | registration_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `HOLDS_REGISTRATION` → `ProductRegistration` | CNPJ integral do titular na fonte | Não atribuir fabricação quando a empresa é só detentora do registro. | proposed |
| `ProductRegistration` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_anvisa_registrations.py`
- `etl/src/bracc_etl/pipelines/anvisa_registrations.py`
- `etl/src/bracc_etl/schemas/anvisa_registrations.py`
- `etl/tests/test_anvisa_registrations_pipeline.py`
- `docs/source-runbooks/anvisa_registrations.md`

Tarefas específicas, em ordem:

1. Inventariar classes e seus dicionários; separar registro, apresentação, modelo, preço CMED e relato de evento adverso.
1. Conferir se titular é detentor ou fabricante; criar vínculos distintos; testar registros expirados/cancelados e mudanças de titular.
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
- [ ] Apresentações/modelos sob um registro têm chaves sem colisão e não duplicam detentor.
- [ ] Registro expirado/cancelado mantém datas; detentor não é marcado como fabricante sem campo específico.

## Riscos e decisões pendentes

- Arquivos de modelos podem superar 1GB; diretório também reúne notificações sem escopo de registro.

## Evidências e referências

- [https://dados.anvisa.gov.br/dados/](https://dados.anvisa.gov.br/dados/)
- `docs/source_registry_br_v1.csv`
- [https://www.gov.br/anvisa/pt-br/assuntos/fiscalizacao-e-monitoramento/farmacovigilancia/relatorios-periodicos-de-avaliacao-beneficio-risco-rpbr-1](https://www.gov.br/anvisa/pt-br/assuntos/fiscalizacao-e-monitoramento/farmacovigilancia/relatorios-periodicos-de-avaliacao-beneficio-risco-rpbr-1)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
