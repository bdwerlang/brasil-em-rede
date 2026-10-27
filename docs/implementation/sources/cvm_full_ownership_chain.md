# cvm_full_ownership_chain — CVM ownership chains

Expandir participações societárias das companhias abertas a partir de FRE sem prometer identificação de toda a cadeia ou beneficiário final.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `cvm_full_ownership_chain`.
- Ordem topológica: **58**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **XL**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dados.cvm.gov.br/](https://dados.cvm.gov.br/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Identificador e situação real da fonte; atualizar apenas após implementação e carga comprovadas.
- [etl/src/bracc_etl/base.py](../../../etl/src/bracc_etl/base.py): Contrato Pipeline.extract/transform/load e rastreamento IngestionRun.
- [etl/src/bracc_etl/loader.py](../../../etl/src/bracc_etl/loader.py): Carga por lotes, MERGE e repetição de falhas.
- [scripts/bootstrap_all/adapters/registry.py](../../../scripts/bootstrap_all/adapters/registry.py): Aquisição por script_download ou file_manifest; blocked_external/blocked_credentials explícitos.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato de entradas e preparação a ampliar.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Labels, constraints e índices existentes; incluir migração para labels propostos.
- [etl/src/bracc_etl/pipelines/cvm.py](../../../etl/src/bracc_etl/pipelines/cvm.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.
- [etl/src/bracc_etl/pipelines/holdings.py](../../../etl/src/bracc_etl/pipelines/holdings.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dados.cvm.gov.br/dataset/cia_aberta-doc-fre](https://dados.cvm.gov.br/dataset/cia_aberta-doc-fre) | Conjunto oficial de FRE com posição acionária, participação em sociedades e partes relacionadas. | Catálogo oficial consultado; CSVs estruturados, reapresentações semanais e mudança de leiaute a partir de 2023. |
| [https://dados.cvm.gov.br/](https://dados.cvm.gov.br/) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Enumerar ZIPs anuais e dicionário FRE; carregar posição acionária e participação em sociedades; manter versão de entrega e reapresentação.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** ZIP com múltiplos CSVs; dicionário ZIP
- **Partições e backfill:** Ano de entrega × tipo de tabela × versão/documento
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- FRE muda leiaute a partir de 2023 e sofre reapresentações semanais; histórico desde 2010 tem repositório e política próprios.

## Contrato de ingestão

**Entrada esperada:** data/cvm_full_ownership_chain/raw/<partição>/ com bytes originais e manifest.json; emissor, data, versão, acionista/participada, documento publicado, tipo de participação, quantidade/percentual e classe; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** ownership_statement_id=CNPJ_emissor+data_referencia+versao+tipo_tabela+acionista_id_publico+classe_acao

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `OwnershipStatement` | statement_id | proposed |
| `Company` | cnpj | existing |
| `Person` | cpf | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `DISCLOSES_OWNERSHIP` → `OwnershipStatement` | CNPJ emissor+documento FRE | Conservar data de referência e versão. | proposed |
| `OwnershipStatement` → `IDENTIFIES_HOLDER` → `Company` | CNPJ integral do acionista/participada | Sem união por nome; cadeia só até os elos efetivamente declarados. | proposed |
| `OwnershipStatement` → `IDENTIFIES_PERSON` → `Person` | CPF integral publicamente fornecido | Documentos mascarados permanecem sem resolução nominal automática. | proposed |
| `OwnershipStatement` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_cvm_full_ownership_chain.py`
- `etl/src/bracc_etl/pipelines/cvm_full_ownership_chain.py`
- `etl/src/bracc_etl/schemas/cvm_full_ownership_chain.py`
- `etl/tests/test_cvm_full_ownership_chain_pipeline.py`
- `docs/source-runbooks/cvm_full_ownership_chain.md`

Tarefas específicas, em ordem:

1. Mapear leiautes anteriores e posteriores a 2023 e o versionamento de entrega; testar reapresentação sem acumular percentuais duplicados.
1. Criar declarações de participação intermediárias; resolver PJ por CNPJ exato e PF apenas com documento publicado; detectar ciclos e não multiplicar percentuais de classes diferentes.
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
- [ ] Mesmo emissor/acionista em dois anos preserva observações temporais distintas; nova versão substitui leitura corrente sem apagar bruto.
- [ ] Dois titulares sem documento integral não são fundidos pelo nome; percentuais de classes/anos/versões diferentes não são somados como mesma participação.

## Riscos e decisões pendentes

- FRE cobre universo regulado e participações declaradas; não garante cadeia completa ou beneficiário final.

## Evidências e referências

- [https://dados.cvm.gov.br/dataset/cia_aberta-doc-fre](https://dados.cvm.gov.br/dataset/cia_aberta-doc-fre)
- `docs/source_registry_br_v1.csv`
- `etl/src/bracc_etl/pipelines/cvm.py`
- `etl/src/bracc_etl/pipelines/holdings.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
