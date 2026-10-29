# Evidência municipal DTB e fixture Siconfi

O artefato oficial retido e rotulado `DTB_2023` foi conferido contra quatro códigos não vazios da fixture: 3550308 São Paulo (UF 35, linha física 3838), 3304557 Rio de Janeiro (33, 3249), 5300108 Brasília (53, 5576) e 2927408 Salvador (29, 2169). Uma linha com código vazio foi excluída explicitamente. A receipt registra URL solicitada/final, HTTP 200, captura UTC `2026-10-29T01:47:18.591611+00:00` e hash correspondente; não houve refetch.

Hashes e campos capturados: [JSON da evidência](evidence/dtb-2023-siconfi.json). Replay integral, opt-in manual com ZIP privado: `python scripts/check_f09_dtb2023.py /caminho/privado/DTB_2023.zip`. Testes default usam ZIP/ODS sintético pequeno offline e fixture factual versionada, sem depender do raw privado. O sintético não é evidência factual. O ZIP bruto não é versionado.

`DTB_2023` é rótulo, `DATA BASE: 22/11/2024` é data interna e `Last-Modified: 18/12/2024` é metadado HTTP. Página oficial corrente, versão retida e rótulo não são a mesma afirmação. Nada aqui certifica edição territorial fiscal 2023 ou compatibilidade histórica; nome/UF não valida valores, órgãos/UG ou crosswalk de produção.

Verificador offline sem rede, com limites de tamanho, hashes do artefato/membro/XML e rejeição de DTD/entidades. Nenhuma dependência nova.
