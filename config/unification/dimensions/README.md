# Dimensões observadas

A materialização recebe códigos e versões fornecidos explicitamente por cada
contrato de fonte. Nenhuma lista oficial foi adquirida ou certificada aqui.
`system`, `classification`, `jurisdiction` e `version` delimitam namespaces;
órgão, UG e ente têm papéis distintos. Moeda e outras unidades usam `Unit`
com sistema e código explícitos. Exercício é texto de quatro dígitos.

`Territory` requer sistema, tipo, código, versão territorial e UF; os quatro
primeiros compõem a chave e UF é atributo verificável. `EconomicActivity`
usa classificação, versão e código. `PublicBody` usa jurisdição, sistema,
papel, código e versão. Não há crosswalk implícito nem validação de existência
em tabela oficial. A identidade institucional precisa ser reconciliada por
crosswalk documentado, nunca por nome.

O módulo `crosswalk` oferece correspondência explícita contra uma tabela local
fornecida pelo chamador. A tabela exige fonte, versão e SHA-256 das entradas
serializadas em JSON canônico (UTF-8, chaves ordenadas, sem espaços); sem tabela
ou entrada correspondente, o resultado é pendente. A correspondência não prova
que a fonte seja oficial. Nenhuma tabela é fornecida nesta entrega. RAIS e Siconfi aceitam uma tabela
opcional `dimension_crosswalk`; o fato registra `code_validation_status`
como `pending` ou `matched_local` e a razão. A correspondência local não
certifica validação oficial nem substitui a reconciliação de snapshots U05.
Reprocessar uma chave com dimensões removidas pode conservar vínculos antigos;
a correção requer preservar histórico e continua pendente.

No Siconfi, linhas com o mesmo identificador são reconciliadas sem depender da
ordem: uma observação completa prevalece sobre uma incompleta compatível.
Valores ou metadados explícitos divergentes para o mesmo identificador causam
erro; a reconciliação de revisões históricas continua pendente de U05/U06.

O Siconfi registra também `public_body_validation_status` e
`public_body_validation_reason` separadamente: `pending` quando faltam dados
institucionais, tabela ou entrada; `matched_local` quando jurisdição, sistema,
papel, código e versão coincidem com a tabela local. Esse resultado não atesta
oficialidade nem confirma vínculos entre órgãos, UGs e entes.
O status geral `code_validation_status` só chega a `matched_local` se a
verificação de território/unidade e a institucional coincidirem; a verificação
territorial separada está em `territory_unit_validation_status` e
`territory_unit_validation_reason`, mesmo quando o órgão também está pendente.
