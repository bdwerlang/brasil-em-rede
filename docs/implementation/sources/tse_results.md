# tse_results — Resultados Eleitorais

Implementar aquisição, cadastro e ligações verificáveis de Resultados Eleitorais.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `tse_results`.
- Ordem topológica: **38**; onda de execução: **3**; prioridade temática inicial: 3.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **M**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [tse](tse.md)
- Contrato de acesso catalogado: [https://dadosabertos.tse.jus.br/](https://dadosabertos.tse.jus.br/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.
- [etl/src/bracc_etl/pipelines/tse.py](../../../etl/src/bracc_etl/pipelines/tse.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dadosabertos.tse.jus.br/](https://dadosabertos.tse.jus.br/) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/justica-eleitoral-tse/resultados-eleitorais.md |

- **Método:** Descobrir arquivos/endpoint na publicação oficial; baixar com timeout, backoff e limite de concorrência. Guardar bruto imutável, URL efetiva, hash SHA-256, bytes e instante de coleta.
- **Autenticação:** Não requerida Indicação importada, a confirmar no contrato oficial.
- **Formato bruto:** CSV
- **Partições e backfill:** Recurso, versão e período; dividir adicionalmente por UF quando suportado.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** per_election no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Página de descoberta não é endpoint de dados; disponibilidade de URL não comprova completude.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: numero_candidato, codigo_municipio, zona_eleitoral, secao_eleitoral, quantidade_votos, ano_eleicao. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Separar resultados de candidatos/doações do pipeline tse; vincular candidatura por SQ_CANDIDATO+pleito e código oficial, nunca número ou nome isolado.

**Chave natural / namespace:** pleito + turno + cargo + território + candidato/partido/opção + tipo voto + revisão

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
| `ElectionResult` | pleito + turno + cargo + território + candidato/partido/opção + tipo voto + revisão | proposed |
| `ElectionContest` | código eleição + turno + cargo + circunscrição | proposed |
| `Person` | cpf | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `ElectionResult` → `RESULTADO_DO_PLEITO` → `ElectionContest` | pleito + turno + cargo + circunscrição | Suplementar e turno são chaves, não apenas ano. | proposed |
| `Person` → `OBTEVE_RESULTADO` → `ElectionResult` | SQ_CANDIDATO + pleito cruzado com tse; CPF integral validado quando público | Número/nome não resolvem identidade; sem crosswalk seguro, manter resultado com candidatura local sem Person. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_tse_results.py`
- `etl/src/bracc_etl/pipelines/tse_results.py`
- `etl/tests/test_tse_results.py`
- `docs/sources/tse_results.md`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Separar resultados de candidatos/doações do pipeline tse; vincular candidatura por SQ_CANDIDATO+pleito e código oficial, nunca número ou nome isolado.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Criar migração para entidades/arestas propostas e registro no runner; piloto registra SourceDocument/IngestionRun e compara contagens/totais oficiais antes do histórico.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto por período/UF tem manifesto e contagens de lidos/aceitos/rejeitados; interrupção retoma sem duplicação.
- [ ] Reexecução da mesma versão conserva cardinalidades; revisão oficial preserva histórico.
- [ ] Ligações de amostra têm identificador exato e evidência; casos ambíguos permanecem pendentes, sem união por nome.
- [ ] Seção agrega ao município sob mesmo tipo/versão; turno e eleição suplementar no mesmo ano não colidem.

## Riscos e decisões pendentes

- Mudança de leiaute/cobertura coloca a partição em quarentena até revisão do contrato.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/justica-eleitoral-tse/resultados-eleitorais.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/justica-eleitoral-tse/resultados-eleitorais.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
