# inep — INEP school census

Cadastrar escolas do Censo Escolar e suas mantenedoras com indicadores anuais e vínculos empresariais.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `inep`.
- Ordem topológica: **96**; onda de execução: **5**; prioridade temática inicial: 5.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/inep.py](../../../etl/src/bracc_etl/pipelines/inep.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_inep_pipeline.py](../../../etl/tests/test_inep_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar) | Entrada atualmente cadastrada para INEP school census. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Descobrir links de cada edição anual do INEP, baixar ZIP e dicionário da mesma edição e adaptar nomes de arquivo.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** ZIP com CSV e dicionários anuais.
- **Partições e backfill:** Ano do censo e escola; tabelas de pessoas não fazem parte deste plano de cadastro institucional.
- **Retomada e deduplicação de download:** Checkpoint por ano do censo e escola; tabelas de pessoas não fazem parte deste plano de cadastro institucional; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Anual por edição/ano de referência, com revisão quando o provedor republicar.

Limites e pré-condições:

- Ano e filename estão fixos em 2022.
- Código atual usa MANTEDORA_DE para CNPJ da própria escola e da mantenedora.
- Bootstrap só verifica presença em data/inep/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Divergência de identidade: runner/registro=inep; Pipeline.source_id=inep_censo_escolar. Reconciliar runs e proveniência preservando alias do provedor.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/inep/microdados_ed_basica_2022.csv; ponto e vírgula, Latin-1; CO_ENTIDADE, CO_MUNICIPIO e NU_CNPJ_ESCOLA_PRIVADA/NU_CNPJ_MANTENEDORA.

**Chave natural / namespace:** Education.school_id = CO_ENTIDADE; indicadores por escola + ano; mantença por CNPJ/escola/intervalo.

Normalização:

- Eliminar ano 2022 fixo no filename e no atributo year.
- Códigos de escola e município como strings; CNPJ com letras e zeros.
- Distinguir mantenedora e CNPJ da escola privada; não atribuir ambos ao mesmo papel MANTEDORA_DE.
- Matrículas e funcionários são indicadores anuais, sem linkar indivíduos.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Education` | school_id | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `MANTEDORA_DE` → `Education` | CNPJ oficial da mantenedora e CO_ENTIDADE | Separar CNPJ da escola de CNPJ mantenedor e preservar ano/vigência. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/inep.py`
- `config/sources/inep.yml`
- `etl/src/bracc_etl/pipelines/inep.py`
- `etl/tests/test_inep_acquisition.py`

Tarefas específicas, em ordem:

1. Implementar inventário anual dos arquivos oficiais e validação por dicionário.
1. Parametrizar ano e arquivo, sem depender de microdados_ed_basica_2022.csv.
1. Reconciliar alias inep_censo_escolar com source_id inep.
1. Adicionar fotografia anual de indicadores e vigência das ligações à mantenedora.
1. Corrigir papéis entre CNPJ da escola e mantenedora e conciliar totais por UF/ano.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Dois anos do censo coexistem sem sobrescrever matrículas.
- [ ] Escola com mantenedora diferente do CNPJ próprio preserva dois papéis corretos.
- [ ] Escola sem CNPJ permanece ligada ao código institucional e município.
- [ ] Reprocessamento de uma edição mantém totais por UF.

## Riscos e decisões pendentes

- Ano e filename estão fixos em 2022.
- Código atual usa MANTEDORA_DE para CNPJ da própria escola e da mantenedora.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/inep.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_inep_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
