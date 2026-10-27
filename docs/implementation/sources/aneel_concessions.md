# aneel_concessions — ANEEL concessions

Ingerir outorgas e empreendimentos de geração, transmissão e distribuição com titulares documentados e vigência.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `aneel_concessions`.
- Ordem topológica: **41**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dadosabertos.aneel.gov.br/](https://dadosabertos.aneel.gov.br/).

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
| [https://dadosabertos.aneel.gov.br/dataset/atos-de-outorgas-de-geracao](https://dadosabertos.aneel.gov.br/dataset/atos-de-outorgas-de-geracao) | Atos de outorga de geração; complementar SIGA e SIGET conforme cada recurso. | Catálogo oficial consultado: atos desde 2015 e frequência mensal; SIGET contém múltiplas tabelas. |
| [https://dadosabertos.aneel.gov.br/](https://dadosabertos.aneel.gov.br/) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Enumerar recursos CKAN de atos, SIGA e SIGET; baixar arquivos/dicionários separadamente e definir crosswalk entre CEG, ato, contrato e agente.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** CSV/Parquet e dicionários; preservar o formato por conjunto
- **Partições e backfill:** Subsistema × snapshot/data-base × arquivo
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- Atos de geração desde 2015, SIGA e SIGET têm arquivos/leiautes distintos; SIGA de ativos não garante CNPJ do titular.

## Contrato de ingestão

**Entrada esperada:** data/aneel_concessions/raw/<partição>/ com bytes originais e manifest.json; ato, tipo, identificador empreendimento, vigência, titular/CNPJ somente quando fornecido; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** grant_id=ANEEL+tipo+numero_ato+ano; asset_id=CEG ou identificador SIGET

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.
- Unidades kW/MW e percentuais de participação explícitos.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `RegulatoryGrant` | grant_id | proposed |
| `EnergyAsset` | asset_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `HOLDS_GRANT` → `RegulatoryGrant` | CNPJ integral+ato | Participação e vigência conforme origem. | proposed |
| `RegulatoryGrant` → `COVERS_ASSET` → `EnergyAsset` | CEG/código SIGET explicitamente citado | Sem união por nome da usina. | proposed |
| `RegulatoryGrant` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_aneel_concessions.py`
- `etl/src/bracc_etl/pipelines/aneel_concessions.py`
- `etl/src/bracc_etl/schemas/aneel_concessions.py`
- `etl/tests/test_aneel_concessions_pipeline.py`
- `docs/source-runbooks/aneel_concessions.md`

Tarefas específicas, em ordem:

1. Mapear geração/transmissão/distribuição como subprodutos; verificar campos de titular nos recursos de agentes; SIGA sozinho não garante CNPJ.
1. Separar ato, ativo e concessão; testar empreendimentos com múltiplos titulares e transferências.
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
- [ ] Ativo com dois titulares conserva participações/intervalos sem duplicar CEG; troca de titular não apaga história.
- [ ] Cobertura dos atos, SIGA e SIGET é declarada separadamente; ausência de CNPJ não gera ligação por nome.

## Riscos e decisões pendentes

- Um ativo pode ter copropriedade; não inferir titular pelo município.

## Evidências e referências

- [https://dadosabertos.aneel.gov.br/dataset/atos-de-outorgas-de-geracao](https://dadosabertos.aneel.gov.br/dataset/atos-de-outorgas-de-geracao)
- `docs/source_registry_br_v1.csv`
- [https://dadosabertos.aneel.gov.br/dataset/sistema-de-gestao-da-transmissao-siget](https://dadosabertos.aneel.gov.br/dataset/sistema-de-gestao-da-transmissao-siget)
- [https://dadosabertos.aneel.gov.br/dataset/siga-sistema-de-informacoes-de-geracao-da-aneel](https://dadosabertos.aneel.gov.br/dataset/siga-sistema-de-informacoes-de-geracao-da-aneel)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
