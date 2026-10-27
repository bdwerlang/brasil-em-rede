# caged — CAGED labor movements

Cadastrar movimentações de emprego como agregados mensais por território, CNAE, CBO e tipo de movimento.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `caged`.
- Ordem topológica: **82**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `partial`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED/](https://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED/).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/caged.py](../../../etl/src/bracc_etl/pipelines/caged.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_caged_pipeline.py](../../../etl/tests/test_caged_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED/](https://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED/) | Entrada atualmente cadastrada para CAGED labor movements. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |
| [https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/estatisticas-trabalho](https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/estatisticas-trabalho) | Referência oficial de acesso, formato ou limitação para esta implementação. | Página oficial consultada; encaminha aos microdados e séries RAIS/CAGED. |

- **Método:** Descobrir microdados do Novo CAGED via PDET e protocolo realmente disponível; baixar movimento e revisões segundo leiaute oficial.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** Arquivos compactados TXT/CSV oficiais, convertidos para caged_*.csv.
- **Partições e backfill:** Ano-mês, família de arquivo e UF/município; declarações fora do prazo/revisões em partições específicas.
- **Retomada e deduplicação de download:** Checkpoint por ano-mês, família de arquivo e uf/município; declarações fora do prazo/revisões em partições específicas; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Cobertura declarada é somente agregada; não prometer vínculo de emprego individual.
- Protocolo e disponibilidade de arquivos históricos precisam ser validados na aquisição.
- Bootstrap só verifica presença em data/caged/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/caged/caged_*.csv; normalização por aliases do Novo CAGED; modelo implementado é agregado, sem vínculo individual.

**Chave natural / namespace:** Hash de ano, mês, UF, município, CNAE, CBO e tipo de movimentação, acrescido da fonte CAGED e versão da revisão.

Normalização:

- Separar admissões, desligamentos, saldo e correções fora do prazo.
- Manter CBO, CNAE e município como códigos com zeros e versão.
- Não usar célula agregada para identificar pessoa ou empresa.
- Salário médio deve ser ponderado por contagem; ausente não vira zero.
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

- `etl/src/bracc_etl/acquisition/caged.py`
- `config/sources/caged.yml`
- `etl/src/bracc_etl/pipelines/caged.py`
- `etl/tests/test_caged_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Validar FTP/HTTPS vigente no PDET; URL https do registro não comprova acesso ao FTP.
1. Implementar extração de todas as famílias mensais e suas revisões.
1. Garantir que a revisão substitua/reconcilie a partição anterior sem somar duas vezes o mesmo movimento.
1. Incluir fonte na chave LaborStats para não colidir com RAIS.
1. Conciliar admissões, desligamentos e saldo por competência e dimensão.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Admissões menos desligamentos igualam saldo na mesma metodologia.
- [ ] Revisão de um mês não duplica contagens anteriores.
- [ ] RAIS e CAGED mantêm estatísticas separadas.
- [ ] Nenhuma pessoa/empresa é identificada por CNAE/município/CBO.

## Riscos e decisões pendentes

- Cobertura declarada é somente agregada; não prometer vínculo de emprego individual.
- Protocolo e disponibilidade de arquivos históricos precisam ser validados na aquisição.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/caged.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- [https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/estatisticas-trabalho](https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/estatisticas-trabalho)
- `etl/tests/test_caged_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
