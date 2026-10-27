# Brasil em Rede: início da construção

Estado inicial em 2026-10-27: código herdado em validação, catálogo de 169
fontes, plano individual de aquisição/cadastro/ligações e nenhum novo conector
ou carga nacional certificado por esta publicação.

## Objetivo do primeiro sistema utilizável

Uma pessoa deve conseguir consultar uma empresa, identificar a origem e a data
de cada informação e navegar pelos vínculos documentados com sanções e
contratos públicos. A primeira entrega usa um recorte pequeno e reproduzível.
Expandir a cobertura exige repetir os mesmos critérios por fonte.

O [plano de ação](action-plan.md) organiza a execução em cinco rodadas, com
primeira fila de quatro tarefas, limite de duas implementações em andamento e
oito gates para concluir a v0.1. Ele reaproveita os marcos e planos técnicos abaixo.

## Marcos

| Marco | Resultado e condição de conclusão |
|---|---|
| M0 — Fundação verificável | CI executado e auditorias de dependências resolvidas; IDs, documentos, esquema, aquisição, loader e orquestração corrigidos; falhas explícitas; migração ensaiada; nenhuma alegação de carga sem evidência |
| M1 — Piloto CNPJ, sanções e contratos | Download de partições delimitadas, manifestos, carga idempotente, ligações por chave exata e consulta pela API/interface com origem e data; teste de ponta a ponta |
| M2 — Expansão das fontes | Executar as oito ondas do plano; aprovar individualmente download, carga e cruzamentos de cada fonte elegível; documentar bloqueios de acesso |

As tarefas iniciais estão no [backlog versionado](../../config/github_backlog.json).
Os itens F01–F10 têm escopo e critérios completos na
[arquitetura](../implementation/architecture.md). A expansão tem uma
[ficha para cada fonte](../implementation/README.md) e
[21 planos de cruzamentos](../implementation/crossings.md).

A [unificação das bases](../unification/README.md) detalha como as fontes
convergem para identidades, fatos e consultas comuns. Suas doze etapas reutilizam
as issues de fundação/piloto existentes e incluem o mapa de todas as fontes e
o procedimento de migração/publicação. Os novos serviços estão propostos, sem
implantação realizada por esse plano.

## Ordem de execução

1. Registrar a linha de base dos testes e fechar as falhas que impedem o desenvolvimento.
2. Resolver IDs e documentos antes de consolidar identidades no grafo.
3. Ensaiar migração e reconciliar o esquema; implementar aquisição e escrita verificáveis.
4. Validar ligações, orquestração, dimensões e configuração no recorte do piloto.
5. Entregar CNPJ, sanções e contratos com teste de ponta a ponta e evidência consultável.
6. Expandir conforme dependências das fontes, sem promover planejamento a implementação.

## Definição de entrega de uma fonte

- Endpoint/exportação e condições de acesso documentados.
- Partição, período, bytes e hash registrados em manifesto.
- Normalização testada com casos válidos, inválidos e mudança de esquema.
- Escrita que falha explicitamente, reconcilia contagens e pode ser repetida.
- Entidades e relações com chave, origem, data e regra de ligação verificáveis.
- Casos negativos que mantenham homônimos e documentos parciais separados.
- Consulta pela API e evidência de execução anexada à issue correspondente.

Código, primeiro download, primeira carga e cruzamentos são entregas distintas.
As fontes restritas e os portais de descoberta seguem sua ficha; não recebem
um downloader genérico nem o estado de carga concluída.

## Rotina de contribuição

Escolher uma issue, criar uma branch `codex/<assunto>` ou equivalente, abrir uma
PR pequena e executar os checks do escopo. A revisão deve conferir os critérios
de aceite e a evidência, além do código. Não há merge, deploy, publicação de
imagens ou ingestão agendada automática na configuração inicial.

Os workflows anteriores foram preservados como
[referência histórica](../history/workflows/README.md). O CI ativo valida
API, ETL, frontend, segurança e consistência do catálogo. Um check verde do
catálogo não comprova disponibilidade dos portais ou dados carregados.

## Linha de base de qualidade

Lint, tipos e testes de API, ETL e interface são executados na preparação
da publicação. A auditoria inicial do frontend reportou 17 alertas
(11 altos e 2 críticos), registrados na tarefa F00. A auditoria de segurança
continua configurada para falhar diante desses alertas; não há release de produção suportada.
