# cnpj_simples — Simples Nacional / MEI

Implementar aquisição, cadastro e ligações verificáveis de Simples Nacional / MEI.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `cnpj_simples`.
- Ordem topológica: **5**; onda de execução: **1**; prioridade temática inicial: 1.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **M**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://www.gov.br/receitafederal/dados](https://www.gov.br/receitafederal/dados).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.
- [etl/src/bracc_etl/pipelines/cnpj.py](../../../etl/src/bracc_etl/pipelines/cnpj.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.
- [etl/src/bracc_etl/transforms/document_formatting.py](../../../etl/src/bracc_etl/transforms/document_formatting.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.gov.br/receitafederal/dados](https://www.gov.br/receitafederal/dados) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/receita-federal/simples-nacional.md |
| [https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico/cnpj-alfa](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico/cnpj-alfa) | CNPJ admite letras nas novas inscrições desde2026; tratar como string e normalizar apenas máscara/caixa. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |
| [https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/documentos-tecnicos/cnpj](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/documentos-tecnicos/cnpj) | Referência técnica oficial de cálculo do DV alfanumérico. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |

- **Método:** Reutilizar manifesto/download do dump CNPJ e selecionar arquivo Simples do MESMO snapshot; ler CSV sem cabeçalho por leiaute, dtype string, em streaming. Sem consulta empresa a empresa.
- **Autenticação:** Não requerida Indicação importada, a confirmar no contrato oficial.
- **Formato bruto:** CSV
- **Partições e backfill:** Snapshot mensal + arquivo Simples do mesmo dump CNPJ.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** monthly no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Página de descoberta não é endpoint de dados; disponibilidade de URL não comprova completude.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: CNPJ básico, opção pelo Simples, opção pelo MEI. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Reutilizar arquivo Simples do mesmo dump CNPJ, não baixar cadastro duplicado; raiz de 8 posições liga a empresas por raiz existente, sem inventar 0001/DV.

**Chave natural / namespace:** CNPJ básico + snapshot + regime + vigência

Normalização:

- Preservar códigos como strings e valores originais; vazio/ignorado não equivale a zero.
- Datas de evento, referência e coleta são campos distintos; manter histórico de revisão.
- Identificador completo válido permite ligação; nome isolado ou documento parcial não resolve identidade. CNPJ alfanumérico mantém letras, zeros e dígitos verificadores.
- Auditar document_formatting e demais normalizadores compartilhados: strip_document apenas numérico destrói chaves alfanuméricas. Fixture numérica/alfanumérica e DV conforme referência oficial são pré-requisito.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `TaxRegimeSnapshot` | CNPJ básico + snapshot + regime + vigência | proposed |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `REGIME_TRIBUTARIO_OBSERVADO` → `TaxRegimeSnapshot` | raiz cnpj_root já validada do cnpj = básico do arquivo no mesmo snapshot | Não criar estabelecimento fictício; regime é da raiz e mantém datas de opção/exclusão. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_cnpj_simples.py`
- `etl/src/bracc_etl/pipelines/cnpj_simples.py`
- `etl/tests/test_cnpj_simples.py`
- `docs/sources/cnpj_simples.md`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Reutilizar arquivo Simples do mesmo dump CNPJ, não baixar cadastro duplicado; raiz de 8 posições liga a empresas por raiz existente, sem inventar 0001/DV.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Criar migração para entidades/arestas propostas e registro no runner; piloto registra SourceDocument/IngestionRun e compara contagens/totais oficiais antes do histórico.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto por período/UF tem manifesto e contagens de lidos/aceitos/rejeitados; interrupção retoma sem duplicação.
- [ ] Reexecução da mesma versão conserva cardinalidades; revisão oficial preserva histórico.
- [ ] Ligações de amostra têm identificador exato e evidência; casos ambíguos permanecem pendentes, sem união por nome.
- [ ] CNPJ alfanumérico preserva letras; raiz não vira empresa completa fictícia e datas opção/exclusão preservam história.

## Riscos e decisões pendentes

- Mudança de leiaute/cobertura coloca a partição em quarentena até revisão do contrato.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/receita-federal/simples-nacional.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/receita-federal/simples-nacional.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`
- [https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico/cnpj-alfa](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico/cnpj-alfa)
- [https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/documentos-tecnicos/cnpj](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/documentos-tecnicos/cnpj)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
