# ceaf — CEAF expelled servants

Cadastrar expulsões de servidores com ato, fundamento e órgão, vinculando a identidade apenas quando houver identificador suficiente.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `ceaf`.
- Ordem topológica: **1**; onda de execução: **1**; prioridade temática inicial: 1.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://portaldatransparencia.gov.br/download-de-dados/ceaf](https://portaldatransparencia.gov.br/download-de-dados/ceaf).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/ceaf.py](../../../etl/src/bracc_etl/pipelines/ceaf.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_ceaf_pipeline.py](../../../etl/tests/test_ceaf_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://portaldatransparencia.gov.br/download-de-dados/ceaf](https://portaldatransparencia.gov.br/download-de-dados/ceaf) | Entrada atualmente cadastrada para CEAF expelled servants. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Baixar o snapshot CEAF disponibilizado pela CGU e materializar ceaf.csv compatível com o parser.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** ZIP/CSV oficial e CSV canônico.
- **Partições e backfill:** Snapshot e data do ato; controle de atos revogados/retificados.
- **Retomada e deduplicação de download:** Checkpoint por snapshot e data do ato; controle de atos revogados/retificados; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- O modelo atual faz identificação com dígitos e idx; não sustenta reordenação.
- Expulsion não tem constraint no schema atual.
- Bootstrap só verifica presença em data/ceaf/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/ceaf/ceaf.csv, Latin-1, vírgula; transformar o layout oficial conforme cabeçalhos usados no pipeline.

**Chave natural / namespace:** Identificador oficial do registro/ato CEAF; alternativa órgão + ato/processo + data + identificador da parte; eliminar idx.

Normalização:

- Preservar cargo, órgão, número do ato e datas de expulsão/reintegração.
- Manter expulsão identificável mesmo com CPF mascarado; identidade local de parte, sem fusão com Person.
- Validar CPF completo antes de usar a constraint Person.cpf.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Expulsion` | expulsion_id | existing |
| `Person` | cpf | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person` → `EXPULSO` → `Expulsion` | CPF completo validado | Sem CPF completo, ato é cadastrado mas identidade fica pendente. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/ceaf.py`
- `config/sources/ceaf.yml`
- `etl/src/bracc_etl/pipelines/ceaf.py`
- `etl/tests/test_ceaf_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Adaptar separador e nomes do arquivo oficial para ceaf.csv com rejeições auditadas.
1. Substituir expulsion_id baseado em índice por chave do ato/registro.
1. Adicionar unicidade de Expulsion e tratar expurgos, reintegrações e retificações como mudanças de situação.
1. Separar cadastro do ato de resolução da pessoa para não descartar registros mascarados.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Ordem do arquivo não altera expulsion_id.
- [ ] Ato CEAF sem CPF integral permanece consultável com fonte e data.
- [ ] Uma reintegração atualiza situação com histórico, sem eliminar a expulsão documentada.

## Riscos e decisões pendentes

- O modelo atual faz identificação com dígitos e idx; não sustenta reordenação.
- Expulsion não tem constraint no schema atual.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/ceaf.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_ceaf_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
