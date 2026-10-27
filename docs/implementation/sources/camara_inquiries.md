# camara_inquiries — Camara inquiries and requirements

Cadastrar CPIs/comissões de inquérito da Câmara, requerimentos e sessões e extrair menções documentais a empresas.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `camara_inquiries`.
- Ordem topológica: **27**; onda de execução: **3**; prioridade temática inicial: 3.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **L**.
- Registro atual: implementação `implemented`, carga `partial`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [camara](camara.md)
- Contrato de acesso catalogado: [https://dadosabertos.camara.leg.br/](https://dadosabertos.camara.leg.br/).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/camara_inquiries.py](../../../etl/src/bracc_etl/pipelines/camara_inquiries.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_camara_inquiries_pipeline.py](../../../etl/tests/test_camara_inquiries_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://dadosabertos.camara.leg.br/](https://dadosabertos.camara.leg.br/) | Entrada atualmente cadastrada para Camara inquiries and requirements. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Consultar dados abertos da Câmara para órgãos, eventos, proposições e autores, baixar também documentos e textos autorizados por URL oficial.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** JSON oficial e documentos PDF/HTML/texto; saída em três CSVs canônicos.
- **Partições e backfill:** Legislatura, comissão, requerimento e sessão; retorno paginado e metadados de cada documento.
- **Retomada e deduplicação de download:** Checkpoint por legislatura, comissão, requerimento e sessão; retorno paginado e metadados de cada documento; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Diária, com janela de revisita para retificações.

Limites e pré-condições:

- Pipeline atual vincula autores por nome isolado.
- Fallbacks de chave com texto truncado podem colidir ou mudar.
- Bootstrap só verifica presença em data/camara_inquiries/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/camara_inquiries/inquiries.csv, requirements.csv e sessions.csv, UTF-8; arquivos opcionais hoje podem resultar em cobertura incompleta sem falha.

**Chave natural / namespace:** ID oficial de órgão/comissão, proposição/requerimento e evento; incluir Casa e legislatura no namespace.

Normalização:

- Autor por ID de deputado/proposição, substituindo match nominal.
- CNPJ extraído do texto deve ter validação, trecho, página/offset e URL de prova.
- Menção em requerimento não equivale a participação empresarial ou culpa.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `Inquiry` | inquiry_id | existing |
| `InquiryRequirement` | requirement_id | existing |
| `InquirySession` | session_id | existing |
| `Company` | cnpj | existing |
| `Person` | cpf | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Inquiry` → `TEM_REQUERIMENTO` → `InquiryRequirement` | ID da comissão em cada requerimento | Proposição deve estar formalmente relacionada à comissão. | existing |
| `Inquiry` → `REALIZOU_SESSAO` → `InquirySession` | ID comissão + ID evento oficial | Data e Casa preservadas. | existing |
| `Person` → `PROPOS_REQUERIMENTO` → `InquiryRequirement` | Proposto: ID deputado; CPF quando oficial integral | Desativar fallback nominal existente. | existing |
| `Company` → `MENCIONADA_EM` → `InquiryRequirement` | CNPJ válido extraído no documento | Guardar trecho e URL; menção não prova irregularidade. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/camara_inquiries.py`
- `config/sources/camara_inquiries.yml`
- `etl/src/bracc_etl/pipelines/camara_inquiries.py`
- `etl/tests/test_camara_inquiries_acquisition.py`

Tarefas específicas, em ordem:

1. Implementar mapeamento dos endpoints oficiais de órgãos/eventos/proposições e paginação para os três arquivos.
1. Preferir IDs oficiais em vez de hashes de texto truncado que mudam em retificações.
1. Substituir PROPOS_REQUERIMENTO por nome por vínculo de ID da Câmara.
1. Extrair PDF/HTML com proveniência e conferir CNPJ no texto original.
1. Marcar documentos sem texto e sessões não publicadas como lacunas, sem inventar eventos.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Requerimento preserva autor oficial mesmo com variação do nome.
- [ ] Todo MENCIONADA_EM possui URL e trecho verificável.
- [ ] Reordenação/retificação de texto não duplica ID oficial.
- [ ] Cobertura informa separadamente CPIs, requerimentos, sessões e documentos sem texto.

## Riscos e decisões pendentes

- Pipeline atual vincula autores por nome isolado.
- Fallbacks de chave com texto truncado podem colidir ou mudar.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/camara_inquiries.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_camara_inquiries_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
