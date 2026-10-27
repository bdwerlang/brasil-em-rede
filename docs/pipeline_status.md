# Pipeline Status

Generated from `docs/source_registry_br_v1.csv` (as-of UTC: 2026-10-27T02:22:10Z).

Status buckets:
- `implemented_loaded`: implemented and loaded in registry.
- `implemented_partial`: implemented but partial/stale/not fully loaded.
- `blocked_external`: implemented but externally blocked.
- `not_built`: not implemented in public repo.

| Source ID | Pipeline ID | Status Bucket | Load State | Source Format | Required Input | Known Blockers |
|---|---|---|---|---|---|---|
| ana_water_grants | ana_water_grants | not_built | not_loaded | api_json | API payload from https://dados.gov.br/dados/conjuntos-dados/ana | Water use rights |
| ana_water_resources | ana_water_resources | not_built | not_loaded | api_json | API payload from https://dadosabertos.ana.gov.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| anac_aviation_concessions | anac_aviation_concessions | not_built | not_loaded | api_json | API payload from https://dados.gov.br/dados/conjuntos-dados/anac | Aviation contracts |
| anac_flights | anac_flights | not_built | not_loaded | file_batch | data/anac_flights/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| anatel_access | anatel_access | not_built | not_loaded | file_batch | data/anatel_access/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| anatel_telecom_licenses | anatel_telecom_licenses | not_built | not_loaded | api_json | API payload from https://dados.gov.br/dados/conjuntos-dados/anatel | Telecom operators |
| ancine_audiovisual | ancine_audiovisual | not_built | not_loaded | api_json | API payload from https://www.gov.br/ancine/pt-br/oca | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| aneel_concessions | aneel_concessions | not_built | not_loaded | api_json | API payload from https://dadosabertos.aneel.gov.br/ | Energy concessions |
| aneel_energy | aneel_energy | not_built | not_loaded | api_json | API payload from https://dadosabertos.aneel.gov.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| anm_mining_rights | anm_mining_rights | not_built | not_loaded | api_json | API payload from https://dados.gov.br/dados/conjuntos-dados/anm | Mining rights and permits |
| anp_royalties | anp_royalties | not_built | not_loaded | api_json | API payload from https://dados.gov.br/dados/conjuntos-dados/anp | Oil and gas royalties |
| ans_health_plans | ans_health_plans | not_built | not_loaded | api_json | API payload from https://dados.gov.br/dados/conjuntos-dados/ans | Health insurance operators |
| antaq_port_contracts | antaq_port_contracts | not_built | not_loaded | api_json | API payload from https://dados.gov.br/dados/conjuntos-dados/antaq | Port concessions |
| antaq_water_transport | antaq_water_transport | not_built | not_loaded | file_batch | data/antaq_water_transport/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| antt_transport_concessions | antt_transport_concessions | not_built | not_loaded | api_json | API payload from https://dados.gov.br/dados/conjuntos-dados/antt | Transport concessions |
| anvisa_registrations | anvisa_registrations | not_built | not_loaded | api_json | API payload from https://dados.gov.br/dados/conjuntos-dados/anvisa | Regulatory registrations |
| b3_trades | b3_trades | not_built | not_loaded | file_batch | data/b3_trades/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| basedosdados_catalog | basedosdados_catalog | not_built | not_loaded | api_json | API payload from https://basedosdados.org/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: API Key. |
| bcb | bcb | implemented_loaded | loaded | file_batch | data/bcb/* | - |
| bcb_liquidacao | bcb_liquidacao | not_built | not_loaded | file_batch | data/bcb_liquidacao/* | Regulatory actions |
| bcb_sgs_base_monetaria | bcb_sgs_base_monetaria | not_built | not_loaded | api_json | API payload from https://dadosabertos.bcb.gov.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| bcb_sgs_cambio | bcb_sgs_cambio | not_built | not_loaded | api_json | API payload from https://dadosabertos.bcb.gov.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| bcb_sgs_credito | bcb_sgs_credito | not_built | not_loaded | api_json | API payload from https://dadosabertos.bcb.gov.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| bcb_sgs_indices | bcb_sgs_indices | not_built | not_loaded | api_json | API payload from https://dadosabertos.bcb.gov.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| bcb_sgs_juros | bcb_sgs_juros | not_built | not_loaded | api_json | API payload from https://dadosabertos.bcb.gov.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| bcb_sgs_meios_pagamento | bcb_sgs_meios_pagamento | not_built | not_loaded | api_json | API payload from https://dadosabertos.bcb.gov.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| bcb_sgs_pix | bcb_sgs_pix | not_built | not_loaded | api_json | API payload from https://dadosabertos.bcb.gov.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| bcb_sgs_reservas_internacionais | bcb_sgs_reservas_internacionais | not_built | not_loaded | api_json | API payload from https://dadosabertos.bcb.gov.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| bndes | bndes | implemented_loaded | loaded | file_batch | data/bndes/* | - |
| bolsa_familia_bpc | bolsa_familia_bpc | not_built | not_loaded | file_batch | data/bolsa_familia_bpc/* | High volume masked identities |
| cadin | cadin | not_built | not_loaded | api_json | API payload from https://cadin.pgfn.gov.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: OAuth 2.0 (Gov.br Conecta) / Gov.br (consulta cidadã). |
| caged | caged | implemented_partial | partial | file_batch | data/caged/* | Aggregate-only implementation |
| camara | camara | implemented_loaded | loaded | api_json | API payload from https://dadosabertos.camara.leg.br/ | - |
| camara_inquiries | camara_inquiries | implemented_partial | partial | api_json | API payload from https://dadosabertos.camara.leg.br/ | Sessions still low |
| camara_votes_bills | camara_votes_bills | not_built | not_loaded | api_json | API payload from https://dadosabertos.camara.leg.br/api/v2 | Legislative behavior |
| carf_tax_appeals | carf_tax_appeals | not_built | not_loaded | file_batch | data/carf_tax_appeals/* | Tax litigation |
| ceaf | ceaf | implemented_loaded | loaded | file_batch | data/ceaf/* | - |
| cepim | cepim | implemented_loaded | loaded | file_batch | data/cepim/* | - |
| cnciai_improbidade | cnciai_improbidade | not_built | not_loaded | api_json | API payload from https://www.cnj.jus.br/sistemas/cnciai/ | Misconduct convictions |
| cnj_bnmp | cnj_bnmp | not_built | not_loaded | api_json | API payload from https://portalbnmp.cnj.jus.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida (consulta básica) / Token (API PDPJ-Br). |
| cnj_justice_statistics | cnj_justice_statistics | not_built | not_loaded | file_batch | data/cnj_justice_statistics/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| cnpj | cnpj | implemented_loaded | loaded | file_batch | data/cnpj/* | - |
| cnpj_simples | cnpj_simples | not_built | not_loaded | file_batch | data/cnpj_simples/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| comprasnet | comprasnet | implemented_partial | partial | file_batch | data/comprasnet/* | Needs freshness backfill |
| cpgf | cpgf | implemented_loaded | loaded | file_batch | data/cpgf/* | - |
| cprm_geology | cprm_geology | not_built | not_loaded | api_json | API payload from https://geosgb.sgb.gov.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| cvm | cvm | implemented_loaded | loaded | file_batch | data/cvm/* | - |
| cvm_directors | cvm_directors | not_built | not_loaded | file_batch | data/cvm_directors/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| cvm_financial_statements | cvm_financial_statements | not_built | not_loaded | api_json | API payload from https://dados.cvm.gov.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| cvm_full_ownership_chain | cvm_full_ownership_chain | not_built | not_loaded | file_batch | data/cvm_full_ownership_chain/* | Shareholder graph expansion |
| cvm_funds | cvm_funds | implemented_loaded | loaded | file_batch | data/cvm_funds/* | - |
| cvm_material_disclosures | cvm_material_disclosures | not_built | not_loaded | file_batch | data/cvm_material_disclosures/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| dados_gov_catalog | dados_gov_catalog | not_built | not_loaded | api_json | API payload from https://dados.gov.br/swagger-ui/index.html | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| datajud | datajud | blocked_external | not_loaded | api_json | API payload from https://api-publica.datajud.cnj.jus.br/ | Credentials not fully operational in prod |
| datasus | datasus | implemented_loaded | loaded | file_batch | data/datasus/* | - |
| datasus_sih | datasus_sih | not_built | not_loaded | file_batch | data/datasus_sih/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| datasus_sim | datasus_sim | not_built | not_loaded | file_batch | data/datasus_sim/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| datasus_sinan | datasus_sinan | not_built | not_loaded | file_batch | data/datasus_sinan/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| datasus_sinasc | datasus_sinasc | not_built | not_loaded | file_batch | data/datasus_sinasc/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| datasus_tabnet | datasus_tabnet | not_built | not_loaded | web_portal | Portal export/scrape output under data/datasus_tabnet/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| dnit_roads | dnit_roads | not_built | not_loaded | api_json | API payload from https://servicos.dnit.gov.br/dadosabertos/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| dou | dou | implemented_loaded | loaded | bigquery_table | BigQuery query/export result | - |
| estban | estban | not_built | not_loaded | file_batch | data/estban/* | Banking aggregates |
| eu_sanctions | eu_sanctions | implemented_loaded | loaded | file_batch | data/eu_sanctions/* | - |
| fnde_transfers | fnde_transfers | not_built | not_loaded | file_batch | data/fnde_transfers/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| holdings | holdings | implemented_loaded | loaded | file_batch | data/holdings/* | - |
| ibama | ibama | implemented_loaded | loaded | file_batch | data/ibama/* | - |
| ibge_census | ibge_census | not_built | not_loaded | api_json | API payload from https://servicodados.ibge.gov.br/api/v3/agregados | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| ibge_geosciences | ibge_geosciences | not_built | not_loaded | api_json | API payload from https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| ibge_ipca | ibge_ipca | not_built | not_loaded | api_json | API payload from https://servicodados.ibge.gov.br/api/v3/agregados | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| ibge_municipal_gdp | ibge_municipal_gdp | not_built | not_loaded | api_json | API payload from https://servicodados.ibge.gov.br/api/v3/agregados | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| ibge_pnad | ibge_pnad | not_built | not_loaded | api_json | API payload from https://servicodados.ibge.gov.br/api/v3/agregados | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| icij | icij | implemented_loaded | loaded | file_batch | data/icij/* | - |
| icmbio_cnuc | icmbio_cnuc | not_built | not_loaded | file_batch | data/icmbio_cnuc/* | Protected areas |
| if_data | if_data | not_built | not_loaded | file_batch | data/if_data/* | Institution KPIs |
| incra_land_registry | incra_land_registry | not_built | not_loaded | api_json | API payload from https://acervofundiario.incra.gov.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Gov.br (Silver ou Gold) para portais interativos / Não requerida para downloads. |
| inde | inde | not_built | not_loaded | api_json | API payload from https://visualizador.inde.gov.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| inep | inep | implemented_loaded | loaded | file_batch | data/inep/* | - |
| inep_enem | inep_enem | not_built | not_loaded | file_batch | data/inep_enem/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| inep_higher_education | inep_higher_education | not_built | not_loaded | file_batch | data/inep_higher_education/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| inpe_deter | inpe_deter | not_built | not_loaded | api_json | API payload from http://terrabrasilis.dpi.inpe.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| inpe_fires | inpe_fires | not_built | not_loaded | api_json | API payload from https://terrabrasilis.dpi.inpe.br/queimadas/bdqueimadas/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| inpe_prodes | inpe_prodes | not_built | not_loaded | api_json | API payload from http://terrabrasilis.dpi.inpe.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| inpe_satellite | inpe_satellite | not_built | not_loaded | web_portal | Portal export/scrape output under data/inpe_satellite/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Cadastro gratuito. |
| inss_benefits | inss_benefits | not_built | not_loaded | file_batch | data/inss_benefits/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| interpol_red_notices | interpol_red_notices | not_built | not_loaded | api_json | API payload from https://www.interpol.int/How-we-work/Notices/Red-Notices | Requires key |
| ipeadata | ipeadata | not_built | not_loaded | api_json | API payload from http://www.ipeadata.gov.br/api/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| leniency | leniency | implemented_loaded | loaded | file_batch | data/leniency/* | - |
| mapbiomas_alertas | mapbiomas_alertas | not_built | not_loaded | api_json | API payload from https://alerta.mapbiomas.org/api | Deforestation alerts |
| mides | mides | implemented_loaded | loaded | bigquery_table | BigQuery query/export result | - |
| ofac | ofac | implemented_loaded | loaded | file_batch | data/ofac/* | - |
| opensanctions | opensanctions | implemented_loaded | loaded | file_batch | data/opensanctions/* | - |
| pep_cgu | pep_cgu | implemented_loaded | loaded | file_batch | data/pep_cgu/* | - |
| pgfn | pgfn | implemented_loaded | loaded | file_batch | data/pgfn/* | - |
| pncp | pncp | implemented_partial | partial | api_json | API payload from https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao | Freshness SLA pending |
| previc_pension_funds | previc_pension_funds | not_built | not_loaded | file_batch | data/previc_pension_funds/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida (dados públicos) / Gov.br (CADPREVIC restrito). |
| prf_accidents | prf_accidents | not_built | not_loaded | file_batch | data/prf_accidents/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| querido_diario | querido_diario | implemented_partial | partial | api_json | API payload from https://queridodiario.ok.org.br/api | Text availability gap |
| rais | rais | implemented_loaded | loaded | bigquery_table | BigQuery query/export result | - |
| receita_dirbi | receita_dirbi | not_built | not_loaded | file_batch | data/receita_dirbi/* | Tax benefit declarations |
| renuncias | renuncias | implemented_loaded | loaded | file_batch | data/renuncias/* | - |
| sanctions | sanctions | implemented_loaded | loaded | file_batch | data/sanctions/* | - |
| senado | senado | implemented_loaded | loaded | api_json | API payload from https://www12.senado.leg.br/dados-abertos | - |
| senado_cpis | senado_cpis | implemented_partial | partial | api_json | API payload from https://www12.senado.leg.br/dados-abertos | Needs richer sessions and requirements |
| senado_votes_bills | senado_votes_bills | not_built | not_loaded | api_json | API payload from https://legis.senado.leg.br/dadosabertos | Legislative behavior |
| senatran_fleet | senatran_fleet | not_built | not_loaded | file_batch | data/senatran_fleet/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| siafi_budget_execution | siafi_budget_execution | not_built | not_loaded | api_json | API payload from https://apidatalake.tesouro.gov.br/docs/sadipem/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. The reference points to SADIPem documentation; the SIAFI endpoint requires review before ingestion. |
| siape | siape | not_built | not_loaded | api_json | API payload from https://www.gov.br/conecta/catalogo/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: OAuth. |
| sicar_rural_registry | sicar_rural_registry | not_built | not_loaded | file_batch | data/sicar_rural_registry/* | Property boundaries and owners |
| siconfi | siconfi | implemented_partial | partial | api_json | API payload from https://apidatalake.tesouro.gov.br/docs/siconfi/ | No CNPJ direct links |
| siga_brasil | siga_brasil | not_built | not_loaded | file_batch | data/siga_brasil/* | Federal budget traces |
| sinesp_statistics | sinesp_statistics | not_built | not_loaded | file_batch | data/sinesp_statistics/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| siop | siop | implemented_partial | partial | api_json | API payload from https://www.siop.planejamento.gov.br/ | Author linkage limited |
| siorg | siorg | not_built | not_loaded | api_json | API payload from https://siorg.gov.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| state_gazettes | state_gazettes | not_built | not_loaded | api_json | API payload from https://queridodiario.ok.org.br/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. Reference points to Querido Diario; state-gazette coverage has not been verified. |
| state_portal_ba | state_portal_ba | not_built | not_loaded | web_portal | Portal export/scrape output under data/state_portal_ba/ | State expenses and contracts |
| state_portal_ce | state_portal_ce | not_built | not_loaded | web_portal | Portal export/scrape output under data/state_portal_ce/ | State expenses and contracts |
| state_portal_go | state_portal_go | not_built | not_loaded | web_portal | Portal export/scrape output under data/state_portal_go/ | State expenses and contracts |
| state_portal_mg | state_portal_mg | not_built | not_loaded | web_portal | Portal export/scrape output under data/state_portal_mg/ | State expenses and contracts |
| state_portal_pe | state_portal_pe | not_built | not_loaded | web_portal | Portal export/scrape output under data/state_portal_pe/ | State expenses and contracts |
| state_portal_pr | state_portal_pr | not_built | not_loaded | web_portal | Portal export/scrape output under data/state_portal_pr/ | State expenses and contracts |
| state_portal_rj | state_portal_rj | not_built | not_loaded | web_portal | Portal export/scrape output under data/state_portal_rj/ | State expenses and contracts |
| state_portal_rs | state_portal_rs | not_built | not_loaded | web_portal | Portal export/scrape output under data/state_portal_rs/ | State expenses and contracts |
| state_portal_sc | state_portal_sc | not_built | not_loaded | web_portal | Portal export/scrape output under data/state_portal_sc/ | State expenses and contracts |
| state_portal_sp | state_portal_sp | not_built | not_loaded | api_json | API payload from https://www.transparencia.sp.gov.br/ | State expenses and contracts |
| stf | stf | implemented_loaded | loaded | bigquery_table | BigQuery query/export result | - |
| stj_dados_abertos | stj_dados_abertos | implemented_partial | not_loaded | file_batch | data/stj_dados_abertos/* | Pipeline exists in the public runner; requires data/stj_dados_abertos/decisoes.csv. No load verified by this catalogue update. |
| susep_insurance_market | susep_insurance_market | not_built | not_loaded | file_batch | data/susep_insurance_market/* | Insurance entities |
| tce_al | tce_al | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_al/ | State audit procurement |
| tce_am | tce_am | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_am/ | State audit procurement |
| tce_ap | tce_ap | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_ap/ | State audit procurement |
| tce_ba | tce_ba | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_ba/ | State audit procurement |
| tce_ce | tce_ce | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_ce/ | State audit procurement |
| tce_es | tce_es | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_es/ | State audit procurement |
| tce_go | tce_go | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_go/ | State audit procurement |
| tce_ma | tce_ma | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_ma/ | State audit procurement |
| tce_mg | tce_mg | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_mg/ | State audit procurement |
| tce_ms | tce_ms | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_ms/ | State audit procurement |
| tce_mt | tce_mt | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_mt/ | State audit procurement |
| tce_pa | tce_pa | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_pa/ | State audit procurement |
| tce_pb | tce_pb | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_pb/ | State audit procurement |
| tce_pe | tce_pe | not_built | not_loaded | api_json | API payload from https://sistemas.tce.pe.gov.br/ | State audit procurement |
| tce_pi | tce_pi | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_pi/ | State audit procurement |
| tce_pr | tce_pr | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_pr/ | State audit procurement |
| tce_rj | tce_rj | not_built | not_loaded | api_json | API payload from https://dados.tce.rj.gov.br/ | State audit procurement |
| tce_rn | tce_rn | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_rn/ | State audit procurement |
| tce_ro | tce_ro | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_ro/ | State audit procurement |
| tce_rr | tce_rr | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_rr/ | State audit procurement |
| tce_rs | tce_rs | not_built | not_loaded | file_batch | data/tce_rs/* | State audit procurement |
| tce_sc | tce_sc | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_sc/ | State audit procurement |
| tce_se | tce_se | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_se/ | State audit procurement |
| tce_sp | tce_sp | not_built | not_loaded | api_json | API payload from https://transparencia.tce.sp.gov.br/ | State audit procurement |
| tce_to | tce_to | not_built | not_loaded | web_portal | Portal export/scrape output under data/tce_to/ | State audit procurement |
| tcu | tcu | implemented_loaded | loaded | file_batch | data/tcu/* | - |
| tesouro_catalog | tesouro_catalog | not_built | not_loaded | api_json | API payload from https://apidatalake.tesouro.gov.br/docs/sadipem/ | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. Catalogue landing page; the reference points to SADIPem, not every Tesouro dataset. |
| tesouro_emendas | tesouro_emendas | implemented_partial | not_loaded | file_batch | data/tesouro_emendas/* | Pipeline exists in the public runner; requires data/tesouro_emendas/emendas_tesouro.csv. No load verified by this catalogue update. |
| transferegov | transferegov | implemented_loaded | loaded | file_batch | data/transferegov/* | - |
| transparencia | transparencia | implemented_loaded | loaded | file_batch | data/transparencia/* | - |
| transparencia_api_catalog | transparencia_api_catalog | not_built | not_loaded | api_json | API payload from https://api.portaldatransparencia.gov.br/swagger-ui/index.html | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: API Key. |
| tse | tse | implemented_loaded | loaded | file_batch | data/tse/* | - |
| tse_ballot_boxes | tse_ballot_boxes | not_built | not_loaded | file_batch | data/tse_ballot_boxes/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| tse_bens | tse_bens | implemented_loaded | loaded | file_batch | data/tse_bens/* | - |
| tse_electorate | tse_electorate | not_built | not_loaded | file_batch | data/tse_electorate/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| tse_filiados | tse_filiados | implemented_loaded | loaded | file_batch | data/tse_filiados/* | - |
| tse_results | tse_results | not_built | not_loaded | file_batch | data/tse_results/* | Brazil Visible catalogue reference; no local pipeline or load verified. Authentication: Não requerida. |
| un_sanctions | un_sanctions | implemented_loaded | loaded | file_batch | data/un_sanctions/* | - |
| viagens | viagens | implemented_loaded | loaded | file_batch | data/viagens/* | - |
| world_bank | world_bank | implemented_loaded | loaded | file_batch | data/world_bank/* | - |
