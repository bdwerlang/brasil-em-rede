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
versão territorial apropriadas antes da publicação. Não há aquisição nem
crosswalk oficial; a correspondência com catálogo local não comprova oficialidade.

RAIS e Siconfi podem projetar dimensões no Neo4j usando as labels e chaves do
esquema integrado. Os ensaios usam dados sintéticos e não demonstram acesso a
fontes reais nem cobertura dos vocabulários oficiais. A reconciliação de
vínculos antigos em reprocessamentos e a integração das métricas de carga da
projeção permanecem pendentes.

O caminho de CSV agregado RAIS projeta dimensões e vínculos para `LaborStats`
quando cada linha fornece explicitamente `ibge_code`, `territorial_version`,
`cnae_version`, `unit_system`, `unit_code` e `exercise`, além de CNAE e UF.
Sem esses campos, a dimensão fica pendente; o fluxo legado de estatísticas
permanece disponível. Os metadados devem corresponder ao ano e à medida da
linha: uma unidade não representa automaticamente todas as suas medidas.
A projeção usa `MERGE` em transação e rejeita propriedades conflitantes. A
unicidade sob gravações concorrentes requer constraints de #5. A carga legada
e a projeção são transações separadas; falha de projeção exige reexecução.

No Siconfi, a projeção exige por fato os campos textuais `cod_ibge`,
`exercicio`, `uf`, `versao_territorial`, `tipo_territorio` (`municipio` ou
`uf`), `unidade_sistema` e `unidade_codigo`. A dimensão institucional é
opcional e exige também `orgao_jurisdicao`, `orgao_sistema`, `orgao_papel`
(`orgao`, `ug` ou `ente`), `orgao_codigo` e `orgao_versao`. Dados incompletos
ficam pendentes; códigos não são conferidos contra registros oficiais. A
mesma chave de fato com dimensões divergentes gera erro. A declaração agregada
não cria nem vincula `Company` a partir do CNPJ da linha. A projeção requer
as constraints da entrega #5 para unicidade em execução concorrente.

Esta mudança interrompe a criação automática de `Company` e da relação
`DECLAROU_FINANCA` pelo Siconfi. Consultas que dependem desse vínculo exigem
adaptação às dimensões explícitas; vínculos antigos já persistidos não são
removidos por esta entrega e requerem migração planejada separadamente.

## Proveniência oficial consultada (2026-10-28)

Esta revisão documenta referências oficiais e limites de validação; não baixou
nem incorporou partições de dados reais. Os links abaixo são evidência de
referência, não evidência de que os crosswalks locais foram obtidos desses
artefatos.

| Caminho realmente usado | Campos/vocabulários observados | Unidade e período | Fonte oficial / estado de validação |
|---|---|---|---|
| RAIS `rais_2022_aggregated.csv` | CNAE subclass, UF, contagem de estabelecimentos, vínculos totais/CLT/estatutários, média. Fixture contém só CNAE e UF; campos IBGE, versão territorial/CNAE, exercício e unidade não estão nela, logo dimensão/crosswalk fica pendente. | Métricas têm grãos distintos: estabelecimentos, vínculos e média de vínculos por estabelecimento. Uma única `unit_code` não está ligada a cada medida; requer contrato por medida antes de validar. | MTE RAIS 2022 e comunicado de correção CNAE. `cnae_version`/snapshot do artefato não identificados; nenhuma existência individual CNAE validada. |
| RAIS arquivo bruto `RAIS_ESTAB_PUB*.txt*` | CNAE 2.0 Subclasse e UF numérica; projeção bruta atual agrega por CNAE/UF sem dimensões territoriais versionadas. UF numérica desconhecida agora falha em vez de virar sigla. | Qtd Vínculos Ativos/CLT/Estatutários e contagem de estabelecimentos; versão do arquivo e ano-base não são transportados para dimensões. | MTE/PDET RAIS. Mapa IBGE estrutural das UFs; código municipal, CNAE existente e revisão RAIS continuam pendentes de crosswalk/manifesto oficial. |
| Siconfi DCA `dca_*.csv` / fixture `dca_2023.json` | `cod_ibge`, `ente`, `exercicio`, `conta`, `coluna`, `valor`; fixture JSON não tem UF, versão territorial, sistema/tipo de unidade ou identificação institucional. `instituicao` é órgão responsável pela publicação e fica separado de `municipality`; não se infere órgão/UG de seu nome. | Metadados oficiais DCA declaram valores nominais em reais e exercício como ano. `fiscal_year` e `Unit` estruturais só são crosswalkados quando campos são fornecidos; sem metadados, status pendente. | Tesouro/Siconfi DCA e Tabela de Entes. `cod_ibge` confronta estrutura de sete dígitos/prefixo UF, mas tabela DTB/edição usada não está ligada ao fato; DCA não fornece UG nem versão territorial. |

Na fixture `dca_2023.json`, os códigos São Paulo `3550308`, Rio de Janeiro
`3304557`, Brasília `5300108` e Salvador `2927408` aparecem na [página corrente
de códigos do IBGE](https://www.ibge.gov.br/explica/codigos-dos-municipios.php).
Essa coincidência de consulta não prova que o arquivo represente a DTB de 2023,
nem valida outros códigos da fonte.

Os exemplos no conjunto de testes que contêm metadados completos são sintéticos;
`v1`, `2022`, CNAE `2.0`, unidades `pessoas`/`BRL` não são declaração de
versão oficial de partição. Materializar uma unidade para todas as medidas RAIS
sem um vínculo medida→unidade explícito permanece bloqueado.

- IBGE, [códigos dos municípios](https://www.ibge.gov.br/explica/codigos-dos-municipios.php)
  e [Divisão Territorial Brasileira](https://www.ibge.gov.br/geociencias/organizacao-do-territorio/estrutura-territorial/23701-divisao-territorialbrasileira).
  A página oficial descreve códigos municipais em sete posições e códigos de
  UF em duas; estruturalmente, o prefixo municipal deve coincidir com o código da UF e, para território tipo UF, o código deve corresponder à sigla. A página DTB lista a edição 2025. O acesso HTTP direto automatizado
  local retornou 403, mas as páginas oficiais foram consultadas via navegador.
  Nenhum arquivo de tabela foi baixado ou comparado aos códigos dos fatos.
  Uma versão territorial deve identificar o artefato/ano usado; `uf` isolada
  não certifica correspondência com o código municipal.
- IBGE/CONCLA, [estrutura detalhada da CNAE 2.0](https://concla.ibge.gov.br/images/concla/documentacao/EstruturaDetalhadaCNAE_CNAEFiscal2_Atualizada.pdf)
  e [introdução às subclasses](https://concla.ibge.gov.br/images/concla/documentacao/CNAE20_Subclasses_Introducao.pdf).
  CNAE 2.0 separa seção (letra), divisão (2 dígitos), grupo (3), classe (4
  dígitos mais DV) e subclasse (7 dígitos incluindo DV). O formato não prova
  existência, vigência ou nível sem
  tabela/versionamento declarado. Os documentos oficiais foram consultados via
  navegador; nenhum catálogo de códigos foi baixado e comparado aos fatos.
- MTE, [página da RAIS 2022](https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/rais/rais-2022) e [comunicado da correção da CNAE na RAIS 2022](https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/estatisticas-trabalho/comunicados/correcao-cnae-rais22), publicado em 2023 e atualizado em 2026. O comunicado registra atualização da RAIS 2022 entre 30/04 e 02/05/2024 e redistribuição de vínculos entre CNAEs. O pipeline não identifica o snapshot de entrada; não se certifica que um artefato local represente a revisão corrigida.
- Tesouro Nacional, [documentação da API Siconfi](https://apidatalake.tesouro.gov.br/docs/siconfi/), [metadados DCA](https://www.tesourotransparente.gov.br/ckan/dataset/26fab98f-8cd2-4d34-9176-eef0fb4a296e/resource/1c5351ca-fcb4-4077-9bd9-95bdec8a204d/download/metadadosdca.pdf)
  e [catálogo DCA de entes](https://www.tesourotransparente.gov.br/ckan/dataset/api-dca-entes). Os metadados DCA definem exercício como ano, `cod_ibge` como código do ente, `instituicao` como órgão responsável pelo envio/publicação, UF e valores nominais em reais; não definem versão territorial nem código de UG. O catálogo DCA informa atualização em 28/05/2025. Nome de instituição não valida município, UG ou versão territorial.
- Tesouro Nacional, [metadados da Tabela de Entes](https://www.tesourotransparente.gov.br/ckan/dataset/8bc0bf13-9ee8-47b9-bcf8-9a7318d46d0b/resource/67a231ce-31b2-4071-b779-b47696987c98/download/metadadostabelaentes.pdf)
  e [catálogo da API](https://www.tesourotransparente.gov.br/ckan/dataset/api-tabela-entes). O catálogo registra atualização em 10/10/2019; campos incluem código IBGE, ente, capital, região, UF e esfera. Não há UG. Nome institucional no DCA não deve ser convertido em identidade/código de órgão ou UG.

`matched_local` continua significando apenas que os campos explícitos coincidem
com as entradas e proveniência declaradas no crosswalk fornecido. A validação
não verifica autenticidade institucional, atualidade do arquivo, compatibilidade
entre revisão de RAIS e CNAE, associação órgão–UG–ente, nem existência oficial
de códigos. O exercício agora participa da correspondência local junto das
dimensões de cada fato RAIS/Siconfi; continua sem uma fonte oficial autônoma que
certifique o exercício.
