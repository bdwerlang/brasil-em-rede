# M0 / A01 — inventário e contrato inicial do piloto

Observação em **2026-10-27**. Escopo: [issue #19](https://github.com/bdwerlang/brasil-em-rede/issues/19),
primeira rodada de #11/U01. Este relatório registra uma inspeção somente de
leitura e um recorte **proposto, sem aquisição, carga ou ligações executadas**.
Não encerra M0 nem todo o escopo de F10.

## O que foi observado

A inspeção usou metadados do Docker, versões de ferramentas, nomes de processos,
recursos do sistema e a árvore de arquivos de entrada do checkout operacional.
Não iniciou serviços, abriu conexão a bancos, leu `.env`, montou volumes,
executou seed ou baixou conjuntos de dados. Consultas externas foram limitadas
a páginas oficiais, dicionários e documentação OpenAPI.

| Item | Observação | Limite da evidência |
|---|---|---|
| Python / uv | Python 3.12.3; uv 0.10.9 | Versões disponíveis; não certifica dependências instaladas ou auditorias de #20 |
| Node / npm | Node 26.9.0; npm 11.19.1 | README pede Node 22; alinhar e testar em #21/#11 antes de afirmar reprodutibilidade |
| Git | 2.43.0 | Checkout de referência do código: `b4f0014` |
| Docker / Compose | Docker 29.1.3; Compose 2.37.1 | Cliente e daemon responderam à inspeção passiva |
| Serviços deste projeto | Contêineres de Neo4j, API e frontend existentes e parados | Sem teste de saúde, versão executável do banco, integridade ou consulta |
| Neo4j | Imagem declarada `neo4j:5-community`; volume de dados existente | Tag mutável; versão binária, bancos internos, esquema, conteúdo e origem dos dados não inspecionados |
| Outros bancos | Processos PostgreSQL/Redis e volumes de outros contextos foram identificados | Sem conexão, consulta, atribuição de dados ao projeto ou reutilização |
| Clientes adicionais | SQLite 3.45.1 e psql 16.15 disponíveis; DuckDB e cypher-shell ausentes do PATH | Cliente instalado não prova serviço correspondente disponível |
| CPU, RAM e disco | Metadados e disponibilidade pontual registrados em evidência privada | Sem benchmark, pico de uso, orçamento de recursos ou estimativa de capacidade |
| Entradas locais | `data/demo/synthetic_graph.json` e placeholders CNPJ; nenhum arquivo em `infra/neo4j/import` | Dentro desses diretórios acessíveis, não foram encontrados dumps reais CSV/ZIP/Parquet; não é inspeção de todos os discos, backups ou volumes |
| Dados sintéticos | Fixture JSON identificada pelo README, metadados e gerador de demo; seed Cypher de desenvolvimento presente | A existência do seed não comprova que foi executado; conteúdo do volume Neo4j permanece desconhecido |

Detalhes de infraestrutura, inventário de arquivos, retornos dos comandos e
metadados de volumes ficam em `audit-results/m0/inventory/`, ignorado pelo Git,
com acesso local restrito. Nenhum hostname, IP, identificador de contêiner,
caminho absoluto do host, total de infraestrutura privada ou dado pessoal deve
ser anexado à PR. Revisar a sanitização antes de publicar qualquer evidência.

## Contratos de planejamento

Os arquivos [CNPJ](../../config/source_contracts/cnpj.json),
[sanções](../../config/source_contracts/sanctions.json) e
[contratos PNCP](../../config/source_contracts/pncp.json) seguem o
[schema v1](../../config/source_contracts/source-contract.schema.json).
São especificações revisáveis. Nenhum runner atual os consome, e
`execution_enabled: false` registra essa condição; não funciona como trava dos
scripts herdados. Aquisição, carga e ligações têm evidências separadas e estão
todas marcadas como não executadas.

| Fonte / período proposto | Partição e seleção inicial | Aquisição admitida e estado observado |
|---|---|---|
| CNPJ / snapshot mensal `2026-09` | `Empresas0.zip`, `Estabelecimentos0.zip`, `Socios0.zip` e tabelas de referência explicitadas no contrato. Até 1.000 estabelecimentos ordenados por CNPJ canônico cuja raiz também esteja em Empresas0; sócios apenas quando encontrados em Socios0 | Exportação oficial RFB. Listagem e disponibilidade desses arquivos ainda não confirmadas; a URL legada da página de orientação redirecionou para login nesta consulta |
| CEIS e CNEP / snapshot-alvo `2026-10-26` | Um arquivo de cada lista, com manifesto independente; preservar a cobertura integral de cada arquivo adquirido e projetar empresas por documento completo | Páginas oficiais de download e dicionários acessíveis. Os seletores de datas e as URLs finais dos arquivos não foram resolvidos; data-alvo ainda depende de disponibilidade |
| PNCP / publicação em `2026-09-01` | `/v1/contratos`, páginas de 50 registros, no máximo 10 páginas na primeira rodada; preservar também partes fora da projeção PJ para contabilizar exclusões | OpenAPI oficial consultada, sem consultar registros de contratos. Endpoint de listagem e parâmetros confirmados na documentação; operação e cobertura reais continuam pendentes |

Esses números limitam a experiência proposta, não estimam tamanho da fonte ou
capacidade. Um único shard CNPJ pode exigir download e descompressão grandes;
o limite de 1.000 saídas não limita os bytes brutos. Os shards das três famílias
não garantem a mesma população: a amostra pode ser pequena ou vazia, e QSA não
é completo. Atingir o teto PNCP sem esgotar as páginas implica cobertura parcial,
nunca conclusão do dia. Não há garantia de interseção entre as três fontes;
resultados vazios e vínculos pendentes devem permanecer explícitos.

As datas são propostas fixas para revisão. Se uma partição não existir ou
exceder o orçamento que ainda será medido, registrar o bloqueio e revisar o
contrato versionado antes de outra seleção. Não substituir silenciosamente por
“mais recente”, espelhos, consulta de CPF ou outra fonte. Usar apenas o acesso
público oficial; interromper diante de autenticação não prevista, CAPTCHA,
restrição de acesso, 401/403 ou limite de orçamento.

O CNPJ é identificador textual, inclusive alfanumérico; normalização/validação
dependem da fundação comum. Não unir por nome, raiz de CNPJ, CPF mascarado ou
documento parcial. Sanção preserva lista, ato, órgão e vigência; contrato preserva
fornecedor, comprador e referência oficial. Uma publicação de licitação não
comprova contrato. O adaptador herdado `comprasnet` lê contratos PNCP; reconciliar
fonte, namespace e formato antes de utilizá-lo, sem alegar cobertura do legado
ComprasNet a partir deste recorte.

## Acesso, limites e custos

- **RFB:** o [endereço cadastrado](https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/)
  não pôde ser acessado pela ferramenta de consulta. A
  [página legada de orientação](https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/cadastros/consultas/dados-publicos-cnpj)
  redirecionou para autenticação. Isso é um limite desta verificação, não prova
  de indisponibilidade geral nem autorização para contornar o acesso. Confirmar
  listagem, leiaute, licença/condições e limites do recurso oficial antes da aquisição.
- **CGU:** os portais de download [CEIS](https://portaldatransparencia.gov.br/download-de-dados/ceis)
  e [CNEP](https://portaldatransparencia.gov.br/download-de-dados/cnep) oferecem seleção
  de data e apontam seus dicionários. Formato, codificação e delimitador do arquivo
  escolhido ainda precisam ser inspecionados. A alternativa de API não está
  selecionada: o [cadastro oficial](https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email)
  exige token via Gov.br e publica 700 requisições/min entre 00h e 06h, 400 nos demais
  horários e 180 para APIs restritas. Não se deve aplicar essa cota aos arquivos
  de download nem presumir credenciais disponíveis.
- **PNCP:** a [OpenAPI de consulta](https://pncp.gov.br/api/consulta/v3/api-docs)
  informa `dataInicial`/`dataFinal` em `yyyyMMdd`, `pagina >= 1` e `tamanhoPagina`
  entre 10 e 500. O recorte escolhe 50. O
  [manual de integração v2.6](https://pncp.gov.br/manual/pt-br/latest/singlehtml/index.html)
  distingue consulta pública de operações de manutenção autenticadas; o
  [recurso de detalhe](https://pncp.gov.br/manual/pt-br/latest/contrato_empenho/consultar_contrato_ou_empenho.html)
  documenta consulta por órgão, ano e sequencial. Não foi encontrada cota por
  minuto nessas referências. Confirmar tratamento de paginação, vazios,
  retificações, fusos e limites efetivos antes de adquirir.

Não foi verificada tabela de cobrança nas referências consultadas; não há custo
monetário de aquisição contratado ou estimado. Tráfego, armazenamento, CPU,
backups e eventuais serviços externos ainda precisam de medição. Não usar API
comercial ou espelho pago por substituição implícita.

Para futura aquisição, propõe-se concorrência 1, no máximo 10 requisições/min e
até 3 retentativas por recurso, respeitando `Retry-After`; são limites locais
conservadores, não cotas oficiais. Persistir checkpoint e parar após esgotá-los,
sem repetição infinita. Confirmar condições de acesso/reutilização do recurso
final em cada fonte antes de habilitar execução.

## Isolamento e instrução de operação

**Durante A01, executar apenas inspeções passivas e validações de arquivos. Não
iniciar bancos, baixar dados, executar seeds, resetar, migrar ou reutilizar
volumes.** Os seguintes destinos são reservados para implementação posterior;
nada foi criado no Docker por esta tarefa:

| Uso | Arquivos relativos ao repositório, ignorados pelo Git | Instância / volume novos propostos |
|---|---|---|
| Demonstração | Fixture de origem `data/demo/`; artefatos de execução em `audit-results/local/demo/` | Instância `bracc-m0-demo`; volume `bracc-m0-demo-data` |
| Piloto com dados reais | `audit-results/local/pilot/<source_id>/{raw,staged,manifests}/` | Instância `bracc-m0-pilot`; volume `bracc-m0-pilot-data` |

Cada instância Community deve ter seu próprio volume e usar o banco interno
`neo4j`; não se presume suporte a múltiplos bancos de usuário. Também separar
credenciais, rede, portas e configuração de API. Não montar o volume existente
em nenhum desses destinos. Validar previamente que os nomes propostos ainda
estão livres. Só definir `COMPOSE_PROJECT_NAME` é insuficiente: os Compose e
scripts herdados contêm `container_name`/`docker exec` fixos. Exigir uma
configuração e um runner corrigidos, com destino efetivamente verificado, antes
de qualquer execução futura. A configuração atual não certifica esse isolamento.

**Não usar os comandos abaixo como instalação, diagnóstico ou primeiro passo
do piloto.** Uma decisão futura explícita sobre uma instância descartável,
backup/restore e escopo de descarte deve preceder qualquer operação destrutiva.

| Entrada herdada | Efeito identificado por leitura |
|---|---|
| `make seed`, `infra/scripts/seed-dev.sh` e `seed-dev.cypher` | Seed inicia com `MATCH (n) DETACH DELETE n`; shell pode atingir contêiner fixo |
| `make bootstrap-demo`, `make bootstrap-full` e `scripts/bootstrap_public_demo.sh` | Iniciam stack e chamam o seed destrutivo, inclusive no perfil demo |
| `make bootstrap-all`, `scripts/bootstrap_all_public.sh` e `scripts/run_bootstrap_all.py` | Iniciam stack; runner oferece reset e pode executá-lo antes da ingestão |
| `make bootstrap-all-noninteractive` ou `--yes-reset` | Selecionam reset do grafo explicitamente |
| `docker compose down -v`, remoção/prune de volumes ou reset/migração direta | Podem destruir estado persistente; fora do escopo A01 |

`--no-reset` não torna um bootstrap uma inspeção passiva: ele ainda pode iniciar
serviços e escrever dados. Esta é uma instrução operacional explícita; a
proteção automatizada dos scripts pertence à correção de orquestração de #11.

## Medições pendentes e próximo passo

Antes de estimar capacidade, custo ou datas, medir em um destino isolado e com
orçamento acordado:

1. Disponibilidade e tamanho comprimido das partições exatas; autenticação e
   condições de acesso; limites observados sem testes de carga no provedor.
2. Expansão ZIP/CSV, bytes por linha e campo, codificação, schema, temporários,
   disco livre/reservado e retenção de bruto, manifesto e backup.
3. Tempo de aquisição, extração, transformação e escrita; pico de RAM/CPU/disco,
   throughput por lote, índices e crescimento de nós/relações.
4. Contagens por etapa, rejeições, documentos válidos/parciais, páginas faltantes,
   duplicatas, interseção real das amostras e vínculos sem correspondente.
5. Custo e duração de repetição idempotente, falha parcial/retomada,
   reconciliação, backup, restore e rollback; latência da consulta pela API.

O próximo trabalho de aquisição depende de contratos e acesso confirmados,
destino isolado implementado e fundação de IDs, manifesto, normalização e
loader. Depois registrar por recurso: URL pública sem segredo, partição,
período, instante de aquisição, bytes, SHA-256, schema e contagens; guardar
payloads e documentos pessoais fora do Git. Só promover cobertura após validar
aquisição, carga e ligações separadamente. O catálogo não substitui essa prova.

## Validação desta entrega

Verificar os três JSON contra o schema Draft 2020-12, conferir que continuam
desabilitados e sem evidência de aquisição/carga/ligação, revisar links locais,
caminhos ignorados, `git diff --check` e sanitização do diff. Nenhum teste de
runtime, integração, benchmark ou estado de banco é alegado por esses checks.
