# dou — Diario Oficial da Uniao

Cadastrar atos do Diário Oficial da União com texto e evidência, extraindo menções e nomeações sem transformar menção em relação comprovada.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `dou`.
- Ordem topológica: **30**; onda de execução: **3**; prioridade temática inicial: 3.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **XL**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://www.in.gov.br/leiturajornal](https://www.in.gov.br/leiturajornal).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/dou.py](../../../etl/src/bracc_etl/pipelines/dou.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_dou_pipeline.py](../../../etl/tests/test_dou_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.
- [etl/src/bracc_etl/schemas/dou.py](../../../etl/src/bracc_etl/schemas/dou.py): Contrato/validação existente a alinhar ao leiaute oficial.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.in.gov.br/leiturajornal](https://www.in.gov.br/leiturajornal) | Entrada atualmente cadastrada para Diario Oficial da Uniao. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir canal oficial de exportação da Imprensa Nacional e sua disponibilidade histórica; BigQuery é alternativa explícita, não condição necessária de um canal oficial que não o exija.
- **Autenticação:** Validar mecanismo do canal oficial escolhido. Alternativa BigQuery exige credencial/projeto; requisito atual GOOGLE_APPLICATION_CREDENTIALS não comprova que todo canal oficial DOU precise dela.
- **Formato bruto:** XML/JSON/HTML/PDF oficial conforme canal publicado; Parquet derivado se usado, com SQL e versão registrados.
- **Partições e backfill:** Data, edição, seção e ato; arquivos extraordinários e republicações em partições próprias.
- **Retomada e deduplicação de download:** Checkpoint por data, edição, seção e ato; arquivos extraordinários e republicações em partições próprias; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Diária, com janela de revisita para retificações.

Limites e pré-condições:

- Acesso oficial ao histórico e termos de extração precisam validação; não prometer BigQuery gratuito.
- Atuais relações PUBLICOU/MENCIONOU podem misturar papel do citado e do publicador.
- DOUAct não possui constraint única.
- Bootstrap só verifica presença em data/dou/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Divergência de identidade: runner/registro=dou; Pipeline.source_id=imprensa_nacional. Reconciliar runs e proveniência preservando alias do provedor.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/dou/**/*.parquet, **/*.xml ou *.json; pipeline prioriza Parquet, depois XML, depois JSON e não combina os três formatos.

**Chave natural / namespace:** ID oficial do ato/URL e edição/seção/data; hash atual url_title+data precisa preservar republicações e retificações.

Normalização:

- Separar publicação, vigência, retificação e republicação.
- CPF/CNPJ extraído só gera identidade quando completo; nomes geram apenas candidatos.
- CNPJ no texto gera menção com trecho/página e método, não prova de contratação.
- PUBLICOU não deve atribuir publicação à pessoa simplesmente citada no ato.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `DOUAct` | act_id | existing |
| `Person` | cpf | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person` → `PUBLICOU` → `DOUAct` | CPF extraído no ato | Rever semântica: CPF citado não prova que a pessoa publicou o ato. | existing |
| `Company` → `MENCIONOU` → `DOUAct` | CNPJ extraído no ato | Migrar para menção documental com evidência, sem inferir autoria. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/dou.py`
- `config/sources/dou.yml`
- `etl/src/bracc_etl/pipelines/dou.py`
- `etl/tests/test_dou_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Validar acesso oficial e limites antes de construir downloader; catalogar cobertura histórica efetivamente exportável.
1. Preservar bruto, texto extraído, URL do ato e checksum; deduplicar formatos do mesmo ato.
1. Rever relações PUBLICOU/MENCIONOU para refletir papel expresso no documento e criar MENCIONADA_EM quando adequado.
1. Reconciliar alias imprensa_nacional com dou e criar constraint DOUAct.act_id.
1. Construir extração de nomeações/cargos somente com data, órgão e pessoa identificada por prova suficiente.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Republicação e retificação permanecem ligadas ao original com IDs rastreáveis.
- [ ] Menção a CNPJ sempre tem trecho e URL.
- [ ] Pessoa citada não é rotulada automaticamente como autora/publicadora.
- [ ] Parquet/XML do mesmo ato não geram duplicidade.

## Riscos e decisões pendentes

- Acesso oficial ao histórico e termos de extração precisam validação; não prometer BigQuery gratuito.
- Atuais relações PUBLICOU/MENCIONOU podem misturar papel do citado e do publicador.
- DOUAct não possui constraint única.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/dou.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_dou_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
