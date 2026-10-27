# basedosdados_catalog — Base dos Dados

Implementar aquisição, cadastro e ligações verificáveis de Base dos Dados.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `basedosdados_catalog`.
- Ordem topológica: **148**; onda de execução: **8**; prioridade temática inicial: 8.
- Tipo de trabalho: **Descoberta de recursos do catálogo**; complexidade relativa: **M**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://basedosdados.org/](https://basedosdados.org/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://basedosdados.org/](https://basedosdados.org/) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/portais-centrais/base-dos-dados.md |

- **Método:** Inventariar somente metadados por mecanismo oficial documentado; cada recurso real precisa de contrato, licença, chave, grão, fonte responsável e política de acesso. Não carregar dados de domínio pelo catálogo genérico.
- **Autenticação:** Catálogo público; BigQuery/ferramenta pode exigir projeto Google Cloud, credencial e gestão de custo, não API key universal.
- **Formato bruto:** JSON, CSV
- **Partições e backfill:** Recurso, versão e período; dividir adicionalmente por UF quando suportado.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** variable no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Página de descoberta não é endpoint de dados; disponibilidade de URL não comprova completude.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: dataset_id, table_id, id_municipio, ano, sigla_uf, CNPJ, CPF. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Inventariar metadados, licença, origem/cobertura e custo/acesso por recurso; BigQuery pode exigir projeto/credenciais, não presumir API key universal.

**Chave natural / namespace:** provedor + dataset_id + table_id + versão

Normalização:

- Preservar identificadores do catálogo e URLs efetivas por versão; recurso removido não apaga histórico.
- Catálogo não tem CPF/CNPJ de todas as bases: campos possíveis não são colunas universais.
- Deduplicar recurso já atribuído a fonte oficial; espelho é proveniência e não segundo evento/carga.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `DatasetResource` | provedor + dataset_id + table_id + versão | proposed |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| Sem relação nominal prevista | — | Registrar recurso/estatística conforme contrato; não inferir identidade | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `docs/sources/basedosdados_catalog.md`
- `docs/source-contracts/basedosdados_catalog.json`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Inventariar metadados, licença, origem/cobertura e custo/acesso por recurso; BigQuery pode exigir projeto/credenciais, não presumir API key universal.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Registrar contrato, gate e estado bloqueado/somente catálogo sem marcar dados como carregados; nenhuma implementação de acesso não autorizado.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Fixture sintética ou inventário de metadados validado, sem extração bulk de fonte restrita.
- [ ] Sem recurso/contrato/autorização, execução de carga fica desabilitada e status não simula implementação/cobertura.
- [ ] Cada metadado/gate de acesso tem evidência e campo de pendência; fonte sem recurso aberto não gera dados nem duplica outro ID do catálogo.
- [ ] Réplica de fonte já catalogada é proveniência, não segunda carga; tabelas listadas não são marcadas carregadas.

## Riscos e decisões pendentes

- Mudança de leiaute/cobertura coloca a partição em quarentena até revisão do contrato.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/portais-centrais/base-dos-dados.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/portais-centrais/base-dos-dados.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
