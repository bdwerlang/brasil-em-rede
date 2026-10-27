# Plano dos cruzamentos definidos pelo projeto

[Índice](README.md) · [Regras de identidade e evidência](architecture.md)

Este inventário cobre todos os IDs de `PATTERN_METADATA`. Uma definição em metadados não significa consulta implementada. Os oito padrões comunitários têm arquivos de consulta identificados; os demais exigem implementação ou revisão explícita de viabilidade.

Em cada requisito, alternativas entre parênteses significam **qualquer uma**; grupos separados por `+` precisam estar disponíveis em conjunto. Cobertura e vigência devem ser compatíveis. Amostras sintéticas de aceite não afirmam casos reais.

## self_dealing_amendment

- **Estado auditado / condição:** Metadado dependente de vínculos pessoais/parentesco não garantidos pelas fontes públicas; revisão de viabilidade obrigatória.
- **Fontes necessárias:** ([cnpj](sources/cnpj.md)) + ([tse](sources/tse.md) ou [camara](sources/camara.md) ou [senado](sources/senado.md)) + ([transparencia](sources/transparencia.md) ou [transferegov](sources/transferegov.md) ou [tesouro_emendas](sources/tesouro_emendas.md) ou [siop](sources/siop.md)) + ([transparencia](sources/transparencia.md) ou [comprasnet](sources/comprasnet.md) ou [pncp](sources/pncp.md) ou [mides](sources/mides.md))
- **Campos e ligações:** Autor identificado → Amendment → beneficiário CNPJ → Contract; participação societária temporal. Parentesco, se necessário, exige evidência independente e não é derivado de sobrenome.
- **Temporalidade:** Mandato, autoria, sociedade e contrato precisam de intervalos compatíveis; sociedade atual não comprova vínculo histórico.
- **Implementação a fazer:** Separar coocorrência documental de interpretação; criar consulta e testes somente para elos comprovados. Manter variante familiar bloqueada sem fonte apropriada. Exigir projeção canônica Contract/VENCEU para MiDES; PNCP de publicações só participa após adquirir e resolver contratos/resultados, nunca como fornecedor contratado por inferência. Registrar e rotear no provider/tier apropriado, respeitar saída pública e testar pelo endpoint; query isolada não disponibiliza o padrão.
- **Consulta atual:** Sem query específica confirmada no escopo comunitário.
- **Aceite positivo:** Fixture com autoria, beneficiário, contrato e sociedade documentados devolve todos os IDs de evidência.
- **Aceite negativo:** Sobrenome igual ou sociedade iniciada após o contrato não fecha o caminho.

## patrimony_incompatibility

- **Estado auditado / condição:** Metadado com limitação conceitual: dados existentes não sustentam teste automático de incompatibilidade patrimonial.
- **Fontes necessárias:** ([cnpj](sources/cnpj.md)) + ([tse_bens](sources/tse_bens.md))
- **Campos e ligações:** Candidatura/declarante identificado + DeclaredAsset e participação societária comprovada; capital social de empresa não é patrimônio pessoal do sócio.
- **Temporalidade:** Comparar declarações da mesma eleição/data-base; manter revisões e natureza de avaliação.
- **Implementação a fazer:** Revisar definição antes de programar: sem percentual de participação e base de avaliação compatível, produzir apenas quadro contextual, sem rótulo de incompatibilidade. Registrar e rotear no provider/tier apropriado, respeitar saída pública e testar pelo endpoint; query isolada não disponibiliza o padrão.
- **Consulta atual:** Sem query específica confirmada no escopo comunitário.
- **Aceite positivo:** Fixture contextual apresenta bens, valores e data-base em colunas separadas com origem.
- **Aceite negativo:** Capital social integral de uma sociedade não é atribuído a cada sócio nem comparado automaticamente ao total declarado.

## sanctioned_still_receiving

- **Estado auditado / condição:** Query comunitária existente; validar após correções de ingestão e identidade.
- **Fontes necessárias:** ([cnpj](sources/cnpj.md)) + ([sanctions](sources/sanctions.md) ou [tcu](sources/tcu.md)) + ([transparencia](sources/transparencia.md) ou [comprasnet](sources/comprasnet.md) ou [pncp](sources/pncp.md) ou [mides](sources/mides.md))
- **Campos e ligações:** Company.cnpj canônico; Company-SANCIONADA-Sanction e Company-VENCEU-Contract; IDs oficiais e documentos.
- **Temporalidade:** Data do contrato dentro de vigência registrada da sanção; tipo e alcance são preservados e avaliados separadamente.
- **Implementação a fazer:** Reconciliar CNPJ, datas/ausência de fim e escopo; query deve apresentar coocorrência, não conclusão automática de impedimento. Exigir projeção canônica Contract/VENCEU para MiDES; PNCP de publicações só participa após adquirir e resolver contratos/resultados, nunca como fornecedor contratado por inferência.
- **Consulta atual:** [api/src/bracc/queries/public_pattern_sanctioned_still_receiving.cypher](../../api/src/bracc/queries/public_pattern_sanctioned_still_receiving.cypher)
- **Aceite positivo:** Empresa exata com contrato em vigência retorna contrato e sanção.
- **Aceite negativo:** CNPJ distinto ou sanção vencida antes do evento não entra no resultado temporal.

## donation_contract_loop

- **Estado auditado / condição:** Definido em metadados; sem execução comunitária dedicada confirmada.
- **Fontes necessárias:** ([cnpj](sources/cnpj.md)) + ([tse](sources/tse.md)) + ([transparencia](sources/transparencia.md) ou [comprasnet](sources/comprasnet.md) ou [pncp](sources/pncp.md) ou [mides](sources/mides.md)) + ([camara](sources/camara.md) ou [senado](sources/senado.md) ou [transparencia](sources/transparencia.md))
- **Campos e ligações:** Doador identificado → campanha/candidatura → agente público; fornecedor exato → contrato; vínculo do agente ao órgão requer evidência própria.
- **Temporalidade:** Doação precede o evento contratual e os mandatos/competências coincidem com as datas.
- **Implementação a fazer:** Criar consulta de caminho comprovado, definir papel de autoridade e limitar às classes de doações realmente existentes no período. Exigir projeção canônica Contract/VENCEU para MiDES; PNCP de publicações só participa após adquirir e resolver contratos/resultados, nunca como fornecedor contratado por inferência. Registrar e rotear no provider/tier apropriado, respeitar saída pública e testar pelo endpoint; query isolada não disponibiliza o padrão.
- **Consulta atual:** Sem query específica confirmada no escopo comunitário.
- **Aceite positivo:** Fixture documenta doação, candidatura e contrato posterior de órgão cuja relação com o agente é explicitamente sustentada.
- **Aceite negativo:** Mandato federal isolado não atribui ao parlamentar decisão sobre todo contrato do governo.

## contract_concentration

- **Estado auditado / condição:** Query comunitária existente; validar após correções de ingestão e identidade.
- **Fontes necessárias:** ([transparencia](sources/transparencia.md) ou [comprasnet](sources/comprasnet.md) ou [pncp](sources/pncp.md) ou [mides](sources/mides.md))
- **Campos e ligações:** Supplier CNPJ + órgão/UG/ente normalizados + contratos conciliados entre provedores; denominador inclui todos os fornecedores da mesma cobertura.
- **Temporalidade:** Numerador e denominador têm o mesmo intervalo e tipo de valor; parcelas/aditivos não são contratos adicionais.
- **Implementação a fazer:** Adicionar filtros de cobertura e período; impedir indicador se só foi baixado o fornecedor consultado. Exigir projeção canônica Contract/VENCEU para MiDES; PNCP de publicações só participa após adquirir e resolver contratos/resultados, nunca como fornecedor contratado por inferência.
- **Consulta atual:** [api/src/bracc/queries/public_pattern_contract_concentration.cypher](../../api/src/bracc/queries/public_pattern_contract_concentration.cypher)
- **Aceite positivo:** Fixture completa de um órgão calcula participação acima do limiar a partir de todos os fornecedores.
- **Aceite negativo:** Download parcial ou denominador de outro exercício produz indicador indisponível, não concentração confirmada.

## debtor_contracts

- **Estado auditado / condição:** Query comunitária existente; validar após correções de ingestão e identidade.
- **Fontes necessárias:** ([cnpj](sources/cnpj.md)) + ([pgfn](sources/pgfn.md)) + ([transparencia](sources/transparencia.md) ou [comprasnet](sources/comprasnet.md) ou [pncp](sources/pncp.md) ou [mides](sources/mides.md))
- **Campos e ligações:** CNPJ do devedor e do fornecedor exatos; dívida e contratos mantêm natureza, status e IDs de origem.
- **Temporalidade:** Snapshot da dívida e datas contratuais comparáveis; marcar desconhecido quando não existe histórico da dívida para o evento.
- **Implementação a fazer:** Separar coocorrência no snapshot de afirmação de simultaneidade histórica; incluir cobertura e status da dívida. Exigir projeção canônica Contract/VENCEU para MiDES; PNCP de publicações só participa após adquirir e resolver contratos/resultados, nunca como fornecedor contratado por inferência.
- **Consulta atual:** [api/src/bracc/queries/public_pattern_debtor_contracts.cypher](../../api/src/bracc/queries/public_pattern_debtor_contracts.cypher)
- **Aceite positivo:** Fixture com a mesma empresa e observações temporais declaradas retorna dívida e contratos.
- **Aceite negativo:** Nome semelhante ou snapshot atual usado para afirmar dívida em contrato antigo sem prova não confirma simultaneidade.

## embargoed_receiving

- **Estado auditado / condição:** Query comunitária existente; validar após correções de ingestão e identidade.
- **Fontes necessárias:** ([cnpj](sources/cnpj.md)) + ([ibama](sources/ibama.md)) + ([transparencia](sources/transparencia.md) ou [comprasnet](sources/comprasnet.md) ou [pncp](sources/pncp.md) ou [mides](sources/mides.md) ou [bndes](sources/bndes.md))
- **Campos e ligações:** Embargo associado por documento exato à empresa; contrato ou financiamento mantêm identificador e origem.
- **Temporalidade:** Vigência do embargo comparada ao evento de contrato/desembolso; data de consulta não substitui data do evento.
- **Implementação a fazer:** Completar baixa/suspensão de embargo, alcance e datas; adaptar evidência de contratos e empréstimos de forma distinta. Exigir projeção canônica Contract/VENCEU para MiDES; PNCP de publicações só participa após adquirir e resolver contratos/resultados, nunca como fornecedor contratado por inferência.
- **Consulta atual:** [api/src/bracc/queries/public_pattern_embargoed_receiving.cypher](../../api/src/bracc/queries/public_pattern_embargoed_receiving.cypher)
- **Aceite positivo:** Fixture com embargo vigente e evento financeiro em período compatível retorna ambos os documentos.
- **Aceite negativo:** Polígono próximo ou documento parcial não atribui embargo à empresa; embargo encerrado antes não satisfaz regra temporal.

## loan_debtor

- **Estado auditado / condição:** Definido em metadados; sem execução comunitária dedicada confirmada.
- **Fontes necessárias:** ([cnpj](sources/cnpj.md)) + ([bndes](sources/bndes.md)) + ([pgfn](sources/pgfn.md))
- **Campos e ligações:** Empresa tomadora exata + Finance de empréstimo e dívida com tipos separados; garantia/beneficiário indireto não vira tomador.
- **Temporalidade:** Contrato de crédito, desembolso e snapshot da dívida têm datas explícitas; somente histórico adequado prova concomitância.
- **Implementação a fazer:** Implementar query dedicada e parâmetros de data, mantendo consulta agregada legada apenas como referência. Registrar e rotear no provider/tier apropriado, respeitar saída pública e testar pelo endpoint; query isolada não disponibiliza o padrão.
- **Consulta atual:** [api/src/bracc/queries/public_patterns_company.cypher](../../api/src/bracc/queries/public_patterns_company.cypher)
- **Aceite positivo:** Fixture do mesmo CNPJ tem crédito/desembolso e dívida contemporâneos com proveniência.
- **Aceite negativo:** Dívida registrada apenas anos depois não é tratada como existente na contratação do empréstimo.

## donation_amendment_loop

- **Estado auditado / condição:** Definido em metadados; sem execução comunitária dedicada confirmada.
- **Fontes necessárias:** ([cnpj](sources/cnpj.md)) + ([tse](sources/tse.md)) + ([transparencia](sources/transparencia.md) ou [transferegov](sources/transferegov.md) ou [tesouro_emendas](sources/tesouro_emendas.md) ou [siop](sources/siop.md))
- **Campos e ligações:** Doador → candidatura/pessoa identificada → autor oficial de emenda → beneficiário CNPJ; não deduzir autor pelo nome.
- **Temporalidade:** Doação, autoria e benefício preservam eleição, exercício e evento financeiro distintos.
- **Implementação a fazer:** Implementar crosswalk de IDs TSE/casas/orçamento e consulta de trilha com cada elo verificável. Registrar e rotear no provider/tier apropriado, respeitar saída pública e testar pelo endpoint; query isolada não disponibiliza o padrão.
- **Consulta atual:** Sem query específica confirmada no escopo comunitário.
- **Aceite positivo:** Fixture contém IDs oficiais compatíveis e benefício da mesma empresa doadora.
- **Aceite negativo:** Emenda com autor homônimo ou beneficiário diferente não forma ciclo.

## amendment_beneficiary_contracts

- **Estado auditado / condição:** Query comunitária existente; validar após correções de ingestão e identidade.
- **Fontes necessárias:** ([cnpj](sources/cnpj.md)) + ([transparencia](sources/transparencia.md) ou [transferegov](sources/transferegov.md) ou [tesouro_emendas](sources/tesouro_emendas.md) ou [siop](sources/siop.md)) + ([transparencia](sources/transparencia.md) ou [comprasnet](sources/comprasnet.md) ou [pncp](sources/pncp.md) ou [mides](sources/mides.md))
- **Campos e ligações:** Amendment-BENEFICIOU-Company + Company-VENCEU-Contract; Convenio opcional com ID próprio.
- **Temporalidade:** Exercício/repasse e contrato exibidos; coocorrência não prova que a emenda financiou aquele contrato.
- **Implementação a fazer:** Conciliar múltiplos provedores, preservar tipo de beneficiário e distinguir vínculo documental de causalidade. Exigir projeção canônica Contract/VENCEU para MiDES; PNCP de publicações só participa após adquirir e resolver contratos/resultados, nunca como fornecedor contratado por inferência.
- **Consulta atual:** [api/src/bracc/queries/public_pattern_amendment_beneficiary_contracts.cypher](../../api/src/bracc/queries/public_pattern_amendment_beneficiary_contracts.cypher)
- **Aceite positivo:** Fixture retorna mesma empresa como beneficiária e fornecedora com IDs de emenda e contrato.
- **Aceite negativo:** Órgão intermediário ou empresa com nome semelhante não é substituído pelo beneficiário final.

## debtor_health_operator

- **Estado auditado / condição:** Definido em metadados; sem execução comunitária dedicada confirmada.
- **Fontes necessárias:** ([cnpj](sources/cnpj.md)) + ([pgfn](sources/pgfn.md)) + ([datasus](sources/datasus.md))
- **Campos e ligações:** CNES → mantenedora/operadora CNPJ explícita → Company → dívida; prestador físico e entidade jurídica separados.
- **Temporalidade:** Competência CNES e snapshot da dívida informados; mudança de mantenedora tem vigência.
- **Implementação a fazer:** Implementar query dedicada, crosswalk de estabelecimentos e status de atendimento SUS por competência. Corrigir CNES: separar atendimento SUS ambulatorial/hospitalar, preservar indicador desconhecido e distinguir operador/mantenedor. Registrar e rotear no provider/tier apropriado, respeitar saída pública e testar pelo endpoint; query isolada não disponibiliza o padrão.
- **Consulta atual:** Sem query específica confirmada no escopo comunitário.
- **Aceite positivo:** Fixture de operadora exata com CNES SUS na competência e observação de dívida retorna evidências.
- **Aceite negativo:** Nome da unidade ou CNPJ de antiga mantenedora não atribui dívida à operadora atual. Indicador ambulatorial ausente não equivale a ausência de atendimento SUS; papel de mantenedor não vira operador automaticamente.

## sanctioned_health_operator

- **Estado auditado / condição:** Definido em metadados; sem execução comunitária dedicada confirmada.
- **Fontes necessárias:** ([cnpj](sources/cnpj.md)) + ([sanctions](sources/sanctions.md) ou [tcu](sources/tcu.md)) + ([datasus](sources/datasus.md))
- **Campos e ligações:** Operadora CNPJ exata no CNES; sanção tipificada por esse documento.
- **Temporalidade:** Competência da operação e vigência da sanção sobrepostas; não inferir efeito automático sobre atendimento SUS.
- **Implementação a fazer:** Implementar consulta de coocorrência com competência, vigência e escopo documental. Corrigir CNES: separar atendimento SUS ambulatorial/hospitalar, preservar indicador desconhecido e distinguir operador/mantenedor. Registrar e rotear no provider/tier apropriado, respeitar saída pública e testar pelo endpoint; query isolada não disponibiliza o padrão.
- **Consulta atual:** Sem query específica confirmada no escopo comunitário.
- **Aceite positivo:** Fixture da mesma operadora e período compatível produz referências do CNES e sanção.
- **Aceite negativo:** Empresa homônima, antiga operadora ou sanção fora de vigência não confirma o cruzamento. Indicador ambulatorial ausente não equivale a ausência de atendimento SUS; papel de mantenedor não vira operador automaticamente.

## shell_company_contracts

- **Estado auditado / condição:** Limitação de granularidade: fonte RAIS agregada não sustenta o critério nominal descrito no metadado.
- **Fontes necessárias:** ([cnpj](sources/cnpj.md)) + ([rais](sources/rais.md)) + ([transparencia](sources/transparencia.md) ou [comprasnet](sources/comprasnet.md) ou [pncp](sources/pncp.md) ou [mides](sources/mides.md))
- **Campos e ligações:** RAIS pública usada no projeto é agregada por setor/território; não fornece emprego nominal por empresa.
- **Temporalidade:** Contexto setorial por ano e território pode ser comparado, sem atribuir quadro funcional a CNPJ.
- **Implementação a fazer:** Revisar definição: implementar somente contexto agregado, ou manter variante nominal bloqueada até existir fonte adequada de vínculos empregador/quantidade. Exigir projeção canônica Contract/VENCEU para MiDES; PNCP de publicações só participa após adquirir e resolver contratos/resultados, nunca como fornecedor contratado por inferência. Registrar e rotear no provider/tier apropriado, respeitar saída pública e testar pelo endpoint; query isolada não disponibiliza o padrão.
- **Consulta atual:** Sem query específica confirmada no escopo comunitário.
- **Aceite positivo:** Fixture apresenta indicador setorial contextual com unidade, território e ano, sem rotular empresa pela estatística.
- **Aceite negativo:** Zero/baixo emprego do setor nunca vira zero empregados de uma empresa específica.

## offshore_connection

- **Estado auditado / condição:** Definido em metadados; sem execução comunitária dedicada confirmada.
- **Fontes necessárias:** ([icij](sources/icij.md)) + ([cnpj](sources/cnpj.md)) + ([transparencia](sources/transparencia.md) ou [comprasnet](sources/comprasnet.md) ou [pncp](sources/pncp.md) ou [mides](sources/mides.md) ou [bndes](sources/bndes.md))
- **Campos e ligações:** IDs ICIJ + vínculo documentado para pessoa/empresa brasileira; nome só gera candidato. Preservar jurisdição e tipo de papel.
- **Temporalidade:** Data dos documentos vazados e período do evento público separados; não presumir vínculo atual.
- **Implementação a fazer:** Implementar candidatos auditáveis e consulta confirmada somente com evidência de identidade independente. Exigir projeção canônica Contract/VENCEU para MiDES; PNCP de publicações só participa após adquirir e resolver contratos/resultados, nunca como fornecedor contratado por inferência. Registrar e rotear no provider/tier apropriado, respeitar saída pública e testar pelo endpoint; query isolada não disponibiliza o padrão.
- **Consulta atual:** Sem query específica confirmada no escopo comunitário.
- **Aceite positivo:** Fixture com identidade corroborada e vínculo offshore documentado retorna caminho e proveniência.
- **Aceite negativo:** Empresa estrangeira homônima não é unida ao fornecedor brasileiro por nome.

## deputy_supplier_loop

- **Estado auditado / condição:** Definido em metadados; sem execução comunitária dedicada confirmada.
- **Fontes necessárias:** ([camara](sources/camara.md)) + ([tse](sources/tse.md)) + ([cnpj](sources/cnpj.md))
- **Campos e ligações:** deputy_id oficial → Expense → fornecedor CNPJ; doação/campanha identificada por chave e crosswalk verificado.
- **Temporalidade:** Ano da despesa, eleição e vigência do mandato explícitos; respeitar tipos de doadores do período.
- **Implementação a fazer:** Criar crosswalk de identidade e query de coocorrência sem inferir benefício político só pela despesa. Registrar e rotear no provider/tier apropriado, respeitar saída pública e testar pelo endpoint; query isolada não disponibiliza o padrão.
- **Consulta atual:** Sem query específica confirmada no escopo comunitário.
- **Aceite positivo:** Fixture do mesmo fornecedor e parlamentar com doação documentada e despesa CEAP retorna ambos.
- **Aceite negativo:** Despesa cancelada/duplicada ou candidatura homônima não fecha o caminho.

## cvm_sanctioned_receiving

- **Estado auditado / condição:** Definido em metadados; sem execução comunitária dedicada confirmada.
- **Fontes necessárias:** ([cvm](sources/cvm.md)) + ([cnpj](sources/cnpj.md)) + ([transparencia](sources/transparencia.md) ou [comprasnet](sources/comprasnet.md) ou [pncp](sources/pncp.md) ou [mides](sources/mides.md) ou [bndes](sources/bndes.md))
- **Campos e ligações:** CNPJ exato do participante + processo CVM; distinguir instaurado, julgado e penalidade efetiva.
- **Temporalidade:** Data e estágio do processo e evento financeiro explicitados; processo em aberto não equivale a sanção.
- **Implementação a fazer:** Corrigir nome/classificação do resultado e criar query que separa procedimento de penalidade, com decisão de origem. Exigir projeção canônica Contract/VENCEU para MiDES; PNCP de publicações só participa após adquirir e resolver contratos/resultados, nunca como fornecedor contratado por inferência. Registrar e rotear no provider/tier apropriado, respeitar saída pública e testar pelo endpoint; query isolada não disponibiliza o padrão.
- **Consulta atual:** Sem query específica confirmada no escopo comunitário.
- **Aceite positivo:** Fixture com decisão/estágio comprovado e evento financeiro da mesma entidade mostra a classificação correta.
- **Aceite negativo:** Somente nome em processo sem CNPJ ou procedimento não julgado não vira empresa sancionada.

## global_pep_contracts

- **Estado auditado / condição:** Definido em metadados; sem execução comunitária dedicada confirmada.
- **Fontes necessárias:** ([opensanctions](sources/opensanctions.md)) + ([cnpj](sources/cnpj.md)) + ([transparencia](sources/transparencia.md) ou [comprasnet](sources/comprasnet.md) ou [pncp](sources/pncp.md) ou [mides](sources/mides.md))
- **Campos e ligações:** GlobalPEP namespace + identidade corroborada + sociedade QSA documentada + fornecedor CNPJ; não usar score de nome como prova.
- **Temporalidade:** Função pública, sociedade e contrato com vigências conhecidas; PEP não é sanção nem ato irregular.
- **Implementação a fazer:** Implementar trilha de evidência de identidade e papéis, com revisão de candidatos e regras de exposição. Exigir projeção canônica Contract/VENCEU para MiDES; PNCP de publicações só participa após adquirir e resolver contratos/resultados, nunca como fornecedor contratado por inferência. Registrar e rotear no provider/tier apropriado, respeitar saída pública e testar pelo endpoint; query isolada não disponibiliza o padrão.
- **Consulta atual:** Sem query específica confirmada no escopo comunitário.
- **Aceite positivo:** Fixture com identidade corroborada e sociedade válida retorna caminho e documentos.
- **Aceite negativo:** Nome aproximado, ex-sócio fora do intervalo ou classificação PEP isolada não gera conclusão sobre contrato.

## legislator_supplier_loop

- **Estado auditado / condição:** Definido em metadados; sem execução comunitária dedicada confirmada.
- **Fontes necessárias:** ([camara](sources/camara.md) ou [senado](sources/senado.md)) + ([cnpj](sources/cnpj.md)) + ([tse](sources/tse.md) ou [transparencia](sources/transparencia.md))
- **Campos e ligações:** ID legislativo → pessoa identificada → SOCIO_DE temporal → Company fornecedora de Expense CEAP/CEAPS do mesmo agente.
- **Temporalidade:** Sociedade e mandato coincidem com a data da despesa; snapshots atuais não retroagem.
- **Implementação a fazer:** Implementar identidade entre casas/cadastro/QSA e query apenas para sociedade com evidência temporal. Registrar e rotear no provider/tier apropriado, respeitar saída pública e testar pelo endpoint; query isolada não disponibiliza o padrão.
- **Consulta atual:** Sem query específica confirmada no escopo comunitário.
- **Aceite positivo:** Fixture contém vínculo societário documentado do legislador e despesa ao mesmo CNPJ no intervalo.
- **Aceite negativo:** Sócio homônimo ou sociedade posterior à despesa não satisfaz a regra.

## split_contracts_below_threshold

- **Estado auditado / condição:** Query comunitária existente; validar após correções de ingestão e identidade.
- **Fontes necessárias:** ([transparencia](sources/transparencia.md) ou [comprasnet](sources/comprasnet.md) ou [pncp](sources/pncp.md) ou [mides](sources/mides.md))
- **Campos e ligações:** Mesmo fornecedor CNPJ + órgão/UG + objeto categorizado e contrato conciliado; limiar é parâmetro de análise.
- **Temporalidade:** Janela mensal explícita e datas de contratação; separar parcelas/aditivos e publicações duplicadas.
- **Implementação a fazer:** Versionar normalização de objetos, filtros de valores/cobertura e parâmetros; resultado é recorrência, sem concluir fracionamento ilícito. Exigir projeção canônica Contract/VENCEU para MiDES; PNCP de publicações só participa após adquirir e resolver contratos/resultados, nunca como fornecedor contratado por inferência.
- **Consulta atual:** [api/src/bracc/queries/public_pattern_split_contracts_below_threshold.cypher](../../api/src/bracc/queries/public_pattern_split_contracts_below_threshold.cypher)
- **Aceite positivo:** Fixture com três contratos distintos e objetos comparáveis no mesmo mês satisfaz limiar configurado.
- **Aceite negativo:** Três publicações do mesmo contrato, parcelas ou meses diferentes não contam como três contratos.

## srp_multi_org_hitchhiking

- **Estado auditado / condição:** Query comunitária existente; validar após correções de ingestão e identidade.
- **Fontes necessárias:** ([pncp](sources/pncp.md) ou [comprasnet](sources/comprasnet.md))
- **Campos e ligações:** Contract-REFERENTE_A-Bid ou ata canônica, ID de SRP, órgãos/UGs distintos e vínculos oficiais de adesão.
- **Temporalidade:** Vigência da ata e datas de adesão/contrato compatíveis.
- **Implementação a fazer:** Garantir que downloader preserva ata/adesão, criar conciliação de IDs e query sem deduzir SRP só do objeto textual. Adquirir atas e adesões com documentos oficiais; modelar adesão e distinguir participante original de aderente. A flag SRP não é prova de carona.
- **Consulta atual:** [api/src/bracc/queries/public_pattern_srp_multi_org_hitchhiking.cypher](../../api/src/bracc/queries/public_pattern_srp_multi_org_hitchhiking.cypher)
- **Aceite positivo:** Fixture de uma ata com adesões documentadas de órgãos suficientes retorna IDs da ata e contratos.
- **Aceite negativo:** Atas homônimas em exercícios diferentes ou contratos sem referência oficial à ata não são agrupados. Órgãos participantes originais sem adesão documentada não são classificados como caronas.

## inexigibility_recurrence

- **Estado auditado / condição:** Query comunitária existente; validar após correções de ingestão e identidade.
- **Fontes necessárias:** ([pncp](sources/pncp.md) ou [comprasnet](sources/comprasnet.md))
- **Campos e ligações:** Fornecedor CNPJ + órgão/UG + modalidade oficial + objeto comparável; usar código de modalidade, não apenas substring.
- **Temporalidade:** Janela definida por data/ano e competência normativa do parâmetro; contratos/aditivos deduplicados.
- **Implementação a fazer:** Preservar código e descrição oficiais de modalidade, versionar classificação de objeto e query parametrizada.
- **Consulta atual:** [api/src/bracc/queries/public_pattern_inexigibility_recurrence.cypher](../../api/src/bracc/queries/public_pattern_inexigibility_recurrence.cypher)
- **Aceite positivo:** Fixture tem contratos distintos por inexigibilidade com fornecedor/órgão/objeto compatíveis na janela.
- **Aceite negativo:** Dispensa ou outro código de modalidade, aditivo duplicado ou objeto não comparável não entra na recorrência.
