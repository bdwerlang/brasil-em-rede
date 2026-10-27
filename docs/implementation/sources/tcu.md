# tcu — TCU sanctions

Ingerir as quatro listas do TCU preservando diferenças entre inabilitação, inidoneidade e contas irregulares.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `tcu`.
- Ordem topológica: **12**; onda de execução: **1**; prioridade temática inicial: 1.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://contas.tcu.gov.br/ords/f?p=INIDONEAS:INIDONEAS](https://contas.tcu.gov.br/ords/f?p=INIDONEAS:INIDONEAS).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/tcu.py](../../../etl/src/bracc_etl/pipelines/tcu.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_tcu_pipeline.py](../../../etl/tests/test_tcu_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://contas.tcu.gov.br/ords/f?p=INIDONEAS:INIDONEAS](https://contas.tcu.gov.br/ords/f?p=INIDONEAS:INIDONEAS) | Entrada atualmente cadastrada para TCU sanctions. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Resolver downloads oficiais de cada lista, baixar independentemente e manter cobertura por lista e data.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** CSV de quatro listas com cabeçalhos normalizados pelo adaptador.
- **Partições e backfill:** Lista, snapshot e processo/acórdão; versões e decisões posteriores.
- **Retomada e deduplicação de download:** Checkpoint por lista, snapshot e processo/acórdão; versões e decisões posteriores; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Portal ORDS é entrada de consulta e não contrato estável de exportação; endpoints finais precisam ser descobertos.
- TCU usa idx em diversas chaves atuais.
- Bootstrap só verifica presença em data/tcu/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/tcu/inabilitados-funcao-publica.csv; licitantes-inidoneos.csv; resp-contas-julgadas-irregulares.csv; resp-contas-julgadas-irreg-implicacao-eleitoral.csv.

**Chave natural / namespace:** Lista TCU + processo/acórdão + responsável/documento + evento; substituir IDs baseados em idx.

Normalização:

- Separar condenação administrativa, irregularidade de contas e consequência eleitoral; não equiparar automaticamente.
- Preservar processo, acórdão, fundamento e vigência.
- CPF parcial fica no registro de responsável; CNPJ alfanumérico usa chave comum.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Sanction` | sanction_id | existing |
| `Person` | cpf | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company\|Person` → `SANCIONADA` → `Sanction` | CNPJ/CPF completo e chave do processo | O tipo da decisão permanece explícito; dados mascarados não geram identidade. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/tcu.py`
- `config/sources/tcu.yml`
- `etl/src/bracc_etl/pipelines/tcu.py`
- `etl/tests/test_tcu_acquisition.py`

Tarefas específicas, em ordem:

1. Descobrir quatro recursos oficiais e validar seus dicionários separadamente.
1. Reescrever sanction_id de cada modalidade para não depender da posição da linha.
1. Cadastrar registros sem documento completo, adiando apenas resolução da pessoa.
1. Adicionar teste de retificação de acórdão e de mesmo responsável em múltiplas listas.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Todas as quatro listas geram métricas de cobertura próprias.
- [ ] Reordenar registros preserva IDs e vínculos.
- [ ] Nome igual em duas listas não une responsáveis sem identificador forte.

## Riscos e decisões pendentes

- Portal ORDS é entrada de consulta e não contrato estável de exportação; endpoints finais precisam ser descobertos.
- TCU usa idx em diversas chaves atuais.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/tcu.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_tcu_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
