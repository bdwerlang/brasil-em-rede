# M0 / F01 — identidade das fontes

Entrega da [issue #2](https://github.com/bdwerlang/brasil-em-rede/issues/2):
[config/source_aliases.json](../../config/source_aliases.json), versão 1, contém
as 169 entradas do catálogo e seus 47 runners existentes. `source_id` é o ID do
catálogo; `runner_name` é a chave de despacho; `provider_id` preserva o
`Pipeline.source_id` legado. Este último descreve o identificador usado pelo
código herdado, não certifica o provedor real ou cobertura do conjunto de dados.
Entradas sem módulo têm runner/provedor nulos, sem implementação fictícia.

| Catálogo | Runner | ID legado do pipeline |
|---|---|---|
| `cnpj` | `cnpj` | `receita_federal` |
| `sanctions` | `sanctions` | `ceis_cnep` |
| `pncp` | `pncp` | `pncp_bids` |
| `comprasnet` | `comprasnet` | `comprasnet` |

O resolver compartilhado aceita os três identificadores e `legacy_aliases`
explicitamente registrados. Rejeita IDs desconhecidos, versões não suportadas,
chaves JSON duplicadas e aliases duplicados/ambíguos. A CLI distingue fonte
catalogada sem runner de ID desconhecido, antes de abrir o driver. Aliases não
são inferidos por nome parecido, prefixo, endpoint, caixa ou espaço removido.

Em **novos `IngestionRun`**, `source_id` passa a ser canônico e são persistidos
`runner_name`, `provider_id` e `source_aliases_version`. As classes mantêm seu
`source_id` legado, e payloads, diretórios de entrada, propriedades das entidades
e geração de `run_id` permanecem como antes. O leitor `sources --status` resolve
registros antigos que só têm `source_id`, escolhe a execução mais recente entre
aliases e desempata pelo `run_id`. IDs não mapeados e campos conflitantes geram
mensagem explícita; não são atribuídos silenciosamente a outra fonte.

**Nenhum registro antigo, ID de entidade ou grafo é migrado por esta mudança.**
Leitores externos de `IngestionRun.source_id` precisam aceitar IDs canônicos
novos e consultar o mapa para IDs antigos. Não há leitor desse estado de
ingestão na API atual; seu catálogo JSON continua baseado no CSV. A semântica
herdada de `loaded`, contagens, colisões temporais de `run_id` e migração de
identidade pertencem às tarefas seguintes.

O adaptador `comprasnet` consome contratos PNCP, enquanto `pncp` consome
licitações. Ambos continuam com entradas e namespaces distintos. Compartilhar
provedor não autoriza juntá-los; conciliar dataset, cobertura e possíveis
duplicidades exige a implementação específica posterior.

O pacote distribui uma cópia idêntica do mapa em
`bracc_etl/data/source_aliases.json`, carregada por `importlib.resources`.
Assim, wheel e imagem ETL não dependem de `config/` externo. Após editar o mapa
canônico, executar `python3 scripts/check_source_aliases.py --sync-package`.
O check de contratos já usado no CI também verifica essa cópia e a concordância
entre catálogo, runner e metadados dos módulos, usando apenas a biblioteca
padrão, sem importar pipelines ou conectar ao banco.

Validação: `python3 scripts/check_source_aliases.py`, checks existentes do
catálogo, Ruff, mypy e testes ETL. Os testes cobrem os 47 módulos, 169 entradas,
histórico, colisões, falhas explícitas e despacho/hooks com mocks. A wheel foi
verificada em diretório externo, em Python isolado e sem checkout/config
disponíveis. Nenhum serviço, download de fonte ou ingestão foi executado.
