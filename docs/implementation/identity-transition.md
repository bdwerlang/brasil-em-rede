# Transição de identidade: protótipo para snapshot isolado

O módulo `bracc_etl.identity.migration` planeja UUIDs opacos por nó e grava
`entity_id`, `identity_snapshot` e `identity_legacy_id` na mesma transação, sem
recriar nós ou arestas. O alias é associado ao snapshot de origem; não pressupõe
que `elementId` sobreviva à reconstrução. UUIDs novos só passam a ser estáveis
após o commit do mapa. IDs existentes são preservados. O crosswalk versionado é exportado por criação exclusiva, contém somente alias
Neo4j e UUID, e possui SHA-256 para detectar alterações. Importação valida o
checksum, duplicatas e cobertura completa; recebe mapeamento explicitamente
verificado de alias original para nó reconstruído. Esse mapeamento de origem e
a custódia/autenticidade do arquivo são responsabilidades do processo U11; o
checksum não autentica o arquivo. Não há resolução global de identidade.

`plan_snapshot` reporta documentos completos válidos repetidos como colisões;
máscaras, nomes e raízes não produzem resolução. `Collision.value` pode conter
CPF ou CNPJ: nunca registrar em logs ou relatórios públicos. `apply_snapshot`
bloqueia toda a transação quando há colisões, IDs duplicados ou propriedades de
migração preexistentes. A auditoria não supre revisão manual de outros conflitos.
Não há constraint global para `entity_id`; writers devem estar interrompidos
durante planejamento, aplicação e validação. Aplicar apenas a uma candidata
isolada obtida de snapshot consistente, após os pré-requisitos U11 e aprovação.
Esta implementação não executa migração por conta própria.

`rollback_snapshot` remove as propriedades adicionadas por esta etapa e mantém
IDs preexistentes. Exige mapa de IDs e manifesto de estados original (`created`
ou `existing`) confiáveis, retidos antes de qualquer alteração, e bloqueia
divergências com os metadados atuais. Requer candidata congelada. Rollback de release continua sendo retorno ao bundle anterior;
este rollback local não substitui backup, restore, publicação ou ensaio U11.

A API oferece `/api/v1/entity/by-canonical-id/{entity_id}` e
`/api/v1/entity/by-snapshot-alias/{snapshot}/{legacy_id}` com 409 para múltiplos
resultados. A consulta por CPF/CNPJ também retorna 409 para ambiguidade. Busca, consulta por documento, rota por element ID e grafo aceitam ou retornam
UUID quando disponível, com fallback ao ID legado. Outros consumidores, incluindo
investigações e timeline, ainda precisam de adaptação coordenada. As novas rotas não
substituem autorização ou política de exposição existente.

Ensaio local: `etl/tests/test_identity_neo4j_synthetic.py` requer instância Neo4j
5 descartável no loopback configurada explicitamente e cria somente fixtures
sintéticas. Verifica colisão que aborta, gravação e mapa, contagens, IDs e arestas,
reversão preservando um ID anterior e restauração do crosswalk em grafo sintético
reconstruído. O alias Neo4j contém dois pontos, aceitos pela rota; clientes também
podem codificá-los como `%3A`. Esse teste sintético não comprova reconstrução
integral, concorrência, backup, restore ou a homologação U11.

Em 27/10/2026, um ensaio separado usou uma cópia isolada de um grafo local
obtida com a origem em somente leitura. A integridade da cópia foi comparada
antes do uso e a origem foi verificada novamente após o ensaio. A procedência
integral do grafo não foi certificada: parte de sua composição é compatível com
uma fixture de desenvolvimento, mas isso não comprova a origem de todos os nós.
O resultado não certifica uma carga de fontes reais.

A cópia tinha 27 nós e 24 arestas. Dos 24 nós elegíveis, 24 receberam
identidade e os 24 foram revertidos. As contagens por label e tipo de relação e
as impressões digitais dos IDs, arestas e propriedades anteriores coincidiram
após a reversão; a estrutura e as propriedades anteriores também coincidiram
após a aplicação. O mapa efetivamente aplicado e o manifesto de estados foram
retidos de forma privada. O crosswalk versionado foi exportado e lido com
verificação de checksum; um checksum alterado foi rejeitado. A reversão usou o
crosswalk lido e o manifesto. O checksum detecta alteração, mas não comprova
autenticidade nem substitui custódia independente.

A auditoria encontrou, nos cinco nós `Person`, zero CPF válidos e cinco
inválidos ou mascarados; nos cinco nós `Company`, um CNPJ válido e quatro
inválidos ou mascarados. Não havia valores ausentes nesses grupos. A regra de
documentos fortes válidos não reportou colisões, mas uma comparação textual
identificou um possível conflito de CPF inválido ou mascarado entre um nó
`Person` e um `PublicOffice`. A repetição não comprova identidade. O planejador
considera CPF válido em `Person` e não examina CPF de `PublicOffice`; outros
conflitos de identificadores por fonte podem existir.

O ensaio não demonstrou reconstrução integral, concorrência, backup ou restore.
A homologação U11 e a revisão dos possíveis conflitos permanecem pendentes.
