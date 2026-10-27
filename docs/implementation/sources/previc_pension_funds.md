# previc_pension_funds — PREVIC — Previdência Complementar Fechada

Implementar aquisição, cadastro e ligações verificáveis de PREVIC — Previdência Complementar Fechada.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `previc_pension_funds`.
- Ordem topológica: **67**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **M**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://www.gov.br/previc/pt-br/acesso-a-informacao/dados-abertos](https://www.gov.br/previc/pt-br/acesso-a-informacao/dados-abertos).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.gov.br/previc/pt-br/acesso-a-informacao/dados-abertos](https://www.gov.br/previc/pt-br/acesso-a-informacao/dados-abertos) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/previdencia-social/previc.md |
| [https://www.gov.br/previc/pt-br/sistemas/informacoes-sobre-os-sistemas-previc/cadastro-de-entidades-e-planos-cadprevic/cadastro-de-entidades-e-planos-cadprevic](https://www.gov.br/previc/pt-br/sistemas/informacoes-sobre-os-sistemas-previc/cadastro-de-entidades-e-planos-cadprevic/cadastro-de-entidades-e-planos-cadprevic) | Escopo oficial entidades, planos e patrocinadores; não comprova download irrestrito do sistema transacional. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |

- **Método:** Descobrir arquivos/endpoint na publicação oficial; baixar com timeout, backoff e limite de concorrência. Guardar bruto imutável, URL efetiva, hash SHA-256, bytes e instante de coleta.
- **Autenticação:** Não requerida (dados públicos) / Gov.br (CADPREVIC restrito) Indicação importada, a confirmar no contrato oficial.
- **Formato bruto:** CSV, XLSX, PDF, JSON (CADPREVIC)
- **Partições e backfill:** Recurso, versão e período; dividir adicionalmente por UF quando suportado.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** variable no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Página de descoberta não é endpoint de dados; disponibilidade de URL não comprova completude.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: cnpj_efpc, nome_entidade, patrocinador, total_ativos, patrimonio_liquido, numero_participantes. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Resolver arquivos PREVIC públicos por CNPJ/CNPB e patrocínio, sem acesso ao CADPREVIC transacional; separar plano, EFPC e consolidado financeiro.

**Chave natural / namespace:** CNPB; indicador: tabela + entidade/plano + período + métrica + revisão

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
| `PensionPlan` | CNPB; indicador: tabela + entidade/plano + período + métrica + revisão | proposed |
| `Company` | cnpj | existing |
| `PensionStatistic` | tabela + plano/entidade + período + métrica + revisão | proposed |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `ADMINISTRA_PLANO` → `PensionPlan` | CNPJ EFPC + CNPB publicados | CNPB não é CNPJ; separar plano e entidade. | proposed |
| `Company` → `PATROCINA_PLANO` → `PensionPlan` | CNPJ patrocinador/instituidor + CNPB publicados | Papel e vigência explícitos; não inferir patrocínio por nome. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_previc_pension_funds.py`
- `etl/src/bracc_etl/pipelines/previc_pension_funds.py`
- `etl/tests/test_previc_pension_funds.py`
- `docs/sources/previc_pension_funds.md`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Resolver arquivos PREVIC públicos por CNPJ/CNPB e patrocínio, sem acesso ao CADPREVIC transacional; separar plano, EFPC e consolidado financeiro.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Criar migração para entidades/arestas propostas e registro no runner; piloto registra SourceDocument/IngestionRun e compara contagens/totais oficiais antes do histórico.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto por período/UF tem manifesto e contagens de lidos/aceitos/rejeitados; interrupção retoma sem duplicação.
- [ ] Reexecução da mesma versão conserva cardinalidades; revisão oficial preserva histórico.
- [ ] Ligações de amostra têm identificador exato e evidência; casos ambíguos permanecem pendentes, sem união por nome.
- [ ] Dois planos da EFPC mantêm CNPB distintos; patrocinador sem CNPJ não é resolvido por nome e consolidado não duplica planos.

## Riscos e decisões pendentes

- Mudança de leiaute/cobertura coloca a partição em quarentena até revisão do contrato.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/previdencia-social/previc.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/previdencia-social/previc.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`
- [https://www.gov.br/previc/pt-br/sistemas/informacoes-sobre-os-sistemas-previc/cadastro-de-entidades-e-planos-cadprevic/cadastro-de-entidades-e-planos-cadprevic](https://www.gov.br/previc/pt-br/sistemas/informacoes-sobre-os-sistemas-previc/cadastro-de-entidades-e-planos-cadprevic/cadastro-de-entidades-e-planos-cadprevic)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
