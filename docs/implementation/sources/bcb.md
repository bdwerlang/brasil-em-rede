# bcb — BCB penalties

Cadastrar penalidades administrativas do Banco Central com processo, sanção e instituição atingida.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `bcb`.
- Ordem topológica: **45**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dadosabertos.bcb.gov.br/dataset/processo-administrativo-sancionador---penalidades-aplicadas](https://dadosabertos.bcb.gov.br/dataset/processo-administrativo-sancionador---penalidades-aplicadas).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/bcb.py](../../../etl/src/bracc_etl/pipelines/bcb.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_bcb_pipeline.py](../../../etl/tests/test_bcb_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dadosabertos.bcb.gov.br/dataset/processo-administrativo-sancionador---penalidades-aplicadas](https://dadosabertos.bcb.gov.br/dataset/processo-administrativo-sancionador---penalidades-aplicadas) | Entrada atualmente cadastrada para BCB penalties. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir recurso oficial no catálogo do BCB, baixar CSV/API publicado e mapear ao contrato canônico.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** CSV/JSON oficial a validar; penalidades.csv canônico.
- **Partições e backfill:** Processo, data da decisão e snapshot; incluir alterações recursais em versões.
- **Retomada e deduplicação de download:** Checkpoint por processo, data da decisão e snapshot; incluir alterações recursais em versões; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Cobertura atual limitada a linhas com CNPJ integral.
- BCBPenalty não tem constraint única no schema.
- Bootstrap só verifica presença em data/bcb/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/bcb/penalidades.csv; ponto e vírgula, Latin-1; CNPJ, Nome Instituição, Tipo Penalidade, Valor Penalidade, Número Processo e Data Decisão.

**Chave natural / namespace:** ID oficial da penalidade ou processo + parte/documento + tipo + decisão; hash atual documento/processo/tipo precisa distinguir múltiplas decisões.

Normalização:

- Separar penalidade pecuniária e não pecuniária; valor ausente não é zero.
- Manter instância, data, recurso e situação quando disponibilizados.
- Preservar registro PF sem inventar CNPJ e suportar CNPJ alfanumérico para PJ.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `BCBPenalty` | penalty_id | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `BCB_PENALIZADA` → `BCBPenalty` | CNPJ integral e identificador do processo/decisão | Situação e tipo da penalidade ficam explícitos. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/bcb.py`
- `config/sources/bcb.yml`
- `etl/src/bracc_etl/pipelines/bcb.py`
- `etl/tests/test_bcb_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Resolver recurso vigente do dataset de processo administrativo sancionador.
1. Criar adaptador de nomes/tipos sem descartar penalidades não pecuniárias.
1. Rever penalty_id para várias decisões/tipos no mesmo processo e criar constraint BCBPenalty.
1. Separar fluxo PF, pois transformação atual só aceita PJ.
1. Associar por documento forte e conservar prova da decisão.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Advertência sem multa continua cadastrada.
- [ ] Duas decisões diferentes do mesmo processo não colidem.
- [ ] PJ associa à Company canônica e PF a Person somente com CPF válido.
- [ ] Retificação não duplica penalidade.

## Riscos e decisões pendentes

- Cobertura atual limitada a linhas com CNPJ integral.
- BCBPenalty não tem constraint única no schema.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/bcb.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_bcb_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
