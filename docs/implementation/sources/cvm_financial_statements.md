# cvm_financial_statements — CVM DFP/ITR — Demonstrações Financeiras de Empresas Abertas

Implementar aquisição, cadastro e ligações verificáveis de CVM DFP/ITR — Demonstrações Financeiras de Empresas Abertas.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `cvm_financial_statements`.
- Ordem topológica: **57**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dados.cvm.gov.br/](https://dados.cvm.gov.br/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.
- [etl/src/bracc_etl/pipelines/cvm.py](../../../etl/src/bracc_etl/pipelines/cvm.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dados.cvm.gov.br/](https://dados.cvm.gov.br/) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/mercado-financeiro/cvm-dfp-itr.md |
| [https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp](https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp) | DFP oficial, atualizações semanais e reapresentações. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |
| [https://dados.cvm.gov.br/dataset/cia_aberta-doc-itr](https://dados.cvm.gov.br/dataset/cia_aberta-doc-itr) | Descoberta do ITR e dicionário próprio, a confirmar no piloto. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |

- **Método:** Descobrir arquivos/endpoint na publicação oficial; baixar com timeout, backoff e limite de concorrência. Guardar bruto imutável, URL efetiva, hash SHA-256, bytes e instante de coleta.
- **Autenticação:** Não requerida Indicação importada, a confirmar no contrato oficial.
- **Formato bruto:** JSON, CSV
- **Partições e backfill:** Recurso, versão e período; dividir adicionalmente por UF quando suportado.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** quarterly no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Página de descoberta não é endpoint de dados; disponibilidade de URL não comprova completude.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: cnpj_cia, denominacao_cia, cd_conta, ds_conta, vl_conta, dt_refer. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Criar contratos DFP/ITR separados, individuais/consolidados, moeda/escala e exercício comparativo. Saldo financeiro não usa Finance transacional.

**Chave natural / namespace:** DFP/ITR + emissor + referência + versão + grupo + demonstração + conta + período/ordem

Normalização:

- Preservar códigos como strings e valores originais; vazio/ignorado não equivale a zero.
- Datas de evento, referência e coleta são campos distintos; manter histórico de revisão.
- Identificador completo válido permite ligação; nome isolado ou documento parcial não resolve identidade. CNPJ alfanumérico mantém letras, zeros e dígitos verificadores.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `FinancialStatementFact` | DFP/ITR + emissor + referência + versão + grupo + demonstração + conta + período/ordem | proposed |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `DECLAROU_DEMONSTRACAO` → `FinancialStatementFact` | CNPJ do emissor declarado em DFP/ITR | Conta/saldo não é pagamento ou transação financeira. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_cvm_financial_statements.py`
- `etl/src/bracc_etl/pipelines/cvm_financial_statements.py`
- `etl/tests/test_cvm_financial_statements.py`
- `docs/sources/cvm_financial_statements.md`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Criar contratos DFP/ITR separados, individuais/consolidados, moeda/escala e exercício comparativo. Saldo financeiro não usa Finance transacional.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Criar migração para entidades/arestas propostas e registro no runner; piloto registra SourceDocument/IngestionRun e compara contagens/totais oficiais antes do histórico.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto por período/UF tem manifesto e contagens de lidos/aceitos/rejeitados; interrupção retoma sem duplicação.
- [ ] Reexecução da mesma versão conserva cardinalidades; revisão oficial preserva histórico.
- [ ] Ligações de amostra têm identificador exato e evidência; casos ambíguos permanecem pendentes, sem união por nome.
- [ ] Conta de amostra reproduz valor/unidade; individual/consolidado e reapresentações não colidem.

## Riscos e decisões pendentes

- Mudança de leiaute/cobertura coloca a partição em quarentena até revisão do contrato.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/mercado-financeiro/cvm-dfp-itr.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/mercado-financeiro/cvm-dfp-itr.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`
- [https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp](https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp)
- [https://dados.cvm.gov.br/dataset/cia_aberta-doc-itr](https://dados.cvm.gov.br/dataset/cia_aberta-doc-itr)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
