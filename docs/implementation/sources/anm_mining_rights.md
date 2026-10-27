# anm_mining_rights — ANM mining rights

Cadastrar processos e direitos minerários, titulares publicamente identificados e suas poligonais por snapshot.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `anm_mining_rights`.
- Ordem topológica: **78**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **XL**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dados.gov.br/dados/conjuntos-dados/anm](https://dados.gov.br/dados/conjuntos-dados/anm).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Identificador e situação real da fonte; atualizar apenas após implementação e carga comprovadas.
- [etl/src/bracc_etl/base.py](../../../etl/src/bracc_etl/base.py): Contrato Pipeline.extract/transform/load e rastreamento IngestionRun.
- [etl/src/bracc_etl/loader.py](../../../etl/src/bracc_etl/loader.py): Carga por lotes, MERGE e repetição de falhas.
- [scripts/bootstrap_all/adapters/registry.py](../../../scripts/bootstrap_all/adapters/registry.py): Aquisição por script_download ou file_manifest; blocked_external/blocked_credentials explícitos.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato de entradas e preparação a ampliar.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Labels, constraints e índices existentes; incluir migração para labels propostos.
- [etl/src/bracc_etl/pipelines/ibama.py](../../../etl/src/bracc_etl/pipelines/ibama.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.gov.br/anm/pt-br/acesso-a-informacao/dados-abertos/bases-de-dados](https://www.gov.br/anm/pt-br/acesso-a-informacao/dados-abertos/bases-de-dados) | Índice oficial das bases ANM com SIGMINE e processos minerários. | Índice e diretório https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/ localizados; geometria CP1252/SIRGAS2000 documentada no serviço oficial. |
| [https://dados.gov.br/dados/conjuntos-dados/anm](https://dados.gov.br/dados/conjuntos-dados/anm) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Baixar ZIPs SIGMINE de ativos/inativos e descobrir cadastro de titulares; preferir dump a consultas espaciais unitárias; conferir tabela de processos administrativos.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** ZIP com SHP/DBF/PRJ/SHX; CSV cadastral conforme descoberta
- **Partições e backfill:** Snapshot × ativos/inativos × UF/arquivo nacional
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- Snapshots geográficos mutáveis e arquivos pesados; um snapshot não recompõe histórico de titularidade. Documento do titular pode não constar no SHP.

## Contrato de ingestão

**Entrada esperada:** data/anm_mining_rights/raw/<partição>/ com bytes originais e manifest.json; processo, fase, substância, titular publicado, data-base, geometria e CRS; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** mining_process_id=ANM+numero_processo+ano; direito/versão por ato e data

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `MiningRight` | right_id | proposed |
| `SpatialAsset` | asset_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `HOLDS_MINING_RIGHT` → `MiningRight` | CNPJ integral publicado | Requer titularidade expressa e intervalo. | proposed |
| `MiningRight` → `HAS_GEOMETRY` → `SpatialAsset` | processo/área oficial | Interseções com CAR/UC/alerta são espaciais, não prova de propriedade. | proposed |
| `MiningRight` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_anm_mining_rights.py`
- `etl/src/bracc_etl/pipelines/anm_mining_rights.py`
- `etl/src/bracc_etl/schemas/anm_mining_rights.py`
- `etl/tests/test_anm_mining_rights_pipeline.py`
- `docs/source-runbooks/anm_mining_rights.md`

Tarefas específicas, em ordem:

1. Inspecionar leiaute do DBF e cadastro de titulares; titular nominal sem CPF/CNPJ fica como referência não resolvida.
1. Versionar mudanças de fase/titular e validar geometria; guardar GeoParquet fora do grafo e hash/referência no nó.
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
- [ ] Geometria inválida/CRS ausente vai à quarentena; reprojeção e área verificadas com tolerância documentada.
- [ ] Requerimento e concessão de lavra são fases diferentes; interseção com CAR/UC não atribui propriedade ou autoria.

## Riscos e decisões pendentes

- Área requerida não é autorização de lavra; poligonais podem mudar.

## Evidências e referências

- [https://www.gov.br/anm/pt-br/acesso-a-informacao/dados-abertos/bases-de-dados](https://www.gov.br/anm/pt-br/acesso-a-informacao/dados-abertos/bases-de-dados)
- `docs/source_registry_br_v1.csv`
- `etl/src/bracc_etl/pipelines/ibama.py`
- [https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/](https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/)
- [https://geo.anm.gov.br/arcgis/rest/services/SIGMINE/dados_anm/FeatureServer](https://geo.anm.gov.br/arcgis/rest/services/SIGMINE/dados_anm/FeatureServer)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
