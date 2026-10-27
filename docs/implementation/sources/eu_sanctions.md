# eu_sanctions — EU sanctions

Cadastrar a lista consolidada de sanções financeiras da União Europeia com identidade lógica, regulamento e aliases.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `eu_sanctions`.
- Ordem topológica: **114**; onda de execução: **6**; prioridade temática inicial: 6.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions](https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/eu_sanctions.py](../../../etl/src/bracc_etl/pipelines/eu_sanctions.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_eu_sanctions_pipeline.py](../../../etl/tests/test_eu_sanctions_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions](https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions) | Entrada atualmente cadastrada para EU sanctions. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir recurso oficial da lista consolidada e requisitos atuais de acesso, baixar CSV/XML e regulamentos referidos.
- **Autenticação:** Validar acesso ao recurso oficial: se exigir token, usar variável de ambiente e registrar origem/expiração; não assumir acesso anônimo nem embutir token.
- **Formato bruto:** CSV/XML oficial conforme recurso vigente; preservar cabeçalho e codificação.
- **Partições e backfill:** Snapshot, entidade lógica, alias e regulamento; não contar cada alias como pessoa diferente.
- **Retomada e deduplicação de download:** Checkpoint por snapshot, entidade lógica, alias e regulamento; não contar cada alias como pessoa diferente; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Verificar alteração diariamente e publicar versão quando a lista mudar; cadência mensal do registro não garante atualização sancionadora.

Limites e pré-condições:

- Acesso efetivo do recurso oficial pode exigir credencial/token a validar.
- Vínculos atuais por Person.name e Company.razao_social são inseguros.
- Bootstrap só verifica presença em data/eu_sanctions/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/eu_sanctions/eu_sanctions.csv; ponto e vírgula, UTF-8 BOM; aliases de cabeçalho antigo/novo no parser.

**Chave natural / namespace:** Entity_LogicalId oficial em namespace UE; hash atual nome/programa/regulamento muda com aliases e pode fragmentar um sancionado.

Normalização:

- Agrupar aliases pelo identificador lógico oficial, mantendo grafias e idiomas.
- Datas de nascimento e documentos com país/tipo são evidências; nome isolado não identifica brasileiro.
- Distinguir vigência do regulamento, data da inclusão e publicação.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `InternationalSanction` | sanction_id | existing |
| `Person` | cpf | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person\|Company` → `SANCIONADA_INTERNACIONALMENTE` → `InternationalSanction` | Proposto: documento/ID forte e país; atual usa nome | Desativar vínculo nominal e preservar aliases como evidências. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/eu_sanctions.py`
- `config/sources/eu_sanctions.yml`
- `etl/src/bracc_etl/pipelines/eu_sanctions.py`
- `etl/tests/test_eu_sanctions_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Validar URL do recurso e eventual requisito de token do distribuidor oficial, sem presumir acesso anônimo.
1. Implementar downloader versionado e parser que não pule linhas sem contabilização.
1. Trocar ID por identificador lógico e criar constraint InternationalSanction.
1. Remover MATCH nominal de pessoa/empresa e criar etapa de candidatos com evidências compostas.
1. Atualizar alterações de regulamento e exclusões sem apagar histórico.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Vários aliases da mesma Entity_LogicalId produzem um sancionado.
- [ ] Homônimo no Brasil não recebe relação definitiva.
- [ ] Mudança de regulamento preserva entidade e histórico.
- [ ] Falha de acesso é separada de CSV vazio e impede snapshot completo.

## Riscos e decisões pendentes

- Acesso efetivo do recurso oficial pode exigir credencial/token a validar.
- Vínculos atuais por Person.name e Company.razao_social são inseguros.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/eu_sanctions.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_eu_sanctions_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
