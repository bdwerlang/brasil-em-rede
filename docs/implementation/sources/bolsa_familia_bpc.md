# bolsa_familia_bpc — Bolsa Familia and BPC

Baixar pagamentos do Bolsa Família e do BPC separadamente e registrar cobertura por benefício e competência, sem identificação artificial de beneficiários.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `bolsa_familia_bpc`.
- Ordem topológica: **81**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://portaldatransparencia.gov.br/download-de-dados/bolsa-familia-pagamentos](https://portaldatransparencia.gov.br/download-de-dados/bolsa-familia-pagamentos).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Identificador e situação real da fonte; atualizar apenas após implementação e carga comprovadas.
- [etl/src/bracc_etl/base.py](../../../etl/src/bracc_etl/base.py): Contrato Pipeline.extract/transform/load e rastreamento IngestionRun.
- [etl/src/bracc_etl/loader.py](../../../etl/src/bracc_etl/loader.py): Carga por lotes, MERGE e repetição de falhas.
- [scripts/bootstrap_all/adapters/registry.py](../../../scripts/bootstrap_all/adapters/registry.py): Aquisição por script_download ou file_manifest; blocked_external/blocked_credentials explícitos.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato de entradas e preparação a ampliar.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Labels, constraints e índices existentes; incluir migração para labels propostos.
- [etl/src/bracc_etl/pipelines/transparencia.py](../../../etl/src/bracc_etl/pipelines/transparencia.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://portaldatransparencia.gov.br/download-de-dados/bolsa-familia-pagamentos](https://portaldatransparencia.gov.br/download-de-dados/bolsa-familia-pagamentos) | Página pública de download mensal do Bolsa Família; localizar o conjunto próprio do BPC no mesmo portal. | Página oficial consultada em 26/10/2026 confirma seleção por exercício/mês e dicionário; BPC ainda exige descoberta do recurso final. |

- **Método:** Enumerar exercícios/meses e os dois programas; preferir ZIP/CSV mensal ao endpoint de consulta individual; não deduzir URL de BPC a partir da de Bolsa Família.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** ZIP contendo CSV e dicionário por programa
- **Partições e backfill:** Programa × competência de pagamento × arquivo; manter competência da parcela distinta da de disponibilização.
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- Bolsa Família e BPC têm arquivos/dicionários próprios; o recurso BPC não foi validado. Arquivos mensais são volumosos e documentos podem ser mascarados.

## Contrato de ingestão

**Entrada esperada:** data/bolsa_familia_bpc/raw/<partição>/ com bytes originais e manifest.json; programa, competência, município, identificação pública disponível, valor e parcela; sem exigir CPF completo; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** benefit_payment_id=SHA256(source_id+programa+ID público do pagamento+competência+parcela); se não houver ID único, hash da linha com ocorrência, sem fusão de pessoas.

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.
- NIS/CPF parcial permanece identificador de origem; proibir cruzamento automático com TSE, servidores ou empresas por nome.
- Projetar dimensões comuns conforme F09: Territory.territory_id=sistema:tipo:codigo:versao_territorial; EconomicActivity.activity_id=classificacao:versao:codigo; PublicBody.public_body_id=jurisdicao:sistema:identificador:versao. Aplicar somente as dimensões usadas nesta fonte, preservar códigos originais e validar crosswalks; município é Territory, sem dimensão paralela incompatível.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `BenefitPayment` | benefit_payment_id | proposed |
| `Territory` | territory_id | proposed |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `BenefitPayment` → `PAID_IN` → `Territory` | código IBGE oficial do município | Agregação territorial explícita; vínculo nominal só em camada futura com chave integral publicada. | proposed |
| `BenefitPayment` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_bolsa_familia_bpc.py`
- `etl/src/bracc_etl/pipelines/bolsa_familia_bpc.py`
- `etl/src/bracc_etl/schemas/bolsa_familia_bpc.py`
- `etl/tests/test_bolsa_familia_bpc_pipeline.py`
- `docs/source-runbooks/bolsa_familia_bpc.md`

Tarefas específicas, em ordem:

1. Descobrir download e dicionário do BPC; mapear mudanças entre Bolsa Família, Auxílio Brasil e novo Bolsa Família sem somar séries sobrepostas.
1. Baixar piloto de um mês de cada programa; medir tamanho e suportar leitura em chunks; validar tratamento de estornos e parcelas retroativas.
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
- [ ] Totais por programa/mês/município reconciliados com exportação oficial; nenhum Person criado com CPF parcial.
- [ ] Um mês de cada programa tem total reconciliado com exportação de mesma competência; CPF/NIS mascarados não geram Person nem vínculo nominal.

## Riscos e decisões pendentes

- Grande volume mensal; CPF e identidade podem estar mascarados.
- O único entrypoint verificado cobre Bolsa Família; não prova disponibilidade de BPC.

## Evidências e referências

- [https://portaldatransparencia.gov.br/download-de-dados/bolsa-familia-pagamentos](https://portaldatransparencia.gov.br/download-de-dados/bolsa-familia-pagamentos)
- `docs/source_registry_br_v1.csv`
- `etl/src/bracc_etl/pipelines/transparencia.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
