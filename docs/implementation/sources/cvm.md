# cvm — CVM proceedings

Cadastrar processos administrativos sancionadores CVM e acusados, distinguindo acusação, julgamento e penalidade.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `cvm`.
- Ordem topológica: **56**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dados.cvm.gov.br/](https://dados.cvm.gov.br/).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/cvm.py](../../../etl/src/bracc_etl/pipelines/cvm.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_cvm_pipeline.py](../../../etl/tests/test_cvm_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dados.cvm.gov.br/](https://dados.cvm.gov.br/) | Entrada atualmente cadastrada para CVM proceedings. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Baixar arquivo oficial de processos sancionadores e seus acusados no catálogo CVM; validar se inclui decisões e respectivos estados.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** ZIP/CSV oficial de processo_sancionador com tabelas relacionadas.
- **Partições e backfill:** Snapshot do cadastro, NUP, acusado e decisão; tabela principal e tabelas filhas atômicas.
- **Retomada e deduplicação de download:** Checkpoint por snapshot do cadastro, nup, acusado e decisão; tabela principal e tabelas filhas atômicas; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- MATCH atual por Person.name/Company.razao_social pode atribuir processo a homônimo.
- Nome da relação CVM_SANCIONADA exagera o fato quando só há acusação.
- Bootstrap só verifica presença em data/cvm/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/cvm/processo_sancionador.csv e processo_sancionador_acusado.csv; Latin-1, ponto e vírgula; primeiro arquivo obrigatório.

**Chave natural / namespace:** Processo por NUP; proposto acusado por ID oficial da parte no processo; decisão e penalidade por ID/data própria.

Normalização:

- Manter nome do acusado como atributo, sem atribuir identidade por nome isolado.
- Separar acusado, absolvido, sancionado, decisão e recurso.
- CNPJ/CPF completos quando publicados geram ligação forte; sem eles manter parte contextual do processo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `CVMProceeding` | pas_id | existing |
| `Person` | cpf | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company\|Person` → `CVM_SANCIONADA` → `CVMProceeding` | Proposto: documento/ID forte da parte + decisão; atual usa nome | Desativar regra nominal e só afirmar sanção quando houver decisão compatível. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/cvm.py`
- `config/sources/cvm.yml`
- `etl/src/bracc_etl/pipelines/cvm.py`
- `etl/tests/test_cvm_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Criar downloader do pacote CVM e validação de NUP e chaves entre processos/acusados.
1. Remover CVM_SANCIONADA gerada hoje por nome e restringir a decisão sancionadora comprovada.
1. Adicionar registros contextuais de parte/acusado e candidaturas de resolução sem SAME_AS.
1. Criar constraint CVMProceeding.pas_id e granularidade de decisão/penalidade.
1. Reconciliar decisões e alterações de situação com evidência do documento.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Acusado sem julgamento não recebe relação de sanção definitiva.
- [ ] Homônimo de acusado não é vinculado automaticamente.
- [ ] NUP presente em várias tabelas resulta em um processo com partes distintas.
- [ ] Reprocessamento mantém histórico de recurso e estado.

## Riscos e decisões pendentes

- MATCH atual por Person.name/Company.razao_social pode atribuir processo a homônimo.
- Nome da relação CVM_SANCIONADA exagera o fato quando só há acusação.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/cvm.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_cvm_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
