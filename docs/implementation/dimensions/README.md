# Materialização local de dimensões (F09)

`bracc_etl.dimensions.materialize` transforma referências explícitas em registros
distintos e referências por linha, em memória. Aceita território, órgão/UG/ente,
atividade econômica, moeda ou unidade e exercício. Códigos e versões são texto:
zeros iniciais permanecem e códigos numéricos são rejeitados. A repetição da
mesma chave com atributos divergentes falha; não há resolução por nome.

O resultado representa apenas as dimensões fornecidas, inclusive em linhas
agregadas. Não cria pessoas ou empresas, nem transforma estatísticas em
identidades. UF e exercício recebem validação estrutural, não certificação
contra cadastros oficiais. A entrada deve ser validada contra a fonte e a
versão territorial apropriadas antes da publicação. Não há aquisição,
crosswalk oficial, persistência ou integração com pipelines existentes.

As labels e chaves são propostas locais. Integração com o esquema e projeção
Neo4j depende de #5 e de revisão das chaves; esta entrega não demonstra carga
em grafo, acesso a fontes ou cobertura dos vocabulários oficiais. A base local
contém alterações ainda dependentes das PRs #23–#26.

O caminho de CSV agregado RAIS projeta dimensões e vínculos para `LaborStats`
quando cada linha fornece explicitamente `ibge_code`, `territorial_version`,
`cnae_version`, `unit_system`, `unit_code` e `exercise`, além de CNAE e UF.
Sem esses campos, a dimensão fica pendente; o fluxo legado de estatísticas
permanece disponível. Os metadados devem corresponder ao ano e à medida da
linha: uma unidade não representa automaticamente todas as suas medidas.
A projeção usa `MERGE` em transação e rejeita propriedades conflitantes. A
unicidade sob gravações concorrentes requer constraints de #5. A carga legada
e a projeção são transações separadas; falha de projeção exige reexecução.
