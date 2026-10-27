# camara — Camara CEAP expenses

Cadastrar despesas CEAP da Câmara e relacionar parlamentar, documento de despesa e fornecedor.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `camara`.
- Ordem topológica: **14**; onda de execução: **2**; prioridade temática inicial: 2.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dadosabertos.camara.leg.br/](https://dadosabertos.camara.leg.br/).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/camara.py](../../../etl/src/bracc_etl/pipelines/camara.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_camara_pipeline.py](../../../etl/tests/test_camara_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dadosabertos.camara.leg.br/](https://dadosabertos.camara.leg.br/) | Entrada atualmente cadastrada para Camara CEAP expenses. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Baixar arquivos anuais CEAP e cadastro de deputados em dados abertos oficiais, guardando referências de documento e período.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** CSV/ZIP CEAP e JSON do cadastro parlamentar.
- **Partições e backfill:** Ano de despesa e deputado; correções de exercícios recentes em snapshots versionados.
- **Retomada e deduplicação de download:** Checkpoint por ano de despesa e deputado; correções de exercícios recentes em snapshots versionados; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Chave derivada atual é insuficiente para múltiplos documentos iguais em data/valor.
- Hook link_persons.cypher configurado não existe.
- Bootstrap só verifica presença em data/camara/*; não baixa, não valida schema, não verifica completude e não comprova carga.

## Contrato de ingestão

**Entrada esperada:** data/camara/*.csv, ponto e vírgula, UTF-8 BOM; campos txNomeParlamentar, nuDeputadoId, txtFornecedor e documentos/valores conforme parser.

**Chave natural / namespace:** Proposto: código oficial do documento/reembolso + parcela; hash atual deputado/data/fornecedor/valor pode unir notas diferentes.

Normalização:

- Identidade parlamentar por ID da Câmara, CPF somente quando completo e validado.
- Separar valor do documento, glosa, líquido e reembolso/parcela.
- Documento do fornecedor com PF/PJ e CNPJ alfanumérico; não unir homônimos.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Expense` | expense_id | existing |
| `Person` | cpf/deputy_id | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person` → `GASTOU` → `Expense` | CPF completo ou ID oficial da Câmara | ID parlamentar identifica o registro; não vincular a outra pessoa apenas por nome. | existing |
| `Company\|Person` → `FORNECEU` → `Expense` | CNPJ/CPF completo do fornecedor | Nota/recibo prova a transação, sem inferir sociedade ou vínculo pessoal. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/camara.py`
- `config/sources/camara.yml`
- `etl/src/bracc_etl/pipelines/camara.py`
- `etl/tests/test_camara_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Implementar descoberta e download dos CSVs de todos os anos efetivamente publicados.
1. Rever expense_id para código de documento e parcela, com namespace camara.
1. Adicionar unicidade Expense.expense_id e Person.deputy_id ou dimensão parlamentar própria.
1. Substituir hook ausente por ligação documentada de ID da Câmara a CPF; medir fornecedores sem correspondência.
1. Guardar URL de nota/recibo e versão da linha para auditoria.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Duas notas do mesmo deputado, fornecedor, data e valor continuam distintas.
- [ ] Reprocessar parcela/glosa não duplica despesas.
- [ ] Parlamentar sem CPF mantém ID oficial e suas despesas.
- [ ] CNPJ alfanumérico do fornecedor preserva relação FORNECEU.

## Riscos e decisões pendentes

- Chave derivada atual é insuficiente para múltiplos documentos iguais em data/valor.
- Hook link_persons.cypher configurado não existe.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/camara.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_camara_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
