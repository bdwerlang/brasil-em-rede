# Contribuindo com o Brasil em Rede

Idioma: [English](../../CONTRIBUTING.md) | **Português (Brasil)**

Comece pelo [roteiro](../project/README.md) e pelas tarefas de fundação.
As [fichas das fontes](../implementation/README.md) definem escopo e aceite de
cada conector. Preserve a atribuição e a licença AGPL; veja [NOTICE.md](../../NOTICE.md).

## Regras Gerais

- Mantenha as mudanças alinhadas ao objetivo de transparência de interesse público.
- Não adicione segredos, credenciais ou detalhes de infraestrutura privada.
- Respeite defaults públicos de segurança, privacidade e compliance.

## Setup de Desenvolvimento

```bash
(cd api && uv sync --locked --extra dev)
(cd etl && uv sync --locked --extra dev)
(cd frontend && npm ci)
```

## Checagens de Qualidade

Execute antes de abrir PR:

```bash
make check
make neutrality
```

## Expectativas para Pull Request

- Mantenha o escopo da PR focado e explique o impacto para usuário.
- Inclua testes para mudanças de comportamento.
- Atualize documentação quando interfaces ou fluxos mudarem.
- Garanta todos os checks obrigatórios verdes no CI.

## Contribuições com Assistência de IA

Contribuições com assistência de IA são permitidas.  
Contribuidores humanos continuam responsáveis por:

- correção técnica,
- conformidade de segurança e privacidade,
- revisão final e aprovação antes do merge.
