# siorg — SIORG — Estrutura Organizacional do Governo Federal

Implementar aquisição, cadastro e ligações verificáveis de SIORG — Estrutura Organizacional do Governo Federal.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `siorg`.
- Ordem topológica: **11**; onda de execução: **1**; prioridade temática inicial: 1.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://siorg.gov.br/](https://siorg.gov.br/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://siorg.gov.br/](https://siorg.gov.br/) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/apis-governamentais/siorg.md |
| [https://www.gov.br/conecta/catalogo/apis/estrutura-organizacional](https://www.gov.br/conecta/catalogo/apis/estrutura-organizacional) | Catálogo oficial declara endpoint e manual SIORG. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |
| [https://estruturaorganizacional.dados.gov.br](https://estruturaorganizacional.dados.gov.br) | Serviço de consulta SIORG com operações a selecionar no manual. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |
| [https://siorg.planejamento.gov.br/manuais/manual-webservices/html/demo_3.html](https://siorg.planejamento.gov.br/manuais/manual-webservices/html/demo_3.html) | Manual oficial informa consultas REST/SOAP livres e abertas. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |

- **Método:** Descobrir arquivos/endpoint na publicação oficial; baixar com timeout, backoff e limite de concorrência. Guardar bruto imutável, URL efetiva, hash SHA-256, bytes e instante de coleta.
- **Autenticação:** Consulta pública livre/aberta documentada; login do módulo de gestão não é necessário.
- **Formato bruto:** JSON
- **Partições e backfill:** Recurso, versão e período; dividir adicionalmente por UF quando suportado.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** monthly no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Página de descoberta não é endpoint de dados; disponibilidade de URL não comprova completude.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: codigo_orgao, nome_orgao, sigla, orgao_superior, tipo_unidade, dirigente. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Extrair unidades, órgão-pai e domínios SIORG; construir correspondência SIORG–SIAFI/UASG apenas por evidência oficial e período.

**Chave natural / namespace:** public_body_id = siorg: + código oficial da unidade; snapshot separado por vigência

Normalização:

- Preservar códigos como strings e valores originais; vazio/ignorado não equivale a zero.
- Datas de evento, referência e coleta são campos distintos; manter histórico de revisão.
- Identificador completo válido permite ligação; nome isolado ou documento parcial não resolve identidade. CNPJ alfanumérico mantém letras, zeros e dígitos verificadores.
- Projetar dimensões comuns conforme F09: Territory.territory_id=sistema:tipo:codigo:versao_territorial; EconomicActivity.activity_id=classificacao:versao:codigo; PublicBody.public_body_id=jurisdicao:sistema:identificador:versao. Aplicar somente as dimensões usadas nesta fonte, preservar códigos originais e validar crosswalks; município é Territory, sem dimensão paralela incompatível.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `PublicBody` | public_body_id | proposed |
| `OrganizationSnapshot` | public_body_id + vigência + revisão | proposed |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `PublicBody` → `SUBORDINADO_A` → `PublicBody` | SIORG pai e filho com vigência | public_body_id usa namespace siorg; código SIAFI/UASG é correspondência oficial datada, não identidade por igualdade numérica. | proposed |
| `PublicBody` → `POSSUI_VERSAO` → `OrganizationSnapshot` | public_body_id + vigência | Nome e estrutura podem mudar sem recriar órgão; unidade extinta conserva histórico. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_siorg.py`
- `etl/src/bracc_etl/pipelines/siorg.py`
- `etl/tests/test_siorg.py`
- `docs/sources/siorg.md`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Extrair unidades, órgão-pai e domínios SIORG; construir correspondência SIORG–SIAFI/UASG apenas por evidência oficial e período.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Criar migração para entidades/arestas propostas e registro no runner; piloto registra SourceDocument/IngestionRun e compara contagens/totais oficiais antes do histórico.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto por período/UF tem manifesto e contagens de lidos/aceitos/rejeitados; interrupção retoma sem duplicação.
- [ ] Reexecução da mesma versão conserva cardinalidades; revisão oficial preserva histórico.
- [ ] Ligações de amostra têm identificador exato e evidência; casos ambíguos permanecem pendentes, sem união por nome.
- [ ] Unidade renomeada mantém identidade; hierarquia piloto não contém ciclos e código órfão aparece em relatório.

## Riscos e decisões pendentes

- Mudança de leiaute/cobertura coloca a partição em quarentena até revisão do contrato.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/apis-governamentais/siorg.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/apis-governamentais/siorg.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`
- [https://www.gov.br/conecta/catalogo/apis/estrutura-organizacional](https://www.gov.br/conecta/catalogo/apis/estrutura-organizacional)
- [https://estruturaorganizacional.dados.gov.br](https://estruturaorganizacional.dados.gov.br)
- [https://siorg.planejamento.gov.br/manuais/manual-webservices/html/demo_3.html](https://siorg.planejamento.gov.br/manuais/manual-webservices/html/demo_3.html)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
