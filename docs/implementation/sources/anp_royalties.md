# anp_royalties — ANP royalties and fuel

Cadastrar royalties/participações especiais por beneficiário e competência e, em subproduto separado, cadastro de revendas e preços de combustíveis por coleta.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `anp_royalties`.
- Ordem topológica: **13**; onda de execução: **2**; prioridade temática inicial: 2.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dados.gov.br/dados/conjuntos-dados/anp](https://dados.gov.br/dados/conjuntos-dados/anp).

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
| [https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/pg/royalties-uniao](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/pg/royalties-uniao) | Coleção oficial de CSV de royalties da União; descobrir também municípios/estados e participação especial. | Coleção anual oficial consultada; não cobre sozinha os três entes nem os dois tipos de repasse. |
| [https://dados.gov.br/dados/conjuntos-dados/anp](https://dados.gov.br/dados/conjuntos-dados/anp) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |
| [https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis) | CSV da pesquisa de preços por revenda; recursos históricos agrupados por semestre e recursos recentes por mês. | Página oficial e metadados consultados; pesquisa semanal com CNPJ da revenda, produto, data, preço e unidade. |
| [https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/dados-cadastrais-dos-revendedores-varejistas-de-combustiveis-automotivos](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/dados-cadastrais-dos-revendedores-varejistas-de-combustiveis-automotivos) | Cadastro regulatório oficial das revendas; recurso final e dicionário a validar. | Página oficial localizada; dados cadastrais e API de revendedores publicados pela ANP. |

- **Método:** Enumerar coleções de distribuição nos dados abertos ANP; descobrir recursos por tipo de beneficiário; usar dados efetivos em vez de previsões de painel.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** CSV anual por tema/beneficiário; CSV de revenda/preços e cadastro.
- **Partições e backfill:** Ano × tipo (royalty/PE) × esfera; competência mensal de royalty ou trimestral de PE; combustíveis: ano/semestre ou mês do arquivo × tipo automotivo/GLP, mantendo data da coleta.
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Royalties: mensal; PE: trimestral; preços: conforme publicação semanal e distribuição por arquivo; cadastro de revendas por snapshot. Revisitar arquivos recentes corrigidos.

Limites e pré-condições:

- Coleção União não cobre automaticamente estados/municípios ou PE. Preços são pesquisa amostral por revenda e têm distribuição distinta dos royalties.

## Contrato de ingestão

**Entrada esperada:** data/anp_royalties/raw/<partição>/ com bytes originais e manifest.json; competência, ente, código beneficiário, valor, componente e tipo; saída normalizada versionada e rejeições separadas. Subcontrato combustível: CNPJ da revenda, produto, data de coleta, preço, unidade, bandeira; cadastro e preço são arquivos distintos.

**Chave natural / namespace:** royalty_transfer_id=tipo+competencia+beneficiario_oficial+componente; preço: price_id=CNPJ_revenda+data_coleta+produto+unidade+tipo_preco; revenda: CNPJ integral+autorização quando publicada.

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.
- Projetar dimensões comuns conforme F09: Territory.territory_id=sistema:tipo:codigo:versao_territorial; EconomicActivity.activity_id=classificacao:versao:codigo; PublicBody.public_body_id=jurisdicao:sistema:identificador:versao. Aplicar somente as dimensões usadas nesta fonte, preservar códigos originais e validar crosswalks; município é Territory, sem dimensão paralela incompatível.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `RoyaltyTransfer` | transfer_id | proposed |
| `PublicBody` | public_body_id | proposed |
| `Territory` | territory_id | proposed |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |
| `FuelPriceObservation` | price_id | proposed |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `RoyaltyTransfer` → `RECEIVED_BY` → `PublicBody` | ID oficial do beneficiário+esfera | Não associar royalties municipais a empresas exploradoras sem dado específico. | proposed |
| `RoyaltyTransfer` → `ALLOCATED_TO` → `Territory` | IBGE/UF oficial | Repasse territorial não é vínculo societário. | proposed |
| `RoyaltyTransfer` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |
| `Company` → `HAS_FUEL_PRICE_OBSERVATION` → `FuelPriceObservation` | CNPJ integral da revenda+registro de coleta | Preço de pesquisa é observação, não pagamento nem contrato; bandeira não demonstra controle societário. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_anp_royalties.py`
- `etl/src/bracc_etl/pipelines/anp_royalties.py`
- `etl/src/bracc_etl/schemas/anp_royalties.py`
- `etl/tests/test_anp_royalties_pipeline.py`
- `docs/source-runbooks/anp_royalties.md`

Tarefas específicas, em ordem:

1. Localizar coleções de municípios, estados e participação especial; baixar dicionário e validar um município contra publicação oficial.
1. Distinguir competência de produção e pagamento, deduções/ajustes e projeções; cadastrar códigos de ente e município.
1. Criar subadaptadores independentes royalties/PE, cadastro de revendas e pesquisa de preços; baixar um CSV de preços e mapear produto/unidade/coleta, CNPJ e bandeira; manter preço de compra, venda e agregado separados.
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
- [ ] Um preço de revenda liga ao CNPJ exato; bandeira permanece atributo de marca e não gera HOLDING_DE; valores de preços e royalties nunca são somados.
- [ ] Repasse efetivo por município/competência confere com CSV oficial; projeções ficam fora do realizado.
- [ ] Preço GLP por botijão e combustível por litro conservam unidade e não são comparados sem conversão explícita.

## Riscos e decisões pendentes

- A cobertura da pesquisa de preços é amostral; ausência de revenda não indica inatividade.
- Royalties e combustíveis têm granularidade e atualizações distintas; não podem compartilhar a mesma tabela de fatos.

## Evidências e referências

- [https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/pg/royalties-uniao](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/pg/royalties-uniao)
- `docs/source_registry_br_v1.csv`
- [https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis)
- [https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/dados-cadastrais-dos-revendedores-varejistas-de-combustiveis-automotivos](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/dados-cadastrais-dos-revendedores-varejistas-de-combustiveis-automotivos)
- [https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/metadados-serie-historica-precos-combustiveis-1.pdf/@@download/file](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/metadados-serie-historica-precos-combustiveis-1.pdf/@@download/file)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
