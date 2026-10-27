# holdings — Brasil IO holdings

Enriquecer participações entre pessoas jurídicas com Brasil.IO, preservando snapshot e origem derivada do QSA.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `holdings`.
- Ordem topológica: **62**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://brasil.io/dataset/socios-brasil/holdings/](https://brasil.io/dataset/socios-brasil/holdings/).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/holdings.py](../../../etl/src/bracc_etl/pipelines/holdings.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_holdings_pipeline.py](../../../etl/tests/test_holdings_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://brasil.io/dataset/socios-brasil/holdings/](https://brasil.io/dataset/socios-brasil/holdings/) | Entrada atualmente cadastrada para Brasil IO holdings. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir exportação publicada pelo mantenedor Brasil.IO e baixar arquivo completo, registrando origem primária e data de atualização.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** CSV.gz do dataset de sócios/holdings; entrada interna holding.csv.gz.
- **Partições e backfill:** Versão do dataset e par de CNPJs; manter snapshot de origem RFB se informado.
- **Retomada e deduplicação de download:** Checkpoint por versão do dataset e par de cnpjs; manter snapshot de origem rfb se informado; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Fonte secundária pode ter defasagem em relação à Receita.
- HOLDING_DE pode sugerir controle que dados de sócios não provam.
- Bootstrap só verifica presença em data/holdings/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Divergência de identidade: runner/registro=holdings; Pipeline.source_id=brasil_io_holdings. Reconciliar runs e proveniência preservando alias do provedor.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/holdings/holding.csv.gz ou holding.csv; parser aceita cnpj_empresa/cnpj e cnpj_socia/holding_cnpj.

**Chave natural / namespace:** CNPJ controladora/sócia + CNPJ investida + snapshot/origem; não tratar relação societária como controle majoritário sem participação comprovada.

Normalização:

- CNPJs de sócia e investida com normalização alfanumérica comum.
- Preservar direção da participação e tipo societário; nome holding não demonstra controle.
- Não duplicar valor ou vínculo já obtido do QSA; conservar múltiplas evidências da mesma relação.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `HOLDING_DE` → `Company` | CNPJ sócia/controladora e CNPJ investida declarados no dataset | Guardar origem, data e papel; não inferir controle majoritário. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/holdings.py`
- `config/sources/holdings.yml`
- `etl/src/bracc_etl/pipelines/holdings.py`
- `etl/tests/test_holdings_acquisition.py`

Tarefas específicas, em ordem:

1. Validar URL do dataset e licença de uso com o mantenedor, sem assumir atualização mensal.
1. Implementar download completo com hash e campo de revisão.
1. Confirmar direção semântica de cnpj_empresa e cnpj_socia por amostra documentada.
1. Reconciliar alias brasil_io_holdings com holdings e manter origem derivada.
1. Consolidar evidência com SOCIO_DE sem afirmar percentual/controle inexistente.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Direção sócia → investida coincide com amostra da fonte.
- [ ] CNPJ já carregado não cria Company paralela.
- [ ] Reprocessamento mantém um vínculo e atualiza sua evidência.
- [ ] Snapshot sem data original não é declarado atualizado.

## Riscos e decisões pendentes

- Fonte secundária pode ter defasagem em relação à Receita.
- HOLDING_DE pode sugerir controle que dados de sócios não provam.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/holdings.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_holdings_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
