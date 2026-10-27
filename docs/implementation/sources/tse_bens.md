# tse_bens — TSE candidate assets

Cadastrar bens declarados por candidatura e eleição, permitindo evolução patrimonial sem afirmar propriedade verificada.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `tse_bens`.
- Ordem topológica: **35**; onda de execução: **3**; prioridade temática inicial: 3.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [tse](tse.md)
- Contrato de acesso catalogado: [https://dadosabertos.tse.jus.br/dataset/candidatos-2024](https://dadosabertos.tse.jus.br/dataset/candidatos-2024).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/tse_bens.py](../../../etl/src/bracc_etl/pipelines/tse_bens.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_tse_bens_pipeline.py](../../../etl/tests/test_tse_bens_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dadosabertos.tse.jus.br/dataset/candidatos-2024](https://dadosabertos.tse.jus.br/dataset/candidatos-2024) | Entrada atualmente cadastrada para TSE candidate assets. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Baixar bens e cadastro de candidaturas da mesma eleição no TSE; juntar por SQ_CANDIDATO, nunca por nome.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** ZIP/CSV oficial e bens.csv canônico.
- **Partições e backfill:** Eleição, UF e candidatura; preservar extração/retificação do arquivo.
- **Retomada e deduplicação de download:** Checkpoint por eleição, uf e candidatura; preservar extração/retificação do arquivo; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** A cada eleição publicada, com acompanhamento de retificações durante o período eleitoral.

Limites e pré-condições:

- Código atual descarta todos os bens sem CPF de 11 dígitos.
- Valor declarado não comprova titularidade ou valor de mercado.
- Bootstrap só verifica presença em data/tse_bens/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/tse_bens/bens.csv; CSV canônico com cpf, nome_candidato, ano, tipo_bem, descricao_bem, valor_bem, sigla_uf e sigla_partido.

**Chave natural / namespace:** Proposto: eleição + SQ_CANDIDATO + número de ordem do bem; hash atual CPF/ano/tipo/valor/descrição não distingue bens idênticos e muda em retificações.

Normalização:

- Admitir bens sem CPF integral usando a candidatura oficial como âncora.
- Converter valores com separador decimal declarado e manter valor original.
- Distinguir ano eleitoral e data de declaração; não presumir preço de mercado nem proprietário registral.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `DeclaredAsset` | asset_id | existing |
| `Person` | cpf | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person` → `DECLAROU_BEM` → `DeclaredAsset` | CPF completo; proposto também eleição + SQ_CANDIDATO via candidatura | Expressa declaração eleitoral, não confirmação registral. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/tse_bens.py`
- `config/sources/tse_bens.yml`
- `etl/src/bracc_etl/pipelines/tse_bens.py`
- `etl/tests/test_tse_bens_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Implementar aquisição dos ZIPs de bens e candidatos e validar integridade da junção por eleição/SQ_CANDIDATO.
1. Trocar requisito obrigatório de CPF integral para candidatura contextual quando CPF vier mascarado.
1. Criar constraint DeclaredAsset.asset_id e preservar número de ordem do bem.
1. Versionar retificações sem criar compra/venda fictícia por mudança de texto/valor.
1. Expor ligação DECLAROU_BEM e dados originais com proveniência.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Dois bens com mesma descrição e valor mas ordens distintas permanecem separados.
- [ ] Bens de candidato com CPF mascarado são cadastrados pela candidatura.
- [ ] Reprocessar a mesma declaração não aumenta patrimônio total.
- [ ] Retificação mantém histórico e referência ao arquivo oficial.

## Riscos e decisões pendentes

- Código atual descarta todos os bens sem CPF de 11 dígitos.
- Valor declarado não comprova titularidade ou valor de mercado.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/tse_bens.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_tse_bens_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
