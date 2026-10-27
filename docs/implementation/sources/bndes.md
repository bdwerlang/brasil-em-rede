# bndes — BNDES financings

Cadastrar operações de financiamento BNDES e ligar beneficiário, contrato, valor contratado e desembolsado.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `bndes`.
- Ordem topológica: **55**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://www.bndes.gov.br/wps/portal/site/home/transparencia/dados](https://www.bndes.gov.br/wps/portal/site/home/transparencia/dados).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/bndes.py](../../../etl/src/bracc_etl/pipelines/bndes.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_bndes_pipeline.py](../../../etl/tests/test_bndes_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.bndes.gov.br/wps/portal/site/home/transparencia/dados](https://www.bndes.gov.br/wps/portal/site/home/transparencia/dados) | Entrada atualmente cadastrada para BNDES financings. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Resolver exportação oficial de operações não automáticas; inventariar automáticas/indiretas como expansão com layout próprio.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** CSV/planilha oficial adaptada ao CSV esperado.
- **Partições e backfill:** Modalidade de operação, ano de contratação e snapshot; preservar estágio de desembolso.
- **Retomada e deduplicação de download:** Checkpoint por modalidade de operação, ano de contratação e snapshot; preservar estágio de desembolso; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Pipeline não cobre todo o BNDES embora nome genérico possa sugerir isso.
- Semântica de contrato e agente/cliente deve ser confirmada no dicionário.
- Bootstrap só verifica presença em data/bndes/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/bndes/operacoes-nao-automaticas.csv; ponto e vírgula, Latin-1; somente operações não automáticas cobertas pelo parser atual.

**Chave natural / namespace:** Finance.finance_id = bndes_<contrato>; ampliar para item/operação se contrato não for grão único.

Normalização:

- Separar valor contratado e desembolsado, taxa, moeda, datas e tipo de operação.
- CNPJ do cliente com letras e zeros preservados; agente financeiro não é beneficiário automaticamente.
- Mudanças no desembolso são versões de uma operação, não novos financiamentos.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Finance` | finance_id | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `RECEBEU_EMPRESTIMO` → `Finance` | CNPJ do cliente e contrato BNDES | Valores contratado/desembolsado e data preservados. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/bndes.py`
- `config/sources/bndes.yml`
- `etl/src/bracc_etl/pipelines/bndes.py`
- `etl/tests/test_bndes_acquisition.py`

Tarefas específicas, em ordem:

1. Implementar aquisição de operações não automáticas e comparar cobertura real com catálogo.
1. Confirmar unicidade do número de contrato e inserir item quando necessário.
1. Versionar desembolsos e atualizar saldos sem duplicar valor contratado.
1. Padronizar CNPJ e evitar sobrescrever cadastro oficial com nome do financiamento.
1. Adicionar modo separado para automáticas somente após descobrir dados e contrato próprios.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Total contratado e total desembolsado conciliam separadamente.
- [ ] Atualização de desembolso não cria segundo Finance.
- [ ] Um cliente com várias operações mantém contratos distintos.
- [ ] Relatório declara explicitamente cobertura não automática.

## Riscos e decisões pendentes

- Pipeline não cobre todo o BNDES embora nome genérico possa sugerir isso.
- Semântica de contrato e agente/cliente deve ser confirmada no dicionário.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/bndes.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_bndes_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
