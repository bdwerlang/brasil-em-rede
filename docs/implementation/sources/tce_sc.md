# tce_sc — TCE Santa Catarina

Baixar e cadastrar licitações, contratos, aditivos e despesas disponíveis de TCE Santa Catarina, delimitando jurisdição e dados próprios do Tribunal.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `tce_sc`.
- Ordem topológica: **167**; onda de execução: **8**; prioridade temática inicial: 8.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://www.tcesc.tc.br/](https://www.tcesc.tc.br/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Identificador e situação real da fonte; atualizar apenas após implementação e carga comprovadas.
- [etl/src/bracc_etl/base.py](../../../etl/src/bracc_etl/base.py): Contrato Pipeline.extract/transform/load e rastreamento IngestionRun.
- [etl/src/bracc_etl/loader.py](../../../etl/src/bracc_etl/loader.py): Carga por lotes, MERGE e repetição de falhas.
- [scripts/bootstrap_all/adapters/registry.py](../../../scripts/bootstrap_all/adapters/registry.py): Aquisição por script_download ou file_manifest; blocked_external/blocked_credentials explícitos.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato de entradas e preparação a ampliar.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Labels, constraints e índices existentes; incluir migração para labels propostos.
- [etl/src/bracc_etl/pipelines/mides.py](../../../etl/src/bracc_etl/pipelines/mides.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.
- [etl/src/bracc_etl/pipelines/pncp.py](../../../etl/src/bracc_etl/pipelines/pncp.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.
- [etl/src/bracc_etl/transforms/document_formatting.py](../../../etl/src/bracc_etl/transforms/document_formatting.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.tcesc.tc.br/](https://www.tcesc.tc.br/) | Farol público/e-Sfinge como sistema de origem | Farol apresenta licitações/contratos de Estado e municípios; e-Sfinge administrativo é restrito às UGs. |

- **Método:** Extrair recurso público do Farol; documentar a cobertura curta do painel e buscar histórico oficial separado.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** CSV/exportação pública a validar
- **Partições e backfill:** Sistema/escopo × UF SC × ente IBGE/CNPJ × UG × exercício × mês/remessa/recurso
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- Farol público pode ter janela curta; e-Sfinge administrativo é restrito a UGs e não deve ser usado como API pública.

## Contrato de ingestão

**Entrada esperada:** data/tce_sc/raw/<partição>/ com bytes originais e manifest.json; contratos/licitacoes/despesas como tabelas distintas, identificador local, ente, UG, exercício, fornecedor/documento, número do ato, datas, valores e situação; somente temas realmente exportados; saída normalizada versionada e rejeições separadas. Contrato-base possui contract_base_id estável; aditivos referenciam contract_base_id e têm addendum_id próprio, sem criar outro Contract.

**Chave natural / namespace:** contract_id=tce_sc:<sistema>:<ente_CNPJ_ou_IBGE>:<UG>:<exercício_contrato>:<numero_contrato_base>; addendum_id=contract_base_id+<ID_ou_numero_aditivo>+<ano_aditivo>; expenditure_id=tce_sc:<sistema>:<ente>:<UG>:<exercício_empenho>:<numero_empenho>:<estágio>:<documento_evento>; bid_id=tce_sc:<sistema>:<ente>:<UG>:<exercício_processo>:<ID_processo_ou_numero+modalidade>

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.
- Namespace obrigatório: UF=SC, source_id=tce_sc, sistema, escopo próprio/fiscalizado, ente, UG, exercício e número textual de contrato/empenho; CNPJ do ente e fornecedor em campos distintos.
- Valores inicial, atualizado, aditivo, empenhado, liquidado, pago, anulado e RAP separados; não somar snapshots.
- Aditivo não integra Contract.contract_id; valores original/atualizado e eventos de alteração ficam separados do contrato-base.
- Projetar dimensões comuns conforme F09: Territory.territory_id=sistema:tipo:codigo:versao_territorial; EconomicActivity.activity_id=classificacao:versao:codigo; PublicBody.public_body_id=jurisdicao:sistema:identificador:versao. Aplicar somente as dimensões usadas nesta fonte, preservar códigos originais e validar crosswalks; município é Territory, sem dimensão paralela incompatível.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Contract` | contract_id | existing |
| `Bid` | bid_id | existing |
| `StateExpenditure` | expenditure_id | proposed |
| `PublicBody` | public_body_id | proposed |
| `Company` | cnpj | existing |
| `Person` | cpf | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |
| `ContractAddendum` | addendum_id | proposed |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `VENCEU` → `Contract` | CNPJ integral do vencedor/contratado expresso no contrato-base | Projeção compatível com queries atuais; evidência contratual, source_id e data na aresta; aditivos não repetem adjudicação. | existing |
| `PublicBody` → `ISSUED_STATE_CONTRACT` → `Contract` | UF+ente+UG com identificador oficial | UG não é resolvida pelo nome do órgão. | proposed |
| `StateExpenditure` → `EXECUTES_CONTRACT` → `Contract` | referência expressa número/ID+ente+UG+exercício | Se só existe fornecedor/data/valor, manter sem vínculo; empenho, liquidação, pagamento e estorno não são soma de uma mesma despesa. | proposed |
| `Contract` → `DUPLICATE_PUBLICATION_OF` → `Contract` | ID PNCP ou crosswalk oficial+documentos compatíveis | Não fundir TCE, portal estadual e PNCP por número/objeto; preservar observações de fonte separadas. | proposed |
| `Contract` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |
| `Contract` → `REFERENTE_A` → `Bid` | Referência expressa de ID licitação/processo+UF SC+ente+UG+exercício | Aresta existente para navegação contratual; não vincular só por fornecedor/valor/objeto. | existing |
| `ContractAddendum` → `AMENDS_CONTRACT` → `Contract` | contract_base_id oficial ou crosswalk comprovado | Conservar ID do aditivo, data, efeito, valor e vigência; não contar como outro contrato. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_tce_sc.py`
- `etl/src/bracc_etl/pipelines/tce_sc.py`
- `etl/src/bracc_etl/schemas/tce_sc.py`
- `etl/tests/test_tce_sc_pipeline.py`
- `docs/source-runbooks/tce_sc.md`

Tarefas específicas, em ordem:

1. Localizar exportações públicas Farol/dados abertos; medir janela efetiva de histórico; não usar webservices de remessa de e-Sfinge.
1. Criar dimensão de ente/UG e correspondência entre códigos locais e CNPJ/IBGE; medir anos/municípios/UGs presentes, ausentes e pendentes de remessa.
1. Implementar parser específico de Farol público/e-Sfinge como sistema de origem com versões de leiaute e chaves acima; testar homônimo de contrato/empenho em UGs e exercícios distintos.
1. Projetar vínculos exatos em Company-[:VENCEU]->Contract e Contract-[:REFERENTE_A]->Bid para API/padrões atuais; aditivos em ContractAddendum com contract_base_id, e pagamentos/empenhos em observações próprias.
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
- [ ] Piloto de duas UGs e dois exercícios não colide números iguais; total por estágio/ente/período confere com exportação oficial.
- [ ] Matriz de cobertura por ente/UG/ano publicada; não declarar todos os municípios por apenas possuir portal estadual.
- [ ] Cruzamento com sanções usa CNPJ exato e sobreposição entre vigência sancionatória e data do contrato, como sinal verificável.
- [ ] Contrato-base com 3 aditivos produz 1 Contract e 3 ContractAddendum; concentração/recorrência conta o contrato uma vez; VENCEU/REFERENTE_A só com evidência exata.
- [ ] Gate fecha só com recurso oficial, escopo, schema e piloto; indisponibilidade vira blocked_external/blocked_credentials com motivo, sem loaded vazio.

## Riscos e decisões pendentes

- Remessas declaradas por jurisdicionados podem ser incompletas, corrigidas ou tardias; publicação não prova auditoria do Tribunal.
- Método/endpoint de recurso específico permanece condicionado ao piloto quando indicado como descoberta; não usar credenciais de transmissão.

## Evidências e referências

- [https://www.tcesc.tc.br/](https://www.tcesc.tc.br/)
- `docs/source_registry_br_v1.csv`
- `etl/src/bracc_etl/pipelines/mides.py`
- `etl/src/bracc_etl/pipelines/pncp.py`
- `etl/src/bracc_etl/transforms/document_formatting.py`
- [https://www.tcesc.tc.br/farol-tcesc-disponibiliza-informacoes-sobre-licitacoes-em-andamento-cotacao-de-precos-e-situacao-de](https://www.tcesc.tc.br/farol-tcesc-disponibiliza-informacoes-sobre-licitacoes-em-andamento-cotacao-de-precos-e-situacao-de)
- [https://www.tcesc.tc.br/modulo-de-atos-juridicos-do-e-sfinge-e-tema-de-evento-line-do-tcesc](https://www.tcesc.tc.br/modulo-de-atos-juridicos-do-e-sfinge-e-tema-de-evento-line-do-tcesc)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
