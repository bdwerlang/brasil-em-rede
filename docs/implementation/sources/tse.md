# tse — TSE elections and donations

Cadastrar candidaturas, eleições e receitas eleitorais com identidade por eleição e prestação de contas, conectando doador e candidato por transação documentada.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `tse`.
- Ordem topológica: **33**; onda de execução: **3**; prioridade temática inicial: 3.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **XL**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dadosabertos.tse.jus.br/](https://dadosabertos.tse.jus.br/).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/tse.py](../../../etl/src/bracc_etl/pipelines/tse.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_tse_pipeline.py](../../../etl/tests/test_tse_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.
- [etl/src/bracc_etl/schemas/tse.py](../../../etl/src/bracc_etl/schemas/tse.py): Contrato/validação existente a alinhar ao leiaute oficial.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dadosabertos.tse.jus.br/](https://dadosabertos.tse.jus.br/) | Entrada atualmente cadastrada para TSE elections and donations. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir no catálogo TSE arquivos de candidaturas e prestações de contas por eleição, baixar ZIPs e dicionários e gerar os dois contratos internos.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** ZIP/CSV oficial TSE, normalmente ponto e vírgula e encoding declarado no layout; saída canônica adaptada.
- **Partições e backfill:** Eleição, UF, cargo, turno e tipo de prestação; anos com layouts próprios.
- **Retomada e deduplicação de download:** Checkpoint por eleição, uf, cargo, turno e tipo de prestação; anos com layouts próprios; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** A cada eleição publicada, com acompanhamento de retificações durante o período eleitoral.

Limites e pré-condições:

- Modelo atual Person.sq_candidato é singular e pode perder candidaturas históricas.
- CNPJ alfanumérico deve ser suportado mesmo que só apareça em novas receitas.
- Doação e participação eleitoral são fatos declarados, não prova de irregularidade.
- Bootstrap só verifica presença em data/tse/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Divergência de identidade: runner/registro=tse; Pipeline.source_id=tribunal_superior_eleitoral. Reconciliar runs e proveniência preservando alias do provedor.

## Contrato de ingestão

**Entrada esperada:** data/tse/candidatos.csv e doacoes.csv; arquivos internos com cabeçalho canônico e vírgula, Latin-1; bruto oficial exige adaptação.

**Chave natural / namespace:** Candidatura = eleição + SQ_CANDIDATO; eleição por ano/turno/cargo/UF/município; doação = identificador oficial da receita e prestação de contas.

Normalização:

- Sentinela -4 ou CPF mascarado não vira identidade de Person; preservar SQ_CANDIDATO com ano.
- Separar candidatura e pessoa para não sobrescrever uma eleição com outra.
- CPF/CNPJ do doador só é usado integral e válido; preservar doador originário e intermediário quando o layout distinguir.
- Receitas retificadas, estimáveis e financeiras precisam de tipo e estado próprios.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Person` | cpf/sq_candidato | existing |
| `Company` | cnpj | existing |
| `Election` | year,cargo,uf,municipio | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person` → `CANDIDATO_EM` → `Election` | SQ_CANDIDATO + eleição e documento integral quando disponível | Separar pessoa de candidatura e preservar turno. | existing |
| `Company\|Person` → `DOOU` → `Person` | Documento do doador + SQ_CANDIDATO da prestação + ID da receita | Grão transacional idempotente; não fundir por nome. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/tse.py`
- `config/sources/tse.yml`
- `etl/src/bracc_etl/pipelines/tse.py`
- `etl/tests/test_tse_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Implementar descoberta por eleição e adaptar layouts/versionar dicionários, sem forçar todos os anos a um único cabeçalho.
1. Reconciliar alias tribunal_superior_eleitoral com source_id tse nos runs.
1. Criar entidade de candidatura para múltiplos SQ_CANDIDATO da mesma pessoa e migrar sobrescrita atual de p.sq_candidato.
1. Criar ID único por receita; MERGE atual por doador/candidato/ano com SET valor sobrescreve várias receitas e deve ser substituído por fatos transacionais idempotentes.
1. Completar constraints para eleição/candidatura/receita e ligar doadores por documento forte.
1. Substituir hook nominal ausente por reconciliação auditável de identidades.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Uma pessoa com candidaturas em duas eleições mantém as duas participações.
- [ ] CPF -4/ausente não gera Person inválida.
- [ ] Reexecutar receitas não muda os totais nem duplica transações.
- [ ] Retificação de prestação produz versão rastreável e concilia com totais oficiais.

## Riscos e decisões pendentes

- Modelo atual Person.sq_candidato é singular e pode perder candidaturas históricas.
- CNPJ alfanumérico deve ser suportado mesmo que só apareça em novas receitas.
- Doação e participação eleitoral são fatos declarados, não prova de irregularidade.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.
- DOOU atual usa MERGE por doador/candidato/ano e SET r.valor por linha: várias receitas do mesmo par/ano podem ser sobrescritas, restando só a última.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/tse.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_tse_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
