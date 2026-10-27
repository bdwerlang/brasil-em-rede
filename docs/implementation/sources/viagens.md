# viagens — Viagens a servico

Cadastrar viagens a serviço e suas despesas com pessoa e órgão, preservando autorização, competência e valores.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `viagens`.
- Ordem topológica: **26**; onda de execução: **2**; prioridade temática inicial: 2.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://portaldatransparencia.gov.br/download-de-dados/viagens](https://portaldatransparencia.gov.br/download-de-dados/viagens).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/viagens.py](../../../etl/src/bracc_etl/pipelines/viagens.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_viagens_pipeline.py](../../../etl/tests/test_viagens_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://portaldatransparencia.gov.br/download-de-dados/viagens](https://portaldatransparencia.gov.br/download-de-dados/viagens) | Entrada atualmente cadastrada para Viagens a servico. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Baixar arquivos oficiais de viagens da CGU por período, incluindo tabelas auxiliares e despesas associadas quando publicadas.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** ZIP/CSV de viagens e despesas, CSV canônico do pipeline.
- **Partições e backfill:** Ano-mês, solicitação e tipo de despesa (diária/passagem/restituição).
- **Retomada e deduplicação de download:** Checkpoint por ano-mês, solicitação e tipo de despesa (diária/passagem/restituição); baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Parser atual ignora CSV que falha sem propagar falha de cobertura.
- Chave baseada em valor pode criar nova viagem toda vez que valor é retificado.
- Bootstrap só verifica presença em data/viagens/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Divergência de identidade: runner/registro=viagens; Pipeline.source_id=portal_transparencia_viagens. Reconciliar runs e proveniência preservando alias do provedor.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/viagens/*.csv; Latin-1, ponto e vírgula; aliases de pessoa, destino, data e valor no parser.

**Chave natural / namespace:** ID oficial da solicitação/viagem e item de despesa; substituir hash CPF/destino/início/valor quando houver múltiplos pagamentos.

Normalização:

- CPF parcial fica como informação do viajante na viagem, sem criar Person.
- Separar data da viagem, pagamento, autorização e competência.
- Não somar valor total da viagem em cada trecho ou item de despesa.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `GovTravel` | travel_id | existing |
| `Person` | cpf | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person` → `VIAJOU` → `GovTravel` | CPF completo válido ou ID oficial comprovado | Dados mascarados não suportam identificação direta. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/viagens.py`
- `config/sources/viagens.yml`
- `etl/src/bracc_etl/pipelines/viagens.py`
- `etl/tests/test_viagens_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Mapear o grão dos arquivos atuais de viagens, trechos, passagens e pagamentos.
1. Criar aquisição e adaptador que produza viagem identificada por código oficial e detalhes associados.
1. Substituir source_id portal_transparencia_viagens por alias operacional viagens.
1. Adicionar constraint GovTravel.travel_id e ligações somente por CPF completo ou ID oficial de servidor comprovado.
1. Testar viagem cancelada/estornada e alteração de valor sem gerar nova identidade da viagem.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Uma viagem com dois trechos não duplica seu total.
- [ ] Viagem de pessoa sem CPF completo continua cadastrada.
- [ ] Reprocessamento de retificação altera versão e soma esperada, sem duplicação.
- [ ] A mesma pessoa com CPF completo compartilha identidade com outras fontes.

## Riscos e decisões pendentes

- Parser atual ignora CSV que falha sem propagar falha de cobertura.
- Chave baseada em valor pode criar nova viagem toda vez que valor é retificado.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/viagens.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_viagens_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
