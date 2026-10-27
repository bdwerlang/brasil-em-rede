# siop — SIOP emendas

Cadastrar programação e execução de emendas SIOP e vincular autoria sem confundir dotações com pagamentos.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `siop`.
- Ordem topológica: **22**; onda de execução: **2**; prioridade temática inicial: 2.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `partial`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://www.siop.planejamento.gov.br/](https://www.siop.planejamento.gov.br/).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/siop.py](../../../etl/src/bracc_etl/pipelines/siop.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_siop_pipeline.py](../../../etl/tests/test_siop_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.siop.planejamento.gov.br/](https://www.siop.planejamento.gov.br/) | Entrada atualmente cadastrada para SIOP emendas. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir recurso oficial de dados abertos SIOP, validar mecanismo de extração e emitir CSV compatível, sem supor que a página inicial é endpoint de API.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** A confirmar no recurso oficial: exportação CSV/API/SPARQL; saída interna CSV canônico.
- **Partições e backfill:** Exercício, código de emenda e unidade orçamentária; programação e execução separadas.
- **Retomada e deduplicação de download:** Checkpoint por exercício, código de emenda e unidade orçamentária; programação e execução separadas; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Anual por edição/ano de referência, com revisão quando o provedor republicar.

Limites e pré-condições:

- Fonte ainda tem ligação de autor limitada; página principal não confirma download automatizável.
- Mesmo rótulo de Amendment é usado com chaves diferentes por múltiplos pipelines.
- Bootstrap só verifica presença em data/siop/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/siop/*.csv com ponto e vírgula e Latin-1; aliases de campos já implementados, mas aquisição remota inexistente.

**Chave natural / namespace:** Código de emenda + exercício + detalhe orçamentário quando houver múltiplas dotações; substituir siop_<código> isolado se o código não for global.

Normalização:

- Manter função, subfunção, ação, plano orçamentário e estágio da despesa.
- Distinguir autor individual, bancada, comissão e relatoria; não fabricar CPF para autoria coletiva.
- Separar dotação, empenho, liquidação e pagamento, sem converter ausente em zero.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Amendment` | amendment_id | existing |
| `Person` | cpf | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person` → `AUTOR_EMENDA` → `Amendment` | CPF completo válido do autor e código/exercício da emenda | Autoria coletiva ou sem identificador fica em dimensão proposta de autor. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/siop.py`
- `config/sources/siop.yml`
- `etl/src/bracc_etl/pipelines/siop.py`
- `etl/tests/test_siop_acquisition.py`

Tarefas específicas, em ordem:

1. Validar dataset e endpoint oficial antes de automatizar download.
1. Documentar transformação da extração SIOP ao CSV esperado, incluindo tipo e exercício da emenda.
1. Ampliar chave Amendment para granularidade real e construir crosswalk exato com Portal/Tesouro.
1. Criar dimensão de autor com ID parlamentar/contextual e vincular a Person só quando houver prova forte.
1. Executar conciliação por exercício e estágio, registrando diferenças de atualização.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Emenda coletiva é cadastrada sem CPF inventado.
- [ ] Código repetido em exercícios diferentes não colide.
- [ ] Valores de empenho/liquidação/pagamento são reconciliados separadamente.
- [ ] Autor sem identificador completo aparece como pendência, sem ligação por nome.

## Riscos e decisões pendentes

- Fonte ainda tem ligação de autor limitada; página principal não confirma download automatizável.
- Mesmo rótulo de Amendment é usado com chaves diferentes por múltiplos pipelines.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/siop.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_siop_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
