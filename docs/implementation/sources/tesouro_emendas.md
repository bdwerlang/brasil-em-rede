# tesouro_emendas — Tesouro emendas

Cadastrar pagamentos de emendas do Tesouro por ordem bancária e favorecido, sem confundir pagamento com total de emenda.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `tesouro_emendas`.
- Ordem topológica: **23**; onda de execução: **2**; prioridade temática inicial: 2.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://www.tesourotransparente.gov.br/](https://www.tesourotransparente.gov.br/).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/tesouro_emendas.py](../../../etl/src/bracc_etl/pipelines/tesouro_emendas.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.tesourotransparente.gov.br/](https://www.tesourotransparente.gov.br/) | Entrada atualmente cadastrada para Tesouro emendas. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |
| [https://www.tesourotransparente.gov.br/consultas/painel-das-emendas-parlamentares-individuais-e-de-bancada](https://www.tesourotransparente.gov.br/consultas/painel-das-emendas-parlamentares-individuais-e-de-bancada) | Referência oficial de acesso, formato ou limitação para esta implementação. | Painel oficial consultado; oferece ligação para extração dos valores, cujo arquivo final deve ser inspecionado. |

- **Método:** Usar a extração oficial indicada pelo painel de emendas individuais/de bancada do Tesouro, descobrir formato e adaptar ao CSV requerido.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** Exportação oficial do painel a confirmar; CSV canônico interno preserva serial de data e valor bruto.
- **Partições e backfill:** Ano, mês, tipo de emenda e identificação da ordem bancária; guardar filtros do painel no manifesto.
- **Retomada e deduplicação de download:** Checkpoint por ano, mês, tipo de emenda e identificação da ordem bancária; guardar filtros do painel no manifesto; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Conector existe no runner, mas está ausente do contrato bootstrap.
- Nome Emenda no CSV não comprova ID individual da emenda; não prometer ligação de autoria se o export só tiver agregados.
- Ausente do contrato bootstrap atual; incluir fonte, entradas e aquisição antes da execução integral.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/tesouro_emendas/emendas_tesouro.csv; ponto e vírgula, Latin-1; OB, Data, Ano, Mês, Nome Emenda, Transferência Especial, Categoria Econômica Despesa, Valor, CNPJ do Favorecido.

**Chave natural / namespace:** Proposto: provedor + exercício + OB + unidade emitente + item/favorecido; transfer_tesouro_<OB> atual pode colidir entre exercícios e linhas.

Normalização:

- Unificar CNPJ com o restante da base: o pipeline atual grava 14 caracteres sem máscara, enquanto outros formatam.
- Corrigir parser de moeda para valores como 1.234,56 e distinguir nulo de zero.
- Converter data serial Excel com origem declarada; validar datas textuais pelo layout.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Payment` | transfer_id | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Payment` → `PAGO_PARA` → `Company` | CNPJ completo do favorecido | Vínculo preserva exercício e item da ordem bancária. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/tesouro_emendas.py`
- `config/sources/tesouro_emendas.yml`
- `etl/src/bracc_etl/pipelines/tesouro_emendas.py`
- `etl/tests/test_tesouro_emendas_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Adicionar tesouro_emendas ao bootstrap e atualizar contagem esperada de 45 para a contagem auditada de implementadas.
1. Resolver e documentar exportação do painel oficial e comparar colunas com _COL_RENAME.
1. Reformular transfer_id para granularidade da OB e criar constraint Payment.transfer_id.
1. Migrar Company.cnpj divergente e reconciliar favorecidos com CNPJ.
1. Vincular opcionalmente pagamento a Amendment somente quando exportação contiver código/exercício oficial; tipo/nome da emenda não basta.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] OB repetida em anos ou favorecidos diferentes não colide.
- [ ] Valor 1.234,56 equivale a 1234.56 após normalização.
- [ ] Favorecido existente converge para a mesma Company.
- [ ] Carga do snapshot repetida preserva soma de pagamentos e contagem.

## Riscos e decisões pendentes

- Conector existe no runner, mas está ausente do contrato bootstrap.
- Nome Emenda no CSV não comprova ID individual da emenda; não prometer ligação de autoria se o export só tiver agregados.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/tesouro_emendas.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- [https://www.tesourotransparente.gov.br/consultas/painel-das-emendas-parlamentares-individuais-e-de-bancada](https://www.tesourotransparente.gov.br/consultas/painel-das-emendas-parlamentares-individuais-e-de-bancada)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
