# siconfi — SICONFI municipal finance

Cadastrar declarações fiscais por ente e conta, conectando municípios por código IBGE e CNPJ oficial quando disponível.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `siconfi`.
- Ordem topológica: **70**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `partial`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://apidatalake.tesouro.gov.br/docs/siconfi/](https://apidatalake.tesouro.gov.br/docs/siconfi/).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/siconfi.py](../../../etl/src/bracc_etl/pipelines/siconfi.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_siconfi_pipeline.py](../../../etl/tests/test_siconfi_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://apidatalake.tesouro.gov.br/docs/siconfi/](https://apidatalake.tesouro.gov.br/docs/siconfi/) | Entrada atualmente cadastrada para SICONFI municipal finance. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Consultar API SICONFI oficial para entes e declarações, paginar recursos e salvar resposta original antes do CSV.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** JSON API e CSV canônico de DCA; relatórios adicionais com contratos próprios.
- **Partições e backfill:** Exercício, ente, tipo de declaração e anexo; respeitar periodicidade de DCA/RREO/RGF conforme escopo implementado.
- **Retomada e deduplicação de download:** Checkpoint por exercício, ente, tipo de declaração e anexo; respeitar periodicidade de dca/rreo/rgf conforme escopo implementado; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Anual por edição/ano de referência, com revisão quando o provedor republicar.

Limites e pré-condições:

- Conector atual fica sem ligação quando CSV não tem CNPJ.
- MunicipalFinance não tem constraint e a chave não inclui anexo/relatório.
- Bootstrap só verifica presença em data/siconfi/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/siconfi/dca_*.csv ou *.json com items; cod_ibge, exercicio, conta, coluna, valor e opcional cnpj.

**Chave natural / namespace:** Ente + exercício + demonstrativo/anexo/conta/coluna + período/retificação; chave atual só cod_ibge/exercicio/conta/coluna é insuficiente para expansão.

Normalização:

- Código IBGE identifica município, não CNPJ: obter crosswalk oficial e nunca preencher por nome.
- Separar conta contábil, coluna, anexo, período e tipo de relatório.
- Guardar status/homologação e versão da declaração; retificação substitui valor vigente sem apagar histórico.
- Projetar dimensões comuns conforme F09: Territory.territory_id=sistema:tipo:codigo:versao_territorial; EconomicActivity.activity_id=classificacao:versao:codigo; PublicBody.public_body_id=jurisdicao:sistema:identificador:versao. Aplicar somente as dimensões usadas nesta fonte, preservar códigos originais e validar crosswalks; município é Territory, sem dimensão paralela incompatível.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `MunicipalFinance` | finance_id | existing |
| `Company` | cnpj | existing |
| `Territory` | territory_id | proposed |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `DECLAROU_FINANCA` → `MunicipalFinance` | CNPJ oficial do ente quando publicado | Não construir CNPJ a partir de nome ou código IBGE. | existing |
| `Territory` → `DECLAROU_FINANCA` → `MunicipalFinance` | cod_ibge | Manter relatório vinculado ao território mesmo sem CNPJ, com versão e período. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/siconfi.py`
- `config/sources/siconfi.yml`
- `etl/src/bracc_etl/pipelines/siconfi.py`
- `etl/tests/test_siconfi_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Criar aquisição da dimensão de entes e das páginas DCA com checkpoint por ente/ano.
1. Adicionar Municipality por código IBGE e mapear CNPJ apenas com campo oficial comprovado.
1. Ampliar finance_id para grão contábil e criar constraint MunicipalFinance.
1. Evitar ler simultaneamente JSON e CSV da mesma extração como dados independentes.
1. Validar balanços e totais por anexo e declarar cobertura DCA, expandindo RREO/RGF em contratos separados.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Declaração sem CNPJ se liga ao ente pelo IBGE.
- [ ] Conta com mesmo código em anexos distintos não colide.
- [ ] JSON e CSV da mesma extração não duplicam valores.
- [ ] Retificação mantém valor vigente e referência à versão anterior.

## Riscos e decisões pendentes

- Conector atual fica sem ligação quando CSV não tem CNPJ.
- MunicipalFinance não tem constraint e a chave não inclui anexo/relatório.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/siconfi.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_siconfi_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
