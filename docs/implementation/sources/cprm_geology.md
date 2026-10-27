# cprm_geology — SGB-CPRM — Geologia, Recursos Minerais e Hidrogeologia

Implementar aquisição, cadastro e ligações verificáveis de SGB-CPRM — Geologia, Recursos Minerais e Hidrogeologia.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `cprm_geology`.
- Ordem topológica: **83**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [ibge_geosciences](ibge_geosciences.md)
- Contrato de acesso catalogado: [https://geosgb.sgb.gov.br/](https://geosgb.sgb.gov.br/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://geosgb.sgb.gov.br/](https://geosgb.sgb.gov.br/) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/dados-geoespaciais/cprm-geologia.md |

- **Método:** Descobrir arquivos/endpoint na publicação oficial; baixar com timeout, backoff e limite de concorrência. Guardar bruto imutável, URL efetiva, hash SHA-256, bytes e instante de coleta.
- **Autenticação:** Não requerida Indicação importada, a confirmar no contrato oficial.
- **Formato bruto:** WMS, WFS, SHP, GeoJSON, JSON
- **Partições e backfill:** Recurso, versão e período; dividir adicionalmente por UF quando suportado.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** annual no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Página de descoberta não é endpoint de dados; disponibilidade de URL não comprova completude.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: unidade_geologica, tipo_rocha, idade_geologica, recurso_mineral, bacia_hidrografica. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Ler WFS GetCapabilities/DescribeFeatureType ou metadata ArcGIS; selecionar geologia/poços e conservar CRS, escala e geometria externa ao grafo. WMS só visualiza.

**Chave natural / namespace:** serviço + camada + ID da feição + versão

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
| `GeologicalFeature` | serviço + camada + ID da feição + versão | proposed |
| `Territory` | territory_id | proposed |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `GeologicalFeature` → `INTERSECTA` → `Territory` | interseção espacial versionada | Guardar tabela/série, geografia e período; algoritmo, projeção, área/distância e versões são evidência derivada, sem atribuir propriedade/autoria. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_cprm_geology.py`
- `etl/src/bracc_etl/pipelines/cprm_geology.py`
- `etl/tests/test_cprm_geology.py`
- `docs/sources/cprm_geology.md`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Ler WFS GetCapabilities/DescribeFeatureType ou metadata ArcGIS; selecionar geologia/poços e conservar CRS, escala e geometria externa ao grafo. WMS só visualiza.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Criar migração para entidades/arestas propostas e registro no runner; piloto registra SourceDocument/IngestionRun e compara contagens/totais oficiais antes do histórico.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto por período/UF tem manifesto e contagens de lidos/aceitos/rejeitados; interrupção retoma sem duplicação.
- [ ] Reexecução da mesma versão conserva cardinalidades; revisão oficial preserva histórico.
- [ ] Ligações de amostra têm identificador exato e evidência; casos ambíguos permanecem pendentes, sem união por nome.
- [ ] Uma camada piloto tem contagem oficial e CRS/escala registrados; mesmos IDs em camadas diferentes não colidem.

## Riscos e decisões pendentes

- Mudança de leiaute/cobertura coloca a partição em quarentena até revisão do contrato.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/dados-geoespaciais/cprm-geologia.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/dados-geoespaciais/cprm-geologia.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
