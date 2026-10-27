# datasus — DATASUS CNES

Cadastrar estabelecimentos CNES e as pessoas jurídicas responsáveis por competência, conectando serviços de saúde a empresas.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `datasus`.
- Ordem topológica: **84**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://opendatasus.saude.gov.br/](https://opendatasus.saude.gov.br/).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/datasus.py](../../../etl/src/bracc_etl/pipelines/datasus.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_datasus_pipeline.py](../../../etl/tests/test_datasus_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://opendatasus.saude.gov.br/](https://opendatasus.saude.gov.br/) | Entrada atualmente cadastrada para DATASUS CNES. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir recurso oficial CNES e formato disponível; baixar por competência/UF e converter para cnes_all.csv, sem assumir que a página OpenDataSUS entrega o contrato já pronto.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** API/CSV/DBC/DBF oficial conforme recurso efetivo; saída CSV UTF-8 canônica.
- **Partições e backfill:** Competência, UF e estabelecimento; tabelas de serviços/profissionais somente após contrato próprio.
- **Retomada e deduplicação de download:** Checkpoint por competência, uf e estabelecimento; tabelas de serviços/profissionais somente após contrato próprio; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Downloader referenciado não existe e o formato de entrada já é uma transformação não documentada.
- Parser atual Health sobrescreve indicadores de competências diferentes.
- Contrato chama script de download ausente; implementar ou substituir o caminho antes da execução.
- Divergência de identidade: runner/registro=datasus; Pipeline.source_id=cnes. Reconciliar runs e proveniência preservando alias do provedor.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/datasus/cnes_all.csv; campos codigo_cnes, numero_cnpj/numero_cnpj_entidade, nome_razao_social/fantasia, codigo_municipio e demais campos CNES usados.

**Chave natural / namespace:** Health.cnes_code para identidade do estabelecimento; fotografia por CNES + competência; operação/mantença com vigência.

Normalização:

- Código CNES é string com zeros; não é CNPJ.
- Distinguir CNPJ do estabelecimento e da entidade mantenedora conforme dicionário.
- Tratar código de município DATASUS/IBGE com crosswalk oficial, sem usar nome como chave.
- Estabelecimento em competência não implica operação contínua fora do período.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Health` | cnes_code | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `OPERA_UNIDADE` → `Health` | CNPJ completo no papel definido pelo layout CNES | Preservar competência e distinguir estabelecimento de mantenedora. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/datasus.py`
- `config/sources/datasus.yml`
- `etl/src/bracc_etl/pipelines/datasus.py`
- `etl/tests/test_datasus_acquisition.py`

Tarefas específicas, em ordem:

1. Substituir chamada bootstrap a scripts/download_datasus.py inexistente por aquisição implementada e testada.
1. Confirmar recurso CNES e mapeamento de campos ao cnes_all.csv.
1. Reconciliar alias source_id=cnes com registro datasus.
1. Adicionar histórico de competências e papel temporal OPERA_UNIDADE, separando entidade mantenedora quando aplicável.
1. Conciliar número de estabelecimentos por UF/competência e registrar unidades sem CNPJ.
1. Corrigir atende_sus: o código atual deriva apenas atendimento ambulatorial e converte ausente em negativo. Preservar categorias de atendimento ambulatorial/hospitalar e estado desconhecido por competência; distinguir operador, mantenedor e estabelecimento.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Mesmo CNES em duas competências mantém identidade e duas fotografias.
- [ ] CNPJ do estabelecimento e da mantenedora não são trocados.
- [ ] Unidade sem CNPJ continua cadastrada e ligada ao município quando código permitir.
- [ ] CNPJ alfanumérico converge com Company do cadastro.
- [ ] Fixture com campo ambulatorial ausente e atendimento hospitalar SUS explícito não recebe atende_sus=false; desconhecido continua desconhecido e mantenedor não vira operador automaticamente.

## Riscos e decisões pendentes

- Downloader referenciado não existe e o formato de entrada já é uma transformação não documentada.
- Parser atual Health sobrescreve indicadores de competências diferentes.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/datasus.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_datasus_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
