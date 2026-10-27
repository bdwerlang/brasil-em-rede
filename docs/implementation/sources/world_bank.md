# world_bank — World Bank debarment

Cadastrar impedimentos de firmas e indivíduos no Banco Mundial com fundamento e período.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `world_bank`.
- Ordem topológica: **122**; onda de execução: **6**; prioridade temática inicial: 6.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://www.worldbank.org/en/projects-operations/procurement/debarred-firms](https://www.worldbank.org/en/projects-operations/procurement/debarred-firms).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/world_bank.py](../../../etl/src/bracc_etl/pipelines/world_bank.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_world_bank_pipeline.py](../../../etl/tests/test_world_bank_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.worldbank.org/en/projects-operations/procurement/debarred-firms](https://www.worldbank.org/en/projects-operations/procurement/debarred-firms) | Entrada atualmente cadastrada para World Bank debarment. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir exportação/API oficial por trás da lista de debarred firms; baixar a lista completa com data de disponibilização.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** CSV/JSON oficial convertido para debarred.csv.
- **Partições e backfill:** Snapshot, entidade e episódio de impedimento; distinguir cross-debarment quando publicado.
- **Retomada e deduplicação de download:** Checkpoint por snapshot, entidade e episódio de impedimento; distinguir cross-debarment quando publicado; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Verificar alteração diariamente e publicar versão quando a lista mudar; cadência mensal do registro não garante atualização sancionadora.

Limites e pré-condições:

- Pipeline cadastra registros internacionais sem vincular Company/Person.
- Página pública não é endpoint de CSV; recurso final precisa inspeção.
- Bootstrap só verifica presença em data/world_bank/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/world_bank/debarred.csv; parser aceita Firm Name/Country/From Date e SUPP_NAME/COUNTRY_NAME/DEBAR_FROM_DATE.

**Chave natural / namespace:** ID oficial do impedimento/fornecedor quando disponível; alternativa nome original+país+início deve ganhar namespace world_bank e controle de aliases.

Normalização:

- Nomes e aliases internacionais não são identidade brasileira comprovada.
- Período e fundamento explícitos; indefinido não vira data arbitrária.
- Preservar impedimento original versus reconhecimento cruzado por outra instituição.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `InternationalSanction` | sanction_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company\|Person` → `SANCIONADA_INTERNACIONALMENTE` → `InternationalSanction` | Documento registral/ID forte validado com país e período | Nome é pista de busca, não prova de correspondência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/world_bank.py`
- `config/sources/world_bank.yml`
- `etl/src/bracc_etl/pipelines/world_bank.py`
- `etl/tests/test_world_bank_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Resolver endpoint oficial de exportação e paginação antes de automatizar.
1. Documentar mapeamento dos dois layouts aceitos e detectar schema novo.
1. Adicionar namespace estável ao sanction_id e constraint InternationalSanction.
1. Criar etapa opcional de resolução documental com país, registro legal e evidência adicional.
1. Versionar renovações/encerramentos sem apagar episódios anteriores.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Lista paginada é conciliada com total divulgado.
- [ ] Mesmo nome em países diferentes não é fundido.
- [ ] Reprocessamento preserva episódios e datas.
- [ ] Nenhuma associação brasileira é criada só por semelhança nominal.

## Riscos e decisões pendentes

- Pipeline cadastra registros internacionais sem vincular Company/Person.
- Página pública não é endpoint de CSV; recurso final precisa inspeção.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/world_bank.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_world_bank_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
