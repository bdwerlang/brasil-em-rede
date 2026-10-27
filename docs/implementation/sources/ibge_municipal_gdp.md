# ibge_municipal_gdp — PIB Municipal — Produto Interno Bruto dos Municípios

Implementar aquisição, cadastro e ligações verificáveis de PIB Municipal — Produto Interno Bruto dos Municípios.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `ibge_municipal_gdp`.
- Ordem topológica: **92**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **M**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [ibge_geosciences](ibge_geosciences.md)
- Contrato de acesso catalogado: [https://servicodados.ibge.gov.br/api/v3/agregados](https://servicodados.ibge.gov.br/api/v3/agregados).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://servicodados.ibge.gov.br/api/v3/agregados](https://servicodados.ibge.gov.br/api/v3/agregados) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/ibge-estatisticas/pib-municipal.md |
| [https://servicodados.ibge.gov.br/api/v3/agregados/5938/metadados](https://servicodados.ibge.gov.br/api/v3/agregados/5938/metadados) | Metadados oficiais do piloto; título/variáveis/unidades conferidos em consulta direta de 26/10/2026. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |
| [https://servicodados.ibge.gov.br/api/docs/agregados?versao=3](https://servicodados.ibge.gov.br/api/docs/agregados?versao=3) | Contrato API Agregados v3. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |

- **Método:** API Agregados v3: baixar metadados, períodos e localidades disponíveis antes dos valores. Selecionar variáveis/categorias explicitamente, dividir por UF/período e guardar a consulta exata.
- **Autenticação:** Sem autenticação para consultas públicas.
- **Formato bruto:** JSON, CSV
- **Partições e backfill:** Tabela + variável + período + nível geográfico + bloco de localidades + classificação.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** annual no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Página de descoberta não é endpoint de dados; disponibilidade de URL não comprova completude.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: codigo_municipio, pib_total, pib_per_capita, vab_agropecuaria, vab_industria, vab_servicos, vab_administracao_publica. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Iniciar tabela 5938, variável 37 PIB corrente em mil reais; selecionar demais VAB/metadados explicitamente e preservar referência 2010. Deflação exige fórmula/série separadas.

**Chave natural / namespace:** IBGE + tabela + variável + categorias + nível/código + ano + revisão

Normalização:

- Preservar códigos como strings e valores originais; vazio/ignorado não equivale a zero.
- Datas de evento, referência e coleta são campos distintos; manter histórico de revisão.
- Identificador completo válido permite ligação; nome isolado ou documento parcial não resolve identidade. CNPJ alfanumérico mantém letras, zeros e dígitos verificadores.
- Símbolos de ausente/sigilo/não aplicável são status com valor nulo, não zero. Série/tabela, variável, categorias, geografia e período são obrigatórios; unidade/escala/metodologia acompanham cada célula.
- Projetar dimensões comuns conforme F09: Territory.territory_id=sistema:tipo:codigo:versao_territorial; EconomicActivity.activity_id=classificacao:versao:codigo; PublicBody.public_body_id=jurisdicao:sistema:identificador:versao. Aplicar somente as dimensões usadas nesta fonte, preservar códigos originais e validar crosswalks; município é Territory, sem dimensão paralela incompatível.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `StatisticalObservation` | IBGE + tabela + variável + categorias + nível/código + ano + revisão | proposed |
| `Territory` | territory_id | proposed |
| `StatisticalSeries` | provedor IBGE + tabela + variável + classificação | proposed |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `StatisticalObservation` → `REFERE_SE_A` → `Territory` | nível/código territorial publicado, namespace e versão; crosswalk oficial quando necessário | Guardar tabela/série, geografia e período; não desagregar UF/Brasil para município e nunca criar Person/Company de agregado. | proposed |
| `StatisticalObservation` → `OBSERVACAO_DE` → `StatisticalSeries` | tabela + variável + classificação | Categorias preservam códigos e descrição; total e subgrupos não são fatos somáveis ao mesmo tempo. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_ibge_municipal_gdp.py`
- `etl/src/bracc_etl/pipelines/ibge_municipal_gdp.py`
- `etl/tests/test_ibge_municipal_gdp.py`
- `docs/sources/ibge_municipal_gdp.md`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Iniciar tabela 5938, variável 37 PIB corrente em mil reais; selecionar demais VAB/metadados explicitamente e preservar referência 2010. Deflação exige fórmula/série separadas.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Criar migração para entidades/arestas propostas e registro no runner; piloto registra SourceDocument/IngestionRun e compara contagens/totais oficiais antes do histórico.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto por período/UF tem manifesto e contagens de lidos/aceitos/rejeitados; interrupção retoma sem duplicação.
- [ ] Reexecução da mesma versão conserva cardinalidades; revisão oficial preserva histórico.
- [ ] Ligações de amostra têm identificador exato e evidência; casos ambíguos permanecem pendentes, sem união por nome.
- [ ] PIB piloto reproduz valor/escala oficiais; valor corrente não é apresentado como crescimento real.

## Riscos e decisões pendentes

- Mudança de leiaute/cobertura coloca a partição em quarentena até revisão do contrato.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/ibge-estatisticas/pib-municipal.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/ibge-estatisticas/pib-municipal.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`
- [https://servicodados.ibge.gov.br/api/v3/agregados/5938/metadados](https://servicodados.ibge.gov.br/api/v3/agregados/5938/metadados)
- [https://servicodados.ibge.gov.br/api/docs/agregados?versao=3](https://servicodados.ibge.gov.br/api/docs/agregados?versao=3)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
