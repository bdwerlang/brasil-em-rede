# icij — ICIJ offshore leaks

Cadastrar rede Offshore Leaks com entidades, officers, intermediários e relações, preservando investigação e fonte documental.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `icij`.
- Ordem topológica: **115**; onda de execução: **6**; prioridade temática inicial: 6.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **XL**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://offshoreleaks.icij.org/pages/database](https://offshoreleaks.icij.org/pages/database).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/icij.py](../../../etl/src/bracc_etl/pipelines/icij.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_icij_pipeline.py](../../../etl/tests/test_icij_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://offshoreleaks.icij.org/pages/database](https://offshoreleaks.icij.org/pages/database) | Entrada atualmente cadastrada para ICIJ offshore leaks. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Baixar pacote oficial ICIJ de CSVs e documentação/licença; manter edição e componentes do mesmo pacote.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** ZIP com CSVs de nós e relações.
- **Partições e backfill:** Edição, investigação e tabela; preservar nós fora do Brasil para manter contexto relacional.
- **Retomada e deduplicação de download:** Checkpoint por edição, investigação e tabela; preservar nós fora do brasil para manter contexto relacional; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Por nova edição e revisão da fonte, com verificação anual.

Limites e pré-condições:

- Conector atual usa o mesmo label para intermediários e officers; risco de perda de papel.
- Não existe ligação implementada à base brasileira; resolução requer etapa nova.
- Fonte deve preservar termos/licença e contexto investigativo.
- Bootstrap só verifica presença em data/icij/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Divergência de identidade: runner/registro=icij; Pipeline.source_id=icij_offshore_leaks. Reconciliar runs e proveniência preservando alias do provedor.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/icij/nodes-entities.csv, nodes-officers.csv, nodes-intermediaries.csv e relationships.csv; IDs node_id e referências start/end.

**Chave natural / namespace:** Namespace do dataset/investigação + node_id; relação por IDs de origem/destino + tipo + identificador/atributos do vínculo.

Normalização:

- Identificadores ICIJ não são CPF/CNPJ; nomes não unem entidades nacionais automaticamente.
- Distinguir officer e intermediary mesmo que ambos usem label atual OffshoreOfficer.
- Preservar jurisdição, país, datas e tipo original de relacionamento.
- Presença no vazamento não comprova ilegalidade; relações representam registros do dataset.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `OffshoreEntity` | offshore_id | existing |
| `OffshoreOfficer` | offshore_officer_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `OffshoreOfficer` → `OFFICER_OF` → `OffshoreEntity` | node_id_start/end e tipo original da relação | Preservar investigação e descrição da relação. | existing |
| `OffshoreOfficer` → `INTERMEDIARY_OF` → `OffshoreEntity` | ID do intermediário e entidade nos CSVs | Distinguir papel de intermediário, sem presumir sócio ou beneficiário final. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/icij.py`
- `config/sources/icij.yml`
- `etl/src/bracc_etl/pipelines/icij.py`
- `etl/tests/test_icij_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Implementar aquisição coerente dos quatro recursos com versão e validação de chaves estrangeiras.
1. Criar constraints OffshoreEntity.offshore_id e OffshoreOfficer.offshore_officer_id.
1. Separar papéis de intermediário/officer e manter tipo de relação original.
1. Registrar relações sem nós como pendências com origem, nunca descartar sem métrica.
1. Criar correspondência opcional com Brasil apenas por documento/registro corroborado e revisão, sem merge por nome.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Toda relação válida aponta a dois nós existentes ou consta em relatório de pendências.
- [ ] Officers e intermediários mantêm papéis distintos.
- [ ] Mesma grafia em duas jurisdições não provoca fusão.
- [ ] Reexecução do pacote mantém números de nós e vínculos por investigação.

## Riscos e decisões pendentes

- Conector atual usa o mesmo label para intermediários e officers; risco de perda de papel.
- Não existe ligação implementada à base brasileira; resolução requer etapa nova.
- Fonte deve preservar termos/licença e contexto investigativo.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/icij.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_icij_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
