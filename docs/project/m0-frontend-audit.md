# M0: auditoria do frontend

A03 / [#21](https://github.com/bdwerlang/brasil-em-rede/issues/21), executada
em 2026-10-27 por Codex/OpenAI. Base `b4f0014`; branch
`codex/m0-frontend-audit`. Parte da F00, com revisão e reversão próprias.

## Resultado e correção

`npm audit` passou de **17 alertas** (2 críticos, 11 altos, 3 moderados e 1 baixo)
para **zero**, incluindo dependências de desenvolvimento. Nenhum alerta foi
suprimido. O [resumo estruturado](evidence/m0-frontend-audit.json) registra os
advisories, alterações de versão e hashes do lockfile. A ausência de alertas
conhecidos nessa execução não certifica ausência de vulnerabilidades futuras.

A atualização compatível com os intervalos existentes resolveu 14 entradas,
mas deixou Vitest, seu mocker e Tinypool afetados. A migração explícita de
Vitest **3.2.4 → 4.1.12** removeu as restantes, sem usar `audit fix --force`.
Foi revisado o [guia de migração da versão 4](https://v4.vitest.dev/guide/migration.html):
Vite 6/Node 22 atendem aos requisitos; as configurações e mocks atuais passaram
sem adaptações ou redução de assertions. O projeto não usa as opções de
coverage removidas ou pools personalizados descritos no guia.

Também foram atualizados Vite **6.4.1 → 6.4.5**, React Router **7.13.0 → 7.18.4**,
Zod **4.3.6 → 4.6.7** e transitivas afetadas. Os mínimos diretos desses pacotes
e do Vitest acompanham as versões validadas. React, TypeScript e a versão
principal do Vite foram preservados.

## Verificação

- Instalação limpa com `npm ci`, lint e tipos aprovados em **Node 22.23.4 /
  npm 10.9.9**. A suíte completa passou: **28 arquivos, 159 testes**.
- Build de produção aprovado no mesmo runtime. Também passou no Node 26
  disponível no ambiente. O aviso de chunk acima de 500 kB e os avisos de
  anotação de dependências permanecem; não foram silenciados.
- Chromium, servindo os arquivos compilados: busca com resultado sintético,
  link para análise carregada sob demanda, entidade ausente, histórico do
  navegador, busca vazia, erro HTTP 503 e redirecionamento de rota privada
  para login aprovados, sem exceções JavaScript.
- O navegador interceptou a API com dados sintéticos; não foi teste de
  integração com API/banco nem aquisição de dados reais. Foi exercitado o
  perfil privado padrão. Alinhamento das flags públicas entre Compose, API e
  frontend continua no escopo de #11/#15.

O script de qualidade agora executa também o build, mantendo falha agregada
quando qualquer etapa falha. O gate de segurança mantém `--audit-level=high`
e salva o JSON em `npm-audit-frontend`, inclusive quando a auditoria falha.
Actionlint 1.7.12, sintaxe shell, consistência do lockfile, diff e Gitleaks
integram a validação da alteração.

Para reproduzir, na raiz de um checkout desta branch com Node 22 e npm:

```bash
(cd frontend && bash ../scripts/ci/frontend_quality.sh)
(cd frontend && npm audit --audit-level=high --json)
```

Esta PR não encerra a fundação nem a F00 isoladamente: a atualização Python
está na [PR #23](https://github.com/bdwerlang/brasil-em-rede/pull/23). Os checks
de segurança de cada branch ainda veem as dependências da outra área na base
até que ambas as correções sejam integradas.
