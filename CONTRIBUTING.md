# Contributing to Brasil em Rede

Language: **English** | [Português (Brasil)](docs/pt-BR/CONTRIBUTING.md)

Start with the [project roadmap](docs/project/README.md) and its foundation
issues. The [source cards](docs/implementation/README.md) define the scope and
acceptance criteria for each connector. Preserve upstream attribution and the
AGPL license; see [NOTICE.md](NOTICE.md).

## Ground Rules

- Keep changes aligned with public-interest transparency goals.
- Do not add secrets, credentials, or private infrastructure details.
- Respect public-safe defaults and privacy/legal constraints.

## Development Setup

```bash
(cd api && uv sync --locked --extra dev)
(cd etl && uv sync --locked --extra dev)
(cd frontend && npm ci)
```

## Security and environment

- **Frontend env:** Only `VITE_*` variables are exposed in the client bundle. Do not put secrets in `VITE_*`; use them only for public config (e.g. `VITE_API_URL`, `VITE_PUBLIC_MODE`).
- **Auth:** Keep tokens in memory or HttpOnly cookies only; do not persist JWT in `localStorage` or `sessionStorage`.
- **Releases:** Before releases, run `npm audit` in `frontend/` and address high/critical findings.

## Quality Checks

Run these before opening a pull request:

```bash
make check
make neutrality
```

## Pull Request Expectations

- Keep PR scope focused and explain the user impact.
- Include tests for behavior changes.
- Update docs when interfaces or workflows change.
- Ensure all required CI and security checks are green.

## AI-Assisted Contributions

AI-assisted contributions are allowed.  
Human contributors remain responsible for:

- technical correctness,
- security/privacy compliance,
- and final review/sign-off before merge.
