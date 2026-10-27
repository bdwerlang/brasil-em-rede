# cvm_funds — CVM fund registry

Cadastrar fundos e responsáveis CVM com vigência, distinguindo fundo, classe, administrador e gestor.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `cvm_funds`.
- Ordem topológica: **59**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dados.cvm.gov.br/dados/FI/](https://dados.cvm.gov.br/dados/FI/).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/cvm_funds.py](../../../etl/src/bracc_etl/pipelines/cvm_funds.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_cvm_funds_pipeline.py](../../../etl/tests/test_cvm_funds_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dados.cvm.gov.br/dados/FI/](https://dados.cvm.gov.br/dados/FI/) | Entrada atualmente cadastrada para CVM fund registry. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir arquivo cadastral CVM vigente e tabelas de classes/subclasses; baixar versão e dicionário de cada recurso.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** CSV/ZIP cadastral CVM, com compatibilidade explícita do cad_fi legado.
- **Partições e backfill:** Snapshot, tipo de fundo e classes/subclasses; responsabilidades por período.
- **Retomada e deduplicação de download:** Checkpoint por snapshot, tipo de fundo e classes/subclasses; responsabilidades por período; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Arquivo cad_fi legado pode não representar todo o modelo cadastral vigente.
- Relações atuais não guardam vigência.
- Bootstrap só verifica presença em data/cvm_funds/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/cvm_funds/cad_fi.csv; Latin-1, ponto e vírgula; campos CNPJ_FUNDO, DENOM_SOCIAL, ADMIN/GESTOR e seus documentos conforme parser.

**Chave natural / namespace:** Fund.fund_cnpj para cadastro legado; adaptar para identificadores oficiais de fundo/classe/subclasse quando layout atual exigir.

Normalização:

- CNPJ alfanumérico comum para fundos e prestadores; não perder zeros.
- Separar administrador de gestor e preservar intervalos de responsabilidade.
- Não atribuir administração passada ao prestador atual numa operação histórica.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Fund` | fund_cnpj | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `ADMINISTRA` → `Fund` | CNPJ oficial do administrador e do fundo | Acrescentar vigência e papel documental. | existing |
| `Company` → `GERE` → `Fund` | CNPJ oficial do gestor e do fundo | Não confundir gestão e administração. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/cvm_funds.py`
- `config/sources/cvm_funds.yml`
- `etl/src/bracc_etl/pipelines/cvm_funds.py`
- `etl/tests/test_cvm_funds_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Validar cad_fi e evolução do cadastro diante dos novos layouts de fundos/classes.
1. Implementar aquisição e adaptadores por versão do dicionário.
1. Adicionar constraint Fund.fund_cnpj e IDs próprios de classe/subclasse se necessários.
1. Versionar ADMINISTRA/GERE com data inicial/final e origem.
1. Cruzar prestadores por CNPJ com Company sem vincular por razão social.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Administrador e gestor diferentes geram papéis distintos.
- [ ] Mudança de administrador mantém histórico com vigência.
- [ ] Identificadores alfanuméricos mantêm junção com CNPJ.
- [ ] Classes distintas não são fundidas somente por nome.

## Riscos e decisões pendentes

- Arquivo cad_fi legado pode não representar todo o modelo cadastral vigente.
- Relações atuais não guardam vigência.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/cvm_funds.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_cvm_funds_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
