# state_portal_rs — Rio Grande do Sul transparency portal

Baixar e cadastrar execução financeira, contratos e aditivos do governo de Rio Grande do Sul, mantendo delimitação por Poder, órgão, UG e exercício.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `state_portal_rs`.
- Ordem topológica: **132**; onda de execução: **7**; prioridade temática inicial: 7.
- Tipo de trabalho: **Implementar conector e pipeline**; complexidade relativa: **L**.
- Registro atual: implementação `not_implemented`, carga `not_loaded`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://www.transparencia.rs.gov.br/](https://www.transparencia.rs.gov.br/).

## Artefatos existentes auditados

- [docs/source_registry_br_v1.csv](../../../docs/source_registry_br_v1.csv): Identificador e situação real da fonte; atualizar apenas após implementação e carga comprovadas.
- [etl/src/bracc_etl/base.py](../../../etl/src/bracc_etl/base.py): Contrato Pipeline.extract/transform/load e rastreamento IngestionRun.
- [etl/src/bracc_etl/loader.py](../../../etl/src/bracc_etl/loader.py): Carga por lotes, MERGE e repetição de falhas.
- [scripts/bootstrap_all/adapters/registry.py](../../../scripts/bootstrap_all/adapters/registry.py): Aquisição por script_download ou file_manifest; blocked_external/blocked_credentials explícitos.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato de entradas e preparação a ampliar.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Labels, constraints e índices existentes; incluir migração para labels propostos.
- [etl/src/bracc_etl/pipelines/transparencia.py](../../../etl/src/bracc_etl/pipelines/transparencia.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.
- [etl/src/bracc_etl/pipelines/mides.py](../../../etl/src/bracc_etl/pipelines/mides.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.
- [etl/src/bracc_etl/pipelines/comprasnet.py](../../../etl/src/bracc_etl/pipelines/comprasnet.py): Reuso de parser, modelagem ou vinculação existente; adaptar sem presumir cobertura desta fonte.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://www.transparencia.rs.gov.br/dados-abertos/](https://www.transparencia.rs.gov.br/dados-abertos/) | FPE/Transparência RS | FAQ oficial indica arquivos mensais/anuais de despesas e contratos de obras, serviços, bens, locações e PPPs. |
| [https://www.transparencia.rs.gov.br/](https://www.transparencia.rs.gov.br/) | URL legada do catálogo; resolver redirecionamento e registrar a nova origem, sem assumir que seja API funcional. | docs/source_registry_br_v1.csv; não validada como endpoint de extração. |

- **Método:** Descobrir recursos por meio do catálogo/exportação oficial; preferir arquivo completo para histórico e API pública documentada para incremento. Não assumir que o portal web seja API.
- **Autenticação:** Público; confirmar no recurso final antes de programar. Não reutilizar credenciais de remessa administrativa.
- **Formato bruto:** CSV/XLSX conforme recurso público
- **Partições e backfill:** UF RS × Poder/ente × UG/unidade orçamentária × exercício × competência × tema/recurso
- **Retomada e deduplicação de download:** Checkpoint por partição e página/recurso; partições só concluídas após checksum, validação e reconciliação; reexecução reusa bruto íntegro e refaz partição alterada.
- **Atualização:** Cadência inicial monthly; aferir data de referência e atualização no produtor, sem confundir captura com atualização.

Limites e pré-condições:

- Arquivos mensais e anuais podem se sobrepor; FPE e LicitaCon são distribuições com escopo distinto.

## Contrato de ingestão

**Entrada esperada:** data/state_portal_rs/raw/<partição>/ com bytes originais e manifest.json; tabelas distintas de contrato/aditivo, empenho, liquidação, pagamento e estorno; ente/UG, exercício, documento, fornecedor, valor e datas presentes e tipados; saída normalizada versionada e rejeições separadas. Contrato-base possui contract_base_id estável; aditivos referenciam contract_base_id e têm addendum_id próprio, sem criar outro Contract.

**Chave natural / namespace:** contract_id=state_portal_rs:<sistema>:<ente_CNPJ_ou_IBGE>:<UG>:<exercício_contrato>:<numero_contrato_base>; addendum_id=contract_base_id+<ID_ou_numero_aditivo>+<ano_aditivo>; expenditure_id=state_portal_rs:<sistema>:<ente>:<UG>:<exercício_empenho>:<numero_empenho>:<estágio>:<documento_evento>; bid_id=state_portal_rs:<sistema>:<ente>:<UG>:<exercício_processo>:<ID_processo_ou_numero+modalidade>

Normalização:

- Preservar IDs como texto, zeros iniciais, grafia e valores originais; decimais exatos e datas ISO com fuso quando disponível.
- CNPJ textual normalizado compatível com Company.cnpj existente; não converter identificadores em número; validar formatos oficialmente publicados, inclusive evolução alfanumérica. CPF mascarado nunca vira CPF completo.
- Namespace obrigatório UF=RS, source_id=state_portal_rs, sistema, ente CNPJ, UG, exercício e número textual; CNPJ do credor distinto do CNPJ do ente.
- Contratos com múltiplas parcelas/aditivos não devem duplicar valor global; identificar exercício de emissão e de pagamento dos restos a pagar.
- Aditivo não integra Contract.contract_id; valores original/atualizado e eventos de alteração ficam separados do contrato-base.
- Projetar dimensões comuns conforme F09: Territory.territory_id=sistema:tipo:codigo:versao_territorial; EconomicActivity.activity_id=classificacao:versao:codigo; PublicBody.public_body_id=jurisdicao:sistema:identificador:versao. Aplicar somente as dimensões usadas nesta fonte, preservar códigos originais e validar crosswalks; município é Territory, sem dimensão paralela incompatível.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Contract` | contract_id | existing |
| `StateExpenditure` | expenditure_id | proposed |
| `PublicBody` | public_body_id | proposed |
| `Company` | cnpj | existing |
| `SourceDocument` | doc_id | existing |
| `IngestionRun` | run_id | existing |
| `ContractAddendum` | addendum_id | proposed |
| `Bid` | bid_id | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `PublicBody` → `ISSUED_STATE_CONTRACT` → `Contract` | UF+ente CNPJ+UG+exercício | Unidade orçamentária e gestora não são equivalentes automaticamente. | proposed |
| `Company` → `VENCEU` → `Contract` | CNPJ integral do vencedor/contratado expresso no contrato-base | Projeção compatível com queries atuais; evidência contratual, source_id e data na aresta; aditivos não repetem adjudicação. | existing |
| `StateExpenditure` → `PAID_TO` → `Company` | CNPJ integral do credor no evento de pagamento | Vínculo só para estágio pago; retenções/estornos explicitados. | proposed |
| `StateExpenditure` → `EXECUTES_CONTRACT` → `Contract` | ID oficial contrato ou referência exata+ente+UG+exercício | Se base não fornece referência, registrar despesa sem aresta de contrato. | proposed |
| `Contract` → `DUPLICATE_PUBLICATION_OF` → `Contract` | ID PNCP/crosswalk oficial e campos contratuais compatíveis | Manter identificadores por fonte; somas devem escolher uma observação por fato e não acumular portal e TCE. | proposed |
| `Contract` → `DOCUMENTED_BY` → `SourceDocument` | doc_id=SHA256(source_id+URL+checksum+registro) | Toda aresta factual precisa source_id, documento/linha, data de referência e captured_at; nova relação proposta de proveniência. | proposed |
| `Contract` → `REFERENTE_A` → `Bid` | Referência expressa de ID licitação/processo+UF RS+ente+UG+exercício | Aresta existente para navegação contratual; não vincular só por fornecedor/valor/objeto. | existing |
| `ContractAddendum` → `AMENDS_CONTRACT` → `Contract` | contract_base_id oficial ou crosswalk comprovado | Conservar ID do aditivo, data, efeito, valor e vigência; não contar como outro contrato. | proposed |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `scripts/download_state_portal_rs.py`
- `etl/src/bracc_etl/pipelines/state_portal_rs.py`
- `etl/src/bracc_etl/schemas/state_portal_rs.py`
- `etl/tests/test_state_portal_rs_pipeline.py`
- `docs/source-runbooks/state_portal_rs.md`

Tarefas específicas, em ordem:

1. Inventariar recursos por tipo contratual e arquivos de despesas; diferenciar FPE de LicitaCon TCE-RS e deduplicar apenas com chave comum/documento.
1. Mapear dimensões ente, órgão, UG, UO, credor e classificação orçamentária com códigos oficiais; verificar mudança de estrutura administrativa entre anos.
1. Executar piloto de dois exercícios e duas UGs incluindo aditivo, estorno e RAP; reconciliar valores por estágio sem somar empenho/liquidação/pagamento como despesas distintas.
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
- [ ] Contrato 1/2025 em duas UGs produz IDs distintos; empenho de 2025 pago em 2026 mantém vínculo ao exercício de origem.
- [ ] Somatórios por estágio/UG/período conferem com o relatório/exportação de mesma data-base; zeros e ausência de informação distintos.
- [ ] Piloto registra cobertura, URL final, schema, SHA-256 e dicionário; nova carga preserva histórico e proveniência.
- [ ] Contrato-base com 3 aditivos produz 1 Contract e 3 ContractAddendum; concentração/recorrência conta o contrato uma vez; VENCEU/REFERENTE_A só com evidência exata.

## Riscos e decisões pendentes

- Cadência/limites reais e cobertura de Poderes/órgãos precisam ser medidos por recurso, não presumidos pela existência do portal.
- Duplicação de fatos entre TCE, PNCP e portal estadual se não houver observações separadas e reconciliação.

## Evidências e referências

- [https://www.transparencia.rs.gov.br/dados-abertos/](https://www.transparencia.rs.gov.br/dados-abertos/)
- `docs/source_registry_br_v1.csv`
- `etl/src/bracc_etl/pipelines/transparencia.py`
- `etl/src/bracc_etl/pipelines/mides.py`
- `etl/src/bracc_etl/pipelines/comprasnet.py`
- [https://www.transparencia.rs.gov.br/faq/](https://www.transparencia.rs.gov.br/faq/)
- [https://www.transparencia.rs.gov.br/dados-abertos/dados-transparencia-rs/dados/](https://www.transparencia.rs.gov.br/dados-abertos/dados-transparencia-rs/dados/)

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
