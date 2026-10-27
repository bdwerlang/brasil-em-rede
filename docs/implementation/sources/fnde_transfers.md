# fnde_transfers — FNDE (Repasses)

Implementar aquisição, cadastro e ligações verificáveis de FNDE (Repasses).

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `fnde_transfers`.
- Ordem topológica: **17**; onda de execução: **2**; prioridade temática inicial: 2.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [ibge_geosciences](ibge_geosciences.md), [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://www.fnde.gov.br/dadosabertos/dataset](https://www.fnde.gov.br/dadosabertos/dataset).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.
- [etl/src/bracc_etl/pipelines/transferegov.py](../../../etl/src/bracc_etl/pipelines/transferegov.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.
- [etl/src/bracc_etl/pipelines/inep.py](../../../etl/src/bracc_etl/pipelines/inep.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.fnde.gov.br/dadosabertos/dataset](https://www.fnde.gov.br/dadosabertos/dataset) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/educacao/fnde-repasses.md |

- **Método:** Descobrir arquivos/endpoint na publicação oficial; baixar com timeout, backoff e limite de concorrência. Guardar bruto imutável, URL efetiva, hash SHA-256, bytes e instante de coleta.
- **Autenticação:** Não requerida Indicação importada, a confirmar no contrato oficial.
- **Formato bruto:** CSV
- **Partições e backfill:** Recurso, versão e período; dividir adicionalmente por UF quando suportado.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** annual no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Página de descoberta não é endpoint de dados; disponibilidade de URL não comprova completude.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: código município, UF, programa, valor repasse, ano referência, ente federativo, ação orçamentária. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Resolver recursos por programa PNAE/PNATE/PDDE e separar repasse, pagamento, devolução e autorizado. FUNDEB exige contrato próprio; conciliar eventos sobrepostos com transparencia/transferegov.

**Chave natural / namespace:** finance_id = FNDE + programa + documento/parcela + destinatário + exercício

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
| `Finance` | finance_id = FNDE + programa + documento/parcela + destinatário + exercício | existing |
| `Company` | cnpj | existing |
| `Territory` | territory_id | proposed |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `RECEBEU_REPASSE_FNDE` → `Finance` | CNPJ integral do destinatário declarado | Destinatário/executor não equivale a escola; papel, valor/estágio e parcela rastreáveis. | proposed |
| `Finance` → `DESTINADO_A` → `Territory` | código territorial oficial com período | Geografia beneficiada não identifica favorecido legal; ligação a escola/emenda depende de ID explícito. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_fnde_transfers.py`
- `etl/src/bracc_etl/pipelines/fnde_transfers.py`
- `etl/tests/test_fnde_transfers.py`
- `docs/sources/fnde_transfers.md`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Resolver recursos por programa PNAE/PNATE/PDDE e separar repasse, pagamento, devolução e autorizado. FUNDEB exige contrato próprio; conciliar eventos sobrepostos com transparencia/transferegov.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Criar migração para entidades/arestas propostas e registro no runner; piloto registra SourceDocument/IngestionRun e compara contagens/totais oficiais antes do histórico.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto por período/UF tem manifesto e contagens de lidos/aceitos/rejeitados; interrupção retoma sem duplicação.
- [ ] Reexecução da mesma versão conserva cardinalidades; revisão oficial preserva histórico.
- [ ] Ligações de amostra têm identificador exato e evidência; casos ambíguos permanecem pendentes, sem união por nome.
- [ ] Parcela/devolução são eventos distintos; total piloto por programa/UF/estágio reconcilia e escola só liga por INEP explícito.

## Riscos e decisões pendentes

- Mudança de leiaute/cobertura coloca a partição em quarentena até revisão do contrato.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/educacao/fnde-repasses.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/educacao/fnde-repasses.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
