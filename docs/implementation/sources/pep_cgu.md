# pep_cgu — CGU PEP list

Registrar mandatos e funções de pessoas politicamente expostas, com período de exercício e carência.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `pep_cgu`.
- Ordem topológica: **9**; onda de execução: **1**; prioridade temática inicial: 1.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://portaldatransparencia.gov.br/download-de-dados/pep](https://portaldatransparencia.gov.br/download-de-dados/pep).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/pep_cgu.py](../../../etl/src/bracc_etl/pipelines/pep_cgu.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_pep_cgu_pipeline.py](../../../etl/tests/test_pep_cgu_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://portaldatransparencia.gov.br/download-de-dados/pep](https://portaldatransparencia.gov.br/download-de-dados/pep) | Entrada atualmente cadastrada para CGU PEP list. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir snapshot PEP no Portal da Transparência e reter versão original antes da normalização de colunas.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** ZIP/CSV de PEP; parser interno pep.csv.
- **Partições e backfill:** Data do snapshot, órgão e exercício; alterações como versões, sem recontar a mesma função.
- **Retomada e deduplicação de download:** Checkpoint por data do snapshot, órgão e exercício; alterações como versões, sem recontar a mesma função; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- PEP não é sanção; preservar a diferença semântica nas coligações.
- Schema atual não define unicidade para PEPRecord; chave contém idx.
- Bootstrap só verifica presença em data/pep_cgu/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Divergência de identidade: runner/registro=pep_cgu; Pipeline.source_id=cgu_pep. Reconciliar runs e proveniência preservando alias do provedor.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/pep_cgu/pep.csv, ponto e vírgula, Latin-1; aliases de cabeçalho implementados.

**Chave natural / namespace:** ID oficial PEP ou hash documento/identificador do registro + órgão + função + início; substituir pep_<digits>_<idx>.

Normalização:

- Separar exercício, término e carência, sem inferir atividade atual apenas pela presença na lista.
- Guardar CPF parcial como atributo do PEPRecord, jamais como Person.cpf.
- Conservar função e órgão originais além dos nomes normalizados.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `PEPRecord` | pep_id | existing |
| `Person` | cpf | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person` → `PEP_REGISTRADA` → `PEPRecord` | CPF completo válido | CPF mascarado não identifica uma pessoa; conservar o registro sem ligação. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/pep_cgu.py`
- `config/sources/pep_cgu.yml`
- `etl/src/bracc_etl/pipelines/pep_cgu.py`
- `etl/tests/test_pep_cgu_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Implementar aquisição mensal por recurso publicado e resolver encoding e cabeçalhos por versão.
1. Remover dependência de idx na chave pep_id e mapear o alias cgu_pep para pep_cgu.
1. Adicionar constraints de PEPRecord e evidência de cada função, mantendo associação a Person apenas com CPF completo válido.
1. Agendar revalidação das datas e registrar registros sem documento como pendentes.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Reordenação de linhas e nova competência não duplicam uma função inalterada.
- [ ] CPF parcial permanece no PEPRecord e não cria Person.
- [ ] Registro encerrado mantém histórico de carência verificável.

## Riscos e decisões pendentes

- PEP não é sanção; preservar a diferença semântica nas coligações.
- Schema atual não define unicidade para PEPRecord; chave contém idx.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/pep_cgu.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_pep_cgu_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
