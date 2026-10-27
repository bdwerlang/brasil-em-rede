# M0: auditorias Python da API e do ETL

Execução A02 / [#20](https://github.com/bdwerlang/brasil-em-rede/issues/20),
em 2026-10-27, por Codex/OpenAI. Base: `b4f0014`. Branch:
`codex/m0-python-audits`. Esta entrega é parte da F00; frontend e os demais
critérios do M0 continuam em suas tarefas.

## Resultado reproduzido

Auditoria com `pip-audit 2.10.1`, Python 3.12.3 em Linux x86_64, dos requisitos
exportados dos dois lockfiles com todos os extras e grupos. Os marcadores de
plataforma são avaliados nesse ambiente; isto não certifica outras plataformas
ou vulnerabilidades ainda desconhecidas. Nenhum pacote foi ignorado e nenhuma
vulnerabilidade foi suprimida.

| Projeto | Pacotes antes → depois | Pacotes com alertas antes → depois | Pares pacote/advisory antes → depois |
|---|---|---|---|
| API | 64 → 65 | 16 → 0 | 106 → 0 |
| ETL | 78 → 78 | 11 → 0 | 66 → 0 |

Um mesmo advisory pode ocorrer em registros duplicados do serviço de auditoria.
Os totais acima deduplicam por pacote e ID retornado; aliases distintos não são
tratados como necessariamente a mesma vulnerabilidade.
O [resumo estruturado](evidence/m0-python-audits.json) preserva IDs, versões,
alterações e hashes dos lockfiles. Relatórios JSON completos e requisitos são
publicados separadamente como artefatos `pip-audit-api` e `pip-audit-etl` no CI.

## Alterações e compatibilidade

- Atualizadas as dependências afetadas e as transitivas necessárias, preservando
  os demais pacotes fixados. Os mínimos diretos de FastAPI, pydantic-settings,
  PyJWT, python-multipart, WeasyPrint e pypdf acompanham a correção.
- FastAPI 0.162.0 permite Starlette 1.10.0. A
  [mudança de defaults de booleanos em formulários](https://fastapi.tiangolo.com/release-notes/#01620-2026-10-23)
  foi revisada: os endpoints atuais não declaram esses formulários. Os testes
  de autenticação, erros, privacidade e rotas passaram sem mudança da aplicação.
- [PyJWT 2.15.1](https://pyjwt.readthedocs.io/en/stable/changelog.html)
  mantém o fluxo HS256 usado pela aplicação; os testes existentes de emissão,
  expiração e recusa de tokens passaram. A chave padrão dos fixtures ainda
  gera aviso de comprimento; não foi apresentada como configuração de produção.
- [WeasyPrint 70.0](https://doc.courtbouillon.org/weasyprint/stable/changelog.html#version-70-0),
  Pillow 13 e cryptography 50 exigem atenção às mudanças de versão principal.
  Além dos testes existentes com mocks, dois relatórios sintéticos foram
  renderizados com WeasyPrint real e lidos com pypdf, conferindo páginas,
  título e rótulos em português e inglês.
- [pypdf 6.21.3](https://pypdf.readthedocs.io/en/stable/meta/CHANGELOG.html#version-6-21-3-2026-10-27)
  inclui correções de segurança publicadas na data da execução. Os pacotes gRPC
  do extra BigQuery também foram atualizados para sair de versões retiradas.

## CI e validação

O job Python de segurança agora usa matriz `api`/`etl` com `fail-fast: false`.
Cada job exporta com `--locked`, audita com `--strict` e publica sua evidência
com `if: always()`. Uma falha mantém o respectivo job vermelho e não impede a
auditoria do outro projeto. Não há `continue-on-error` nem exclusões de alertas.

Resultados locais:

- API: Ruff e mypy aprovados; **199 testes passaram**, 1 pulado e 13 de integração
  excluídos pela configuração existente. O teste pulado depende de uma query
  de padrão ausente nesta edição.
- ETL no ambiente padrão: Ruff e mypy aprovados; **959 testes passaram**, 2 pulados
  por falta do extra PyArrow e 2 de integração excluídos.
- ETL com todos os extras instalados: **961 testes passaram**, sem pulos e com
  os mesmos 2 de integração excluídos. Imports reais de BigQuery, BigQuery Storage,
  gRPC, cryptography, ASN.1 e Splink aprovados, sem chamadas aos serviços externos.
- Geração e leitura real de PDF em português e inglês: aprovadas.
- Workflow: Actionlint 1.7.12 e verificação da matriz/ausência de supressões.

Integração com banco, ingestão real e homologação da aplicação pertencem aos
gates posteriores. Estes testes não substituem seus aceites.

Para reproduzir a auditoria, na raiz de um checkout desta branch:

```bash
audit_status=0
for project in api etl; do
  (
    cd "$project" || exit 1
    uv export --locked --all-extras --all-groups --format requirements-txt \
      --no-hashes --no-emit-project --no-emit-local \
      --output-file "/tmp/bracc-${project}-requirements.txt" &&
    uvx pip-audit==2.10.1 -r "/tmp/bracc-${project}-requirements.txt" \
      --strict --format json --output "/tmp/bracc-${project}-audit.json"
  ) || audit_status=1
done
test "$audit_status" -eq 0
```

O resultado agregado local e o CI falham se qualquer projeto falhar; ambas as
auditorias são executadas mesmo quando o primeiro projeto falha.

Checks de código:

```bash
(cd api && uv sync --locked --extra dev && PRODUCT_TIER=community bash ../scripts/ci/python_quality.sh)
(cd etl && uv sync --locked --extra dev && bash ../scripts/ci/python_quality.sh)
(cd etl && uv sync --locked --all-extras && uv run --locked --all-extras pytest -q)
```
