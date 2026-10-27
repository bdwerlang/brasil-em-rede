# inep_higher_education — Censo da Educação Superior

Implementar aquisição, cadastro e ligações verificáveis de Censo da Educação Superior.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `inep_higher_education`.
- Ordem topológica: **98**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **M**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [ibge_geosciences](ibge_geosciences.md)
- Contrato de acesso catalogado: [https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.
- [etl/src/bracc_etl/pipelines/inep.py](../../../etl/src/bracc_etl/pipelines/inep.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/educacao/censo-educacao-superior.md |

- **Método:** Descobrir arquivos/endpoint na publicação oficial; baixar com timeout, backoff e limite de concorrência. Guardar bruto imutável, URL efetiva, hash SHA-256, bytes e instante de coleta.
- **Autenticação:** Não requerida Indicação importada, a confirmar no contrato oficial.
- **Formato bruto:** CSV
- **Partições e backfill:** Recurso, versão e período; dividir adicionalmente por UF quando suportado.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** annual no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Página de descoberta não é endpoint de dados; disponibilidade de URL não comprova completude.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: código IES, código curso, código município, categoria administrativa, organização acadêmica, vagas, ingressos, matrículas, concluintes. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Separar cadastros IES/cursos e agregados anuais; CO_IES não usa Education.school_id escolar. Mantenedora liga por CNPJ público, sem aluno/docente individual.

**Chave natural / namespace:** CO_IES; curso: CO_IES + CO_CURSO; observação: ano + IES/curso + métrica/dimensões

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
| `HigherEducationInstitution` | CO_IES; curso: CO_IES + CO_CURSO; observação: ano + IES/curso + métrica/dimensões | proposed |
| `HigherEducationCourse` | CO_IES + CO_CURSO | proposed |
| `EducationObservation` | tabela + ano + IES/curso + métrica/dimensões | proposed |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `HigherEducationCourse` → `OFERTADO_POR` → `HigherEducationInstitution` | CO_IES + ano/vigência | Namespace IES distinto da escola básica. | proposed |
| `Company` → `MANTEM_IES` → `HigherEducationInstitution` | CNPJ de mantenedora efetivamente publicado | Sem nome aproximado; CNPJ como string alfanumérica. | proposed |
| `EducationObservation` → `REFERE_SE_A` → `HigherEducationCourse` | CO_IES + CO_CURSO + ano | Observação agregada de curso, sem aluno identificado; se recurso é por IES, relação deve apontar IES e guardar grão. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_inep_higher_education.py`
- `etl/src/bracc_etl/pipelines/inep_higher_education.py`
- `etl/tests/test_inep_higher_education.py`
- `docs/sources/inep_higher_education.md`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Separar cadastros IES/cursos e agregados anuais; CO_IES não usa Education.school_id escolar. Mantenedora liga por CNPJ público, sem aluno/docente individual.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Criar migração para entidades/arestas propostas e registro no runner; piloto registra SourceDocument/IngestionRun e compara contagens/totais oficiais antes do histórico.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto por período/UF tem manifesto e contagens de lidos/aceitos/rejeitados; interrupção retoma sem duplicação.
- [ ] Reexecução da mesma versão conserva cardinalidades; revisão oficial preserva histórico.
- [ ] Ligações de amostra têm identificador exato e evidência; casos ambíguos permanecem pendentes, sem união por nome.
- [ ] IES com dois cursos preserva identidades e dois anos de fatos; total de matrículas reproduz sinopse oficial sob mesmo filtro.

## Riscos e decisões pendentes

- Mudança de leiaute/cobertura coloca a partição em quarentena até revisão do contrato.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/educacao/censo-educacao-superior.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/educacao/censo-educacao-superior.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
