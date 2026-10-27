# tesouro_catalog — Tesouro Transparente

Implementar aquisição, cadastro e ligações verificáveis de Tesouro Transparente.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `tesouro_catalog`.
- Ordem topológica: **168**; onda de execução: **8**; prioridade temática inicial: 8.
- Tipo de trabalho: **Descoberta de recursos do catálogo**; complexidade relativa: **M**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://apidatalake.tesouro.gov.br/docs/sadipem/](https://apidatalake.tesouro.gov.br/docs/sadipem/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://apidatalake.tesouro.gov.br/docs/sadipem/](https://apidatalake.tesouro.gov.br/docs/sadipem/) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/portais-centrais/tesouro-transparente.md |
| [https://www.tesourotransparente.gov.br/ckan/](https://www.tesourotransparente.gov.br/ckan/) | Catálogo de conjuntos do Tesouro, diferente da API SADIPem. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |
| [https://apidatalake.tesouro.gov.br/docs/sadipem/](https://apidatalake.tesouro.gov.br/docs/sadipem/) | OpenAPI indica PVL, dívida/operações/garantias; limite documentado de1 req/s e páginas padrão5000 para esse subproduto. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |

- **Método:** Inventariar somente metadados por mecanismo oficial documentado; cada recurso real precisa de contrato, licença, chave, grão, fonte responsável e política de acesso. Não carregar dados de domínio pelo catálogo genérico.
- **Autenticação:** Não requerida Indicação importada, a confirmar no contrato oficial.
- **Formato bruto:** JSON, CSV
- **Partições e backfill:** Recurso, versão e período; dividir adicionalmente por UF quando suportado.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** monthly no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Página de descoberta não é endpoint de dados; disponibilidade de URL não comprova completude.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: código IBGE, código SIAFI, exercício (ano), UF. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Corrigir referência genérica SADIPem: dívida/garantias/PVL é subproduto; inventariar CKAN/Data Lake e remeter siconfi/siop/tesouro_emendas a contratos próprios.

**Chave natural / namespace:** provedor + dataset_id + resource_id + versão

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
| `DatasetResource` | provedor + dataset_id + resource_id + versão | proposed |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| Sem relação nominal prevista | — | Registrar recurso/estatística conforme contrato; não inferir identidade | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `docs/sources/tesouro_catalog.md`
- `docs/source-contracts/tesouro_catalog.json`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Corrigir referência genérica SADIPem: dívida/garantias/PVL é subproduto; inventariar CKAN/Data Lake e remeter siconfi/siop/tesouro_emendas a contratos próprios.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Registrar contrato, gate e estado bloqueado/somente catálogo sem marcar dados como carregados; nenhuma implementação de acesso não autorizado.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Fixture sintética ou inventário de metadados validado, sem extração bulk de fonte restrita.
- [ ] Sem recurso/contrato/autorização, execução de carga fica desabilitada e status não simula implementação/cobertura.
- [ ] Cada metadado/gate de acesso tem evidência e campo de pendência; fonte sem recurso aberto não gera dados nem duplica outro ID do catálogo.
- [ ] SADIPem não é rotulado execução SIAFI nem todo Tesouro; recurso já atribuído não gera segunda ingestão.

## Riscos e decisões pendentes

- Mudança de leiaute/cobertura coloca a partição em quarentena até revisão do contrato.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/portais-centrais/tesouro-transparente.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/portais-centrais/tesouro-transparente.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`
- [https://www.tesourotransparente.gov.br/ckan/](https://www.tesourotransparente.gov.br/ckan/)
- [https://apidatalake.tesouro.gov.br/docs/sadipem/](https://apidatalake.tesouro.gov.br/docs/sadipem/)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
