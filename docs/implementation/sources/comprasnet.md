# comprasnet — ComprasNet contracts

Tornar explícita a cobertura de contratos PNCP do pipeline existente e planejar aquisição separada do legado ComprasNet.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `comprasnet`.
- Ordem topológica: **15**; onda de execução: **2**; prioridade temática inicial: 2.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `partial`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dados.gov.br/dados/conjuntos-dados/comprasnet-contratos](https://dados.gov.br/dados/conjuntos-dados/comprasnet-contratos).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/comprasnet.py](../../../etl/src/bracc_etl/pipelines/comprasnet.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_comprasnet_pipeline.py](../../../etl/tests/test_comprasnet_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dados.gov.br/dados/conjuntos-dados/comprasnet-contratos](https://dados.gov.br/dados/conjuntos-dados/comprasnet-contratos) | Entrada atualmente cadastrada para ComprasNet contracts. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |
| [https://pncp.gov.br/manual/pt-br/latest/singlehtml/index.html](https://pncp.gov.br/manual/pt-br/latest/singlehtml/index.html) | Referência oficial de acesso, formato ou limitação para esta implementação. | Manual oficial consultado; descreve consulta de contrato por órgão, ano e sequencial. |

- **Método:** Implementar consulta de contratos PNCP a partir do manual oficial; resolver em etapa separada a API/dump oficial do legado ComprasNet e seu adaptador.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** JSON PNCP preservado; formato legado a confirmar no recurso oficial, com contrato distinto.
- **Partições e backfill:** Provedor, ano de contrato, janela e página; não prometer contratos de 2019 no PNCP sem fonte histórica.
- **Retomada e deduplicação de download:** Checkpoint por provedor, ano de contrato, janela e página; não prometer contratos de 2019 no pncp sem fonte histórica; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Downloader configurado não existe; parser atual é PNCP apesar do source_id comprasnet.
- Criação de relações via MATCH pode perder vínculos se PNCP carregar depois; requer religação idempotente.
- Contrato chama script de download ausente; implementar ou substituir o caminho antes da execução.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/comprasnet/*_contratos.json como lista de objetos PNCP de contrato; nome do pipeline não corresponde ao catálogo legado registrado.

**Chave natural / namespace:** Contract.contract_id = numeroControlePNCP ou composição órgão + sequencialContrato + anoContrato; namespace do provedor deve impedir colisões com o Portal.

Normalização:

- Normalizar CNPJ PJ sem remover letras; admitir PF/estrangeiros em registros próprios em vez de descartá-los silenciosamente.
- Preservar valor inicial, global e datas vigentes, sem truncar montantes para esconder outliers.
- Guardar numeroControlePncpCompra para ligação exata à licitação.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Contract` | contract_id | existing |
| `Company` | cnpj | existing |
| `Bid` | bid_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `VENCEU` → `Contract` | CNPJ fornecedor + controle PNCP de contrato | Preservar fornecedor e órgão em papéis separados. | existing |
| `Contract` → `REFERENTE_A` → `Bid` | numeroControlePncpCompra = Bid.bid_id | Vínculo exato, pendente se licitação ainda não cadastrada. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/comprasnet.py`
- `config/sources/comprasnet.yml`
- `etl/src/bracc_etl/pipelines/comprasnet.py`
- `etl/tests/test_comprasnet_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Corrigir contrato bootstrap que chama scripts/download_comprasnet.py inexistente.
1. Separar identidade do dataset implementado PNCP do dataset legado ComprasNet no catálogo e manifesto.
1. Criar downloader de contratos com paginação e validação de cobertura; bloquear declaração de histórico anterior sem evidência.
1. Rever filtros PJ/valor positivo e evitar sobrescrita de Company com informação pobre.
1. Conectar Contract a Bid por controle de compra quando Bid existir; registrar pendências para religação posterior.
1. Completar aquisição e contratos de ata/adesão para SRP, com escopo do provedor identificado e distinção entre participante original e órgão aderente; integrar às consultas por REFERENTE_A somente com referência oficial.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Manifesto informa claramente provedor e anos cobertos; contratos legados não são alegados a partir de PNCP.
- [ ] Dois contratos do mesmo fornecedor não colidem.
- [ ] Reprocessamento não duplica VENCEU/REFERENTE_A.
- [ ] Contrato com fornecedor alfanumérico é ligado à mesma Company do CNPJ.
- [ ] A consulta SRP distingue participação original e adesão documentada; a mesma publicação PNCP não vira dois contratos por passar também por este pipeline.

## Riscos e decisões pendentes

- Downloader configurado não existe; parser atual é PNCP apesar do source_id comprasnet.
- Criação de relações via MATCH pode perder vínculos se PNCP carregar depois; requer religação idempotente.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/comprasnet.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- [https://pncp.gov.br/manual/pt-br/latest/singlehtml/index.html](https://pncp.gov.br/manual/pt-br/latest/singlehtml/index.html)
- `etl/tests/test_comprasnet_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
