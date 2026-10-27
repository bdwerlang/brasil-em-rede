# Migração e publicação coerente das bases

Procedimento **proposto**, dependente das etapas do [roadmap](roadmap.md).
Não executar os scripts herdados de reset, carga nacional ou backup como se
este documento já os tivesse corrigido. Esta entrega não aciona migração.

## Catálogo de controle a implementar

| Registro operacional | Chave/controle mínimo |
|---|---|
| `source`, `dataset`, `source_alias` | IDs canônicos e escopo dos aliases; contrato e classe de acesso |
| `artifact`, `acquisition`, `partition_manifest` | Hash de bytes, origem, cobertura, partes esperadas/completas e publicação do manifesto |
| `run`, `run_attempt`, `partition_lease` | UUID, idempotency key, owner/expiração e fencing token para rejeitar worker antigo |
| `entity`, `identifier`, `identity_decision` | ID opaco, namespace/escopo e decisão versionada com suporte; índices de unicidade |
| `quality_result`, `projection_job`, `outbox` | Resultado do gate, trabalho pendente e confirmação idempotente por partição/versão |
| `release_bundle`, `active_release` | Manifests imutáveis, versões dos contratos/regras, alvo do grafo, analytics e ponteiro publicado |
| Schema `app`: usuários, investigações e anotações | Estado mutável fora da projeção dos datasets; referências por ID estável, com release/observação quando o contexto histórico importar |

O mapa de identidade e os manifestos usados por uma release ficam versionados.
Uma atualização global do crosswalk não pode alterar o significado da release
anterior em consultas históricas.

## Estados por dataset/partição

`discovered → contract_validated → acquired → normalized → resolved → projected
→ verified → published`.

Estados alternativos: `blocked_access`, `blocked_external`, `quarantined`,
`failed`, `superseded`. Um catálogo de descoberta termina com recursos
catalogados; uma fonte derivada exige manifests de dependências. O catálogo das
169 fontes e esses estados operacionais são modelos distintos.

A transição guarda quem/qual worker a fez, versão, timestamps, contadores e
evidência. A ausência de erro não promove a próxima etapa. `published` só é
atribuído quando a partição integra um bundle verificado e apontado como ativo.

## Escrita e publicação entre componentes

Não há commit distribuído entre arquivos, PostgreSQL e Neo4j. O caminho
proposto é escrita idempotente com outbox e promoção de bundle:

1. Worker adquire lease da partição com token crescente; o catálogo rejeita
   commits de um token vencido. Dois workers não finalizam o mesmo recurso.
2. Baixar para caminho temporário isolado; conferir conteúdo/partes/checksum e
   publicar bytes sob chave imutável. Arquivo sem registro de controle é órfão
   recuperável, nunca partição concluída.
3. Normalizar para versão própria, validar esquema e reconciliar contagens.
   Gravar manifesto imutável com a lista exata dos arquivos, sem glob sobre
   diretório mutável. Só então registrar o manifesto aprovado no controle.
4. Em transação PostgreSQL, registrar trabalho de projeção na outbox. O
   projetor aceita reentrega com chave `(manifest_id, projection_version,
   partition_id)`. Antes de habilitar um novo writer, sincronizar seu token
   no guard da candidata no Neo4j e confirmar esse estado no controle.
5. Escrever lotes em transações Neo4j confirmadas e consumir resultados;
   registrar contadores e chaves de fatos. Retry esgotado falha o job inteiro.
   Uma queda após commit do grafo e antes do ack exige reexecução idempotente,
   não incremento cego das métricas.
6. Construir projeção candidata isolada e consultas analíticas apontadas aos
   mesmos manifests. Executar gates, reconciliar resultados e congelar a
   candidata para leitura; nenhuma escrita posterior naquele bundle.
7. Gravar o bundle `verified` com schema, versões de resolução/regras,
   `graph_target`, manifests e cobertura. Atualizar `active_release` por
   compare-and-swap na transação do controle: só promove se a release anterior
   ainda for a esperada e o lease/token permanecer válido.
8. A API lê o bundle no início da requisição e fixa seus recursos até o fim,
   inclusive cache e consultas de evidência. Uma requisição em andamento pode
   terminar com a release anterior; a resposta informa seu `release_id`.

### Exclusão efetiva de writers durante o congelamento

Lease/ack no PostgreSQL sozinho não impede uma escrita tardia no Neo4j.
Cada transação de projeção deve adquirir um lock exclusivo num guard local
à candidata, ler seu estado/epoch e token de partição sob o lock e abortar
se não corresponderem ao build/manifest esperado. O lock permanece até o
commit dos fatos no mesmo banco. O coordenador de freeze adquire o mesmo
guard, aguarda transações anteriores, revoga tokens, muda o estado e só então
confirma o congelamento. Transação atrasada não consegue confirmar depois dele.

A implementação U07/U11 deve escolher e testar o mecanismo de lock da versão
Neo4j usada, incluindo a corrida entre leitura do estado e aquisição do lock.
No piloto, um guard global pode serializar commits e é um limite de throughput
a medir. Particionar locks futuramente requer outro ensaio de barreira global.
Expiração por relógio não basta: a ativação de um novo token exige revogar o
anterior no destino; tokens não sincronizados bloqueiam a finalização do build.
Desabilitar caminhos legados que escrevem sem o guard. Fencing só no ack e uma
checagem feita antes de abrir a transação não satisfazem o gate.

O [driver Neo4j documenta transações e retries](https://neo4j.com/docs/python-manual/current/transactions/).
A proposta usa lotes idempotentes e métricas reconciliadas após confirmação;
contadores do driver distinguem nós/relações criados de registros processados.
Os wrappers atuais precisam ser alterados e testados antes desse protocolo.

| Falha induzida no ensaio | Recuperação e critério |
|---|---|
| Arquivo completo sem catálogo | Reconciliar checksum e registrar ou coletar órfão conforme retenção; release ativa preservada |
| Normalização interrompida | Retomar/refazer partição sem publicar temporário; deduplicar pela chave do registro e revisão |
| Worker perde lease ou tenta gravar após freeze | Revogar token no guard do destino; transação atrasada aborta sob lock, e o catálogo rejeita sua finalização |
| Grafo confirma lote, outbox não recebe ack | Reentregar lote com IDs estáveis; reconciliar estado sem duplicar fatos |
| Último lote falha | Candidata permanece incompleta; ponteiro ativo permanece anterior |
| Ponteiro promovido, processo cai | Requisições novas obtêm bundle publicado do controle; operação de promoção é reconciliável |
| Recurso candidato inacessível | Falhar health/ensaio antes da promoção; após incidente, reverter ponteiro explicitamente, sem misturar releases na resposta |

## Estratégia compatível com Community

O [manual de administração do Neo4j](https://neo4j.com/docs/operations-manual/current/database-administration/)
distingue as capacidades por edição. A proposta não depende de múltiplos bancos
de usuário, aliases de banco ou cluster Enterprise numa única instalação.

No piloto, usar **duas instâncias/volumes independentes** para grafo ativo e
candidato, com identificação no bundle. Construir a candidata a partir dos
manifests aprovados ou de restauração consistente da base anterior e aplicar
as mudanças; nunca copiar diretamente um diretório de banco em escrita.
As duas instâncias não compartilham o mesmo volume Neo4j.

Para releases seguintes, alternar o destino após retenção das requisições
em andamento, dos cursores emitidos e do prazo de rollback. Não reutilizar o
volume de uma release ainda retida; adiar a próxima publicação se não houver
instância/volume disponível. Conservar a capacidade de reconstrução
pelos manifests, inclusive releases que já não têm instância ativa.
Se a medição demonstrar que duas projeções não cabem, U11 deve desenhar e
ensaiar janela de manutenção com API indisponível para a mudança. Não prometer
troca sem interrupção ou backfill nacional antes desse dimensionamento.

## Paginação, navegação e estado mutável

O primeiro resultado de busca fixa `release_id` no contexto da interface.
Cursores assinados carregam release, query/filtros, ordenação estável com ID
como desempate, última chave e expiração. Expansões do grafo e páginas seguintes
enviam a mesma release; caches incluem release e perfil de acesso. Autorização
é reavaliada em cada chamada: o cursor não concede acesso por si.

Retenção da projeção deve cobrir a validade dos cursores e requisições emitidos.
Se uma release for retirada, expirada ou bloqueada por correção/privacidade,
retornar erro explícito `410 release_unavailable`; a interface reinicia a
consulta e informa a atualização. Não continuar silenciosamente na versão nova.
U10 deve testar navegação atravessando uma promoção e uma revogação.

Usuários, autenticação persistida, investigações, anotações e referências salvas
passam para schema `app` no PostgreSQL. Referências usam ID estável e, quando
preciso, `release_id`/`observation_id` da evidência. Esse estado tem revisão
própria e pode ser escrito enquanto os datasets publicados são imutáveis.
Migrar hashes de senha e identificadores com cuidado, sem copiá-los para logs,
relatórios públicos ou fixtures. Trocar os serviços leitores/writers e testar
login e edição antes de desabilitar a escrita correspondente no grafo.

## Migração do legado

1. **Inventariar sem alterar:** listar bases, versões, volumes, labels,
   constraints, contagens por fonte/período, chaves ausentes, duplicatas e
   referências salvas em investigações/URLs. Distinguir dados reais de fixtures.
2. **Preparar recuperação:** suspender writers em janela definida e produzir
   backup consistente. Na Community, dump exige DBMS offline segundo o
   [procedimento oficial](https://neo4j.com/docs/operations-manual/current/backup-restore/offline-backup/).
   Corrigir o script atual e restaurar numa instalação separada; hash de arquivo
   sozinho não comprova restore.
3. **Congelar o ponto de partida:** registrar manifest do legado e identificação
   do snapshot. Exportações incompletas não são promovidas como carga integral.
4. **Atribuir IDs e aliases:** criar chaves canônicas paralelas; auditar colisões;
   preservar referências antigas no escopo do snapshot. Não reconstruir um CPF,
   CNPJ completo ou identidade de pessoa a partir de máscara ou nome.
5. **Recuperar observações:** quando o bruto existir, reprocessar com contrato
   rastreável. Quando não existir, registrar `legacy_unverified`, campo de origem
   disponível e motivo; não fabricar artefato/linha. Excluir esses fatos dos
   cruzamentos que exijam prova ausente e de confirmações automáticas.
6. **Construir candidata:** reconciliar labels, eventos, aliases e períodos;
   manter origem das observações divergentes. Não apagar o legado ativo.
7. **Comparar:** executar consultas conhecidas, fixtures negativas, contagens por
   grão e distribuição de vínculos, incluindo diferenças esperadas por filiais,
   doações antes colapsadas e contratos espelhados. Toda divergência material
   precisa de explicação e evidência.
8. **Ensaiar API:** compatibilidade de rotas/IDs, paginação, evidência, filtros
   públicos e serialização sem `labels[0]`. IDs legados ambíguos produzem resposta
   explícita; não escolher uma entidade arbitrária. Migrar estado de aplicação
   e validar que login, investigações e anotações sobrevivem a rebuild/rollback.
9. **Promover:** publicar bundle verificado somente depois do aceite técnico do
   recorte e do ensaio de rollback. Este plano não efetua esse corte.

## Rollback e retenção

Reverter o ponteiro para bundle anterior verificado e ainda acessível. Impedir
escritas na projeção publicada; novas observações aguardam próxima candidata.
Preservar manifests, mapas de identidade e decisões necessários para reproduzir
ambos os estados. Invalidar caches pela chave de release, não por limpeza cega.

Se for necessário restaurar, seguir o ensaio offline em instância/volume
separado e conferir IDs e relações antes de servir tráfego. O catálogo PostgreSQL
e os manifests precisam de backup consistente com as referências dos bundles;
um dump exclusivo do grafo não recupera a plataforma inteira.

U11 deve medir tempo de recuperação e perda máxima aceitável, documentar RTO/RPO
para o ambiente escolhido e testar falha do controle, do volume e da projeção.
Não existe meta de disponibilidade certificada por este plano.

Retenção, correção e expurgo têm política por classe de acesso. Imutabilidade
de release não elimina a necessidade de remoção autorizada: marcar bundles
afetados como não servíveis, recompor projeções e tratar cópias/backups conforme
política efetiva. O que deixa de estar publicável não continua exposto por um
link de evidência ou por uma release histórica.
