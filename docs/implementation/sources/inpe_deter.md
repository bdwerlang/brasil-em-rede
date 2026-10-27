# inpe_deter — DETER — Alertas de Desmatamento em Tempo Real (INPE)

Implementar aquisição, cadastro e ligações verificáveis de DETER — Alertas de Desmatamento em Tempo Real (INPE).

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `inpe_deter`.
- Ordem topológica: **99**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **M**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [ibge_geosciences](ibge_geosciences.md)
- Contrato de acesso catalogado: [http://terrabrasilis.dpi.inpe.br/](http://terrabrasilis.dpi.inpe.br/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [http://terrabrasilis.dpi.inpe.br/](http://terrabrasilis.dpi.inpe.br/) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/meio-ambiente/deter.md |
| [https://terrabrasilis.dpi.inpe.br/download-de-dados/](https://terrabrasilis.dpi.inpe.br/download-de-dados/) | Downloads ZIP e serviço WFS oficiais por programa/bioma. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |
| [https://terrabrasilis.dpi.inpe.br/faq/](https://terrabrasilis.dpi.inpe.br/faq/) | Distingue DETER/PRODES e acesso antecipado apenas institucional. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |
| [https://terrabrasilis.dpi.inpe.br/geoserver/ows](https://terrabrasilis.dpi.inpe.br/geoserver/ows) | Serviço indicado pelo FAQ; resolver nomes de camada por GetCapabilities. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |

- **Método:** Descobrir arquivos/endpoint na publicação oficial; baixar com timeout, backoff e limite de concorrência. Guardar bruto imutável, URL efetiva, hash SHA-256, bytes e instante de coleta.
- **Autenticação:** Não requerida Indicação importada, a confirmar no contrato oficial.
- **Formato bruto:** Shapefile, GeoJSON, CSV
- **Partições e backfill:** Recurso, versão e período; dividir adicionalmente por UF quando suportado.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** daily no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Página de descoberta não é endpoint de dados; disponibilidade de URL não comprova completude.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: data_alerta, area_km2, municipio, UF, classe_alerta, coordenadas_poligono. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Descobrir camadas públicas WFS/ZIP DETER e registrar classe, detecção/publicação/área; acesso antecipado institucional excluído. Alertas não equivalem à taxa anual PRODES.

**Chave natural / namespace:** programa + bioma + camada + UUID/ID + versão

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
| `DeforestationAlert` | programa + bioma + camada + UUID/ID + versão | proposed |
| `Territory` | territory_id | proposed |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `DeforestationAlert` → `INTERSECTA` → `Territory` | interseção espacial versionada | Guardar tabela/série, geografia e período; algoritmo, projeção, área/distância e versões são evidência derivada, sem atribuir propriedade/autoria. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_inpe_deter.py`
- `etl/src/bracc_etl/pipelines/inpe_deter.py`
- `etl/tests/test_inpe_deter.py`
- `docs/sources/inpe_deter.md`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Descobrir camadas públicas WFS/ZIP DETER e registrar classe, detecção/publicação/área; acesso antecipado institucional excluído. Alertas não equivalem à taxa anual PRODES.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Criar migração para entidades/arestas propostas e registro no runner; piloto registra SourceDocument/IngestionRun e compara contagens/totais oficiais antes do histórico.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto por período/UF tem manifesto e contagens de lidos/aceitos/rejeitados; interrupção retoma sem duplicação.
- [ ] Reexecução da mesma versão conserva cardinalidades; revisão oficial preserva histórico.
- [ ] Ligações de amostra têm identificador exato e evidência; casos ambíguos permanecem pendentes, sem união por nome.
- [ ] UUID/área oficiais preservados; ausência sob nuvens não vira zero e interseção com CAR não identifica autor.

## Riscos e decisões pendentes

- Mudança de leiaute/cobertura coloca a partição em quarentena até revisão do contrato.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/meio-ambiente/deter.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/meio-ambiente/deter.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`
- [https://terrabrasilis.dpi.inpe.br/download-de-dados/](https://terrabrasilis.dpi.inpe.br/download-de-dados/)
- [https://terrabrasilis.dpi.inpe.br/faq/](https://terrabrasilis.dpi.inpe.br/faq/)
- [https://terrabrasilis.dpi.inpe.br/geoserver/ows](https://terrabrasilis.dpi.inpe.br/geoserver/ows)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
