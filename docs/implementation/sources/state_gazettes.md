# state_gazettes — DOEs Estaduais — Diários Oficiais dos Estados

Implementar aquisição, cadastro e ligações verificáveis de DOEs Estaduais — Diários Oficiais dos Estados.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `state_gazettes`.
- Ordem topológica: **125**; onda de execução: **7**; prioridade temática inicial: 7.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **XL**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://queridodiario.ok.org.br/](https://queridodiario.ok.org.br/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.
- [etl/src/bracc_etl/pipelines/querido_diario.py](../../../etl/src/bracc_etl/pipelines/querido_diario.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.
- [etl/src/bracc_etl/pipelines/dou.py](../../../etl/src/bracc_etl/pipelines/dou.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://queridodiario.ok.org.br/](https://queridodiario.ok.org.br/) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/diarios-oficiais/does-estaduais.md |

- **Método:** Gate de cobertura: inventariar portais oficiais de cada UF e DF; Querido Diário municipal não substitui DOE estadual. Download por editor/edição/suplemento e OCR quando necessário, sem contornar CAPTCHA.
- **Autenticação:** Depende do portal estadual; bloquear adaptador sem acesso permitido/documentado.
- **Formato bruto:** JSON, PDF, TXT, HTML
- **Partições e backfill:** UF + editor + ano/mês + data + edição + suplemento + revisão.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** daily no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Página de descoberta não é endpoint de dados; disponibilidade de URL não comprova completude.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: territory_id, date, querystring, txt_url, edition. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Resolver escopo incorreto: Querido Diário existente cobre municipal; inventariar DOEs oficiais das 26 UFs e DF e implementar adaptador por portal, começando por dois estados.

**Chave natural / namespace:** UF + editor + edição/data + suplemento + trecho + versão

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
| `StateGazetteAct` | UF + editor + edição/data + suplemento + trecho + versão | proposed |
| `SourceDocument` | doc_id | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `StateGazetteAct` → `EXTRAIDO_DE` → `SourceDocument` | doc_id + página/posição textual | Guardar PDF/HTML original, hash, edição/suplemento e OCR separado; novo conteúdo revisa versão. | proposed |
| `StateGazetteAct` → `MENCIONA` → `Company` | CNPJ completo válido publicado no trecho | É menção textual, sem inferir contrato, sociedade ou irregularidade; OCR incerto fica pendente. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_state_gazettes.py`
- `etl/src/bracc_etl/pipelines/state_gazettes.py`
- `etl/tests/test_state_gazettes.py`
- `docs/sources/state_gazettes.md`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Resolver escopo incorreto: Querido Diário existente cobre municipal; inventariar DOEs oficiais das 26 UFs e DF e implementar adaptador por portal, começando por dois estados.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Criar migração para entidades/arestas propostas e registro no runner; piloto registra SourceDocument/IngestionRun e compara contagens/totais oficiais antes do histórico.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto por período/UF tem manifesto e contagens de lidos/aceitos/rejeitados; interrupção retoma sem duplicação.
- [ ] Reexecução da mesma versão conserva cardinalidades; revisão oficial preserva histórico.
- [ ] Ligações de amostra têm identificador exato e evidência; casos ambíguos permanecem pendentes, sem união por nome.
- [ ] Documento piloto é estadual verificado; nenhum territory_id municipal é usado como UF; suplemento/retificação preserva identidade e menções têm página/trecho.

## Riscos e decisões pendentes

- Não existe endpoint uniforme de DOEs no catálogo; cobertura depende de inventário estadual e pode permanecer parcial. Menção textual não comprova contrato/irregularidade.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/diarios-oficiais/does-estaduais.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/diarios-oficiais/does-estaduais.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
