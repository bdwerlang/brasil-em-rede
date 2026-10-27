# stf — STF court data

Cadastrar processos/decisões do STF com relatoria oficial e ligação processual por identificador, sem atribuir partes por nome.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `stf`.
- Ordem topológica: **119**; onda de execução: **6**; prioridade temática inicial: 6.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://basedosdados.org/dataset/br-stf-corte-aberta](https://basedosdados.org/dataset/br-stf-corte-aberta).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/stf.py](../../../etl/src/bracc_etl/pipelines/stf.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_stf_pipeline.py](../../../etl/tests/test_stf_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://basedosdados.org/dataset/br-stf-corte-aberta](https://basedosdados.org/dataset/br-stf-corte-aberta) | Entrada atualmente cadastrada para STF court data. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir exportação oficial STF/Corte Aberta, validar recurso e layout; alternativa Base dos Dados requer projeto e consulta versionada, sem inventar acesso.
- **Autenticação:** Preferir recurso oficial público se disponível; alternativa BigQuery depende de projeto/permissões e credencial, com estimativa de custo antes da extração.
- **Formato bruto:** CSV/JSON oficial quando disponível; exportação BQ derivada apenas explicitamente; decisoes.csv canônico.
- **Partições e backfill:** Processo, ano e decisão; mudanças de relator como eventos temporais.
- **Retomada e deduplicação de download:** Checkpoint por processo, ano e decisão; mudanças de relator como eventos temporais; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Registro aponta Base dos Dados e bootstrap declara credencial Google; disponibilidade de fonte oficial ainda precisa validação.
- LegalCase não possui constraint e relação atual é nominal.
- Bootstrap só verifica presença em data/stf/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/stf/decisoes.csv; classe, numero, ano, relator, data_decisao, tipo_decisao, andamento, assunto e procedencia.

**Chave natural / namespace:** Processo por STF + classe/número/número CNJ; decisão por ID oficial ou processo + data + órgão/tipo/documento; chave atual classe/número/ano pode colapsar decisões.

Normalização:

- Relator por identificador/cadastro oficial de ministro e vigência, nunca Person.name isolado.
- Separar processo e decisão para não sobrescrever múltiplos julgamentos.
- Número CNJ permite crosswalk com DataJud, sem usar similaridade de partes/assunto.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `LegalCase` | case_id | existing |
| `Person` | cpf | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person` → `RELATOR_DE` → `LegalCase` | Proposto: ID oficial de ministro; atual usa nome | Substituir associação nominal por cadastro oficial e vigência. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/stf.py`
- `config/sources/stf.yml`
- `etl/src/bracc_etl/pipelines/stf.py`
- `etl/tests/test_stf_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Resolver fonte oficial e contrato de decisão/processo antes de automatizar.
1. Separar nós de processo e decisão ou criar coleção de decisões idempotente com constraint.
1. Adicionar namespace STF à chave LegalCase e alinhar crosswalk para JudicialCase quando número CNJ conferir.
1. Substituir RELATOR_DE por nome por registro oficial de ministro/mandato.
1. Versionar decisão e relatoria e manter documento oficial.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Duas decisões no mesmo processo coexistem.
- [ ] Homônimo de ministro não recebe RELATOR_DE.
- [ ] Ligação com DataJud só ocorre por número CNJ/tribunal validado.
- [ ] Fonte secundária é identificada como tal com consulta e data de extração.

## Riscos e decisões pendentes

- Registro aponta Base dos Dados e bootstrap declara credencial Google; disponibilidade de fonte oficial ainda precisa validação.
- LegalCase não possui constraint e relação atual é nominal.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/stf.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_stf_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
