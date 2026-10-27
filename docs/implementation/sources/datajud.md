# datajud — CNJ DataJud

Cadastrar metadados e movimentos processuais públicos do DataJud; identidade das partes fica fora do escopo do canal público.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `datajud`.
- Ordem topológica: **113**; onda de execução: **6**; prioridade temática inicial: 6.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://api-publica.datajud.cnj.jus.br/](https://api-publica.datajud.cnj.jus.br/).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/datajud.py](../../../etl/src/bracc_etl/pipelines/datajud.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_datajud_pipeline.py](../../../etl/tests/test_datajud_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://api-publica.datajud.cnj.jus.br/](https://api-publica.datajud.cnj.jus.br/) | Entrada atualmente cadastrada para CNJ DataJud. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |
| [https://www.cnj.jus.br/api-publica/](https://www.cnj.jus.br/api-publica/) | Referência oficial de acesso, formato ou limitação para esta implementação. | Página oficial consultada; descreve metadados públicos e proteção das informações de partes. |
| [https://datajud-wiki.cnj.jus.br/api-publica/acesso/](https://datajud-wiki.cnj.jus.br/api-publica/acesso/) | Referência oficial de acesso, formato ou limitação para esta implementação. | Wiki oficial conferida pela coordenação; chave pública vigente do DPJ/CNJ é rotacionável e não foi copiada. |

- **Método:** Consultar API pública por alias de tribunal com chave pública vigente disponibilizada pelo CNJ; paginar conforme documentação e salvar consultas e respostas, sem obter dados protegidos de partes.
- **Autenticação:** Chave pública vigente DPJ/CNJ no cabeçalho Authorization conforme wiki oficial; chave rotacionável em variável de ambiente, sem copiá-la para plano, logs ou manifestos. Canal público não fornece identidade das partes.
- **Formato bruto:** JSON de metadados/movimentos; cases.csv canônico. parties.csv apenas se futuramente existir fonte independente e legitimamente autorizada.
- **Partições e backfill:** Tribunal, grau e janela de atualização; cursor de paginação estável documentado pela API.
- **Retomada e deduplicação de download:** Checkpoint por tribunal, grau e janela de atualização; cursor de paginação estável documentado pela api; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Catálogo atual blocked_external pode refletir operação antiga; validar acesso antes de manter bloqueio.
- Vínculos PARTE_PROCESSO implementados dependem de dados de partes indisponíveis no canal público.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/datajud/cases.csv e parties.csv opcionais; dry_run_manifest.json é só diagnóstico e não comprova carga; cases usa número, tribunal, classe e datas.

**Chave natural / namespace:** JudicialCase.judicial_case_id por tribunal + número CNJ + grau/unidade quando necessário; movimento por ID/código/data e complemento oficial.

Normalização:

- Número CNJ como string, preservando todos os dígitos e tribunal/órgão.
- Classes, assuntos e movimentos usam tabelas processuais oficiais e códigos.
- Não esperar CPF/CNPJ ou lista identificada de partes na API pública.
- Distinguir data de ajuizamento, atualização e movimentação; baixa não é decisão de mérito.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `JudicialCase` | judicial_case_id | existing |
| `Person` | cpf | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company\|Person` → `PARTE_PROCESSO` → `JudicialCase` | Somente documento completo oriundo de fonte autorizada separada | Não executar nem prometer este vínculo com metadados da API pública DataJud. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/datajud.py`
- `config/sources/datajud.yml`
- `etl/src/bracc_etl/pipelines/datajud.py`
- `etl/tests/test_datajud_acquisition.py`

Tarefas específicas, em ordem:

1. Remover bloqueio genérico de credenciais do contrato após testar chave pública vigente, sem gravá-la no plano ou logs.
1. Implementar aquisição por tribunal/janela e paginação oficial com retentativas e checkpoint.
1. Transformar capas e movimentos públicos em registros com IDs estáveis.
1. Separar ingestão opcional de parties.csv em fluxo independente com proveniência e autorização, sem prometer partes vindas do DataJud público.
1. Substituir status loaded de dry-run/arquivo vazio por diagnóstico específico e métricas de cobertura.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Canal público funciona sem inventar dados de partes.
- [ ] Chave pública é configurada sem aparecer no log/manifesto.
- [ ] Reinício de paginação não perde nem duplica processos.
- [ ] Dry-run ou ausência de cases nunca é contabilizado como carga concluída.

## Riscos e decisões pendentes

- Catálogo atual blocked_external pode refletir operação antiga; validar acesso antes de manter bloqueio.
- Vínculos PARTE_PROCESSO implementados dependem de dados de partes indisponíveis no canal público.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/datajud.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- [https://www.cnj.jus.br/api-publica/](https://www.cnj.jus.br/api-publica/)
- [https://datajud-wiki.cnj.jus.br/api-publica/acesso/](https://datajud-wiki.cnj.jus.br/api-publica/acesso/)
- `etl/tests/test_datajud_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
