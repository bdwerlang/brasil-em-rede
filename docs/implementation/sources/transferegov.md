# transferegov — TransfereGov emendas e convenios

Cadastrar emendas, favorecidos e convênios e representar o caminho autor → emenda → beneficiário/convênio.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `transferegov`.
- Ordem topológica: **24**; onda de execução: **2**; prioridade temática inicial: 2.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://www.transferegov.sistema.gov.br/portal/download-de-dados](https://www.transferegov.sistema.gov.br/portal/download-de-dados).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/transferegov.py](../../../etl/src/bracc_etl/pipelines/transferegov.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_transferegov_pipeline.py](../../../etl/tests/test_transferegov_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.transferegov.sistema.gov.br/portal/download-de-dados](https://www.transferegov.sistema.gov.br/portal/download-de-dados) | Entrada atualmente cadastrada para TransfereGov emendas e convenios. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Resolver os dumps oficiais Transferegov e os três recursos de emendas efetivamente usados; registrar provedor de cada arquivo e criar adaptadores separados se forem CGU.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** CSV compactado dos sistemas de transferência e arquivos canônicos atuais.
- **Partições e backfill:** Sistema/provedor, exercício e tabela; convênios, propostas e pagamentos em etapas independentes.
- **Retomada e deduplicação de download:** Checkpoint por sistema/provedor, exercício e tabela; convênios, propostas e pagamentos em etapas independentes; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Contrato de entrada não comprova correspondência com dumps Transferegov atuais.
- Chaves compartilhadas de Amendment podem sobrescrever propriedades vindas de outras fontes.
- Bootstrap só verifica presença em data/transferegov/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/transferegov/EmendasParlamentares.csv, EmendasParlamentares_PorFavorecido.csv, EmendasParlamentares_Convenios.csv; Latin-1 e ponto e vírgula; conteúdo aparenta exportação de emendas do Portal, exigindo confirmar proveniência.

**Chave natural / namespace:** Emenda por exercício + código oficial; Convenio por identificador oficial do instrumento; favorecimento por emenda + favorecido + competência/evento.

Normalização:

- Códigos de autor não são CPF: preservar author_key em namespace parlamentar.
- Documento completo do favorecido normalizado com distinção PF/PJ; mascarado fica em ocorrência separada.
- Não somar valor total da emenda repetido em cada favorecido ou convênio.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Amendment` | amendment_id | existing |
| `Person` | author_key | existing |
| `Company` | cnpj | existing |
| `Person` | cpf | existing |
| `Convenio` | convenio_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person` → `AUTOR_EMENDA` → `Amendment` | Código oficial do autor e emenda | Usar identidade parlamentar contextual até prova de CPF/ID de Casa. | existing |
| `Amendment` → `BENEFICIOU` → `Company\|Person` | Documento completo do favorecido e código da emenda | Manter valor e estágio de execução, sem duplicar total. | existing |
| `Amendment` → `GEROU_CONVENIO` → `Convenio` | Código oficial da emenda no instrumento | Relação declarada no recurso, sem inferência por objeto. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/transferegov.py`
- `config/sources/transferegov.yml`
- `etl/src/bracc_etl/pipelines/transferegov.py`
- `etl/tests/test_transferegov_acquisition.py`

Tarefas específicas, em ordem:

1. Auditar a origem real dos três arquivos exigidos para evitar atribuir dumps CGU ao sistema errado.
1. Baixar tabelas e dicionários oficiais com integridade entre chaves emenda/favorecido/convênio.
1. Padronizar amendment_id com crosswalk do Portal e SIOP, sem dependência circular de cargas.
1. Criar histórico de valores empenhado/liquidado/pago e preservar cada granularidade.
1. Religar autores via IDs oficiais das Casas quando disponíveis; manter homônimos separados.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Nenhum favorecido ou convênio aponta a uma emenda inexistente sem pendência registrada.
- [ ] Somas por emenda conferem com o mesmo estágio de execução publicado.
- [ ] Author_key não é tratado como CPF nem vinculado por nome.
- [ ] CSV de provedor diferente leva proveniência própria.

## Riscos e decisões pendentes

- Contrato de entrada não comprova correspondência com dumps Transferegov atuais.
- Chaves compartilhadas de Amendment podem sobrescrever propriedades vindas de outras fontes.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/transferegov.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_transferegov_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
