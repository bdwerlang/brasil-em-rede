# pgfn — PGFN divida ativa

Cadastrar inscrições de dívida ativa por devedor e situação, distinguindo estoque de dívida de pagamento ou sanção.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `pgfn`.
- Ordem topológica: **66**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://www.regularize.pgfn.gov.br/dados-abertos](https://www.regularize.pgfn.gov.br/dados-abertos).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/pgfn.py](../../../etl/src/bracc_etl/pipelines/pgfn.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_pgfn_pipeline.py](../../../etl/tests/test_pgfn_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.
- [etl/src/bracc_etl/schemas/pgfn.py](../../../etl/src/bracc_etl/schemas/pgfn.py): Contrato/validação existente a alinhar ao leiaute oficial.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.regularize.pgfn.gov.br/dados-abertos](https://www.regularize.pgfn.gov.br/dados-abertos) | Entrada atualmente cadastrada para PGFN divida ativa. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir arquivos oficiais da lista de devedores, baixar todas as partições publicadas e preservar snapshot e leiaute.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** ZIP/CSV do SIDA e demais famílias somente após mapear layout.
- **Partições e backfill:** Trimestre/competência publicada, UF/tipo de arquivo e inscrição; não limitar ao padrão de nome sem verificar novas famílias.
- **Retomada e deduplicação de download:** Checkpoint por trimestre/competência publicada, uf/tipo de arquivo e inscrição; não limitar ao padrão de nome sem verificar novas famílias; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Página primary_url pode ter mudado; URL final de arquivo não foi verificada.
- Snapshot mensal do registro pode divergir da periodicidade efetiva publicada.
- Bootstrap só verifica presença em data/pgfn/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/pgfn/arquivo_lai_SIDA_*_*.csv; leitura em chunks; parser e schema local de PGFN devem orientar o adaptador.

**Chave natural / namespace:** Finance.finance_id = pgfn_<inscrição>; adicionar provedor e natureza quando necessária para distinguir sistemas e inscrições.

Normalização:

- CNPJ alfanumérico canônico; não confundir raiz com estabelecimento devedor.
- Valor, natureza, situação, número da inscrição e data do snapshot separados.
- Não tratar ausência na publicação seguinte como pagamento confirmado.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Finance` | finance_id | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `DEVE` → `Finance` | CNPJ integral do devedor e número da inscrição | Preservar estoque e situação na data da fonte, sem inferir ilícito. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/pgfn.py`
- `config/sources/pgfn.yml`
- `etl/src/bracc_etl/pipelines/pgfn.py`
- `etl/tests/test_pgfn_acquisition.py`

Tarefas específicas, em ordem:

1. Descobrir catálogo vigente da PGFN e validar URL do registro antes de criar download automatizado.
1. Baixar e validar todas as partições/UF; processar em fluxo sem concatenar o país em memória.
1. Reconciliar ID de inscrição e versões, preservando origem e natureza do crédito.
1. Garantir DEVE para mesma Company do cadastro, com data e situação da inscrição.
1. Conciliar somas por arquivo e snapshot, com quarentena de registros inválidos.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Inscrição reprocessada não aumenta estoque.
- [ ] Mesmo CNPJ em várias inscrições mantém eventos separados.
- [ ] Partição faltante impede snapshot nacional completo.
- [ ] Desaparecimento de inscrição é registrado como ausência observada, sem baixa financeira inferida.

## Riscos e decisões pendentes

- Página primary_url pode ter mudado; URL final de arquivo não foi verificada.
- Snapshot mensal do registro pode divergir da periodicidade efetiva publicada.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/pgfn.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_pgfn_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
