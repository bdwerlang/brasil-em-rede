# senado_cpis — Senado CPIs

Cobrir CPIs do Senado e comissões mistas com membros, requerimentos, sessões e fontes históricas rastreáveis.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `senado_cpis`.
- Ordem topológica: **31**; onda de execução: **3**; prioridade temática inicial: 3.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **XL**.
- Registro atual: implementação `implemented`, carga `partial`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [senado](senado.md)
- Contrato de acesso catalogado: [https://www12.senado.leg.br/dados-abertos](https://www12.senado.leg.br/dados-abertos).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/senado_cpis.py](../../../etl/src/bracc_etl/pipelines/senado_cpis.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_senado_cpis_pipeline.py](../../../etl/tests/test_senado_cpis_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www12.senado.leg.br/dados-abertos](https://www12.senado.leg.br/dados-abertos) | Entrada atualmente cadastrada para Senado CPIs. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Consultar serviços oficiais de comissões, reuniões, requerimentos e parlamentares; complementar histórico por páginas e documentos oficiais explicitamente catalogados.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** JSON/XML oficial, PDF/HTML e seis CSVs canônicos.
- **Partições e backfill:** Legislatura, comissão, sessão, requerimento e documento; arquivos históricos em partições com origem identificada.
- **Retomada e deduplicação de download:** Checkpoint por legislatura, comissão, sessão, requerimento e documento; arquivos históricos em partições com origem identificada; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Por nova edição e revisão da fonte, com verificação anual.

Limites e pré-condições:

- Histórico de sessões/requerimentos é incompleto e não pode ser inferido de nomes de CPIs.
- Existem três vínculos por nome isolado e o hook adicional também falta.
- Bootstrap só verifica presença em data/senado_cpis/*; não baixa, não valida schema, não verifica completude e não comprova carga.

## Contrato de ingestão

**Entrada esperada:** data/senado_cpis/inquiries.csv ou legado cpis.csv; requirements.csv, sessions.csv, members.csv e history_sources.csv; UTF-8.

**Chave natural / namespace:** Casa/comissão + ID oficial; requerimento e sessão por código oficial; SourceDocument.doc_id por URL e checksum; TemporalViolation por evento/regra.

Normalização:

- Preservar Casa, período de funcionamento e participação de membro com vigência.
- Substituir associação por nome por código de senador/deputado e mandato.
- CNPJ no texto gera MENCIONADA_EM com prova, não participação em CPI.
- Manter eventos fora da vigência em quarentena TemporalViolation, nunca descartados sem registro.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Inquiry` | inquiry_id | existing |
| `CPI` | cpi_id | existing |
| `InquiryRequirement` | requirement_id | existing |
| `InquirySession` | session_id | existing |
| `SourceDocument` | doc_id | existing |
| `TemporalViolation` | violation_id | existing |
| `Person` | cpf | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `CPI` → `EH_INQUIRY` → `Inquiry` | IDs de ponte declarados pelo pipeline | Evitar duplicidade lógica do mesmo inquérito. | existing |
| `Person` → `PARTICIPA_INQUIRY` → `Inquiry` | Proposto: código parlamentar e mandato | Remover match nominal existente. | existing |
| `Inquiry` → `TEM_REQUERIMENTO` → `InquiryRequirement` | ID comissão + requerimento | Validar regra temporal e guardar evento/documento. | existing |
| `Inquiry` → `REALIZOU_SESSAO` → `InquirySession` | ID comissão + sessão | Validar vigência da comissão. | existing |
| `Person` → `PROPOS_REQUERIMENTO` → `InquiryRequirement` | Código parlamentar/CPF comprovado | Sem autoria automática por nome. | existing |
| `Company` → `MENCIONADA_EM` → `InquiryRequirement` | CNPJ íntegro no texto | Trecho, referência e confiança documentados. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/senado_cpis.py`
- `config/sources/senado_cpis.yml`
- `etl/src/bracc_etl/pipelines/senado_cpis.py`
- `etl/tests/test_senado_cpis_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Implementar aquisição dos seis contratos e detectar arquivos historicamente não publicados.
1. Corrigir relações PARTICIPA_INQUIRY, PARTICIPOU_CPI e autoria que hoje fazem MATCH por nome.
1. Manter compatibilidade CPI/EH_INQUIRY enquanto consolida Inquiry com IDs oficiais.
1. Integrar SourceDocument com checksum e data de coleta aos eventos e menções.
1. Testar limites temporais e republicações de sessão/requerimento com intervalos de comissão.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Membro homônimo não entra em comissão sem código oficial.
- [ ] Cada evento fora da vigência cria diagnóstico verificável sem vínculo indevido.
- [ ] Documentos históricos carregados têm URL e hash.
- [ ] Reexecução não duplica ponte CPI/EH_INQUIRY nem requerimentos.

## Riscos e decisões pendentes

- Histórico de sessões/requerimentos é incompleto e não pode ser inferido de nomes de CPIs.
- Existem três vínculos por nome isolado e o hook adicional também falta.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/senado_cpis.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_senado_cpis_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
