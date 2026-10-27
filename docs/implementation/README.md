# Plano de implementação de todas as fontes

Data do planejamento: **2026-10-27**. Cobertura: **169 fichas individuais**,
uma para cada ID em [source_registry_br_v1.csv](../source_registry_br_v1.csv),
incluindo fontes implementadas, novas, derivadas, catálogos e acessos restritos.
Não há fonte omitida por estar bloqueada ou ainda sem endpoint validado.

Cada ficha especifica aquisição, autenticação, particionamento, retomada,
contrato de entrada, normalização, chave de identidade, cadastro no Neo4j,
ligações, dependências, arquivos a entregar e critérios de aceite.
Os estados herdados do registro não comprovam carga no ambiente local.

## Como executar o plano

1. Concluir a **etapa zero F01–F10** da [arquitetura](architecture.md): identidade,
   CNPJ alfanumérico, esquema, aquisição, loader, ligações, orquestração,
   dimensões e ambiente. Ela contém as lacunas comprovadas no código atual.
2. Fazer o piloto CNPJ + sanções + contratos; adicionar emenda/candidatura e
   uma dimensão/série para validar os cruzamentos e medir recursos.
3. Seguir a ordem da [matriz CSV](source_matrix.csv), respeitando dependências.
   A onda é ajustada quando uma base necessária pertence a uma onda posterior.
   Dentro da mesma onda, a ordem topológica determina o que vem antes.
4. Para cada ficha, fechar separadamente contrato, download, transformação,
   cadastro, ligações e operação incremental. Só registrar sucesso com evidência.
5. Expandir backfill após medição do piloto; registrar bloqueios e progresso
   por fonte, sem reset global do banco ou suposição de acesso irrestrito.

## Distribuição do trabalho

- Completar e corrigir pipeline existente: **47**.
- Implementar conector e pipeline: **108**.
- Descoberta de recursos do catálogo: **5**.
- Acesso condicionado / restrito: **9**.

Complexidade **S/M/L/XL** é relativa (pequena/média/grande/muito grande), não uma
promessa de prazo. Volume e tempo de download serão medidos por partição no
piloto; portais indisponíveis e acessos institucionais têm pré-condições próprias.

| Onda | Foco | Fontes na onda efetiva |
|---|---|---|
| 1 | Identidade, dimensões e bases essenciais | 12 |
| 2 | Contratos, emendas, repasses e despesas | 14 |
| 3 | Eleições, mandatos e governança | 12 |
| 4 | Fiscal, crédito e mercado | 33 |
| 5 | Ambiente, serviços e estatísticas | 38 |
| 6 | Justiça e fontes internacionais | 13 |
| 7 | Estados, municípios e cobertura territorial | 25 |
| 8 | Catálogos e acessos condicionados | 22 |

Não há credenciais, scripts novos de download ou cargas executadas por este
documento. Caminhos novos nas fichas são entregáveis propostos. URLs marcadas
como catálogo, descoberta ou pendentes precisam de prova de acesso antes do
desenvolvimento do extrator. Estatísticas ligam território/período; não produzem
vínculos nominais sem chaves. Fontes restritas mantêm uma ficha com seu caminho
de habilitação/exportação e um resultado de bloqueio explícito.

## Entregáveis do planejamento

- [169 fichas por fonte](#índice-individual), com links abaixo.
- [Arquitetura, fundação, modelo de cadastro e regras de ligação](architecture.md).
- [Plano individual dos 21 cruzamentos definidos pelo projeto](crossings.md).
- [Matriz de ordem, dependências e complexidade](source_matrix.csv).
- [Manifesto estruturado do plano](../../config/source_implementation_plan.json).
- [Gerador e verificador de cobertura](../../scripts/generate_source_implementation_plan.py).

Para atualizar o plano, editar o manifesto e executar, da raiz do repositório:

```bash
python3 scripts/generate_source_implementation_plan.py
python3 scripts/generate_source_implementation_plan.py --check
```

O verificador exige cobertura exata do registro, IDs únicos, dependências
existentes e sem ciclos, artefatos atuais existentes e fichas derivadas
sincronizadas. Ele não testa disponibilidade externa nem faz ingestão.

## Índice individual

| Ordem | Fonte | Descrição | Onda | Complexidade | Trabalho |
|---|---|---|---|---|---|
| 1 | [ceaf](sources/ceaf.md) | CEAF expelled servants | 1 | M | Completar e corrigir pipeline existente |
| 2 | [cnpj](sources/cnpj.md) | Receita Federal CNPJ | 1 | XL | Completar e corrigir pipeline existente |
| 3 | [ans_health_plans](sources/ans_health_plans.md) | ANS operators | 1 | M | Implementar conector e pipeline |
| 4 | [cepim](sources/cepim.md) | CEPIM barred NGOs | 1 | S | Completar e corrigir pipeline existente |
| 5 | [cnpj_simples](sources/cnpj_simples.md) | Simples Nacional / MEI | 1 | M | Implementar conector e pipeline |
| 6 | [ibge_geosciences](sources/ibge_geosciences.md) | IBGE Geociências — Limites Territoriais e Malhas Digitais | 1 | M | Implementar conector e pipeline |
| 7 | [ibge_census](sources/ibge_census.md) | Censo Demográfico — Dados Populacionais por Município | 1 | M | Implementar conector e pipeline |
| 8 | [leniency](sources/leniency.md) | Acordos de leniencia | 1 | M | Completar e corrigir pipeline existente |
| 9 | [pep_cgu](sources/pep_cgu.md) | CGU PEP list | 1 | M | Completar e corrigir pipeline existente |
| 10 | [sanctions](sources/sanctions.md) | CEIS CNEP sanctions | 1 | M | Completar e corrigir pipeline existente |
| 11 | [siorg](sources/siorg.md) | SIORG — Estrutura Organizacional do Governo Federal | 1 | L | Implementar conector e pipeline |
| 12 | [tcu](sources/tcu.md) | TCU sanctions | 1 | M | Completar e corrigir pipeline existente |
| 13 | [anp_royalties](sources/anp_royalties.md) | ANP royalties and fuel | 2 | L | Implementar conector e pipeline |
| 14 | [camara](sources/camara.md) | Camara CEAP expenses | 2 | M | Completar e corrigir pipeline existente |
| 15 | [comprasnet](sources/comprasnet.md) | ComprasNet contracts | 2 | L | Completar e corrigir pipeline existente |
| 16 | [cpgf](sources/cpgf.md) | CPGF gov card expenses | 2 | M | Completar e corrigir pipeline existente |
| 17 | [fnde_transfers](sources/fnde_transfers.md) | FNDE (Repasses) | 2 | L | Implementar conector e pipeline |
| 18 | [pncp](sources/pncp.md) | PNCP bids and contracts | 2 | L | Completar e corrigir pipeline existente |
| 19 | [senado](sources/senado.md) | Senado CEAPS expenses | 2 | M | Completar e corrigir pipeline existente |
| 20 | [siafi_budget_execution](sources/siafi_budget_execution.md) | SIAFI (Execução Orçamentária da União) | 2 | XL | Implementar conector e pipeline |
| 21 | [siga_brasil](sources/siga_brasil.md) | SIGA Brasil | 2 | XL | Implementar conector e pipeline |
| 22 | [siop](sources/siop.md) | SIOP emendas | 2 | L | Completar e corrigir pipeline existente |
| 23 | [tesouro_emendas](sources/tesouro_emendas.md) | Tesouro emendas | 2 | M | Completar e corrigir pipeline existente |
| 24 | [transferegov](sources/transferegov.md) | TransfereGov emendas e convenios | 2 | L | Completar e corrigir pipeline existente |
| 25 | [transparencia](sources/transparencia.md) | Portal da Transparencia contracts | 2 | L | Completar e corrigir pipeline existente |
| 26 | [viagens](sources/viagens.md) | Viagens a servico | 2 | M | Completar e corrigir pipeline existente |
| 27 | [camara_inquiries](sources/camara_inquiries.md) | Camara inquiries and requirements | 3 | L | Completar e corrigir pipeline existente |
| 28 | [camara_votes_bills](sources/camara_votes_bills.md) | Camara votes and bills | 3 | L | Implementar conector e pipeline |
| 29 | [cvm_directors](sources/cvm_directors.md) | CVM Administradores — Diretores e Conselheiros | 3 | L | Implementar conector e pipeline |
| 30 | [dou](sources/dou.md) | Diario Oficial da Uniao | 3 | XL | Completar e corrigir pipeline existente |
| 31 | [senado_cpis](sources/senado_cpis.md) | Senado CPIs | 3 | XL | Completar e corrigir pipeline existente |
| 32 | [senado_votes_bills](sources/senado_votes_bills.md) | Senado votes and bills | 3 | L | Implementar conector e pipeline |
| 33 | [tse](sources/tse.md) | TSE elections and donations | 3 | XL | Completar e corrigir pipeline existente |
| 34 | [tse_ballot_boxes](sources/tse_ballot_boxes.md) | Boletins de Urna | 3 | M | Implementar conector e pipeline |
| 35 | [tse_bens](sources/tse_bens.md) | TSE candidate assets | 3 | M | Completar e corrigir pipeline existente |
| 36 | [tse_electorate](sources/tse_electorate.md) | Eleitorado | 3 | M | Implementar conector e pipeline |
| 37 | [tse_filiados](sources/tse_filiados.md) | TSE party memberships | 3 | L | Completar e corrigir pipeline existente |
| 38 | [tse_results](sources/tse_results.md) | Resultados Eleitorais | 3 | M | Implementar conector e pipeline |
| 39 | [anac_aviation_concessions](sources/anac_aviation_concessions.md) | ANAC concessions | 4 | L | Implementar conector e pipeline |
| 40 | [anatel_telecom_licenses](sources/anatel_telecom_licenses.md) | ANATEL licenses | 4 | L | Implementar conector e pipeline |
| 41 | [aneel_concessions](sources/aneel_concessions.md) | ANEEL concessions | 4 | L | Implementar conector e pipeline |
| 42 | [antaq_port_contracts](sources/antaq_port_contracts.md) | ANTAQ contracts | 4 | L | Implementar conector e pipeline |
| 43 | [antt_transport_concessions](sources/antt_transport_concessions.md) | ANTT concessions | 4 | L | Implementar conector e pipeline |
| 44 | [b3_trades](sources/b3_trades.md) | B3 Negociações — Dados de Negociação em Bolsa | 4 | L | Implementar conector e pipeline |
| 45 | [bcb](sources/bcb.md) | BCB penalties | 4 | M | Completar e corrigir pipeline existente |
| 46 | [bcb_liquidacao](sources/bcb_liquidacao.md) | BCB bank liquidation acts | 4 | M | Implementar conector e pipeline |
| 47 | [bcb_sgs_base_monetaria](sources/bcb_sgs_base_monetaria.md) | SGS/API BCB - Base Monetária | 4 | M | Implementar conector e pipeline |
| 48 | [bcb_sgs_cambio](sources/bcb_sgs_cambio.md) | SGS/API BCB - Câmbio | 4 | M | Implementar conector e pipeline |
| 49 | [bcb_sgs_credito](sources/bcb_sgs_credito.md) | SGS/API BCB - Crédito | 4 | M | Implementar conector e pipeline |
| 50 | [bcb_sgs_indices](sources/bcb_sgs_indices.md) | SGS/API BCB - Índices | 4 | M | Implementar conector e pipeline |
| 51 | [bcb_sgs_juros](sources/bcb_sgs_juros.md) | SGS/API BCB - Juros | 4 | M | Implementar conector e pipeline |
| 52 | [bcb_sgs_meios_pagamento](sources/bcb_sgs_meios_pagamento.md) | SGS/API BCB - Meios de Pagamento | 4 | M | Implementar conector e pipeline |
| 53 | [bcb_sgs_pix](sources/bcb_sgs_pix.md) | SGS/API BCB - PIX | 4 | M | Implementar conector e pipeline |
| 54 | [bcb_sgs_reservas_internacionais](sources/bcb_sgs_reservas_internacionais.md) | SGS/API BCB - Reservas Internacionais | 4 | M | Implementar conector e pipeline |
| 55 | [bndes](sources/bndes.md) | BNDES financings | 4 | M | Completar e corrigir pipeline existente |
| 56 | [cvm](sources/cvm.md) | CVM proceedings | 4 | L | Completar e corrigir pipeline existente |
| 57 | [cvm_financial_statements](sources/cvm_financial_statements.md) | CVM DFP/ITR — Demonstrações Financeiras de Empresas Abertas | 4 | L | Implementar conector e pipeline |
| 58 | [cvm_full_ownership_chain](sources/cvm_full_ownership_chain.md) | CVM ownership chains | 4 | XL | Implementar conector e pipeline |
| 59 | [cvm_funds](sources/cvm_funds.md) | CVM fund registry | 4 | M | Completar e corrigir pipeline existente |
| 60 | [cvm_material_disclosures](sources/cvm_material_disclosures.md) | CVM Fatos Relevantes — Comunicados ao Mercado | 4 | L | Implementar conector e pipeline |
| 61 | [estban](sources/estban.md) | BCB ESTBAN balances | 4 | L | Implementar conector e pipeline |
| 62 | [holdings](sources/holdings.md) | Brasil IO holdings | 4 | M | Completar e corrigir pipeline existente |
| 63 | [ibge_ipca](sources/ibge_ipca.md) | IPCA/Inflação — Índice Nacional de Preços ao Consumidor Amplo | 4 | M | Implementar conector e pipeline |
| 64 | [if_data](sources/if_data.md) | BCB IF data indicators | 4 | L | Implementar conector e pipeline |
| 65 | [ipeadata](sources/ipeadata.md) | Ipeadata — Séries Econômicas e Indicadores Sociais | 4 | M | Implementar conector e pipeline |
| 66 | [pgfn](sources/pgfn.md) | PGFN divida ativa | 4 | L | Completar e corrigir pipeline existente |
| 67 | [previc_pension_funds](sources/previc_pension_funds.md) | PREVIC — Previdência Complementar Fechada | 4 | M | Implementar conector e pipeline |
| 68 | [receita_dirbi](sources/receita_dirbi.md) | Receita DIRBI | 4 | L | Implementar conector e pipeline |
| 69 | [renuncias](sources/renuncias.md) | Renuncias fiscais | 4 | M | Completar e corrigir pipeline existente |
| 70 | [siconfi](sources/siconfi.md) | SICONFI municipal finance | 4 | L | Completar e corrigir pipeline existente |
| 71 | [susep_insurance_market](sources/susep_insurance_market.md) | SUSEP insurance market | 4 | L | Implementar conector e pipeline |
| 72 | [ana_water_grants](sources/ana_water_grants.md) | ANA water grants | 5 | L | Implementar conector e pipeline |
| 73 | [ana_water_resources](sources/ana_water_resources.md) | Recursos Hídricos — ANA (Agência Nacional de Águas) | 5 | L | Implementar conector e pipeline |
| 74 | [anac_flights](sources/anac_flights.md) | ANAC Aviação Civil — Voos, Passageiros e Aeroportos | 5 | M | Implementar conector e pipeline |
| 75 | [anatel_access](sources/anatel_access.md) | ANATEL Telecomunicações — Banda Larga e Telefonia | 5 | M | Implementar conector e pipeline |
| 76 | [ancine_audiovisual](sources/ancine_audiovisual.md) | ANCINE/OCA — Audiovisual, Bilheteria e Produção | 5 | M | Implementar conector e pipeline |
| 77 | [aneel_energy](sources/aneel_energy.md) | ANEEL Energia Elétrica — Geração, Distribuição e Tarifas | 5 | M | Implementar conector e pipeline |
| 78 | [anm_mining_rights](sources/anm_mining_rights.md) | ANM mining rights | 5 | XL | Implementar conector e pipeline |
| 79 | [antaq_water_transport](sources/antaq_water_transport.md) | ANTAQ Transporte Aquaviário — Portos e Navegação | 5 | L | Implementar conector e pipeline |
| 80 | [anvisa_registrations](sources/anvisa_registrations.md) | ANVISA products | 5 | L | Implementar conector e pipeline |
| 81 | [bolsa_familia_bpc](sources/bolsa_familia_bpc.md) | Bolsa Familia and BPC | 5 | L | Implementar conector e pipeline |
| 82 | [caged](sources/caged.md) | CAGED labor movements | 5 | L | Completar e corrigir pipeline existente |
| 83 | [cprm_geology](sources/cprm_geology.md) | SGB-CPRM — Geologia, Recursos Minerais e Hidrogeologia | 5 | L | Implementar conector e pipeline |
| 84 | [datasus](sources/datasus.md) | DATASUS CNES | 5 | L | Completar e corrigir pipeline existente |
| 85 | [datasus_sih](sources/datasus_sih.md) | SIH — Sistema de Informações Hospitalares | 5 | L | Implementar conector e pipeline |
| 86 | [datasus_sim](sources/datasus_sim.md) | SIM — Sistema de Informações sobre Mortalidade | 5 | L | Implementar conector e pipeline |
| 87 | [datasus_sinan](sources/datasus_sinan.md) | SINAN — Sistema de Informação de Agravos de Notificação | 5 | L | Implementar conector e pipeline |
| 88 | [datasus_sinasc](sources/datasus_sinasc.md) | SINASC — Sistema de Informações sobre Nascidos Vivos | 5 | L | Implementar conector e pipeline |
| 89 | [datasus_tabnet](sources/datasus_tabnet.md) | TabNet — Ferramenta de Tabulação de Dados do SUS | 5 | L | Implementar conector e pipeline |
| 90 | [dnit_roads](sources/dnit_roads.md) | DNIT Malha Rodoviária — Infraestrutura Rodoviária Federal | 5 | L | Implementar conector e pipeline |
| 91 | [ibama](sources/ibama.md) | IBAMA embargos | 5 | L | Completar e corrigir pipeline existente |
| 92 | [ibge_municipal_gdp](sources/ibge_municipal_gdp.md) | PIB Municipal — Produto Interno Bruto dos Municípios | 5 | M | Implementar conector e pipeline |
| 93 | [ibge_pnad](sources/ibge_pnad.md) | PNAD Contínua — Pesquisa Nacional por Amostra de Domicílios | 5 | M | Implementar conector e pipeline |
| 94 | [icmbio_cnuc](sources/icmbio_cnuc.md) | ICMBio CNUC units | 5 | L | Implementar conector e pipeline |
| 95 | [incra_land_registry](sources/incra_land_registry.md) | INCRA Estrutura Fundiária — Imóveis Rurais e Assentamentos | 5 | L | Implementar conector e pipeline |
| 96 | [inep](sources/inep.md) | INEP school census | 5 | L | Completar e corrigir pipeline existente |
| 97 | [inep_enem](sources/inep_enem.md) | ENEM (Microdados) | 5 | L | Implementar conector e pipeline |
| 98 | [inep_higher_education](sources/inep_higher_education.md) | Censo da Educação Superior | 5 | M | Implementar conector e pipeline |
| 99 | [inpe_deter](sources/inpe_deter.md) | DETER — Alertas de Desmatamento em Tempo Real (INPE) | 5 | M | Implementar conector e pipeline |
| 100 | [inpe_fires](sources/inpe_fires.md) | Focos de Calor / Queimadas — INPE (BDQUEIMADAS) | 5 | M | Implementar conector e pipeline |
| 101 | [inpe_prodes](sources/inpe_prodes.md) | PRODES — Desmatamento Anual da Amazônia Legal (INPE) | 5 | M | Implementar conector e pipeline |
| 102 | [inpe_satellite](sources/inpe_satellite.md) | INPE Imagens de Satélite — Landsat, Sentinel, CBERS | 5 | XL | Implementar conector e pipeline |
| 103 | [inss_benefits](sources/inss_benefits.md) | Benefícios INSS — Aposentadorias, Pensões e Auxílios | 5 | M | Implementar conector e pipeline |
| 104 | [mapbiomas_alertas](sources/mapbiomas_alertas.md) | MapBiomas Alerta | 5 | XL | Acesso condicionado / restrito |
| 105 | [prf_accidents](sources/prf_accidents.md) | PRF Acidentes — Acidentes em Rodovias Federais | 5 | L | Implementar conector e pipeline |
| 106 | [rais](sources/rais.md) | RAIS aggregated labor | 5 | L | Completar e corrigir pipeline existente |
| 107 | [senatran_fleet](sources/senatran_fleet.md) | DENATRAN/RENAVAM — Frota de Veículos | 5 | M | Implementar conector e pipeline |
| 108 | [sicar_rural_registry](sources/sicar_rural_registry.md) | SiCAR rural registry | 5 | XL | Acesso condicionado / restrito |
| 109 | [sinesp_statistics](sources/sinesp_statistics.md) | SINESP — Estatísticas de Criminalidade | 5 | M | Implementar conector e pipeline |
| 110 | [carf_tax_appeals](sources/carf_tax_appeals.md) | CARF tax appeals | 6 | L | Implementar conector e pipeline |
| 111 | [cnciai_improbidade](sources/cnciai_improbidade.md) | CNIAI improbidade | 6 | L | Acesso condicionado / restrito |
| 112 | [cnj_justice_statistics](sources/cnj_justice_statistics.md) | Justiça em Números | 6 | M | Implementar conector e pipeline |
| 113 | [datajud](sources/datajud.md) | CNJ DataJud | 6 | L | Completar e corrigir pipeline existente |
| 114 | [eu_sanctions](sources/eu_sanctions.md) | EU sanctions | 6 | L | Completar e corrigir pipeline existente |
| 115 | [icij](sources/icij.md) | ICIJ offshore leaks | 6 | XL | Completar e corrigir pipeline existente |
| 116 | [interpol_red_notices](sources/interpol_red_notices.md) | Interpol red notices | 6 | L | Acesso condicionado / restrito |
| 117 | [ofac](sources/ofac.md) | OFAC sanctions | 6 | M | Completar e corrigir pipeline existente |
| 118 | [opensanctions](sources/opensanctions.md) | OpenSanctions global PEP | 6 | L | Completar e corrigir pipeline existente |
| 119 | [stf](sources/stf.md) | STF court data | 6 | L | Completar e corrigir pipeline existente |
| 120 | [stj_dados_abertos](sources/stj_dados_abertos.md) | STJ open data | 6 | L | Completar e corrigir pipeline existente |
| 121 | [un_sanctions](sources/un_sanctions.md) | UN sanctions | 6 | M | Completar e corrigir pipeline existente |
| 122 | [world_bank](sources/world_bank.md) | World Bank debarment | 6 | M | Completar e corrigir pipeline existente |
| 123 | [mides](sources/mides.md) | MiDES municipal procurement | 7 | XL | Completar e corrigir pipeline existente |
| 124 | [querido_diario](sources/querido_diario.md) | Querido Diario gazettes | 7 | XL | Completar e corrigir pipeline existente |
| 125 | [state_gazettes](sources/state_gazettes.md) | DOEs Estaduais — Diários Oficiais dos Estados | 7 | XL | Implementar conector e pipeline |
| 126 | [state_portal_ba](sources/state_portal_ba.md) | Bahia transparency portal | 7 | L | Implementar conector e pipeline |
| 127 | [state_portal_ce](sources/state_portal_ce.md) | Ceara transparency portal | 7 | L | Implementar conector e pipeline |
| 128 | [state_portal_go](sources/state_portal_go.md) | Goias transparency portal | 7 | L | Implementar conector e pipeline |
| 129 | [state_portal_mg](sources/state_portal_mg.md) | Minas Gerais transparency portal | 7 | L | Implementar conector e pipeline |
| 130 | [state_portal_pe](sources/state_portal_pe.md) | Pernambuco transparency portal | 7 | L | Implementar conector e pipeline |
| 131 | [state_portal_pr](sources/state_portal_pr.md) | Parana transparency portal | 7 | L | Implementar conector e pipeline |
| 132 | [state_portal_rs](sources/state_portal_rs.md) | Rio Grande do Sul transparency portal | 7 | L | Implementar conector e pipeline |
| 133 | [state_portal_sc](sources/state_portal_sc.md) | Santa Catarina transparency portal | 7 | L | Implementar conector e pipeline |
| 134 | [tce_am](sources/tce_am.md) | TCE Amazonas | 7 | L | Implementar conector e pipeline |
| 135 | [tce_ce](sources/tce_ce.md) | TCE Ceara | 7 | L | Implementar conector e pipeline |
| 136 | [tce_es](sources/tce_es.md) | TCE Espirito Santo | 7 | L | Implementar conector e pipeline |
| 137 | [tce_ma](sources/tce_ma.md) | TCE Maranhao | 7 | XL | Implementar conector e pipeline |
| 138 | [tce_mg](sources/tce_mg.md) | TCE Minas Gerais | 7 | L | Implementar conector e pipeline |
| 139 | [tce_pe](sources/tce_pe.md) | TCE Pernambuco | 7 | L | Implementar conector e pipeline |
| 140 | [tce_pi](sources/tce_pi.md) | TCE Piaui | 7 | L | Implementar conector e pipeline |
| 141 | [tce_pr](sources/tce_pr.md) | TCE Parana | 7 | L | Implementar conector e pipeline |
| 142 | [tce_rn](sources/tce_rn.md) | TCE Rio Grande do Norte | 7 | L | Implementar conector e pipeline |
| 143 | [tce_ro](sources/tce_ro.md) | TCE Rondonia | 7 | L | Implementar conector e pipeline |
| 144 | [tce_rs](sources/tce_rs.md) | TCE Rio Grande do Sul | 7 | L | Implementar conector e pipeline |
| 145 | [tce_se](sources/tce_se.md) | TCE Sergipe | 7 | L | Implementar conector e pipeline |
| 146 | [tce_sp](sources/tce_sp.md) | TCE Sao Paulo | 7 | L | Implementar conector e pipeline |
| 147 | [tce_to](sources/tce_to.md) | TCE Tocantins | 7 | L | Implementar conector e pipeline |
| 148 | [basedosdados_catalog](sources/basedosdados_catalog.md) | Base dos Dados | 8 | M | Descoberta de recursos do catálogo |
| 149 | [cadin](sources/cadin.md) | CADIN — Cadastro de Devedores do Governo Federal | 8 | M | Acesso condicionado / restrito |
| 150 | [cnj_bnmp](sources/cnj_bnmp.md) | BNMP 3.0 — Banco Nacional de Medidas Penais e Prisões | 8 | M | Acesso condicionado / restrito |
| 151 | [cnj_sisbajud](sources/cnj_sisbajud.md) | SISBAJUD — Sistema de Busca de Ativos do Poder Judiciário | 8 | XL | Acesso condicionado / restrito |
| 152 | [dados_gov_catalog](sources/dados_gov_catalog.md) | Portal Brasileiro de Dados Abertos | 8 | M | Descoberta de recursos do catálogo |
| 153 | [inde](sources/inde.md) | INDE — Infraestrutura Nacional de Dados Espaciais | 8 | M | Descoberta de recursos do catálogo |
| 154 | [siape](sources/siape.md) | SIAPE — Dados de Servidores Públicos Federais | 8 | M | Acesso condicionado / restrito |
| 155 | [state_portal_rj](sources/state_portal_rj.md) | Rio de Janeiro transparency portal | 8 | XL | Implementar conector e pipeline |
| 156 | [state_portal_sp](sources/state_portal_sp.md) | Sao Paulo transparency portal | 8 | L | Implementar conector e pipeline |
| 157 | [tce_al](sources/tce_al.md) | TCE Alagoas | 8 | XL | Implementar conector e pipeline |
| 158 | [tce_ap](sources/tce_ap.md) | TCE Amapa | 8 | XL | Implementar conector e pipeline |
| 159 | [tce_ba](sources/tce_ba.md) | TCE Bahia | 8 | L | Implementar conector e pipeline |
| 160 | [tce_go](sources/tce_go.md) | TCE Goias | 8 | L | Implementar conector e pipeline |
| 161 | [tce_ms](sources/tce_ms.md) | TCE Mato Grosso do Sul | 8 | L | Implementar conector e pipeline |
| 162 | [tce_mt](sources/tce_mt.md) | TCE Mato Grosso | 8 | L | Implementar conector e pipeline |
| 163 | [tce_pa](sources/tce_pa.md) | TCE Para | 8 | L | Implementar conector e pipeline |
| 164 | [tce_pb](sources/tce_pb.md) | TCE Paraiba | 8 | L | Acesso condicionado / restrito |
| 165 | [tce_rj](sources/tce_rj.md) | TCE Rio de Janeiro | 8 | L | Implementar conector e pipeline |
| 166 | [tce_rr](sources/tce_rr.md) | TCE Roraima | 8 | XL | Implementar conector e pipeline |
| 167 | [tce_sc](sources/tce_sc.md) | TCE Santa Catarina | 8 | L | Implementar conector e pipeline |
| 168 | [tesouro_catalog](sources/tesouro_catalog.md) | Tesouro Transparente | 8 | M | Descoberta de recursos do catálogo |
| 169 | [transparencia_api_catalog](sources/transparencia_api_catalog.md) | Portal da Transparência | 8 | M | Descoberta de recursos do catálogo |
