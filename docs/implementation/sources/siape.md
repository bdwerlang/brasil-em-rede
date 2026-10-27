# siape — SIAPE — Dados de Servidores Públicos Federais

Implementar aquisição, cadastro e ligações verificáveis de SIAPE — Dados de Servidores Públicos Federais.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `siape`.
- Ordem topológica: **154**; onda de execução: **8**; prioridade temática inicial: 8.
- Tipo de trabalho: **Acesso condicionado / restrito**; complexidade relativa: **M**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [siorg](siorg.md)
- Contrato de acesso catalogado: [https://www.gov.br/conecta/catalogo/](https://www.gov.br/conecta/catalogo/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Entrada da fonte e estados separados de implementação/carga.
- [docs/catalogs/brazil_visible.json](../../../docs/catalogs/brazil_visible.json): Referência importada; campos precisam ser confirmados no dicionário oficial.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Esquema atual; entidades/arestas adicionais desta ficha são propostas.
- [etl/src/bracc_etl/pipelines/transparencia.py](../../../etl/src/bracc_etl/pipelines/transparencia.py): Artefato existente a reutilizar/comparar; não comprova cobertura desta nova fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.gov.br/conecta/catalogo/](https://www.gov.br/conecta/catalogo/) | Descoberta importada; resolver URL efetiva de cada recurso e dicionário. | https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/apis-governamentais/siape.md |
| [https://www.gov.br/servidor/pt-br/acesso-a-informacao/faq/duvidas-frequentes-de-acesso/orgao-integracao-via-webservices-siape](https://www.gov.br/servidor/pt-br/acesso-a-informacao/faq/duvidas-frequentes-de-acesso/orgao-integracao-via-webservices-siape) | API voltada a sistemas autorizados; catálogo Conecta não implica acesso público. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |
| [https://www.gov.br/conecta/catalogo/apis/consulta-siape](https://www.gov.br/conecta/catalogo/apis/consulta-siape) | Contrato/manual e solicitação de integração autorizada. | Fonte primária oficial consultada em 26/10/2026; recurso concreto/dicionário deve ser fixado no piloto. |

- **Método:** Sem varredura de CPF ou reutilização de sessão; definir importador institucional condicionado a acesso, usando transparencia para camada pública já disponível.
- **Autenticação:** Sistemas/órgãos autorizados via Conecta/SIAPE; protocolo e credenciais dependem do contrato.
- **Formato bruto:** JSON
- **Partições e backfill:** Recurso, versão e período; dividir adicionalmente por UF quando suportado.
- **Retomada e deduplicação de download:** Checkpoint por partição/recurso; concluir arquivo .part após validar tamanho/hash; nova versão preserva anterior.
- **Atualização:** monthly no catálogo; confirmar calendário real e períodos sujeitos a revisão.

Limites e pré-condições:

- Catálogo Conecta não é base pública; CPF e remuneração podem não ser liberados ou ter restrições de uso.

## Contrato de ingestão

**Entrada esperada:** Confirmar dicionário e disponibilidade real dos campos importados: cpf, matricula, nome, orgao_lotacao, cargo, remuneracao. Identificadores, grão, período e revisão devem ser fixados antes da carga. Grão/escopo obrigatório: Documentar integração SIAPE de sistemas autorizados; comparar camada pública transparencia e projetar ambiente segregado, sem varredura de CPF.

**Chave natural / namespace:** órgão + matrícula/vínculo + competência + versão

Normalização:

- Preservar códigos como strings e valores originais; vazio/ignorado não equivale a zero.
- Datas de evento, referência e coleta são campos distintos; manter histórico de revisão.
- Identificador completo válido permite ligação; nome isolado ou documento parcial não resolve identidade. CNPJ alfanumérico mantém letras, zeros e dígitos verificadores.
- Projetar dimensões comuns conforme F09: Territory.territory_id=sistema:tipo:codigo:versao_territorial; EconomicActivity.activity_id=classificacao:versao:codigo; PublicBody.public_body_id=jurisdicao:sistema:identificador:versao. Aplicar somente as dimensões usadas nesta fonte, preservar códigos originais e validar crosswalks; município é Territory, sem dimensão paralela incompatível.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `EmploymentSnapshot` | órgão + matrícula/vínculo + competência + versão | proposed |
| `PublicBody` | public_body_id | proposed |
| `Person` | cpf | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `EmploymentSnapshot` → `LOTADO_EM` → `PublicBody` | SIORG/crosswalk oficial e vigência | Ambiente autorizado; matrícula é por vínculo/órgão, não identificador global. | proposed |
| `Person` → `POSSUI_VINCULO` → `EmploymentSnapshot` | CPF integral autorizado e validado | Sem reconstrução de CPF mascarado; não publicar dado restrito. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `docs/sources/siape.md`
- `docs/source-contracts/siape.json`

Tarefas específicas, em ordem:

1. Fixar recurso real, dicionário, licença, granularidade e cobertura temporal em contrato versionado.
1. Documentar integração SIAPE de sistemas autorizados; comparar camada pública transparencia e projetar ambiente segregado, sem varredura de CPF. Acesso não será solicitado nem executado nesta etapa de plano.
1. Implementar downloader retomável e transformação específica com validação de chaves, campos e rejeições justificadas.
1. Registrar contrato, gate e estado bloqueado/somente catálogo sem marcar dados como carregados; nenhuma implementação de acesso não autorizado.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Fixture sintética ou inventário de metadados validado, sem extração bulk de fonte restrita.
- [ ] Sem recurso/contrato/autorização, execução de carga fica desabilitada e status não simula implementação/cobertura.
- [ ] Cada metadado/gate de acesso tem evidência e campo de pendência; fonte sem recurso aberto não gera dados nem duplica outro ID do catálogo.
- [ ] Duas matrículas do mesmo CPF não colidem; CPF mascarado não cria Person resolvida e gate bloqueia sem autorização.

## Riscos e decisões pendentes

- Catálogo Conecta não é base pública; CPF e remuneração podem não ser liberados ou ter restrições de uso.

## Evidências e referências

- [https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/apis-governamentais/siape.md](https://github.com/nferdica/brazil-visible/blob/cad147d28695d2faaa01fa0667ae53b7fef5e776/docs/apis/apis-governamentais/siape.md)
- `docs/catalogs/brazil_visible.json`
- `api/src/bracc/queries/schema_init.cypher`
- [https://www.gov.br/servidor/pt-br/acesso-a-informacao/faq/duvidas-frequentes-de-acesso/orgao-integracao-via-webservices-siape](https://www.gov.br/servidor/pt-br/acesso-a-informacao/faq/duvidas-frequentes-de-acesso/orgao-integracao-via-webservices-siape)
- [https://www.gov.br/conecta/catalogo/apis/consulta-siape](https://www.gov.br/conecta/catalogo/apis/consulta-siape)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
