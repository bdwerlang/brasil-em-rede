# cepim — CEPIM barred NGOs

Cadastrar impedimentos de entidades sem fins lucrativos e associá-los ao convênio e ao CNPJ informado.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `cepim`.
- Ordem topológica: **4**; onda de execução: **1**; prioridade temática inicial: 1.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **S**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://portaldatransparencia.gov.br/download-de-dados/cepim](https://portaldatransparencia.gov.br/download-de-dados/cepim).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/cepim.py](../../../etl/src/bracc_etl/pipelines/cepim.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_cepim_pipeline.py](../../../etl/tests/test_cepim_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://portaldatransparencia.gov.br/download-de-dados/cepim](https://portaldatransparencia.gov.br/download-de-dados/cepim) | Entrada atualmente cadastrada para CEPIM barred NGOs. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Adquirir snapshot CEPIM no catálogo da CGU e preservar registros de pendência por convênio.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** ZIP/CSV de impedimentos, convertido para cepim.csv.
- **Partições e backfill:** Snapshot e órgão/convênio; sem presumir que a lista vigente contém todo o histórico.
- **Retomada e deduplicação de download:** Checkpoint por snapshot e órgão/convênio; sem presumir que a lista vigente contém todo o histórico; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Lista retrata impedimentos administrativos; ausência no snapshot não prova regularidade retroativa.
- Bootstrap só verifica presença em data/cepim/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/cepim/cepim.csv, ponto e vírgula, Latin-1; NOME ENTIDADE, CNPJ e referência do convênio conforme parser.

**Chave natural / namespace:** Identificador CEPIM ou CNPJ + número de convênio + órgão responsável, versionado por situação.

Normalização:

- CNPJ em formato canônico com letras e zeros preservados.
- Conservar número do convênio e órgão impedidor; distinguir entidade e evento impeditivo.
- Usar data de disponibilização quando data do ato estiver ausente, sem inventá-la.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `BarredNGO` | ngo_id | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `IMPEDIDA` → `BarredNGO` | CNPJ completo normalizado | Manter referência do convênio e situação da restrição. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/cepim.py`
- `config/sources/cepim.yml`
- `etl/src/bracc_etl/pipelines/cepim.py`
- `etl/tests/test_cepim_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Criar downloader do recurso CEPIM e validador de cabeçalhos.
1. Garantir estabilidade de ngo_id por convênio e incluir órgão se necessário para evitar colisões.
1. Criar constraint BarredNGO.ngo_id e atualizar situação a cada snapshot.
1. Preparar vínculo opcional ao Convenio já ingerido por transferegov por identificador exato, sem torná-lo dependência obrigatória.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Duas restrições de uma mesma entidade em convênios diferentes permanecem distintas.
- [ ] O mesmo CNPJ converge para Company existente.
- [ ] Desaparecimento da lista muda disponibilidade observada e não apaga o histórico automaticamente.

## Riscos e decisões pendentes

- Lista retrata impedimentos administrativos; ausência no snapshot não prova regularidade retroativa.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/cepim.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_cepim_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
