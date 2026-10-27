# ibama — IBAMA embargos

Cadastrar embargos ambientais e seus responsáveis com local, área, processo e situação.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `ibama`.
- Ordem topológica: **91**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://servicos.ibama.gov.br/ctf/publico/areasembargadas/](https://servicos.ibama.gov.br/ctf/publico/areasembargadas/).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/ibama.py](../../../etl/src/bracc_etl/pipelines/ibama.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_ibama_pipeline.py](../../../etl/tests/test_ibama_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://servicos.ibama.gov.br/ctf/publico/areasembargadas/](https://servicos.ibama.gov.br/ctf/publico/areasembargadas/) | Entrada atualmente cadastrada para IBAMA embargos. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir exportação oficial de áreas embargadas e seu dicionário; baixar snapshot completo, geometria separada se volumosa.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** CSV oficial e geometria WKT/arquivo geográfico quando disponível.
- **Partições e backfill:** Snapshot, UF e termo de embargo; versões de desembargo/retificação.
- **Retomada e deduplicação de download:** Checkpoint por snapshot, uf e termo de embargo; versões de desembargo/retificação; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Geometria é descartada pelo parser atual; exportar vínculo geográfico exige extensão explícita.
- Consulta e dataset de infrações não garantem o mesmo universo do arquivo de áreas embargadas.
- Bootstrap só verifica presença em data/ibama/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/ibama/areas_embargadas.csv; ponto e vírgula, UTF-8; parser ignora WKT_GEOM_AREA_EMBARGADA e descarta linhas ruins.

**Chave natural / namespace:** Embargo.embargo_id por identificador oficial do termo/embargo; preservar auto de infração e processo como referências distintas.

Normalização:

- CPF parcial conserva responsável contextual e não vira Person.
- Distinguir auto de infração, embargo e processo administrativo; não são um único fato.
- Área, coordenadas, município e bioma com unidade e referência territorial explícitas.
- CNPJ alfanumérico e zeros preservados.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Embargo` | embargo_id | existing |
| `Company` | cnpj | existing |
| `Person` | cpf | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company\|Person` → `EMBARGADA` → `Embargo` | Documento completo do responsável e ID do termo | Não vincular por nome nem atribuir responsabilidade a empresa apenas pela área. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/ibama.py`
- `config/sources/ibama.yml`
- `etl/src/bracc_etl/pipelines/ibama.py`
- `etl/tests/test_ibama_acquisition.py`

Tarefas específicas, em ordem:

1. Criar aquisição do dump oficial em lugar da página de consulta e validar leiaute.
1. Trocar on_bad_lines=skip por rejeições contabilizadas e retidas em quarentena.
1. Incluir situação de desembargo, vigência e versão; não apagar embargo histórico.
1. Preservar referência geográfica do bruto e implantar ligação a município por código oficial, sem geocodificar nomes como certeza.
1. Conectar responsável apenas com documento completo e rastrear ocorrências sem identidade.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Embargo desembargado mantém o ato e situação atual.
- [ ] Toda linha rejeitada tem contagem e motivo.
- [ ] Responsável mascarado não gera Person por seis dígitos.
- [ ] Um auto ligado a múltiplos embargos não colapsa os termos.

## Riscos e decisões pendentes

- Geometria é descartada pelo parser atual; exportar vínculo geográfico exige extensão explícita.
- Consulta e dataset de infrações não garantem o mesmo universo do arquivo de áreas embargadas.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/ibama.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_ibama_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
