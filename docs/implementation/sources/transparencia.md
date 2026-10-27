# transparencia — Portal da Transparencia contracts

Baixar e cadastrar contratos federais, vínculos/remuneração de servidores e emendas sem colapsar suas granularidades.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `transparencia`.
- Ordem topológica: **25**; onda de execução: **2**; prioridade temática inicial: 2.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://portaldatransparencia.gov.br/download-de-dados](https://portaldatransparencia.gov.br/download-de-dados).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/transparencia.py](../../../etl/src/bracc_etl/pipelines/transparencia.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_transparencia_pipeline.py](../../../etl/tests/test_transparencia_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.
- [etl/src/bracc_etl/schemas/transparencia.py](../../../etl/src/bracc_etl/schemas/transparencia.py): Contrato/validação existente a alinhar ao leiaute oficial.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://portaldatransparencia.gov.br/download-de-dados](https://portaldatransparencia.gov.br/download-de-dados) | Entrada atualmente cadastrada para Portal da Transparencia contracts. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Criar aquisição por dataset no Portal da Transparência e adaptar explicitamente contratos, cadastro/remuneração e emendas ao contrato interno.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** ZIP/CSV oficial; gerar arquivos internos UTF-8 e manifestos por dataset.
- **Partições e backfill:** Dataset e competência mensal/exercício; estados de sucesso e cobertura independentes.
- **Retomada e deduplicação de download:** Checkpoint por dataset e competência mensal/exercício; estados de sucesso e cobertura independentes; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Chaves atuais de contrato e emenda podem colidir; PublicOffice sobrescreve salário sem competência.
- Um CSV ausente hoje permite execução parcial sem indicar claramente o dataset faltante.
- Bootstrap só verifica presença em data/transparencia/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Divergência de identidade: runner/registro=transparencia; Pipeline.source_id=portal_transparencia. Reconciliar runs e proveniência preservando alias do provedor.

## Contrato de ingestão

**Entrada esperada:** data/transparencia/contratos.csv, servidores.csv e emendas.csv; CSV UTF-8 canônico, incompatível diretamente com diversos ZIPs oficiais.

**Chave natural / namespace:** Contrato por ID oficial do Portal; remuneração por servidor oficial + vínculo + competência; emenda por exercício + código oficial, substituindo CNPJ/data e nome/objeto.

Normalização:

- Preservar matrícula/ID de servidor, vínculo, competência e rubricas; CPF mascarado não é identidade.
- Manter CNPJ do fornecedor e do órgão como campos distintos, com normalização alfanumérica.
- Unificar referência de emenda com SIOP/Transferegov apenas por exercício e código comprovados.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Contract` | contract_id | existing |
| `Company` | cnpj | existing |
| `PublicOffice` | office_id | existing |
| `Person` | servidor_id/author_key | existing |
| `Amendment` | amendment_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `VENCEU` → `Contract` | CNPJ fornecedor e ID oficial contrato | Não confundir fornecedor com órgão contratante. | existing |
| `Person` → `RECEBEU_SALARIO` → `PublicOffice` | Identificador oficial do servidor e vínculo | Competência deve acompanhar cada remuneração. | existing |
| `Person` → `AUTOR_EMENDA` → `Amendment` | Código oficial do autor e código/exercício da emenda | Identidade parlamentar contextual, sem SAME_AS por nome. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/transparencia.py`
- `config/sources/transparencia.yml`
- `etl/src/bracc_etl/pipelines/transparencia.py`
- `etl/tests/test_transparencia_acquisition.py`

Tarefas específicas, em ordem:

1. Documentar mapeamento de cada ZIP oficial e substituir os CSVs canônicos sintéticos por transformação reproduzível.
1. Trocar IDs fracos de contratos e emendas por identificadores oficiais e migrar vínculos.
1. Modelar remuneração mensal como evento/snapshot para não sobrescrever todos os salários num PublicOffice.
1. Corrigir alias portal_transparencia e hook de Person ausente; guardar source_id do registro nos runs.
1. Criar cargas independentes e coligações determinísticas por fornecedor, servidor e emenda.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Dois contratos do mesmo CNPJ iniciados na mesma data permanecem distintos.
- [ ] Salários de duas competências coexistem e valores não somam duplicado em reprocessamento.
- [ ] CPF mascarado nunca é promovido a CPF completo nem fundido por nome.
- [ ] Uma emenda compartilhada com outro conector tem crosswalk documentado, sem dupla contagem.

## Riscos e decisões pendentes

- Chaves atuais de contrato e emenda podem colidir; PublicOffice sobrescreve salário sem competência.
- Um CSV ausente hoje permite execução parcial sem indicar claramente o dataset faltante.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/transparencia.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_transparencia_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
