# sanctions — CEIS CNEP sanctions

Cadastrar separadamente sanções CEIS e CNEP e ligar o sancionado ao ato administrativo com vigência e origem.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `sanctions`.
- Ordem topológica: **10**; onda de execução: **1**; prioridade temática inicial: 1.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://portaldatransparencia.gov.br/sancoes/consulta](https://portaldatransparencia.gov.br/sancoes/consulta).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/sanctions.py](../../../etl/src/bracc_etl/pipelines/sanctions.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_sanctions_pipeline.py](../../../etl/tests/test_sanctions_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://portaldatransparencia.gov.br/sancoes/consulta](https://portaldatransparencia.gov.br/sancoes/consulta) | Entrada atualmente cadastrada para CEIS CNEP sanctions. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |
| [https://portaldatransparencia.gov.br/download-de-dados](https://portaldatransparencia.gov.br/download-de-dados) | Catálogo oficial para descoberta dos arquivos CEIS e CNEP. | Endereço oficial de referência; arquivos finais e acesso ainda não verificados. |

- **Método:** Resolver os arquivos CEIS e CNEP no catálogo de download da CGU, baixar snapshots completos e adaptar o CSV oficial ao contrato interno.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** ZIP/CSV oficial e CSV canônico Latin-1.
- **Partições e backfill:** Lista e data de publicação; histórico de snapshots e atos de inclusão/retificação.
- **Retomada e deduplicação de download:** Checkpoint por lista e data de publicação; histórico de snapshots e atos de inclusão/retificação; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Exigência atual de ambos CSV pode ocultar disponibilidade parcial; registrar cobertura por lista.
- sanction_id atual usa posição da linha e o pipeline aceita dados ausentes sem erro.
- Bootstrap só verifica presença em data/sanctions/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Divergência de identidade: runner/registro=sanctions; Pipeline.source_id=ceis_cnep. Reconciliar runs e proveniência preservando alias do provedor.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/sanctions/ceis.csv e cnep.csv; parser atual espera CSV Latin-1 com cabeçalho canônico, delimitador vírgula.

**Chave natural / namespace:** Proposto: lista CEIS/CNEP + identificador oficial da sanção; na ausência, hash de processo, órgão, documento, tipo e início, nunca índice da linha.

Normalização:

- Preservar identificador oficial, processo sancionador, órgão, abrangência, início/fim e situação.
- CPF mascarado gera registro de parte sem identidade Person; CNPJ usa normalizador alfanumérico comum.
- Não converter sanção expirada ou suspensa em impedimento vigente.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Sanction` | sanction_id | existing |
| `Company` | cnpj | existing |
| `Person` | cpf | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company\|Person` → `SANCIONADA` → `Sanction` | CNPJ/CPF completo normalizado | Documento parcial não participa do vínculo determinístico. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/sanctions.py`
- `config/sources/sanctions.yml`
- `etl/src/bracc_etl/pipelines/sanctions.py`
- `etl/tests/test_sanctions_acquisition.py`

Tarefas específicas, em ordem:

1. Criar aquisição das duas listas com manifestos independentes e união somente após validar cada recurso.
1. Trocar sanction_id que incorpora idx por ID oficial ou composição estável, migrando associações existentes.
1. Reconciliar alias ceis_cnep no IngestionRun com source_id sanctions do registro.
1. Produzir atualização temporal de sanção sem apagar a prova de versões anteriores.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Ordenar o CSV de outra forma não cria novas Sanction.
- [ ] CNPJ presente no QSA e em CEIS resolve para a mesma Company.
- [ ] Sanção sem documento completo fica cadastrada e pendente de resolução, sem associação inventada.
- [ ] Totais por lista e vigência conferem com o manifesto.

## Riscos e decisões pendentes

- Exigência atual de ambos CSV pode ocultar disponibilidade parcial; registrar cobertura por lista.
- sanction_id atual usa posição da linha e o pipeline aceita dados ausentes sem erro.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/sanctions.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_sanctions_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
