# cnpj — Receita Federal CNPJ

Estabelecer a identidade empresarial e o quadro societário, distinguindo empresa, estabelecimento e sócio com documento parcial.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `cnpj`.
- Ordem topológica: **2**; onda de execução: **1**; prioridade temática inicial: 1.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **XL**.
- Registro atual: implementação `implemented`, carga `loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: Sem dependência obrigatória de outra fonte.
- Contrato de acesso catalogado: [https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/](https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/cnpj.py](../../../etl/src/bracc_etl/pipelines/cnpj.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_cnpj_pipeline.py](../../../etl/tests/test_cnpj_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [etl/src/bracc_etl/runner.py](../../../etl/src/bracc_etl/runner.py): Comando de download CNPJ; ainda sem validação robusta de arquivo já existente nem checkpoint por edição completa.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.
- [etl/src/bracc_etl/schemas/cnpj.py](../../../etl/src/bracc_etl/schemas/cnpj.py): Contrato/validação existente a alinhar ao leiaute oficial.
- [api/src/bracc/services/intelligence_provider.py](../../../api/src/bracc/services/intelligence_provider.py): Regex numérica e resolução de CNPJ precisam suportar o formato alfanumérico além da normalização ETL.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/](https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/) | Entrada atualmente cadastrada para Receita Federal CNPJ. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |
| [https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico) | Referência oficial de acesso, formato ou limitação para esta implementação. | Página oficial consultada; confirma identificadores alfanuméricos desde julho de 2026. |

- **Método:** Descobrir a edição publicada no diretório oficial, fixá-la no manifesto, baixar todos os fragmentos Empresas, Estabelecimentos, Socios e tabelas auxiliares; o comando atual baixa apenas três famílias.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** ZIP com CSV posicional Latin-1; preservar layout e dicionários junto do bruto.
- **Partições e backfill:** Edição mensal, família e fragmento; matriz/filiais e histórico em saídas separadas.
- **Retomada e deduplicação de download:** Fixar edição RFB e inventário; baixar .part com Range só se suportado, senão reiniciar arquivo; validar CRC/ZIP, tamanho e SHA-256 antes de rename atômico. skip-existing requer hash válido e extração concluída.
- **Atualização:** Mensal, reavaliando a cadência efetiva do recurso publicado.

Limites e pré-condições:

- Volume nacional exige previsão de disco, RAM e duração; edição parcial não representa todo o país.
- Runner registra cnpj, mas pipeline usa receita_federal; scripts de hook referenciados não existem.
- Validador/formatador atual elimina letras, incompatível com CNPJ alfanumérico.
- Downloader usa skip-existing por existência e converte falha HTTP em aviso; arquivo parcial pode ser reaproveitado e execução incompleta parecer concluída.
- Divergência de identidade: runner/registro=cnpj; Pipeline.source_id=receita_federal. Reconciliar runs e proveniência preservando alias do provedor.

## Contrato de ingestão

**Entrada esperada:** Arquivos RFB sem cabeçalho, separados por ponto e vírgula, Empresas/Socios/Estabelecimentos; tabelas auxiliares em data/cnpj/reference; modos alternativos CSV canônico e histórico já existem.

**Chave natural / namespace:** Company.cnpj canônico de 14 caracteres; raiz RFB separada; Partner.partner_id contextualizado; associação societária com data de entrada e snapshot.

Normalização:

- Substituir strip_document por normalizador de CNPJ que preserve letras A–Z, zeros e dígitos verificadores; CPF permanece numérico.
- Não transformar CPF mascarado em identidade Person: manter Partner com doc_raw/doc_partial e evidência contextual.
- Evitar inventar estabelecimento a partir da raiz; preservar matriz, filial e datas cadastrais.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Company` | cnpj | existing |
| `Person` | cpf | existing |
| `Partner` | partner_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Person` → `SOCIO_DE` → `Company` | CPF completo e CNPJ da empresa | Somente documento íntegro e vínculo explícito no QSA. | existing |
| `Partner` → `SOCIO_DE` → `Company` | partner_id e CNPJ da empresa | Documento parcial identifica apenas a ocorrência de sócio no contexto da fonte. | existing |
| `Company` → `SOCIO_DE` → `Company` | CNPJ do sócio PJ e CNPJ investida | Preservar qualificação, entrada e vigência. | existing |
| `Person\|Partner\|Company` → `SOCIO_DE_SNAPSHOT` → `Company` | membership_id e snapshot_date | Modo histórico mantém fotografia sem sobrescrever vigência anterior. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/cnpj.py`
- `config/sources/cnpj.yml`
- `etl/src/bracc_etl/pipelines/cnpj.py`
- `etl/tests/test_cnpj_acquisition.py`
- `api/src/bracc/services/intelligence_provider.py`

Tarefas específicas, em ordem:

1. Corrigir alias source_id=receita_federal para registro operacional cnpj, preservando identificador do provedor em campo separado.
1. Completar aquisição e validar CRC, tamanho, hashes e todas as famílias da mesma edição antes de publicar.
1. Corrigir busca de referência e extração: diretórios finais devem ser compatíveis com os globs reais, sem ler ZIP como CSV.
1. Ativar carregamento em lotes e snapshots com vigência; confrontar totais de empresas, estabelecimentos e sócios.
1. Substituir hooks ausentes de ligação por implementação rastreável que nunca gere SAME_AS por nome isolado.
1. Adequar validação/resolução de CNPJ na API e interface; o provider atual exige 14 dígitos, inclusive ao resolver entidade por elementId. Validar a cadeia normalização → cadastro → consulta por identificador/ID → padrões.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Um CNPJ com letras chega intacto à mesma identidade usada pelos fornecedores das outras fontes.
- [ ] Reexecutar a edição e trocar a ordem dos fragmentos preserva contagens de nós e associações.
- [ ] Sócio com CPF parcial permanece separado de Person; nenhuma fusão de homônimos.
- [ ] Falha ou ausência de um ZIP obrigatório impede edição marcada completa.
- [ ] Uma fixture de empresa com CNPJ alfanumérico é cadastrada e recuperada pelo endpoint, por identificador e por ID, sem perda de letras ou zeros; CNPJ numérico legado continua acessível.

## Riscos e decisões pendentes

- Volume nacional exige previsão de disco, RAM e duração; edição parcial não representa todo o país.
- Runner registra cnpj, mas pipeline usa receita_federal; scripts de hook referenciados não existem.
- Validador/formatador atual elimina letras, incompatível com CNPJ alfanumérico.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/cnpj.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- [https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico)
- `etl/tests/test_cnpj_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
