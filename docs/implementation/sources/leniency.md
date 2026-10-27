# leniency — Acordos de leniencia

Cadastrar acordos de leniência e empresas signatárias com número, situação e condições publicadas.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `leniency`.
- Ordem topológica: **8**; onda de execução: **1**; prioridade temática inicial: 1.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://portaldatransparencia.gov.br/download-de-dados/acordos-leniencia](https://portaldatransparencia.gov.br/download-de-dados/acordos-leniencia).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/leniency.py](../../../etl/src/bracc_etl/pipelines/leniency.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_leniency_pipeline.py](../../../etl/tests/test_leniency_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://portaldatransparencia.gov.br/download-de-dados/acordos-leniencia](https://portaldatransparencia.gov.br/download-de-dados/acordos-leniencia) | Entrada atualmente cadastrada para Acordos de leniencia. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Baixar exportação de acordos do Portal da Transparência e documentos oficiais vinculados, separando acordo, signatário e obrigação.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** CSV/ZIP da CGU e PDF/HTML dos acordos quando públicos.
- **Partições e backfill:** Acordo, empresa e data do snapshot; aditivos e cumprimento como versões/eventos.
- **Retomada e deduplicação de download:** Checkpoint por acordo, empresa e data do snapshot; aditivos e cumprimento como versões/eventos; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Schema não tem constraint de LeniencyAgreement.
- Assinatura de acordo e situação de cumprimento são fatos distintos.
- Bootstrap só verifica presença em data/leniency/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Divergência de identidade: runner/registro=leniency; Pipeline.source_id=cgu_leniencia. Reconciliar runs e proveniência preservando alias do provedor.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/leniency/leniencia.csv; Latin-1 e vírgula no parser; conteúdo oficial exige mapeamento de cabeçalho.

**Chave natural / namespace:** Identificador oficial do acordo e empresa signatária; chave atual leniencia_<CNPJ> colapsa múltiplos acordos da mesma empresa e deve ser migrada.

Normalização:

- Separar valor global do acordo, valores por empresa, parcelas e obrigações não financeiras.
- CNPJ da signatária usa normalizador alfanumérico; grupo econômico não implica que todas as empresas assinaram.
- Preservar situação, data de assinatura, aditivo e vigência.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `LeniencyAgreement` | leniency_id | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `FIRMOU_LENIENCIA` → `LeniencyAgreement` | CNPJ integral da signatária e ID oficial do acordo | Grupo econômico e outras empresas exigem prova própria. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/leniency.py`
- `config/sources/leniency.yml`
- `etl/src/bracc_etl/pipelines/leniency.py`
- `etl/tests/test_leniency_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Descobrir recurso oficial, campos e identificadores de acordo e signatários.
1. Rever leniency_id e adicionar constraint LeniencyAgreement para distinguir vários acordos da mesma empresa.
1. Reconciliar alias cgu_leniencia com source_id leniency.
1. Cadastrar múltiplas signatárias sem replicar o valor global como dívida individual de cada uma.
1. Ligar documentos e registrar aditivos/alterações sem apagar versões anteriores.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Acordo com três signatárias mantém um acordo e três vínculos documentados.
- [ ] Total global não é multiplicado pelo número de empresas.
- [ ] Nova ordenação do CSV preserva os IDs.
- [ ] CNPJ da signatária converge com cadastro nacional.

## Riscos e decisões pendentes

- Schema não tem constraint de LeniencyAgreement.
- Assinatura de acordo e situação de cumprimento são fatos distintos.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/leniency.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_leniency_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
