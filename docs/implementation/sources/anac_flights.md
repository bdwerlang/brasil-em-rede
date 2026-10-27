# anac_flights — ANAC Aviação Civil — Voos, Passageiros e Aeroportos

Implementar aquisição, cadastro e ligações verificáveis de ANAC Aviação Civil — Voos, Passageiros e Aeroportos.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `anac_flights`.
- Ordem topológica: **74**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **M**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [ibge_geosciences](ibge_geosciences.md)
- Contrato de acesso catalogado: [https://www.gov.br/anac/pt-br/assuntos/dados-e-estatisticas](https://www.gov.br/anac/pt-br/assuntos/dados-e-estatisticas).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.gov.br/anac/pt-br/assuntos/dados-e-estatisticas](https://www.gov.br/anac/pt-br/assuntos/dados-e-estatisticas) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/infraestrutura-transportes/anac-aviacao.md |
| [https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/voos-e-operacoes-aereas/dados-estatisticos-do-transporte-aereo](https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/voos-e-operacoes-aereas/dados-estatisticos-do-transporte-aereo) | Produto estatístico CSV e seus metadados oficiais; não é VRA. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |

- **Método:** Descobrir arquivos/endpoint na publicação oficial; baixar com timeout, backoff e limite de concorrência. Guardar bruto imutável, URL efetiva, hash SHA-256, bytes e instante de coleta.
- **Autenticação:** Não requerida Indicação importada, a confirmar no contrato oficial.
- **Formato bruto:** CSV
- **Partições e backfill:** Recurso, versão e período; dividir adicionalmente por UF quando suportado.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** monthly no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Página de descoberta não é endpoint de dados; disponibilidade de URL não comprova completude.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: empresa_aerea, aeroporto_origem, aeroporto_destino, passageiros_pagos, carga_kg, assentos_ofertados, RPK, ASK. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Usar Dados Estatísticos do Transporte Aéreo, não VRA; separar etapas básicas/combinadas, criar Airport por ICAO e mapa empresa–CNPJ oficial com vigência.

**Chave natural / namespace:** ano/mês + empresa + origem/destino + natureza + tipo etapa + dimensões

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
| `FlightRouteObservation` | ano/mês + empresa + origem/destino + natureza + tipo etapa + dimensões | proposed |
| `Airport` | ICAO | proposed |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `FlightRouteObservation` → `ORIGEM_EM` → `Airport` | ICAO origem | Não confundir IATA e ICAO; aeroportos estrangeiros não ganham município IBGE. | proposed |
| `FlightRouteObservation` → `DESTINO_EM` → `Airport` | ICAO destino | Empresa/rota não identifica passageiro. | proposed |
| `Company` → `OPERADORA_OBSERVADA_EM` → `FlightRouteObservation` | mapa oficial código empresa–CNPJ válido no período | Sem união por nome de companhia; distinguir etapa básica/combinada. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_anac_flights.py`
- `etl/src/bracc_etl/pipelines/anac_flights.py`
- `etl/tests/test_anac_flights.py`
- `docs/sources/anac_flights.md`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Usar Dados Estatísticos do Transporte Aéreo, não VRA; separar etapas básicas/combinadas, criar Airport por ICAO e mapa empresa–CNPJ oficial com vigência.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Criar migração para entidades/arestas propostas e registro no runner; piloto registra SourceDocument/IngestionRun e compara contagens/totais oficiais antes do histórico.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto por período/UF tem manifesto e contagens de lidos/aceitos/rejeitados; interrupção retoma sem duplicação.
- [ ] Reexecução da mesma versão conserva cardinalidades; revisão oficial preserva histórico.
- [ ] Ligações de amostra têm identificador exato e evidência; casos ambíguos permanecem pendentes, sem união por nome.
- [ ] Passageiros/RPK/ASK de rota piloto conferem; etapa básica e combinada não são somadas em duplicidade.

## Riscos e decisões pendentes

- Mudança de leiaute/cobertura coloca a partição em quarentena até revisão do contrato.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/infraestrutura-transportes/anac-aviacao.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/infraestrutura-transportes/anac-aviacao.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`
- [https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/voos-e-operacoes-aereas/dados-estatisticos-do-transporte-aereo](https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/voos-e-operacoes-aereas/dados-estatisticos-do-transporte-aereo)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
