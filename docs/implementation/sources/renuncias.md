# renuncias — Renuncias fiscais

Cadastrar benefícios tributários individualizados com ano, tributo, modalidade e valor informado pela Receita.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `renuncias`.
- Ordem topológica: **69**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **M**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/renuncias.py](../../../etl/src/bracc_etl/pipelines/renuncias.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_renuncias_pipeline.py](../../../etl/tests/test_renuncias_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos) | Entrada atualmente cadastrada para Renuncias fiscais. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir recursos de renúncias individualizadas na Receita; baixar dados com valores e tabelas de habilitação em fluxos diferenciados.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** CSV/ZIP de renúncias e cadastros correlatos, com dicionários por recurso.
- **Partições e backfill:** Ano-calendário, tributo, modalidade/benefício e versão de publicação.
- **Retomada e deduplicação de download:** Checkpoint por ano-calendário, tributo, modalidade/benefício e versão de publicação; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Anual por edição/ano de referência, com revisão quando o provedor republicar.

Limites e pré-condições:

- Heurística atual de nomes pode deixar arquivos válidos de fora ou incluir tabela errada.
- TaxWaiver não tem constraint no schema.
- Bootstrap só verifica presença em data/renuncias/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/renuncias/*.csv; somente arquivos cujo nome contém Ren/ren, excetuando PorBen; Latin-1, ponto e vírgula.

**Chave natural / namespace:** Beneficiário + ano-calendário + tributo + benefício + tipo de demonstrativo; ID oficial preferível; namespace evita colisão com outras fontes.

Normalização:

- Valor de renúncia não equivale a repasse ou pagamento; preserve natureza tributária.
- Distinguir habilitação de benefício efetivamente valorado.
- Moeda BRL com parser robusto e CNPJ alfanumérico normalizado.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `TaxWaiver` | waiver_id | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `RECEBEU_RENUNCIA` → `TaxWaiver` | CNPJ + grão ano/tributo/benefício | Natureza é benefício tributário, sem inferir pagamento público. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/renuncias.py`
- `config/sources/renuncias.yml`
- `etl/src/bracc_etl/pipelines/renuncias.py`
- `etl/tests/test_renuncias_acquisition.py`
- `api/src/bracc/queries/schema_init.cypher`

Tarefas específicas, em ordem:

1. Substituir seleção por substring do filename por manifesto explícito de recursos e esquemas.
1. Mapear dado oficial para campos TaxWaiver e testar diferentes nomes/cabeçalhos.
1. Criar constraint TaxWaiver.waiver_id e estabilidade por grão tributário.
1. Registrar habilitados/imunes em modelo específico sem inventar montantes.
1. Conciliar somas por tributo, benefício e ano, sem combinar totais agregados com individuais.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Arquivo de habilitados não gera valor financeiro fictício.
- [ ] Benefícios de dois tributos no mesmo ano permanecem separados.
- [ ] Reprocessar arquivos não duplica benefício.
- [ ] Totais individuais não são somados novamente com agregado PorBen.

## Riscos e decisões pendentes

- Heurística atual de nomes pode deixar arquivos válidos de fora ou incluir tabela errada.
- TaxWaiver não tem constraint no schema.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/renuncias.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_renuncias_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
