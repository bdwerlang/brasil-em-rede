# siafi_budget_execution — SIAFI (Execução Orçamentária da União)

Implementar aquisição, cadastro e ligações verificáveis de SIAFI (Execução Orçamentária da União).

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `siafi_budget_execution`.
- Ordem topológica: **20**; onda de execução: **2**; prioridade temática inicial: 2.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **XL**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [siorg](siorg.md)
- Contrato de acesso catalogado: [https://apidatalake.tesouro.gov.br/docs/sadipem/](https://apidatalake.tesouro.gov.br/docs/sadipem/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.
- [etl/src/bracc_etl/pipelines/siop.py](../../../etl/src/bracc_etl/pipelines/siop.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.
- [etl/src/bracc_etl/pipelines/tesouro_emendas.py](../../../etl/src/bracc_etl/pipelines/tesouro_emendas.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.
- [etl/src/bracc_etl/pipelines/transparencia.py](../../../etl/src/bracc_etl/pipelines/transparencia.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://apidatalake.tesouro.gov.br/docs/sadipem/](https://apidatalake.tesouro.gov.br/docs/sadipem/) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/tesouro-nacional/siafi.md |
| [https://portaldatransparencia.gov.br/download-de-dados](https://portaldatransparencia.gov.br/download-de-dados) | CSV oficial por tema e periodicidade; selecionar contrato concreto, sem duplicar API e arquivo. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |
| [https://www.gov.br/tesouronacional/pt-br/siafi](https://www.gov.br/tesouronacional/pt-br/siafi) | Sistema SIAFI é distinto das publicações abertas derivadas e do sistema restrito Tesouro Gerencial. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |
| [https://apidatalake.tesouro.gov.br/docs/sadipem/](https://apidatalake.tesouro.gov.br/docs/sadipem/) | Divergência confirmada: API é SADIPem, não execução SIAFI; rejeitar seu payload para este source_id. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |

- **Método:** Gate inicial resolve recurso: descartar SADIPem e selecionar dataset público Tesouro/CGU que realmente exponha execução SIAFI. Se não houver contrato compatível, permanecer bloqueado. Não acessar SIAFI Operacional/Tesouro Gerencial restritos.
- **Autenticação:** CSV público ou API CGU com chave conforme recurso selecionado; sistema SIAFI Operacional não é acesso aberto.
- **Formato bruto:** JSON, CSV
- **Partições e backfill:** Recurso, versão e período; dividir adicionalmente por UF quando suportado.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** monthly no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Página de descoberta não é endpoint de dados; disponibilidade de URL não comprova completude.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: codigo_orgao, codigo_uo, funcao, subfuncao, programa, acao, exercicio. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Gate obrigatório: SADIPem não é SIAFI. Identificar dataset público Tesouro/CGU de execução e comprovar grão; separar empenho/liquidação/pago/RAP/anulação e sobreposição com siop/transparencia/emendas.

**Chave natural / namespace:** documento: exercício + UG/gestão + tipo/número + item/evento; agregado: tabela + período + classificações + estágio + revisão

Normalização:

- Preservar códigos como strings e valores originais; vazio/ignorado não equivale a zero.
- Datas de evento, referência e coleta são campos distintos; manter histórico de revisão.
- Identificador completo válido permite ligação; nome isolado ou documento parcial não resolve identidade. CNPJ alfanumérico mantém letras, zeros e dígitos verificadores.
- Estágio empenhado/liquidado/pago, RAP, anulação/estorno e referência original preservam sinais e tempo. CNPJ só liga quando explícito no documento; agregado não identifica favorecido.
- Projetar dimensões comuns conforme F09: Territory.territory_id=sistema:tipo:codigo:versao_territorial; EconomicActivity.activity_id=classificacao:versao:codigo; PublicBody.public_body_id=jurisdicao:sistema:identificador:versao. Aplicar somente as dimensões usadas nesta fonte, preservar códigos originais e validar crosswalks; município é Territory, sem dimensão paralela incompatível.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `BudgetExecutionFact` | documento: exercício + UG/gestão + tipo/número + item/evento; agregado: tabela + período + classificações + estágio + revisão | proposed |
| `PublicBody` | public_body_id | proposed |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `BudgetExecutionFact` → `EXECUTADA_POR` → `PublicBody` | UG/órgão SIAFI mapeado oficialmente para SIORG e vigência | Namespaces distintos; falta de crosswalk deixa organização pendente. | proposed |
| `BudgetExecutionFact` → `FAVORECEU` → `Company` | CNPJ completo explicitamente público no nível documental | Agregado não gera favorecido/contrato/emenda; estas ligações exigem chave documental explícita. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_siafi_budget_execution.py`
- `etl/src/bracc_etl/pipelines/siafi_budget_execution.py`
- `etl/tests/test_siafi_budget_execution.py`
- `docs/sources/siafi_budget_execution.md`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Gate obrigatório: SADIPem não é SIAFI. Identificar dataset público Tesouro/CGU de execução e comprovar grão; separar empenho/liquidação/pago/RAP/anulação e sobreposição com siop/transparencia/emendas.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Criar migração para entidades/arestas propostas e registro no runner; piloto registra SourceDocument/IngestionRun e compara contagens/totais oficiais antes do histórico.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto por período/UF tem manifesto e contagens de lidos/aceitos/rejeitados; interrupção retoma sem duplicação.
- [ ] Reexecução da mesma versão conserva cardinalidades; revisão oficial preserva histórico.
- [ ] Ligações de amostra têm identificador exato e evidência; casos ambíguos permanecem pendentes, sem união por nome.
- [ ] Payload PVL/SADIPem é rejeitado; mês/UG reconcilia por estágio; se só agregado existir, favorecido/contrato não é inventado.

## Riscos e decisões pendentes

- URL SADIPem importada é fora do escopo. Recurso público SIAFI e cobertura real precisam ser comprovados; dados agregados podem impedir ligação a favorecido/contrato/emenda.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/tesouro-nacional/siafi.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/tesouro-nacional/siafi.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`
- [https://portaldatransparencia.gov.br/download-de-dados](https://portaldatransparencia.gov.br/download-de-dados)
- [https://www.gov.br/tesouronacional/pt-br/siafi](https://www.gov.br/tesouronacional/pt-br/siafi)
- [https://apidatalake.tesouro.gov.br/docs/sadipem/](https://apidatalake.tesouro.gov.br/docs/sadipem/)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
