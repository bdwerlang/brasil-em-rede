# senado — Senado CEAPS expenses

Cadastrar despesas CEAPS do Senado com identidade parlamentar oficial e fornecedor documentado.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `senado`.
- Ordem topológica: **19**; onda de execução: **2**; prioridade temática inicial: 2.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://www12.senado.leg.br/dados-abertos](https://www12.senado.leg.br/dados-abertos).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/senado.py](../../../etl/src/bracc_etl/pipelines/senado.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_senado_pipeline.py](../../../etl/tests/test_senado_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www12.senado.leg.br/dados-abertos](https://www12.senado.leg.br/dados-abertos) | Entrada atualmente cadastrada para Senado CEAPS expenses. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Baixar arquivos CEAPS por ano e cadastro oficial de parlamentares; converter cadastro para lookup por código, não por nome isolado.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** CSV CEAPS e JSON/XML oficial de parlamentares convertido para parlamentares.json.
- **Partições e backfill:** Ano e mês de despesa; cadastro por legislatura e vigência.
- **Retomada e deduplicação de download:** Checkpoint por ano e mês de despesa; cadastro por legislatura e vigência; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Fallback atual liga GASTOU por nome; arquivo parlamentares.json não garante unicidade se lookup permanecer nominal.
- Hook de link_persons ausente.
- Bootstrap só verifica presença em data/senado/*; não baixa, não valida schema, não verifica completude e não comprova carga.

## Contrato de ingestão

**Entrada esperada:** data/senado/*.csv; Latin-1, ponto e vírgula e primeira linha descritiva ignorada; parlamentares.json opcional para identidade.

**Chave natural / namespace:** Código oficial da despesa/documento + parcela, com namespace senado; substituir hash nome/data/fornecedor/valor.

Normalização:

- Preservar código de senador e mandato; CPF completo quando houver no dado oficial.
- Tratar estorno, glosa e parcela sem apagar valor bruto.
- Normalizar fornecedores PF/PJ e CNPJ com letras.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Expense` | expense_id | existing |
| `Person` | cpf | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person` → `GASTOU` → `Expense` | Proposto: código oficial de senador ou CPF completo; atual contém fallback por nome | Desativar fallback nominal antes da carga. | existing |
| `Company\|Person` → `FORNECEU` → `Expense` | CNPJ/CPF completo do fornecedor | Conservar documento de despesa e competência. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/senado.py`
- `config/sources/senado.yml`
- `etl/src/bracc_etl/pipelines/senado.py`
- `etl/tests/test_senado_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Criar aquisição anual CEAPS e de parlamentares com versionamento do lookup.
1. Remover MATCH Person.name do fallback GASTOU, substituindo por código oficial e vínculo com data do mandato.
1. Reformular expense_id com identificador do documento para evitar colisões.
1. Adicionar constraints e religação idempotente aos fornecedores e parlamentares.
1. Exigir métrica de despesas sem parlamentar resolvido e de notas retificadas.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Homônimos ou variações de nome não transferem despesa entre parlamentares.
- [ ] Documento repetido como atualização substitui versão sem duplicar reembolso.
- [ ] Despesas sem CPF continuam ligadas ao registro oficial de senador.
- [ ] Total anual líquido concilia com a exportação oficial.

## Riscos e decisões pendentes

- Fallback atual liga GASTOU por nome; arquivo parlamentares.json não garante unicidade se lookup permanecer nominal.
- Hook de link_persons ausente.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/senado.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_senado_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
