# receita_dirbi — Receita DIRBI

Cadastrar benefícios tributários declarados na DIRBI por empresa, programa e período, com versões e retificações.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `receita_dirbi`.
- Ordem topológica: **68**; onda de execução: **4**; prioridade temática inicial: 4.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://dados.gov.br/dados/conjuntos-dados/declaracao-dirbi](https://dados.gov.br/dados/conjuntos-dados/declaracao-dirbi).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Identificador e situação real da fonte; atualizar apenas após implementação e carga comprovadas.
- [etl/src/bracc_etl/base.py](../../../etl/src/bracc_etl/base.py): Contrato Pipeline.extract/transform/load e rastreamento IngestionRun.
- [etl/src/bracc_etl/loader.py](../../../etl/src/bracc_etl/loader.py): Carga por lotes, MERGE e repetição de falhas.
- [scripts/bootstrap_all/adapters/registry.py](../../../scripts/bootstrap_all/adapters/registry.py): Aquisição por script_download ou file_manifest; blocked_external/blocked_credentials explícitos.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato de entradas e preparação a ampliar.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Labels, constraints e índices existentes; incluir migração para labels propostos.
- [etl/src/bracc_etl/pipelines/renuncias.py](../../../etl/src/bracc_etl/pipelines/renuncias.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/beneficios](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/beneficios) | Página oficial de benefícios fiscais com painel DIRBI e acesso a dados abertos. | Página oficial consultada; Fazenda também publica extrato DIRBI 2024 em XLSB; conjunto específico deve ser confirmado. |
| [https://dados.gov.br/dados/conjuntos-dados/declaracao-dirbi](https://dados.gov.br/dados/conjuntos-dados/declaracao-dirbi) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Seguir extrato público de DIRBI e metadados; aceitar XLSB com leitor explícito quando for distribuição oficial; não acessar API de transmissão da declaração do contribuinte.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** CSV/ZIP ou XLSB oficial conforme distribuição localizada
- **Partições e backfill:** Ano/período apuração × programa/tributo × versão/publicação
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- Extrato público pode ser anual e incluir XLSB; não presumir granularidade mensal nem acesso à API de transmissão de declarações.

## Contrato de ingestão

**Entrada esperada:** data/receita_dirbi/raw/<partição>/ com bytes originais e manifest.json; CNPJ, competência/ano, código de benefício, tributo, valor declarado e versão; saída normalizada versionada e rejeições separadas.

**Chave natural / namespace:** dirbi_benefit_id=CNPJ+periodo_apuracao+codigo_beneficio+tributo+tipo_registro

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `TaxBenefitDeclaration` | declaration_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `DECLARED_TAX_BENEFIT` → `TaxBenefitDeclaration` | CNPJ integral | Valor declarado não é comprovação de deferimento nem irregularidade. | proposed |
| `TaxBenefitDeclaration` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_receita_dirbi.py`
- `etl/src/bracc_etl/pipelines/receita_dirbi.py`
- `etl/src/bracc_etl/schemas/receita_dirbi.py`
- `etl/tests/test_receita_dirbi_pipeline.py`
- `docs/source-runbooks/receita_dirbi.md`

Tarefas específicas, em ordem:

1. Identificar extrato da Receita e confrontar com arquivo publicado pela Fazenda; registrar granularidade mensal ou anual real.
1. Mapear códigos e retificações; diferenciar valor declarado, deferido e estimado; evitar duplicação com renuncias.
1. Implementar aquisição com timeout, backoff para 429/5xx, escrita atômica e manifesto por partição (URL final, parâmetros, retrieved_at, ETag/Last-Modified quando presentes, SHA-256, tamanho e cobertura). Guardar segredos apenas no ambiente.
1. Implementar validação e quarentena com motivo por linha; adaptar Pipeline e Neo4jBatchLoader, preservar SourceDocument/IngestionRun e separar tempo do fato, publicação e captura.
1. Adicionar constraints/índices das chaves propostas e atualizar mapeamento de entidades/consultas da API para os novos labels e relações antes de considerá-los navegáveis; preservar distinção entre vínculos exatos e referências pendentes.
1. Registrar no runner, contrato bootstrap e catálogo; criar fixtures pequenas representativas, caso de retomada e dupla carga; liberar carga histórica só após reconciliação do piloto.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Piloto de uma partição com cobertura declarada, contagem de entrada = aceitas + rejeitadas e rejeições justificadas.
- [ ] Duas cargas do mesmo bruto não duplicam nós/arestas; interrupção retomada sem perda; alteração legítima preserva histórico.
- [ ] Arestas nominais exigem documento integral ou ID oficial resolvido; nome ou documento parcial geram apenas pendência de resolução.
- [ ] Retificação de CNPJ/período/benefício muda visão corrente sem dobrar valor; dado anual não é distribuído artificialmente em meses.
- [ ] Total programa/período reproduz extrato público sem acumular observação equivalente da fonte renuncias.

## Riscos e decisões pendentes

- DIRBI é subconjunto específico de renúncias; não somar extratos sobrepostos com renuncias.

## Evidências e referências

- [https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/beneficios](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/beneficios)
- `docs/source_registry_br_v1.csv`
- `etl/src/bracc_etl/pipelines/renuncias.py`
- [https://www.gov.br/fazenda/pt-br/assuntos/politica-fiscal/atuacao-spe/plataforma-de-desoneracoes-tributarias/arquivos/desoneracoes-dirbi-2024.xlsb/view](https://www.gov.br/fazenda/pt-br/assuntos/politica-fiscal/atuacao-spe/plataforma-de-desoneracoes-tributarias/arquivos/desoneracoes-dirbi-2024.xlsb/view)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
