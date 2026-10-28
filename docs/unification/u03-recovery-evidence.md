# Evidências de recuperação U03 e segurança de backfill futuro

Este documento registra evidências sintéticas locais para a issue [#36](https://github.com/bdwerlang/brasil-em-rede/issues/36). Ele complementa o ensaio de integração U03 anterior com uma etapa de perda destrutiva da origem e reconciliação dos objetos no sistema de arquivos. Não autoriza nem certifica migração, restauração ou backfill em ambiente real.

## Reproduzir o ensaio de recuperação

Na raiz do repositório, execute:

```sh
bash etl/tests/control/recovery.sh
```

O harness constrói a imagem PostgreSQL do repositório e usa contêineres descartáveis com nomes exclusivos, `--network none` e nenhuma porta publicada no host. Ele aplica as migrations 001–005 a um cluster de origem sintético e novo. Os arquivos temporários ficam em `.hermes-run/tmp`, ignorado e local ao worktree. A saída final é registrada em `.hermes-run/logs/U03-recovery-evidence.log`, também local e ignorada. O trap remove somente os contêineres, a imagem e o diretório da execução identificados pelo próprio harness.

A fixture contém linhas dos schemas de controle e de aplicação, bytes de objetos raw e Parquet, chaves e hashes SHA-256 do catálogo, registros de aquisição, execuções, tentativas e linhagem de leases, manifests e vínculos de artefatos, qualidade, projeções, entradas de outbox reconhecida e pendente, releases verificadas anterior e ativa, identidade de worker, associação entre papéis e privilégios. O manifest de `part-b`, cuja outbox permanece pendente, não pertence a nenhuma das releases verificadas; ambas incluem apenas o manifest de `part-a`, com IDs de release e alvos de grafo distintos. O pacote de backup contém `pg_dumpall --globals-only`, dump do banco em formato customizado, arquivo do armazenamento, inventários determinísticos do banco e dos objetos e um manifesto SHA-256. O dump global e os artefatos de banco e armazenamento usam modo 0600, pois o dump global pode conter hashes de senha e dados de papéis.

Após o backup, o harness remove o contêiner de origem e sua árvore de arquivos, confirma que ambos não existem mais e não consulta novamente a origem. A restauração usa o pacote de backup em um novo cluster PostgreSQL e uma nova árvore de arquivos, distintos da origem. O harness compara todas as linhas de `control` e `app`, o DDL dos schemas, atributos selecionados de papéis e associações, versões das migrations e releases ativa e anterior. Para cada chave do catálogo, calcula o hash dos bytes restaurados e exige igualdade exata com o hash esperado; também rejeita objetos ausentes ou extras. Após confirmar que a outbox pendente de `part-b` foi restaurada e que seu manifest está fora das releases anterior e ativa, o projetor a reconhece no banco restaurado e o harness confirma o ack. Também verifica o comportamento de leitor e worker e os limites de menor privilégio.

O harness imprime evidências PASS e remove apenas recursos com seu identificador exclusivo de execução. Use somente recursos locais descartáveis; não o aponte para banco, diretório de armazenamento, contêiner Docker ou imagem de produção existentes.

## O que o ensaio de integração anterior da PR #39 comprovou

O `etl/tests/control/integration.sh` existente restaura os papéis e um dump customizado do banco em um segundo cluster PostgreSQL descartável. Ele verifica a versão das migrations e do schema, a release ativa, a linhagem entre execução e tentativa, os vínculos entre manifest, tentativa e artefato, os vínculos entre release e manifest, estado selecionado da identidade e dos privilégios do worker e o comportamento de leitor, worker e projetor.

Esse ensaio manteve o cluster de origem disponível para comparação. Não simulou a perda destrutiva da origem, não arquivou nem restaurou bytes de artefatos externos, não reconciliou cada objeto do catálogo com o inventário do armazenamento e não comparou todo o estado de aplicação, controle, releases e papéis. Os dados usados eram sintéticos. Nem aquele ensaio nem este novo harness certificam armazenamento real, Neo4j, imagem de produção, desempenho/carga ou consistência de backup online em produção. Os ensaios existentes `integration.sh` e `backfill.sh` não fazem parte deste novo comando e não precisam ser repetidos para executá-lo.

## Migrations 004 e 005: propriedades e riscos restantes

A migration 004 exige as tabelas temporárias `u03_attempt_backfill` e `u03_manifest_backfill` na mesma sessão PostgreSQL da migration. Ela bloqueia `control.run_attempt` e `control.partition_manifest` em modo `ACCESS EXCLUSIVE`. Em uma transação, verifica valores nulos, IDs duplicados, cobertura bidirecional exata das tentativas e manifests existentes e concordância entre partição e token de fencing do manifest e da tentativa mapeada. Em seguida, atualiza as linhas antigas, registra referências imutáveis às evidências e instala constraints, funções e triggers. Qualquer erro reverte integralmente a transação da migration.

A verificação de evidência exige apenas uma referência de texto não vazia. Ela não comprova que a evidência seja autêntica ou esteja retida de forma independente. O UUID do proprietário mapeado não é uma chave estrangeira para `control.worker_identity`. Revisores devem conferir ambos com evidências independentes preservadas; não deduza nenhum dos valores.

A migration 005 adquire bloqueios `SHARE ROW EXCLUSIVE` nas tabelas de fonte, dataset, partição e artefato. Em uma transação, valida a linhagem do catálogo, a classe de acesso, o formato da chave do objeto e a consistência do `sha256` armazenado com a própria chave. Ela não lê o armazenamento externo nem recalcula o hash dos bytes do artefato. Depois instala triggers de identidade do artefato e congelamento dos registros ancestrais. Qualquer divergência verificada no catálogo aborta essa transação. Ela é separada da migration 004: uma pode ser confirmada e a seguinte falhar, deixando o banco em uma versão intermediária até a recuperação ou uma continuação autorizada separadamente.

O bloqueio `ACCESS EXCLUSIVE` da migration 004 impede leituras e escritas comuns em `control.run_attempt` e `control.partition_manifest` durante a transação. Os bloqueios `SHARE ROW EXCLUSIVE` da migration 005 conflitam com escritores e certos DDL, mas permitem leituras comuns com bloqueio `ACCESS SHARE`. A espera por bloqueios pode formar filas, prolongar indisponibilidade ou aumentar a pressão de capacidade; na migration 005, não se deve concluir que todas as leituras comuns serão bloqueadas. As migrations não definem timeout operacional de bloqueio ou de comando. Um dump global do cluster pode conter hashes de senha e deve ser protegido. O estado do banco e os bytes dos objetos exigem congelamento coordenado de escrita ou uma barreira de snapshot documentada; backups do banco e do armazenamento feitos em momentos independentes podem divergir. O rollback consiste em restaurar um conjunto de backup verificado. Não presuma que exista migration reversa para identidades preenchidas ou histórico de artefatos.

## Checklist de aprovação para qualquer backfill real futuro

Um backfill real continua **não autorizado** até que cada item tenha evidência explícita e autorização específica para o ambiente de destino.

- [ ] A autorização identifica ambiente, migrations exatas, janela aprovada, operador e responsável pela decisão de rollback.
- [ ] O inventário confirma versões do banco e dos schemas, linhas afetadas, contagens de tentativas/manifests/artefatos, ponteiros de release, associações entre papéis, identidades de workers, chaves de objetos, classes de armazenamento e escritores atuais.
- [ ] Cada mapeamento da 004 tem evidência revisada de forma independente para ID da tentativa, partição, UUID do proprietário, token, ID do manifest e linhagem. A evidência é retida, autêntica e não contém segredos ou dados pessoais desnecessários. Sem comprovação, interrompa.
- [ ] O conjunto protegido de backup inclui globals, dump do banco em formato customizado e snapshot/arquivo consistente do armazenamento. Verifique checksums, controles de acesso, retenção e credenciais de recuperação; trate o dump global como material sensível.
- [ ] O ensaio de restauração usa esse conjunto real de backup em recursos novos e isolados, com reconciliação independente da origem do banco e dos bytes do armazenamento, verificações de papéis/privilégios e ponteiros de release, além de evidências registradas.
- [ ] Capacidade, espaço livre, duração da restauração, congelamento de escritores/barreira de snapshot, janela de bloqueio, `lock_timeout`, `statement_timeout`, caminho de cancelamento e indisponibilidade dos serviços afetados foram revisados e aprovados.
- [ ] As migrations são aplicadas primeiro a um clone. Revise os mapeamentos exatos e o plano gerado; interrompa diante de qualquer divergência em contagem de linhas, mapeamento, linhagem, classe de acesso ou hash de artefato.
- [ ] As verificações posteriores comparam versões de schema, cobertura exata dos mapeamentos, identidade de proprietário/worker, tokens de fencing, vínculos de manifests, chaves e hashes de artefatos, estado de qualidade/outbox, todas as releases e o ponteiro ativo, schema `app` e comportamento de menor privilégio dos papéis.
- [ ] O rollback foi ensaiado como restauração do conjunto de backup verificado, incluindo globals e armazenamento, com ponto de decisão claro e confirmação de que os escritores da aplicação permanecerão congelados até restabelecer a consistência.

Este checklist é orientação de planejamento, não um procedimento executável de produção. Não acrescente seleção automática de destino de produção nem invoque migrations reais a partir deste harness.
