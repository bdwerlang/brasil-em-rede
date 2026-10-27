# cnj_bnmp — BNMP 3.0 — Banco Nacional de Medidas Penais e Prisões

Implementar aquisição, cadastro e ligações verificáveis de BNMP 3.0 — Banco Nacional de Medidas Penais e Prisões.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `cnj_bnmp`.
- Ordem topológica: **150**; onda de execução: **8**; prioridade temática inicial: 8.
- Tipo de trabalho: **Acesso condicionado / restrito**; complexidade relativa: **M**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [datajud](datajud.md)
- Contrato de acesso catalogado: [https://portalbnmp.cnj.jus.br/](https://portalbnmp.cnj.jus.br/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.
- [etl/src/bracc_etl/pipelines/datajud.py](../../../etl/src/bracc_etl/pipelines/datajud.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://portalbnmp.cnj.jus.br/](https://portalbnmp.cnj.jus.br/) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/poder-judiciario-cnj/bnmp.md |
| [https://www.cnj.jus.br/perguntas-frequentes/](https://www.cnj.jus.br/perguntas-frequentes/) | Consulta pública de peças pendentes/vigentes com CAPTCHA; acesso institucional por credenciamento/cooperação. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |

- **Método:** Sem contornar CAPTCHA ou consultar endpoints privados. Gate de acesso em massa; somente exportação/API expressamente autorizada permite ingestão restrita com atualização de situação.
- **Autenticação:** Público: consulta limitada com CAPTCHA. Institucional: credenciamento/cooperação conforme CNJ.
- **Formato bruto:** HTML, JSON
- **Partições e backfill:** Recurso, versão e período; dividir adicionalmente por UF quando suportado.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** realtime no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Mandados desatualizados não podem ser apresentados como vigentes; pessoa homônima não identifica requerido e mandado não prova culpa.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: numero_mandado, numero_processo, CPF, nome_pessoa, tipo_peca. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Documentar consulta pública limitada com CAPTCHA e gate bulk institucional; apenas exportação/API expressamente autorizada permite adaptador, com revogação/cumprimento.

**Chave natural / namespace:** BNMP + ID/número peça + versão/situação

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
| `JudicialWarrant` | BNMP + ID/número peça + versão/situação | proposed |
| `JudicialCase` | judicial_case_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `JudicialWarrant` → `PECA_DO_PROCESSO` → `JudicialCase` | número CNJ completo publicado/validado | Somente importação autorizada; peça revogada/cumprida exige revisão e mandado não comprova condenação. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `docs/sources/cnj_bnmp.md`
- `docs/source-contracts/cnj_bnmp.json`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Documentar consulta pública limitada com CAPTCHA e gate bulk institucional; apenas exportação/API expressamente autorizada permite adaptador, com revogação/cumprimento. Acesso não será solicitado nem executado nesta etapa de plano.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Registrar contrato, gate e estado bloqueado/somente catálogo sem marcar dados como carregados; nenhuma implementação de acesso não autorizado.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Fixture sintética ou inventário de metadados validado, sem extração bulk de fonte restrita.
- [ ] Sem recurso/contrato/autorização, execução de carga fica desabilitada e status não simula implementação/cobertura.
- [ ] Cada metadado/gate de acesso tem evidência e campo de pendência; fonte sem recurso aberto não gera dados nem duplica outro ID do catálogo.
- [ ] Sem autorização não há download em massa/contorno de CAPTCHA; fixture atualiza revogado e não resolve Person por nome.

## Riscos e decisões pendentes

- Mandados desatualizados não podem ser apresentados como vigentes; pessoa homônima não identifica requerido e mandado não prova culpa.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/poder-judiciario-cnj/bnmp.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/poder-judiciario-cnj/bnmp.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`
- [https://www.cnj.jus.br/perguntas-frequentes/](https://www.cnj.jus.br/perguntas-frequentes/)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
