# Plano de ação para concluir as entregas do Brasil em Rede

Data: **2026-10-27**. Estado: fila preparada; implementação ainda a executar.
O [plano de unificação](../unification/README.md) define o desenho técnico.
Este documento define **o que executar agora, em que ordem e quando encerrar**.

## Dois resultados com critérios de conclusão

**v0.1 — primeiro sistema utilizável:** instalação local reproduzível e jornada
empresa → contratos/sanções → evidência, com recorte real de CNPJ, sanções e
contratos públicos, mais uma dimensão territorial e uma série agregada.
Demonstração sintética e dados reais têm identificação e destinos distintos.
O resultado pode ser ausência de vínculo; os testes não exigem encontrar uma
empresa real que tenha simultaneamente sanção e contrato.

**Expansão do catálogo:** executar as oito ondas das 169 fichas, com aceite de
aquisição, carga e ligações por dataset. Portais de descoberta produzem recursos
catalogados; fontes restritas mantêm acesso condicionado e segregação. Um
bloqueio externo fica explícito e não conta como fonte carregada. O encerramento
do marco integral exige decidir e registrar o tratamento de cada pendência.

A conclusão da v0.1 tem um gate próprio: [A04 / #22](https://github.com/bdwerlang/brasil-em-rede/issues/22).
A expansão continua em [#16](https://github.com/bdwerlang/brasil-em-rede/issues/16)
e no [épico #17](https://github.com/bdwerlang/brasil-em-rede/issues/17).
Atualização contínua das fontes passa a ser operação de uma versão entregue.

## Sequência de execução

| Rodada | Trabalho e tarefas existentes | Saída verificável |
|---|---|---|
| **R1 — Destravar o desenvolvimento** | Inventário #19; auditorias Python #20 e frontend #21, sob #1; aliases #2. U01 e início de U02 | Ambiente e partições documentados; auditorias tratadas com evidência; 169 IDs de catálogo e 47 módulos sem aliases ambíguos |
| **R2 — Fechar a fundação necessária** | Documentos/identidade #3/#4; esquema #5; aquisição #6; escrita #7; ligações #8; orquestração #9; dimensões #10; ambiente #11. U02–U07 | Contratos e persistência implementados, preflight coerente, falha de lote explícita, normalização/projeção repetíveis em fixtures e bancos descartáveis |
| **R3 — Fazer o recorte real funcionar** | CNPJ #12, sanções #13, contratos #14; dimensão IBGE e série do plano; primeiras consultas de #15. U08/U09 | Partições reais verificadas, manifests e cobertura; ligações corretas ou não resolvidas; dados distintos dos exemplos sintéticos |
| **R4 — Concluir a v0.1** | API/interface #15; compatibilidade/migração #4; ambiente/recuperação #11; homologação #22. U10/U11 | Jornada no navegador, integração real, instalação limpa e recuperação demonstradas; relatório de aceite e release preparada |
| **R5 — Expandir com o mesmo padrão** | Ondas de #16 e etapas restantes do épico #17. U12 | Aceite individual das fontes elegíveis, restrições explícitas e cruzamentos habilitados somente com dados/testes próprios |

As rodadas organizam trabalho; não são semanas ou datas prometidas. O primeiro
inventário e as quatro tarefas iniciais medem esforço e capacidade para estimar
as rodadas seguintes. Os marcos M0/M1/M2 continuam existentes: M0 só encerra
quando todos os seus aceites, incluindo migração/recuperação, estiverem demonstrados.

## Primeira fila executável

| Ordem | Tarefa | Papel proposto | Entrega que encerra a tarefa |
|---|---|---|---|
| 1 | [A01 / #19 — Inventário e recorte](https://github.com/bdwerlang/brasil-em-rede/issues/19) | Dados/infraestrutura | Relatório de recursos, serviços/volumes, dados presentes, pendências e contratos iniciais do piloto; não exige iniciar banco ou carga |
| 2 | [A02 / #20 — Auditorias Python](https://github.com/bdwerlang/brasil-em-rede/issues/20) | Backend | Relatórios API e ETL, atualização revisada dos lockfiles e checks relevantes; auditoria de uma parte não oculta falha da outra |
| 3 | [A03 / #21 — Auditoria frontend](https://github.com/bdwerlang/brasil-em-rede/issues/21) | Frontend | Atualização revisada, auditoria, lint, tipos, testes e build; regressões de navegação verificadas |
| 4 | [F01 / #2 — IDs das fontes](https://github.com/bdwerlang/brasil-em-rede/issues/2) | Dados/backend | Mapa versionado para os 47 módulos existentes, IDs das 169 entradas e aliases legados preservados; teste de ambiguidades |

Começar por **#19 e #20**, seguidas de #21 e #2 conforme as dependências e a
capacidade disponível. A equipe alvo de cada rodada tem de três a cinco subagentes
para demandas independentes, ajustada à capacidade real. O agente principal
coordena e revisa; subagentes executam as alterações. Cada entrega tem executor,
branch e worktree próprios, com arquivos de trabalho isolados. Registrar a
responsabilidade e a PR na issue.

As tarefas #20/#21 detalham a F00; #19 é parte de F10. Seus pais conservam o
escopo restante. As demais tarefas ficam bloqueadas até os pré-requisitos do
roadmap estarem cumpridos; `ready` significa pronta para iniciar, não iniciada.
Ao terminar R1, desbloquear os próximos itens conforme seus pré-requisitos e a
capacidade disponível.

## Condições para a v0.1 estar pronta

| Gate | Evidência necessária para encerrar |
|---|---|
| **G1 — Instalação limpa** | Um clone novo executa o procedimento documentado; prontidão verifica banco, catálogo e configuração; reinício preserva dados. Demo usa volume isolado e nenhum reset global como passo padrão |
| **G2 — Perfil e sessão coerentes** | Flags de build do frontend e runtime da API correspondem ao perfil publicado; login/sessão e rotas habilitadas funcionam; funcionalidades fora do aceite têm navegação coerente com sua disponibilidade |
| **G3 — Recorte real comprovado** | CNPJ, sanções e contratos têm manifests íntegros, período, partições e cobertura declarados; dimensão/série preservam unidade e competência; nenhuma evidência sintética é apresentada como aquisição real |
| **G4 — Identidade e evidência** | Matriz/filiais, raiz/QSA, homônimos e fontes sobrepostas exercitados; resultado abre fonte, versão, data e registro de suporte; ausência de confiança é informada, sem percentual inventado |
| **G5 — Operação repetível** | Mesma carga não duplica fatos; interrupção retoma; erro no último lote impede promoção; origem, contadores e pendências permanecem verificáveis |
| **G6 — Jornada útil e honesta** | Busca → empresa → contrato/sanção → evidência funciona no navegador; vazio, erro e atualização são tratados; números exibidos correspondem a cobertura e execução comprovadas |
| **G7 — Teste com os componentes reais** | Integração em bancos descartáveis e teste pelo navegador executados, com relatório; unitários/mocks e integração `skipped` não substituem esse aceite |
| **G8 — Recuperação ensaiada** | Backup consistente, restore e rollback demonstrados; estado mutável de usuários/investigações preservado quando habilitado; cursores e requisições mantêm a versão dos dados |

Segurança das dependências precisa estar tratada e não pode ser ocultada para
obter CI verde. Risco sem correção disponível exige análise, mitigação e decisão
revisadas; não é exceção automática por pertencer a uma dependência transitiva.
O gate #22 consolida G1–G8 e os aceites da fundação e do piloto.

## Pendências concretas que entram nas tarefas

| Achado atual | Ação e responsável no backlog |
|---|---|
| Auditorias pip/npm falham; ETL pode deixar de ser auditado após erro da API | #20/#21 corrigem e reportam as partes separadamente; #1 coordena o fechamento |
| Imagem da API não inclui o catálogo; configuração de path é incompatível com esse layout | #11 deve prover catálogo/configuração na imagem e testar metadata no contêiner, além do código local |
| Flags do frontend são de build; Compose passa parte delas somente em runtime e omite flags públicas da API | #11/#15 devem alinhar build/runtime e testar o perfil distribuído |
| `/health` confirma o processo sem provar banco/catálogo prontos | #11 deve distinguir liveness e prontidão efetiva, com falhas verificáveis |
| Interface ainda tem volumes herdados, versão v1.0 e contagem de catálogo confundida com carga | #15 deve usar dados da execução/cobertura, distinguir catalogado/carregado e exibir versão real |
| Cache de métricas sem validade clara e confiança de vínculo assumida como 100% quando ausente | #15 deve definir validade/release do cache e estado não informado, sem inventar precisão |
| Badge de fonte não oferece sozinho o registro/data de suporte | #15 deve entregar navegação da evidência e seus limites de acesso |
| Rotas adicionais, como emendas, têm URLs e autenticação incompatíveis com os IDs atuais | #15 deve disponibilizar na v0.1 apenas jornadas que passaram pelo aceite, preservando as demais no backlog |
| Seed e rotinas antigas podem resetar o grafo; backup herdado não comprova restore Community | #11/#22 isolam demo, bloqueiam uso indevido e exigem recuperação ensaiada |

Evidências de código: [Dockerfile API](../../api/Dockerfile),
[catálogo da API](../../api/src/bracc/services/source_registry.py),
[Compose](../../docker-compose.yml), [Dockerfile frontend](../../frontend/Dockerfile),
[textos da interface](../../frontend/src/i18n.ts),
[seed](../../infra/scripts/seed-dev.cypher) e
[backup](../../infra/scripts/backup-neo4j.sh). Esses achados permanecem pendentes
até as respectivas PRs e evidências; este documento não os corrige.

## Rotina de execução e encerramento

1. Escolher a próxima tarefa `ready` conforme a capacidade disponível; registrar
   executor, resultado esperado, dependências, branch e worktree da implementação.
2. Abrir PR focada e executar checks do escopo. Atualização Python e frontend
   têm PRs próprias; mudanças de identidade/esquema incluem migração/reversão.
3. Anexar evidência reproduzível e limitações à issue. Encerrar somente quando
   seus critérios de aceite forem demonstrados; documentação sozinha não
   comprova implementação, download, carga ou funcionamento da interface.
4. Quando houver falha externa, registrar motivo e próximo teste, e puxar outra
   tarefa independente conforme a capacidade disponível. Não promover estado
   de sucesso.
5. Ao fechar uma rodada, demonstrar sua saída e atualizar o épico #17. Reavaliar
   estimativa e desbloquear a próxima fila pelos aceites alcançados.

Status de execução: `ready` → responsabilidade/PR registrada → revisão →
concluído com evidência. `blocked` identifica pré-requisito aberto; `tracking`
identifica coordenação e não ocupa vaga de implementação. `priority:p0` é a
primeira rodada; `priority:p1` é o núcleo da v0.1; `priority:p2` é expansão.

## Ponto de partida e publicação

A [PR #18](https://github.com/bdwerlang/brasil-em-rede/pull/18) reúne os planos e
continua em rascunho. As correções independentes da primeira fila podem partir
de `main`; mudanças que dependam dos contratos propostos referenciam a versão
do desenho adotado e incorporam seu teste. O planejamento não deve impedir a
correção das auditorias já conhecidas.

Na verificação de 2026-10-27, a proteção de `main` exige API, ETL e frontend.
Auditorias de segurança não são checks obrigatórios nessa configuração e o
teste de integração atual foi pulado. Portanto, merge permitido ou CI parcial
verde não comprovam aceite da v0.1. #20/#21/#22 devem fechar essas lacunas com
evidência; a política de checks obrigatórios será reconciliada antes da release.

Preparar a release v0.1 depois de G1–G8, com commit, configuração, cobertura,
limitações e instruções reproduzíveis. Hospedagem pública é uma etapa posterior,
com ambiente e capacidade definidos. As fontes brutas volumosas, credenciais e
relatórios sensíveis continuam fora do repositório.

## Acompanhamento do progresso

Registrar tarefas aceitas por rodada; fontes com **download**, **carga** e
**ligações** validados separadamente; defeitos bloqueadores; resultados dos
testes; cobertura real e tempo de recuperação medido. As contagens do catálogo
e os estados históricos `loaded` não são progresso operacional desta execução.

O projeto avança quando uma saída verificável entra na versão e sua tarefa é
encerrada. Depois da v0.1, aplicar o mesmo processo a cada onda e ao escopo de
expansão acordado, mantendo as pendências externas visíveis.
