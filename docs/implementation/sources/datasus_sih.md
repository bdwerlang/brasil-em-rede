# datasus_sih — SIH — Sistema de Informações Hospitalares

Implementar aquisição, cadastro e ligações verificáveis de SIH — Sistema de Informações Hospitalares.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `datasus_sih`.
- Ordem topológica: **85**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [ibge_geosciences](ibge_geosciences.md), [datasus](datasus.md)
- Contrato de acesso catalogado: [ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/](ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.
- [etl/src/bracc_etl/pipelines/datasus.py](../../../etl/src/bracc_etl/pipelines/datasus.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/](ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/saude-datasus/sih.md |
| [https://datasus.saude.gov.br/transferencia-de-arquivos2/](https://datasus.saude.gov.br/transferencia-de-arquivos2/) | Descoberta oficial de arquivos e definições; preferir equivalente HTTPS oficial validado ao FTP legado. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |
| [https://datasus.saude.gov.br/servicos/](https://datasus.saude.gov.br/servicos/) | Portais oficiais e suporte dos serviços; confirmar recurso e dicionário específicos antes da carga. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |

- **Método:** Listar arquivos oficiais por sistema/UF/período; baixar DBC e definições, validar compressão e converter DBF→Parquet em streaming. Registrar versão de conversor/dicionário. Grafo recebe somente agregados aprovados.
- **Autenticação:** Não requerida Indicação importada, a confirmar no contrato oficial.
- **Formato bruto:** DBC, DBF, CSV
- **Partições e backfill:** UF + ano/mês + arquivo RD e demais produtos em contratos separados.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** monthly no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- FTP legado pode falhar: validar HTTPS oficial equivalente; erro de acesso não é partição vazia.
- Dicionários e versões preliminares/finais variam por sistema/ano; IDs anonimizados não são identidade de pessoa.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: AIH, CNES, CID-10, codigo_municipio, procedimento_SUS, valor_internacao. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Converter DBC/DBF RD por UF/competência e dicionário; AIH pode ter prorrogação/reapresentação, não conta pessoa. Separar residência/atendimento, evento e processamento.

**Chave natural / namespace:** SIH + tabela/métrica + nível/geografia ou CNES + competência + dimensões + revisão

Normalização:

- Preservar códigos como strings e valores originais; vazio/ignorado não equivale a zero.
- Datas de evento, referência e coleta são campos distintos; manter histórico de revisão.
- Identificador completo válido permite ligação; nome isolado ou documento parcial não resolve identidade. CNPJ alfanumérico mantém letras, zeros e dígitos verificadores.
- Série/tabela, métrica, nível/código/tipo de geografia e período são obrigatórios nos agregados; residência/ocorrência/atendimento são dimensões distintas. Não criar Person/Company de microdado anônimo; controlar células pequenas no produto público.
- Projetar dimensões comuns conforme F09: Territory.territory_id=sistema:tipo:codigo:versao_territorial; EconomicActivity.activity_id=classificacao:versao:codigo; PublicBody.public_body_id=jurisdicao:sistema:identificador:versao. Aplicar somente as dimensões usadas nesta fonte, preservar códigos originais e validar crosswalks; município é Territory, sem dimensão paralela incompatível.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `HealthStatistic` | SIH + tabela/métrica + nível/geografia ou CNES + competência + dimensões + revisão | proposed |
| `Territory` | territory_id | proposed |
| `Health` | cnes_code | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `HealthStatistic` → `REFERE_SE_A` → `Territory` | nível/código territorial publicado, namespace e versão; crosswalk oficial quando necessário | Guardar tabela/série, geografia e período; não desagregar UF/Brasil para município e nunca criar Person/Company de agregado. | proposed |
| `HealthStatistic` → `PRODUCAO_DO_ESTABELECIMENTO` → `Health` | CNES público e competência compatível com cadastro datasus/CNES | Não liga paciente ou infere operador: operador fica no pipeline cadastral CNES. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_datasus_sih.py`
- `etl/src/bracc_etl/pipelines/datasus_sih.py`
- `etl/tests/test_datasus_sih.py`
- `docs/sources/datasus_sih.md`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Converter DBC/DBF RD por UF/competência e dicionário; AIH pode ter prorrogação/reapresentação, não conta pessoa. Separar residência/atendimento, evento e processamento.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Criar migração para entidades/arestas propostas e registro no runner; piloto registra SourceDocument/IngestionRun e compara contagens/totais oficiais antes do histórico.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto por período/UF tem manifesto e contagens de lidos/aceitos/rejeitados; interrupção retoma sem duplicação.
- [ ] Reexecução da mesma versão conserva cardinalidades; revisão oficial preserva histórico.
- [ ] Ligações de amostra têm identificador exato e evidência; casos ambíguos permanecem pendentes, sem união por nome.
- [ ] Agregado reproduz TabNet sob mesmos filtros; AIH revisada não duplica internação e CNES liga apenas quando publicado.

## Riscos e decisões pendentes

- Mudança de leiaute/cobertura coloca a partição em quarentena até revisão do contrato.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/saude-datasus/sih.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/saude-datasus/sih.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`
- [https://datasus.saude.gov.br/transferencia-de-arquivos2/](https://datasus.saude.gov.br/transferencia-de-arquivos2/)
- [https://datasus.saude.gov.br/servicos/](https://datasus.saude.gov.br/servicos/)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
