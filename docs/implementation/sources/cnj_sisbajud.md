# cnj_sisbajud — SISBAJUD — Sistema de Busca de Ativos do Poder Judiciário

Implementar aquisição, cadastro e ligações verificáveis de SISBAJUD — Sistema de Busca de Ativos do Poder Judiciário.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `cnj_sisbajud`.
- Ordem topológica: **151**; onda de execução: **8**; prioridade temática inicial: 8.
- Tipo de trabalho: **Acesso condicionado / restrito**; complexidade relativa: **XL**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://sisbajud.cnj.jus.br/](https://sisbajud.cnj.jus.br/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://sisbajud.cnj.jus.br/](https://sisbajud.cnj.jus.br/) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/poder-judiciario-cnj/sisbajud.md |
| [https://www.cnj.jus.br/sistemas/sisbajud/](https://www.cnj.jus.br/sistemas/sisbajud/) | Ordens judiciais e ativos financeiros; não há fonte pública bulk estabelecida. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |
| [https://docs.pdpj.jus.br/servicos-negociais/sisbajud/](https://docs.pdpj.jus.br/servicos-negociais/sisbajud/) | Perfis judiciais e credenciamento pelo administrador do tribunal. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |

- **Método:** Nenhuma extração pública ou chamada real. Contrato e fixture sintética; eventual implementação só em ambiente judicial autorizado e segregado do grafo público.
- **Autenticação:** Somente perfis judiciais e credenciamento institucional; sem acesso público bulk.
- **Formato bruto:** JSON (interno)
- **Partições e backfill:** Recurso, versão e período; dividir adicionalmente por UF quando suportado.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** realtime no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Dados bancários/ordens são restritos; não prometer download, acesso por usuário comum ou publicação no grafo público.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: numero_processo, CPF, CNPJ, valor_bloqueio, instituicao_financeira. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Excluir do universo público; desenhar somente contrato e protótipo sintético desabilitado, com segregação/auditoria/retenção para eventual ambiente judicial autorizado.

**Chave natural / namespace:** ambiente institucional + ordem/evento + versão

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
| `JudicialAssetOrder` | ambiente institucional + ordem/evento + versão | proposed |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| Sem relação nominal prevista | — | Registrar recurso/estatística conforme contrato; não inferir identidade | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `docs/sources/cnj_sisbajud.md`
- `docs/source-contracts/cnj_sisbajud.json`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Excluir do universo público; desenhar somente contrato e protótipo sintético desabilitado, com segregação/auditoria/retenção para eventual ambiente judicial autorizado. Acesso não será solicitado nem executado nesta etapa de plano.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Registrar contrato, gate e estado bloqueado/somente catálogo sem marcar dados como carregados; nenhuma implementação de acesso não autorizado.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Fixture sintética ou inventário de metadados validado, sem extração bulk de fonte restrita.
- [ ] Sem recurso/contrato/autorização, execução de carga fica desabilitada e status não simula implementação/cobertura.
- [ ] Cada metadado/gate de acesso tem evidência e campo de pendência; fonte sem recurso aberto não gera dados nem duplica outro ID do catálogo.
- [ ] Rotina pública falha fechada, sem ordens/contas bancárias reais, endpoints privados ou credenciais; nenhum dado entra no grafo público.

## Riscos e decisões pendentes

- Dados bancários/ordens são restritos; não prometer download, acesso por usuário comum ou publicação no grafo público.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/poder-judiciario-cnj/sisbajud.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/poder-judiciario-cnj/sisbajud.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`
- [https://www.cnj.jus.br/sistemas/sisbajud/](https://www.cnj.jus.br/sistemas/sisbajud/)
- [https://docs.pdpj.jus.br/servicos-negociais/sisbajud/](https://docs.pdpj.jus.br/servicos-negociais/sisbajud/)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
