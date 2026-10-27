# sicar_rural_registry — SiCAR rural registry

Ingerir polígonos públicos do CAR e situação cadastral permitida, sem presumir publicação de dados dos proprietários.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `sicar_rural_registry`.
- Ordem topológica: **108**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Acesso condicionado / restrito**; complexidade relativa: **XL**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://www.car.gov.br/publico/municipios/downloads](https://www.car.gov.br/publico/municipios/downloads).

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
| [https://www.car.gov.br/publico/municipios/downloads](https://www.car.gov.br/publico/municipios/downloads) | URL legada de download por município; resolver distribuição pública vigente no serviço oficial CAR. | Consulta desta URL retornou loop de redirecionamento; o portal não foi validado como endpoint de lote. |

- **Método:** Gate: descobrir exportação pública oficial vigente e verificar desafio/captcha; suportar importação de ZIP manual legitimamente baixado com manifesto; nenhuma automação de captcha/área do proprietário.
- **Autenticação:** A confirmar no portal vigente; área de proprietário exige Gov.br e não é fonte pública de terceiros; se captcha, aquisição humana.
- **Formato bruto:** ZIP com SHP/DBF e metadados quando públicos; schema a validar
- **Partições e backfill:** UF × município IBGE × camada × data de extração
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial quarterly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- URL legada retornou redirecionamento circular. Exportação pública e captcha não validados; área Gov.br do proprietário não é fonte pública de terceiros.

## Contrato de ingestão

**Entrada esperada:** data/sicar_rural_registry/raw/<partição>/ com bytes originais e manifest.json; código CAR, município, situação, área, geometria e CRS; titular só se conjunto explicitamente o publicar; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** rural_parcel_id=código CAR integral público; geometria e situação versionadas por snapshot

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
| `RuralParcel` | parcel_id | proposed |
| `Territory` | territory_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `RuralParcel` → `LOCATED_IN` → `Territory` | código IBGE oficial | Um CAR pode cruzar limites; relação territorial não é titularidade. | proposed |
| `Company` → `DECLARED_CAR_HOLDER` → `RuralParcel` | CNPJ integral em base oficial pública que declare titular | Desabilitada na carga pública sem campo de titular; nunca inferir por sobreposição ou nome. | proposed |
| `RuralParcel` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_sicar_rural_registry.py`
- `etl/src/bracc_etl/pipelines/sicar_rural_registry.py`
- `etl/src/bracc_etl/schemas/sicar_rural_registry.py`
- `etl/tests/test_sicar_rural_registry_pipeline.py`
- `docs/source-runbooks/sicar_rural_registry.md`

Tarefas específicas, em ordem:

1. Resolver novo portal e documentar possibilidade de lote/limites; confirmar quais camadas públicas são oferecidas e quais campos foram suprimidos.
1. Validar múltiplas inscrições/sobreposições e declarar que CAR é cadastro declaratório; guardar geometrias fora do Neo4j e referências/hash no grafo.
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
- [ ] Código CAR permanece textual e estável; geometrias inválidas/CRS ausente vão à quarentena; área/reprojeção verificadas com tolerância documentada.
- [ ] Sem documento integral de titular expressamente público não se cria vínculo nominal; sobreposição não estabelece propriedade.

## Riscos e decisões pendentes

- Endpoint legado com redirecionamento circular nesta consulta.
- Dados nominais de titulares não estão comprovados como públicos; polígono CAR não comprova título de propriedade.

## Evidências e referências

- [https://www.car.gov.br/publico/municipios/downloads](https://www.car.gov.br/publico/municipios/downloads)
- `docs/source_registry_br_v1.csv`
- [https://www.gov.br/car/pt-br/dev/servicos/acesso-ao-car-pelo-gov.br](https://www.gov.br/car/pt-br/dev/servicos/acesso-ao-car-pelo-gov.br)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
