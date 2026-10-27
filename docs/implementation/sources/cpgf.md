# cpgf — CPGF gov card expenses

Cadastrar transações do cartão de pagamento federal, incluindo portadores mascarados sem tentar identificá-los.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `cpgf`.
- Ordem topológica: **16**; onda de execução: **2**; prioridade temática inicial: 2.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://portaldatransparencia.gov.br/download-de-dados/cpgf](https://portaldatransparencia.gov.br/download-de-dados/cpgf).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/cpgf.py](../../../etl/src/bracc_etl/pipelines/cpgf.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_cpgf_pipeline.py](../../../etl/tests/test_cpgf_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://portaldatransparencia.gov.br/download-de-dados/cpgf](https://portaldatransparencia.gov.br/download-de-dados/cpgf) | Entrada atualmente cadastrada para CPGF gov card expenses. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Baixar ZIPs mensais CPGF da CGU, preservar cobertura da competência e transformar cabeçalhos sem descartar transações legítimas.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** ZIP/CSV mensal; GovCardExpense normalizado.
- **Partições e backfill:** Ano-mês e unidade gestora; conjunto de arquivos por competência.
- **Retomada e deduplicação de download:** Checkpoint por ano-mês e unidade gestora; conjunto de arquivos por competência; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Ausência de CPF integral impede identidade direta do portador, mas não impede cadastrar transações.
- Schema não define unicidade de GovCardExpense.
- Bootstrap só verifica presença em data/cpgf/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/cpgf/*.csv; ponto e vírgula, Latin-1; aliases de portador, órgão, favorecido, valor e data implementados.

**Chave natural / namespace:** ID oficial de transação quando publicado; alternativa órgão/unidade + competência + registro de transação; não usar CPF mascarado como chave pessoal.

Normalização:

- CPF parcial permanece atributo de transação/portador contextual, não Person.cpf.
- Distinguir saque, compra e estorno; valores negativos não devem ser tratados como erro automaticamente.
- CNPJ do favorecido apenas quando divulgado e validado, sem inferir fornecedor por descrição.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `GovCardExpense` | expense_id | existing |
| `Person` | cpf | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person` → `GASTOU_CARTAO` → `GovCardExpense` | CPF completo validado do portador | Máscara ou nome não permitem atribuir gasto a Person. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/cpgf.py`
- `config/sources/cpgf.yml`
- `etl/src/bracc_etl/pipelines/cpgf.py`
- `etl/tests/test_cpgf_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Implementar aquisição de competências e validação do ZIP completo.
1. Reavaliar hash atual CPF/data/valor/descrição para transações repetidas distintas.
1. Adicionar constraint GovCardExpense.expense_id e registro contextual de portador mascarado.
1. Acrescentar ligação de fornecedor quando o layout tiver documento completo, com evidência da coluna.
1. Conciliar compras/saques/estornos e total da competência, sem promover transação a indício de irregularidade.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Portadores diferentes com mesma máscara não se tornam uma Person.
- [ ] Duas transações idênticas em descrição/data/valor mantêm identidade se IDs oficiais diferentes.
- [ ] Soma líquida da competência confere com estornos.
- [ ] Reexecução não duplica GASTOU_CARTAO.

## Riscos e decisões pendentes

- Ausência de CPF integral impede identidade direta do portador, mas não impede cadastrar transações.
- Schema não define unicidade de GovCardExpense.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/cpgf.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_cpgf_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
