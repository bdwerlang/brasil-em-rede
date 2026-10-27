# rais — RAIS aggregated labor

Cadastrar indicadores agregados anuais de estabelecimentos e empregos por CNAE/UF, sem inventar vínculos entre trabalhadores e empresas.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `rais`.
- Ordem topológica: **106**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://basedosdados.org/dataset/br-me-rais](https://basedosdados.org/dataset/br-me-rais).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/rais.py](../../../etl/src/bracc_etl/pipelines/rais.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_rais_pipeline.py](../../../etl/tests/test_rais_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://basedosdados.org/dataset/br-me-rais](https://basedosdados.org/dataset/br-me-rais) | Entrada atualmente cadastrada para RAIS aggregated labor. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |
| [https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/estatisticas-trabalho](https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/estatisticas-trabalho) | Referência oficial de acesso, formato ou limitação para esta implementação. | Página oficial consultada; publica rota para microdados RAIS/CAGED não identificados e estatísticas do trabalho. |

- **Método:** Preferir microdados públicos não identificados do MTE/PDET; exportação BigQuery só como alternativa explícita com projeto/custo e versão identificados.
- **Autenticação:** Microdados públicos PDET conforme recurso publicado; alternativa BigQuery exige projeto/permissões e possível custo, declarados separadamente.
- **Formato bruto:** Arquivos compactados TXT/CSV do PDET e agregado canônico CSV.
- **Partições e backfill:** Ano, UF e família de estabelecimento; processar todos os arquivos publicados antes de consolidar.
- **Retomada e deduplicação de download:** Checkpoint por ano, uf e família de estabelecimento; processar todos os arquivos publicados antes de consolidar; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Anual por edição/ano de referência, com revisão quando o provedor republicar.

Limites e pré-condições:

- Parser atual usa somente primeiro arquivo bruto e fixa 2022.
- Fonte do registro aponta Base dos Dados, mas o plano oficial de aquisição usa PDET; distinguir provedores.
- Bootstrap só verifica presença em data/rais/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Divergência de identidade: runner/registro=rais; Pipeline.source_id=rais_mte. Reconciliar runs e proveniência preservando alias do provedor.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/rais/rais_2022_aggregated.csv ou primeiro RAIS_ESTAB_PUB*.txt*; parser atual fixa ano 2022 e agrega apenas o primeiro arquivo bruto.

**Chave natural / namespace:** LaborStats.stats_id = fonte RAIS + ano + CNAE + UF e outras dimensões quando declaradas; sem identidade individual.

Normalização:

- CNAE e UF são dimensões agregadas, não chave de identificação de Company.
- Registrar estoque de vínculos versus número de estabelecimentos; não somar média com total.
- Ano de referência vem da edição, nunca constante 2022.
- Não deduzir empregados de uma empresa a partir de média de CNAE/UF.
- Projetar dimensões comuns conforme F09: Territory.territory_id=sistema:tipo:codigo:versao_territorial; EconomicActivity.activity_id=classificacao:versao:codigo; PublicBody.public_body_id=jurisdicao:sistema:identificador:versao. Aplicar somente as dimensões usadas nesta fonte, preservar códigos originais e validar crosswalks; município é Territory, sem dimensão paralela incompatível.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `LaborStats` | stats_id | existing |
| `EconomicActivity` | activity_id | proposed |
| `Territory` | territory_id | proposed |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `LaborStats` → `REFERE_ATIVIDADE` → `EconomicActivity` | CNAE oficial e versão do código | Relação de dimensão agregada; não atribui estatística a uma empresa individual. | proposed |
| `LaborStats` → `REFERE_TERRITORIO` → `Territory` | UF ou código municipal oficial e período | Resolver códigos por dimensão territorial validada; sem inferir identidade de pessoa ou empresa. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/rais.py`
- `config/sources/rais.yml`
- `etl/src/bracc_etl/pipelines/rais.py`
- `etl/tests/test_rais_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Resolver links oficiais de microdados e layout via PDET.
1. Implementar download/descompressão e leitura em fluxo de todos os arquivos/UF, não apenas raw_files[0].
1. Parametrizar ano nas entradas, stats_id e atributos e corrigir alias rais_mte.
1. Validar método de agregação, duplicidade de arquivos e unidades de cada indicador.
1. Criar ligação proposta aos códigos de atividade/território como CONTEXTO agregador, sem SOCIO_DE ou emprego individual.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Troca de ano produz nova partição, sem alterar o ano anterior.
- [ ] Todas as UFs/arquivos esperados são conciliados.
- [ ] Totais de emprego e estabelecimentos batem com os agregados de referência dentro do mesmo universo.
- [ ] Nenhum vínculo de trabalhador/empresa é criado a partir do agregado.

## Riscos e decisões pendentes

- Parser atual usa somente primeiro arquivo bruto e fixa 2022.
- Fonte do registro aponta Base dos Dados, mas o plano oficial de aquisição usa PDET; distinguir provedores.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/rais.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- [https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/estatisticas-trabalho](https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/estatisticas-trabalho)
- `etl/tests/test_rais_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
