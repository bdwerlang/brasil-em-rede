# mides — MiDES municipal procurement

Cadastrar licitações, contratos e itens municipais MiDES com ente e fornecedor documentados, controlando sobreposição com PNCP.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `mides`.
- Ordem topológica: **123**; onda de execução: **7**; prioridade temática inicial: 7.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **XL**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://basedosdados.org/dataset/world-wb-mides](https://basedosdados.org/dataset/world-wb-mides).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/mides.py](../../../etl/src/bracc_etl/pipelines/mides.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_mides_pipeline.py](../../../etl/tests/test_mides_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://basedosdados.org/dataset/world-wb-mides](https://basedosdados.org/dataset/world-wb-mides) | Entrada atualmente cadastrada para MiDES municipal procurement. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Verificar acesso do dataset MiDES do Banco Mundial/Base dos Dados, tabelas e revisão; exportar consultas paginadas/particionadas, registrando projeto BQ, SQL e custo quando aplicável.
- **Autenticação:** Se exportação BigQuery, validar projeto, permissões e GOOGLE_APPLICATION_CREDENTIALS ou identidade gerenciada; não presumir acesso a partir de load_state herdado.
- **Formato bruto:** Parquet/CSV exportado com schema e SQL versionados; bruto oficial upstream separado quando disponível.
- **Partições e backfill:** Provedor/tribunal de contas, município, ano e tabela; licitação/contrato/item com chaves relacionadas.
- **Retomada e deduplicação de download:** Checkpoint por provedor/tribunal de contas, município, ano e tabela; licitação/contrato/item com chaves relacionadas; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Diária, com janela de revisita para retificações.

Limites e pré-condições:

- Acesso BigQuery pode exigir credencial/projeto e gerar custos; confirmar antes da extração completa.
- Fonte é agregadora de coberturas heterogêneas, sem garantia de todos os municípios.
- Código atual pode degradar nome cadastral e mistura papéis de publicador/fornecedor.
- Bootstrap só verifica presença em data/mides/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/mides/licitacao.csv|parquet, contrato.csv|parquet e item.csv|parquet; arquivos opcionais; campos de IDs, município, documento de fornecedor e datas.

**Chave natural / namespace:** ID original MiDES com município/provedor; fallback por número/objeto/data deve ser substituído quando houver identificador publicado; item por contrato/licitação + número do item.

Normalização:

- Código do município e CNPJ do ente não são intercambiáveis.
- Empresa que publica licitação não é automaticamente concorrente; papel precisa vir do campo fonte.
- Não sobrescrever Company.razao_social com o próprio CNPJ como o código atual faz.
- Manter moeda, unidade/quantidade do item e valores de contrato distintos.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `MunicipalBid` | municipal_bid_id | existing |
| `MunicipalContract` | municipal_contract_id | existing |
| `MunicipalBidItem` | municipal_item_id | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `MUNICIPAL_LICITOU` → `MunicipalBid` | CNPJ do campo fonte com papel validado | Confirmar se representa órgão licitante ou participante; corrigir relação conforme semântica. | existing |
| `Company` → `MUNICIPAL_VENCEU` → `MunicipalContract` | CNPJ do contratado e ID do contrato | Só quando o recurso comprovar adjudicação/contratação. | existing |
| `MunicipalContract` → `REFERENTE_A` → `MunicipalBid` | Referência exata à licitação | Sem junção aproximada por objeto. | existing |
| `MunicipalContract` → `TEM_ITEM` → `MunicipalBidItem` | ID de contrato na linha do item | Itens não podem repetir o valor integral do contrato em somas. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/mides.py`
- `config/sources/mides.yml`
- `etl/src/bracc_etl/pipelines/mides.py`
- `etl/tests/test_mides_acquisition.py`

Tarefas específicas, em ordem:

1. Validar acesso real, cobertura por estado/município e schema das três tabelas; load_state herdado não comprova acesso local.
1. Implementar exportação por partição com manifestos e integridade de chaves.
1. Rever semântica de MUNICIPAL_LICITOU conforme CNPJ seja órgão/fornecedor; separar papéis.
1. Corrigir gravação de razao_social=CNPJ e IDs de fallback baseados em texto.
1. Conectar contrato/licitação/itens e criar crosswalk PNCP somente com controle oficial ou composição comprovada.
1. Conciliar contratos e itens sem somar total do contrato repetido em cada item.
1. Implementar projeção canônica dos registros MunicipalContract/MUNICIPAL_VENCEU para Contract/VENCEU, mantendo observações municipais e crosswalk. Atualizar queries consumidoras e deduplicar os mesmos contratos vistos em PNCP/TCE/portal.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Contrato e itens preservam chaves, quantidade, valor unitário e total sem duplicar agregado.
- [ ] Nome cadastral de Company não é substituído por número de CNPJ.
- [ ] Cobertura municipal/estadual é explicitada por provedor e ano.
- [ ] Sobreposição PNCP/MiDES não duplica o mesmo contrato sem crosswalk auditável.
- [ ] Fixture municipal passa pelos endpoints/padrões de Contract/VENCEU com os mesmos fatos e proveniência, sem duplicar o evento entre MunicipalContract, Contract e outro provedor.

## Riscos e decisões pendentes

- Acesso BigQuery pode exigir credencial/projeto e gerar custos; confirmar antes da extração completa.
- Fonte é agregadora de coberturas heterogêneas, sem garantia de todos os municípios.
- Código atual pode degradar nome cadastral e mistura papéis de publicador/fornecedor.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/mides.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_mides_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
