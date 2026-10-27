# opensanctions — OpenSanctions global PEP

Cadastrar registros PEP internacionais do OpenSanctions com datasets de origem e correspondências documentais.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `opensanctions`.
- Ordem topológica: **118**; onda de execução: **6**; prioridade temática inicial: 6.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://www.opensanctions.org/datasets/peps/](https://www.opensanctions.org/datasets/peps/).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/opensanctions.py](../../../etl/src/bracc_etl/pipelines/opensanctions.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_opensanctions_pipeline.py](../../../etl/tests/test_opensanctions_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.opensanctions.org/datasets/peps/](https://www.opensanctions.org/datasets/peps/) | Entrada atualmente cadastrada para OpenSanctions global PEP. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir artefato de download do dataset PEP no mantenedor, validar versão/licença/acesso e baixar stream completo com manifesto.
- **Autenticação:** Confirmar artefato, licença e eventual credencial/condição de acesso do mantenedor; tokens fora de dados e logs.
- **Formato bruto:** JSONL FollowTheMoney; não converter listas de propriedades em uma única informação sem guardar o bruto.
- **Partições e backfill:** Dataset, revisão e entity.id; propriedades multivalor e fonte de origem preservadas.
- **Retomada e deduplicação de download:** Checkpoint por dataset, revisão e entity.id; propriedades multivalor e fonte de origem preservadas; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Disponibilidade/licença de artefatos para uso pretendido precisa validação.
- Parser escolhe primeiro país/data e pode perder contexto temporal.
- GLOBAL_PEP_MATCH usa MATCH, logo ordem de carga pode deixar registros sem relação.
- Bootstrap só verifica presença em data/opensanctions/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/opensanctions/entities.ftm.json; JSON Lines FollowTheMoney com id, schema e properties; parser usa nome, países, posições e documentos.

**Chave natural / namespace:** GlobalPEP.pep_id = os_<id oficial>; posições e mandatos precisam de registros temporais próprios quando múltiplos.

Normalização:

- CPF extraído precisa ser documento brasileiro completo válido e formatado de modo comum.
- Conservar todos os países, nacionalidades, cargos e períodos, sem selecionar somente o primeiro como verdade única.
- PEP não equivale a sancionado; manter tipo e fonte do registro.
- Pessoa sem documento fica registro global independente, sem match nominal automático.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `GlobalPEP` | pep_id | existing |
| `Person` | cpf | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person` → `GLOBAL_PEP_MATCH` → `GlobalPEP` | CPF brasileiro integral validado e ID do registro FTM | Guardar método, confiança e origem documental; sem SAME_AS nominal. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/opensanctions.py`
- `config/sources/opensanctions.yml`
- `etl/src/bracc_etl/pipelines/opensanctions.py`
- `etl/tests/test_opensanctions_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Validar termos/licença e método de acesso do artefato antes de download recorrente.
1. Implementar stream com checksum e proteção contra JSONL truncado.
1. Revisar taxNumber/cpf com país/emissor para evitar usar documento estrangeiro como CPF.
1. Criar constraint GlobalPEP.pep_id e preservar várias posições/períodos.
1. Implementar religação idempotente após chegada de Person, sem hook automático hoje inexistente.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Número de entidades parseadas concilia com linhas válidas do artefato.
- [ ] CPF parcial/estrangeiro não gera GLOBAL_PEP_MATCH.
- [ ] Cargos múltiplos e seus períodos permanecem acessíveis.
- [ ] Carga anterior ao TSE não perde associação: religação posterior a resolve com prova forte.

## Riscos e decisões pendentes

- Disponibilidade/licença de artefatos para uso pretendido precisa validação.
- Parser escolhe primeiro país/data e pode perder contexto temporal.
- GLOBAL_PEP_MATCH usa MATCH, logo ordem de carga pode deixar registros sem relação.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/opensanctions.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_opensanctions_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
