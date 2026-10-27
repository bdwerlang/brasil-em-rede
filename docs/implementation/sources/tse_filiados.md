# tse_filiados — TSE party memberships

Cadastrar registros de filiação partidária por fonte e situação, mantendo identidades incertas sem fusão de pessoas.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `tse_filiados`.
- Ordem topológica: **37**; onda de execução: **3**; prioridade temática inicial: 3.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [tse](tse.md)
- Contrato de acesso catalogado: [https://dadosabertos.tse.jus.br/dataset/delegados-partidarios](https://dadosabertos.tse.jus.br/dataset/delegados-partidarios).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/tse_filiados.py](../../../etl/src/bracc_etl/pipelines/tse_filiados.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_tse_filiados_pipeline.py](../../../etl/tests/test_tse_filiados_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dadosabertos.tse.jus.br/dataset/delegados-partidarios](https://dadosabertos.tse.jus.br/dataset/delegados-partidarios) | Entrada atualmente cadastrada para TSE party memberships. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Corrigir URL do catálogo que aponta delegados-partidarios e descobrir o recurso oficial de filiação; baixar apenas os campos efetivamente públicos.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** ZIP/CSV de filiação, adaptado para filiados.csv.
- **Partições e backfill:** Snapshot, partido e UF; distinguir ativos, cancelados e sub judice conforme layout.
- **Retomada e deduplicação de download:** Checkpoint por snapshot, partido e uf; distinguir ativos, cancelados e sub judice conforme layout; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- URL atual do registro é de delegados partidários e precisa validação.
- Pipeline cria FILIADO_A de baixa confiança por nome+UF, incompatível com coligação segura.
- Bootstrap só verifica presença em data/tse_filiados/*; não baixa, não valida schema, não verifica completude e não comprova carga.

## Contrato de ingestão

**Entrada esperada:** data/tse_filiados/filiados.csv; nome, sigla_partido, sigla_uf, data_filiacao, situacao_registro e, quando publicados, data_nascimento/id_municipio_tse.

**Chave natural / namespace:** ID oficial de registro de filiação ou hash com namespace, município, partido, filiação e campos públicos suficientes; chave nome/partido/UF/data atual pode colidir.

Normalização:

- Não usar título eleitoral, CPF ou nascimento se não forem publicados no canal consultado.
- Nomes, UF e município formam pistas, sem identidade determinística.
- Preservar situação, data de filiação/desfiliação/cancelamento e data do processamento.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `PartyMembership` | membership_id | existing |
| `Person` | cpf | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person` → `FILIADO_A` → `PartyMembership` | Proposto: ID documental forte; atual usa nome+UF e atributos adicionais | Remover vínculo automático de baixa confiança; nome isolado ou nome+UF não prova identidade. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/tse_filiados.py`
- `config/sources/tse_filiados.yml`
- `etl/src/bracc_etl/pipelines/tse_filiados.py`
- `etl/tests/test_tse_filiados_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Validar dataset oficial de filiados e disponibilidade atual; delegados partidários não é substituto.
1. Implementar aquisição e manifestos por partido/UF com cobertura explícita.
1. Desativar fallback FILIADO_A por nome+UF; tornar coincidências compostas candidatos de resolução auditáveis.
1. Rever membership_id para não fundir homônimos e adicionar constraint PartyMembership.
1. Tratar relação à candidatura apenas quando identidade for comprovada, separando confiança de fato documental.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Dois homônimos no mesmo partido/UF não são fundidos automaticamente.
- [ ] Fonte com só nome/UF produz registro e pendência, não FILIADO_A definitivo.
- [ ] Cancelamento atualiza situação com preservação da filiação anterior.
- [ ] Todas as partições publicadas têm contagem e data do snapshot.

## Riscos e decisões pendentes

- URL atual do registro é de delegados partidários e precisa validação.
- Pipeline cria FILIADO_A de baixa confiança por nome+UF, incompatível com coligação segura.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/tse_filiados.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_tse_filiados_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
