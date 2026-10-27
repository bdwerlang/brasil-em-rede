# bcb_sgs_reservas_internacionais — SGS/API BCB - Reservas Internacionais

Implementar aquisição, cadastro e ligações verificáveis de SGS/API BCB - Reservas Internacionais.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `bcb_sgs_reservas_internacionais`.
- Ordem topológica: **54**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **M**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://dadosabertos.bcb.gov.br/](https://dadosabertos.bcb.gov.br/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.
- [etl/src/bracc_etl/pipelines/bcb.py](../../../etl/src/bracc_etl/pipelines/bcb.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dadosabertos.bcb.gov.br/](https://dadosabertos.bcb.gov.br/) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/banco-central/sgs-reservas-internacionais.md |
| [https://dadosabertos.bcb.gov.br/api/3/action/package_search](https://dadosabertos.bcb.gov.br/api/3/action/package_search) | Descoberta oficial das séries/entidades SGS; selecionar recurso específico no contrato. | Catálogo CKAN oficial BCB consultado em 26/10/2026; séries/serviços conferidos. |

- **Método:** Consultar metadados oficiais por série/tabela; baixar recurso SGS com datas explícitas e limites adaptativos. 13982 liquidez diário; 13621 caixa diário, conceitos distintos
- **Autenticação:** Sem autenticação para recursos públicos; limites do serviço validados no piloto.
- **Formato bruto:** JSON, CSV, XML
- **Partições e backfill:** Serviço + código/tabela + período e dimensões; SGS em janelas anuais com datas explícitas; OData segue nextLink.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** Diária conforme conceito

Limites e pré-condições:

- Página de descoberta não é endpoint de dados; disponibilidade de URL não comprova completude.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: data, valor, posicao_reservas, composicao. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Fixar contrato individual: 13982 liquidez diário; 13621 caixa diário, conceitos distintos. Cliente SGS compartilhado; BcbPipeline existente é penalidades e não deve ser reutilizado como macroeconomia.

**Chave natural / namespace:** BCB + serviço/tabela + série/métrica + geografia/nível + período + dimensões + revisão

Normalização:

- Preservar códigos como strings e valores originais; vazio/ignorado não equivale a zero.
- Datas de evento, referência e coleta são campos distintos; manter histórico de revisão.
- Identificador completo válido permite ligação; nome isolado ou documento parcial não resolve identidade. CNPJ alfanumérico mantém letras, zeros e dígitos verificadores.
- Dados agregados: não criar Person/Company nem inferir instituição a partir de estatística PF/PJ.
- Estoque, fluxo e taxa são conceitos distintos; não somar taxas ou estoques mensais. Guardar unidade, escala e frequência por série.
- Projetar dimensões comuns conforme F09: Territory.territory_id=sistema:tipo:codigo:versao_territorial; EconomicActivity.activity_id=classificacao:versao:codigo; PublicBody.public_body_id=jurisdicao:sistema:identificador:versao. Aplicar somente as dimensões usadas nesta fonte, preservar códigos originais e validar crosswalks; município é Territory, sem dimensão paralela incompatível.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `EconomicObservation` | BCB + serviço/tabela + série/métrica + geografia/nível + período + dimensões + revisão | proposed |
| `Territory` | territory_id | proposed |
| `EconomicSeries` | provedor + serviço/tabela + código série/métrica + dimensões | proposed |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `EconomicObservation` → `REFERE_SE_A` → `Territory` | nível/código territorial publicado, namespace e versão; crosswalk oficial quando necessário | Guardar tabela/série, geografia e período; não desagregar UF/Brasil para município e nunca criar Person/Company de agregado. | proposed |
| `EconomicObservation` → `OBSERVACAO_DE` → `EconomicSeries` | código/série/tabela/métrica e dimensões | Unidade, frequência, estoque/fluxo/taxa e revisão não se confundem; comparação entre provedores exige conceito/período compatíveis. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_bcb_sgs_reservas_internacionais.py`
- `etl/src/bracc_etl/pipelines/bcb_sgs_reservas_internacionais.py`
- `etl/tests/test_bcb_sgs_reservas_internacionais.py`
- `docs/sources/bcb_sgs_reservas_internacionais.md`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Fixar contrato individual: 13982 liquidez diário; 13621 caixa diário, conceitos distintos. Cliente SGS compartilhado; BcbPipeline existente é penalidades e não deve ser reutilizado como macroeconomia.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Criar migração para entidades/arestas propostas e registro no runner; piloto registra SourceDocument/IngestionRun e compara contagens/totais oficiais antes do histórico.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto por período/UF tem manifesto e contagens de lidos/aceitos/rejeitados; interrupção retoma sem duplicação.
- [ ] Reexecução da mesma versão conserva cardinalidades; revisão oficial preserva histórico.
- [ ] Ligações de amostra têm identificador exato e evidência; casos ambíguos permanecem pendentes, sem união por nome.
- [ ] Cada observação tem tabela/série, geografia Brasil ou nível explicitamente divulgado, período, unidade e conceito; 12 meses/dias piloto reproduzem recurso sem Person/Company.

## Riscos e decisões pendentes

- Mudança de leiaute/cobertura coloca a partição em quarentena até revisão do contrato.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/banco-central/sgs-reservas-internacionais.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/banco-central/sgs-reservas-internacionais.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`
- [https://dadosabertos.bcb.gov.br/api/3/action/package_search](https://dadosabertos.bcb.gov.br/api/3/action/package_search)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
