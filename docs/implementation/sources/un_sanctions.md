# un_sanctions — UN sanctions

Cadastrar a lista consolidada do Conselho de Segurança da ONU preservando registros, aliases e regimes.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `un_sanctions`.
- Ordem topológica: **121**; onda de execução: **6**; prioridade temática inicial: 6.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://scsanctions.un.org/resources/xml/en/consolidated.xml](https://scsanctions.un.org/resources/xml/en/consolidated.xml).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/un_sanctions.py](../../../etl/src/bracc_etl/pipelines/un_sanctions.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_un_sanctions_pipeline.py](../../../etl/tests/test_un_sanctions_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://scsanctions.un.org/resources/xml/en/consolidated.xml](https://scsanctions.un.org/resources/xml/en/consolidated.xml) | Entrada atualmente cadastrada para UN sanctions. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Baixar XML consolidado oficial e converter registros individuais/entidades para o JSON canônico com referências ao XML bruto.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** XML oficial; JSON canônico derivado para parser existente.
- **Partições e backfill:** Snapshot, regime e DATAID; nomes e aliases como filhos do mesmo registro.
- **Retomada e deduplicação de download:** Checkpoint por snapshot, regime e dataid; nomes e aliases como filhos do mesmo registro; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Verificar alteração diariamente e publicar versão quando a lista mudar; cadência mensal do registro não garante atualização sancionadora.

Limites e pré-condições:

- Não há adaptador XML→JSON apesar de primary_url apontar XML.
- Código atual cria sanção internacional nominal sobre homônimos.
- Bootstrap só verifica presença em data/un_sanctions/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/un_sanctions/un_sanctions.json como lista de objetos name, reference_number, listed_date, un_list_type, nationality, entity_type e aliases; URL do registro é XML, exigindo conversão.

**Chave natural / namespace:** ID oficial DATAID/reference_number em namespace ONU; hash atual referência+nome deve deixar de variar quando nome muda.

Normalização:

- Converter todos os blocos de nomes, aliases, nacionalidades e documentos sem perda de multivalores.
- Preservar identificador oficial mesmo após alteração de grafia.
- Não gerar UN_SANCTIONED por nome; requer documento ou evidência composta validada.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `InternationalSanction` | sanction_id | existing |
| `Person` | cpf | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person\|Company` → `UN_SANCTIONED` → `InternationalSanction` | Proposto: documento/ID forte com jurisdição; atual nome | Desativar associação por nome isolado e manter candidato auditável. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/un_sanctions.py`
- `config/sources/un_sanctions.yml`
- `etl/src/bracc_etl/pipelines/un_sanctions.py`
- `etl/tests/test_un_sanctions_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Implementar downloader XML e transformador XML→JSON com contagem de entidades/indivíduos.
1. Trocar sanction_id derivado de nome por ID oficial e criar constraint compartilhada.
1. Remover MATCH por nome em UN_SANCTIONED e implementar correspondência documentada separada.
1. Guardar lista/regime, datas e documentos com país/emissor.
1. Revisar exclusões e republicações com histórico de situação.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Contagens do JSON derivado coincidem com indivíduos/entidades no XML.
- [ ] Mudança de nome conserva sanction_id.
- [ ] Homônimo brasileiro não é ligado automaticamente.
- [ ] XML malformado ou lista parcial falha explicitamente.

## Riscos e decisões pendentes

- Não há adaptador XML→JSON apesar de primary_url apontar XML.
- Código atual cria sanção internacional nominal sobre homônimos.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/un_sanctions.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_un_sanctions_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
