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
