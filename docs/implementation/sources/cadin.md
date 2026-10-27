# cadin — CADIN — Cadastro de Devedores do Governo Federal

Implementar aquisição, cadastro e ligações verificáveis de CADIN — Cadastro de Devedores do Governo Federal.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `cadin`.
- Ordem topológica: **149**; onda de execução: **8**; prioridade temática inicial: 8.
- Tipo de trabalho: **Acesso condicionado / restrito**; complexidade relativa: **M**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://cadin.pgfn.gov.br/](https://cadin.pgfn.gov.br/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.
- [etl/src/bracc_etl/pipelines/pgfn.py](../../../etl/src/bracc_etl/pipelines/pgfn.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://cadin.pgfn.gov.br/](https://cadin.pgfn.gov.br/) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/apis-governamentais/cadin.md |
| [https://www.gov.br/pgfn/pt-br/servicos/perguntas-frequentes/perguntas-frequentes-sobre-o-cadin-pgfn](https://www.gov.br/pgfn/pt-br/servicos/perguntas-frequentes/perguntas-frequentes-sobre-o-cadin-pgfn) | FAQ distingue visão do cidadão e acesso/integração por órgãos habilitados. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |

- **Método:** Nenhuma extração pública em massa. Adaptador desabilitado até comprovar autorização institucional, operações/campos liberados e retenção; produzir contrato/fixture sintética.
- **Autenticação:** Órgão/entidade habilitado e perfil de consulta; integração institucional conforme PGFN. Visão cidadão cobre as próprias pendências.
- **Formato bruto:** JSON
- **Partições e backfill:** Recurso, versão e período; dividir adicionalmente por UF quando suportado.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** daily no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Consulta pública universal/bulk CADIN não comprovada; dívida não é sanção e campo valor não deve ser presumido.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: cpf_cnpj, nome_devedor, orgao_credor, valor_debito, data_inclusao. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Desenhar adaptador desabilitado até habilitação institucional CADIN; pgfn é alternativa pública com universo diferente.

**Chave natural / namespace:** órgão credor + ID do registro + evento/versão

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
| `CadinRegistration` | órgão credor + ID do registro + evento/versão | proposed |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `REGISTRADA_NO_CADIN` → `CadinRegistration` | CNPJ completo autorizado e validado | Habilitar somente em ambiente institucional autorizado; situação e validade atualizadas; dívida não é sanção. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `docs/sources/cadin.md`
- `docs/source-contracts/cadin.json`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Desenhar adaptador desabilitado até habilitação institucional CADIN; pgfn é alternativa pública com universo diferente. Acesso não será solicitado nem executado nesta etapa de plano.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Registrar contrato, gate e estado bloqueado/somente catálogo sem marcar dados como carregados; nenhuma implementação de acesso não autorizado.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Fixture sintética ou inventário de metadados validado, sem extração bulk de fonte restrita.
- [ ] Sem recurso/contrato/autorização, execução de carga fica desabilitada e status não simula implementação/cobertura.
- [ ] Cada metadado/gate de acesso tem evidência e campo de pendência; fonte sem recurso aberto não gera dados nem duplica outro ID do catálogo.
- [ ] Sem habilitação não ocorre chamada/carga; fixture sintética cobre inclusão, suspensão e exclusão.

## Riscos e decisões pendentes

- Consulta pública universal/bulk CADIN não comprovada; dívida não é sanção e campo valor não deve ser presumido.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/apis-governamentais/cadin.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/apis-governamentais/cadin.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`
- [https://www.gov.br/pgfn/pt-br/servicos/perguntas-frequentes/perguntas-frequentes-sobre-o-cadin-pgfn](https://www.gov.br/pgfn/pt-br/servicos/perguntas-frequentes/perguntas-frequentes-sobre-o-cadin-pgfn)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
