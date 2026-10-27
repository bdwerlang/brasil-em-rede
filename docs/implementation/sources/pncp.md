# pncp — PNCP bids and contracts

Cobrir publicações de contratações do PNCP por modalidade, data e ente, formando a base de licitações vinculável a contratos.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `pncp`.
- Ordem topológica: **18**; onda de execução: **2**; prioridade temática inicial: 2.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `partial`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao](https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/pncp.py](../../../etl/src/bracc_etl/pipelines/pncp.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_pncp_pipeline.py](../../../etl/tests/test_pncp_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao](https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao) | Entrada atualmente cadastrada para PNCP bids and contracts. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |
| [https://www.gov.br/pncp/pt-br/pncp/manuais](https://www.gov.br/pncp/pt-br/pncp/manuais) | Referência oficial de acesso, formato ou limitação para esta implementação. | Página oficial consultada; fornece manual da API de consultas, cujos parâmetros devem ser validados na implementação. |

- **Método:** Implementar GET paginado da API de consulta de contratações/publicacao conforme manual oficial e salvar cada página antes do processamento.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** JSON original de resposta e manifesto de cobertura consolidado.
- **Partições e backfill:** Janela de publicação, modalidade e página; parâmetros opcionais de UF/ente apenas com cobertura declarada.
- **Retomada e deduplicação de download:** Checkpoint por janela de publicação, modalidade e página; parâmetros opcionais de uf/ente apenas com cobertura declarada; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- O pipeline atualmente perde licitações sem valor positivo.
- Manifesto cobre somente o que o downloader declarar; paginação não foi implementada.
- Bootstrap só verifica presença em data/pncp/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Divergência de identidade: runner/registro=pncp; Pipeline.source_id=pncp_bids. Reconciliar runs e proveniência preservando alias do provedor.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/pncp/pncp_*.json como lista ou envelope data; coverage_manifest.json opcional reconhecido pelo pipeline.

**Chave natural / namespace:** Bid.bid_id = numeroControlePNCP; preservar CNPJ do órgão, anoCompra e sequencialCompra; fallback somente quando todos os componentes forem válidos.

Normalização:

- Validar numeroControlePNCP e CNPJ do órgão, preservando letras e zeros.
- Não excluir contratação válida apenas por valor estimado zero ou ainda não informado.
- Separar data de publicação de atualização e valor estimado de homologado.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Bid` | bid_id | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `LICITOU` → `Bid` | CNPJ do órgão em orgaoEntidade | Company representa aqui o ente contratante, não um licitante concorrente. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/pncp.py`
- `config/sources/pncp.yml`
- `etl/src/bracc_etl/pipelines/pncp.py`
- `etl/tests/test_pncp_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Construir aquisição por todas as modalidades oficiais e janelas aceitas, com prova de última página por partição.
1. Atualizar source_id pncp_bids para alias rastreável de pncp.
1. Corrigir inferência de final de mês que gera dia 31 inválido e tornar completude dependente de paginação, não de nomes de arquivos.
1. Criar constraint Bid.bid_id e executar reconciliação com contratos ingeridos pelo conector comprasnet.
1. Medir divergências de conteúdo e atrasos; revisitar janela recente para retificações.
1. Separar a publicação Bid já produzida de resultado/fornecedor contratado: adquirir resultados/contratos oficiais e seus vínculos à licitação, ou consumir o adaptador de contratos PNCP hoje chamado comprasnet. Projeção Contract/VENCEU só para contratação documentada.
1. Para o padrão SRP, adquirir atas, participantes originais e documentos de adesão; modelar adesão com data/evidência. Flag srp e contratos de vários órgãos não provam carona.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Todas as páginas de cada janela/modalidade são conciliadas com totais declarados.
- [ ] Reinício após interrupção não perde nem duplica publicações.
- [ ] Contratação sem valor informado permanece cadastrada.
- [ ] REFERENTE_A conecta contrato por controle PNCP da compra, sem aproximação por objeto.
- [ ] Fixture de órgão publicador LICITOU não o converte em fornecedor VENCEU; somente resultado/contrato oficial identifica contratado e vincula Contract a Bid.
- [ ] Participante original de ata SRP não é classificado como aderente sem documento de adesão; IDs de ata e validade são preservados.

## Riscos e decisões pendentes

- O pipeline atualmente perde licitações sem valor positivo.
- Manifesto cobre somente o que o downloader declarar; paginação não foi implementada.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/pncp.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- [https://www.gov.br/pncp/pt-br/pncp/manuais](https://www.gov.br/pncp/pt-br/pncp/manuais)
- `etl/tests/test_pncp_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
