# stj_dados_abertos — STJ open data

Cadastrar processos/decisões de dados abertos STJ e a relatoria comprovada, com identificadores próprios de cada decisão.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `stj_dados_abertos`.
- Ordem topológica: **120**; onda de execução: **6**; prioridade temática inicial: 6.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://dadosabertos.stj.jus.br/](https://dadosabertos.stj.jus.br/).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/stj_dados_abertos.py](../../../etl/src/bracc_etl/pipelines/stj_dados_abertos.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dadosabertos.stj.jus.br/](https://dadosabertos.stj.jus.br/) | Entrada atualmente cadastrada para STJ open data. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir conjuntos e recursos no catálogo oficial STJ; baixar arquivos publicados por coleção e adaptar o schema real, sem supor que o catálogo publica decisoes.csv pronto.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** CSV/JSON/ZIP oficial conforme recurso descoberto; CSV canônico interno.
- **Partições e backfill:** Coleção/dataset, período, processo e documento; distinguir jurisprudência/inteiro teor e metadados.
- **Retomada e deduplicação de download:** Checkpoint por coleção/dataset, período, processo e documento; distinguir jurisprudência/inteiro teor e metadados; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Pipeline presente não significa dados baixados; load_state local não foi verificado.
- MERGE Person por nome atual cria identidades não fundamentadas.
- Conjunto oficial ainda precisa ser escolhido e seu download final validado.
- Ausente do contrato bootstrap atual; incluir fonte, entradas e aquisição antes da execução integral.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/stj_dados_abertos/decisoes.csv obrigatório; CSV com cabeçalho canônico; campos de classe/número/ano/relator/decisão definidos pelo parser.

**Chave natural / namespace:** Processo STJ por registro/número CNJ e classe; decisão por identificador documental; hash atual stj:classe:número:ano não distingue decisões do mesmo processo.

Normalização:

- Preservar número de registro STJ, número CNJ, órgão julgador, relator e datas distintas.
- Não criar Person por nome do relator; usar cadastro oficial e identificador do ministro.
- Decisão e processo são entidades distintas para evitar sobrescrita.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `LegalCase` | case_id | existing |
| `Person` | nome (chave atual a remover) | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person` → `RELATOR_DE` → `LegalCase` | Proposto: ID ministro; atual MERGE por nome | Desativar criação de pessoa por nome e resolver relatoria no cadastro oficial. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/stj_dados_abertos.py`
- `config/sources/stj_dados_abertos.yml`
- `etl/src/bracc_etl/pipelines/stj_dados_abertos.py`
- `etl/tests/test_stj_dados_abertos_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Adicionar stj_dados_abertos ao contrato bootstrap, atualmente ausente apesar de existir no runner.
1. Inventariar catálogo oficial e escolher recurso cujo leiaute suporte os campos necessários.
1. Criar adaptador para decisoes.csv e teste de divergência de schema.
1. Separar IDs de processo/decisão e criar constraints LegalCase/decisão.
1. Remover MERGE Person{name:...} na relatoria e trocar por referência oficial.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Duas decisões do mesmo processo não colidem.
- [ ] Ministro é representado por cadastro oficial sem fusão por nome.
- [ ] Conector participa do bootstrap com manifesto e contrato específico.
- [ ] Arquivo ausente falha de forma explícita e não marca loaded.

## Riscos e decisões pendentes

- Pipeline presente não significa dados baixados; load_state local não foi verificado.
- MERGE Person por nome atual cria identidades não fundamentadas.
- Conjunto oficial ainda precisa ser escolhido e seu download final validado.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/stj_dados_abertos.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
