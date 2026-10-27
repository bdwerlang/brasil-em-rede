# querido_diario — Querido Diario gazettes

Cadastrar diários municipais e atos/textos extraídos, conectando menções de CNPJ com trecho e documento de prova.

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `querido_diario`.
- Ordem topológica: **124**; onda de execução: **7**; prioridade temática inicial: 7.
- Tipo de trabalho: **Completar e corrigir pipeline existente**; complexidade relativa: **XL**.
- Registro atual: implementação `implemented`, carga `partial`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: [cnpj](cnpj.md)
- Contrato de acesso catalogado: [https://queridodiario.ok.org.br/api](https://queridodiario.ok.org.br/api).

## Artefatos existentes auditados

- [etl/src/bracc_etl/pipelines/querido_diario.py](../../../etl/src/bracc_etl/pipelines/querido_diario.py): Conector existente: leitura, transformação e carga auditadas; existência de código não comprova dados baixados ou banco carregado.
- [etl/tests/test_querido_diario_pipeline.py](../../../etl/tests/test_querido_diario_pipeline.py): Testes existentes do parser/carga; ampliar com os critérios específicos desta ficha.
- [config/bootstrap_all_contract.yml](../../../config/bootstrap_all_contract.yml): Contrato do bootstrap: modos e entradas; esperado ainda é 45, enquanto o runner/registro têm 47.
- [etl/src/bracc_etl/linking_hooks.py](../../../etl/src/bracc_etl/linking_hooks.py): Despacho de hooks pós-carga; scripts Cypher referidos estão ausentes.
- [api/src/bracc/queries/schema_init.cypher](../../../api/src/bracc/queries/schema_init.cypher): Constraints e índices; diversas labels usadas pelos conectores ainda não têm constraint de chave.

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
| [https://queridodiario.ok.org.br/api](https://queridodiario.ok.org.br/api) | Entrada atualmente cadastrada para Querido Diario gazettes. Descobrir o recurso concreto de dados e seu dicionário. | URL de docs/source_registry_br_v1.csv; disponibilidade, formato e abrangência não foram testados nesta auditoria, salvo evidência oficial adicional abaixo. |

- **Método:** Consultar API Querido Diário por território/período com paginação; baixar arquivos/textos acessíveis e preservar URL do município original quando fornecida.
- **Autenticação:** Fluxo planejado de arquivos públicos sem autenticação de usuário; confirmar no recurso final. Se houver credencial, configurá-la fora dos manifestos e registrar bloqueio de acesso explicitamente.
- **Formato bruto:** JSON API, PDF/TXT/HTML de diário e acts.jsonl canônico.
- **Partições e backfill:** Município, data de publicação e edição/arquivo; texto/OCR em etapa própria com status.
- **Retomada e deduplicação de download:** Checkpoint por município, data de publicação e edição/arquivo; texto/ocr em etapa própria com status; baixar em temporário, validar tamanho/hash/schema e promover atomicamente. Retomar partições concluídas e repetir páginas/arquivos sobrepostos com deduplicação pela chave natural; respeitar 429/Retry-After e retentativas limitadas.
- **Atualização:** Diária, com janela de revisita para retificações.

Limites e pré-condições:

- Catálogo tem lacuna de disponibilidade de texto e cobertura municipal parcial.
- Parser não faz download de PDF nem OCR.
- Risco de chamar diário inteiro de ato e atribuir trechos ao contexto errado.
- Bootstrap só verifica presença em data/querido_diario/*; não baixa, não valida schema, não verifica completude e não comprova carga.
- Não há hook pós-carga configurado; vínculos dependentes de outra carga precisam de religação idempotente explícita.

## Contrato de ingestão

**Entrada esperada:** data/querido_diario/acts.csv, acts.jsonl ou acts.json; parser combina os formatos presentes e espera act_id, city_code, published_at, title, source_url e texto.

**Chave natural / namespace:** ID oficial do diário/arquivo + página/seção/ato quando segmentado; hash de município/data/título/URL só como fallback explicitamente versionado.

Normalização:

- Diário completo não é automaticamente um ato individual: manter granularidade e segmentação explícitas.
- CNPJ extraído tem validação alfanumérica, posição no texto e página quando disponível.
- Nome de pessoa/empresa não gera SAME_AS; menção não comprova contrato ou vínculo societário.
- Código territorial deve ser reconciliado com IBGE por tabela de correspondência.

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
| `MunicipalGazetteAct` | municipal_gazette_act_id | existing |
| `Company` | cnpj | existing |

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
| `Company` → `MENCIONADA_EM` → `MunicipalGazetteAct` | CNPJ válido extraído no texto original | Guardar método, confiança, URL, trecho e offset; menção não implica relação econômica. | existing |

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

- `etl/src/bracc_etl/acquisition/querido_diario.py`
- `config/sources/querido_diario.yml`
- `etl/src/bracc_etl/pipelines/querido_diario.py`
- `etl/tests/test_querido_diario_acquisition.py`

Tarefas específicas, em ordem:

1. Implementar aquisição paginada dos territórios e diários, validando limite de cobertura efetivo do projeto.
1. Criar estágio de download de texto/PDF e OCR opcional com versionamento e confiança.
1. Deduplicar CSV/JSONL/JSON da mesma extração em vez de combinar tudo sem manifesto.
1. Padronizar ID do diário e, se houver, IDs dos atos segmentados; guardar documento completo.
1. Criar menções CNPJ com URL, trecho, offset e método; registrar diários sem texto como pendência.
1. Religar menções à Company após carga cadastral sem depender de ordem.

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

- [ ] Diário sem texto permanece cadastrado e sinalizado, sem menções fabricadas.
- [ ] Todo MENCIONADA_EM pode ser reproduzido a partir do trecho/documento.
- [ ] Mesma extração em dois formatos não duplica atos.
- [ ] Cobertura informa municípios, períodos e taxa de texto disponível.

## Riscos e decisões pendentes

- Catálogo tem lacuna de disponibilidade de texto e cobertura municipal parcial.
- Parser não faz download de PDF nem OCR.
- Risco de chamar diário inteiro de ato e atribuir trechos ao contexto errado.
- Status loaded herdado não foi confirmado no banco local; só manifestos, cobertura e execução real validados poderão atualizar load_state.

## Evidências e referências

- `etl/src/bracc_etl/pipelines/querido_diario.py`
- `docs/source_registry_br_v1.csv`
- `config/bootstrap_all_contract.yml`
- `etl/src/bracc_etl/linking_hooks.py`
- `etl/src/bracc_etl/base.py`
- `etl/src/bracc_etl/loader.py`
- `etl/tests/test_querido_diario_pipeline.py`

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
