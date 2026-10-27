# ofac — OFAC sanctions

Cadastrar a lista SDN do Tesouro dos EUA com programas, identificadores e aliases, mantendo identidade internacional separada da base brasileira.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `ofac`.
- Ordem topológica: **117**; onda de execução: **6**; prioridade temática inicial: 6.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://home.treasury.gov/policy-issues/financial-sanctions/sdn-list-data-files](https://home.treasury.gov/policy-issues/financial-sanctions/sdn-list-data-files).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/ofac.py](../../../etl/src/bracc_etl/pipelines/ofac.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_ofac_pipeline.py](../../../etl/tests/test_ofac_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://home.treasury.gov/policy-issues/financial-sanctions/sdn-list-data-files](https://home.treasury.gov/policy-issues/financial-sanctions/sdn-list-data-files) | Entrada atualmente cadastrada para OFAC sanctions. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir na página oficial OFAC SDN os recursos CSV/XML e complementos de nomes/documentos; baixar conjunto coerente por versão.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** CSV SDN sem cabeçalho e recursos oficiais complementares CSV/XML.
- **Partições e backfill:** Snapshot da lista, entidade SDN e arquivo complementar; alterações e exclusões registradas.
- **Retomada e deduplicação de download:** Checkpoint por snapshot da lista, entidade sdn e arquivo complementar; alterações e exclusões registradas; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Verificar alteração diariamente e publicar versão quando a lista mudar; cadência mensal do registro não garante atualização sancionadora.

Limites e pré-condições:

- Parser atual só cadastra sanções e não possui ligação à base brasileira.
- Filtros de tipo e on_bad_lines=skip podem omitir registros sem controle.
- Fonte do registro prevê mensal, mas uma política de atualização diária/on-change deve ser avaliada para lista sancionadora.
- Bootstrap só verifica presença em data/ofac/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Divergência de identidade: runner/registro=ofac; Pipeline.source_id=ofac_sdn. Reconciliar runs e proveniência preservando alias do provedor.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/ofac/sdn.csv sem cabeçalho, 12 colunas posicionais SDN_COLUMNS, UTF-8; parser atual filtra sdn_type individual/entity.

**Chave natural / namespace:** InternationalSanction.sanction_id = ofac_<ent_num>; aliases/documentos têm IDs derivados do mesmo registro, sem trocar identidade pelo nome.

Normalização:

- Validar códigos reais de tipo SDN no dicionário, evitando excluir entidades por convenção textual incorreta.
- Preservar aliases, nacionalidades, datas e documentos com país e tipo.
- CPF/CNPJ brasileiros só geram correspondência quando completos e verificáveis; nomes geram revisão.
- Sanção internacional mantém programa, jurisdição e vigência, sem equivalência automática com impedimento brasileiro.

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
| `Person\|Company` → `SANCIONADA_INTERNACIONALMENTE` → `InternationalSanction` | Documento integral + país/emissor e ID OFAC | Apenas correspondência documentada; candidato nominal fica separado, sem SAME_AS. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/ofac.py`
- `config/sources/ofac.yml`
- `etl/src/bracc_etl/pipelines/ofac.py`
- `etl/tests/test_ofac_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Implementar aquisição do pacote SDN e complementos com verificação de integridade e data de publicação.
1. Reconciliar alias ofac_sdn com source_id ofac.
1. Criar constraint InternationalSanction.sanction_id e preservar IDs OFAC estáveis em mudança de nome.
1. Acrescentar etapa explícita de resolução internacional por documento/jurisdição e revisão de candidatos.
1. Registrar remoções como mudança de situação mantendo snapshot original.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Mudança de nome não altera ID OFAC.
- [ ] Tipos oficiais da lista são contabilizados sem exclusão silenciosa.
- [ ] Nome igual a pessoa brasileira não produz associação automática.
- [ ] Snapshot reprocessado mantém contagens por programa.

## Riscos e decisões pendentes

- Parser atual só cadastra sanções e não possui ligação à base brasileira.
- Filtros de tipo e on_bad_lines=skip podem omitir registros sem controle.
- Fonte do registro prevê mensal, mas uma política de atualização diária/on-change deve ser avaliada para lista sancionadora.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/ofac.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_ofac_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
