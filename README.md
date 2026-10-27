# Brasil em Rede

**Infraestrutura aberta para baixar, cadastrar e conectar dados públicos brasileiros.**

[Português](docs/pt-BR/README.md) · [Implementation plan](docs/implementation/README.md) · [Project roadmap](docs/project/README.md)

Independent continuation of br/acc Open Graph, with its AGPL license and
attribution preserved. See [origin and modifications](NOTICE.md).

## Current status

Development starts from an existing FastAPI API, Neo4j graph, Python ETL and
React interface. The catalog contains **169 sources**, with **168 entries in
the public planning universe** and **47 existing pipeline modules**. Each source
has an individual plan for acquisition, ingestion, linking and acceptance.

These counts describe the repository and its plan. They do not certify 169
working connectors, current portal availability or a populated database. Existing
`loaded` states are historical metadata pending validation in this project.

The first deliverable is a reproducible **CNPJ → sanctions → public contracts**
pilot. Foundation work and acceptance criteria are in the
[project roadmap](docs/project/README.md). No production service is announced.

The [database unification plan](docs/unification/README.md) defines a common
identity and evidence model, storage responsibilities, migration and rollback,
and an individual integration route for all 169 sources. It is a proposed
implementation, with twelve delivery stages and explicit acceptance gates.

## What Is Included In This Public Repo

- API, frontend, ETL modules, Neo4j schema and synthetic development fixtures.
- [Source registry](docs/source_registry_br_v1.csv) and [current source summary](docs/data-sources.md).
- [169 individual source plans](docs/implementation/README.md), [implementation matrix](docs/implementation/source_matrix.csv) and [21 crossing plans](docs/implementation/crossings.md).
- [Machine-readable plan](config/source_implementation_plan.json), generator and validation checks.
- [Initial delivery backlog](config/github_backlog.json) and CI for code, security and catalog consistency.

## What Is Not Included By Default

Bulk datasets, credentials, production backups and a preloaded national graph
are not distributed here. Discovery portals, derived datasets and restricted
systems have different acquisition requirements. See each source card before
implementing a connector.

## What Is Reproducible Locally Today

Catalog and plan checks require Python 3.12 and do not download source data:

```bash
python3 scripts/generate_source_implementation_plan.py --check
python3 scripts/generate_data_sources_summary.py --check
python3 scripts/check_public_claims.py --repo-root .
python3 scripts/check_pipeline_contracts.py
python3 scripts/check_pipeline_inputs.py
```

For application development, install Python 3.12, uv and Node.js 22:

```bash
(cd api && uv sync --locked --extra dev)
(cd etl && uv sync --locked --extra dev)
(cd frontend && npm ci)
```

Run `make check` and `make neutrality` after installing dependencies. The test
configuration excludes integration tests by default. Database integration and
live-source ingestion require separate setup and execution evidence.

The inherited Docker Compose setup and synthetic seed are available for local
experiments; environment alignment and full-system validation are foundation
tasks. This publication does not certify that bootstrap downloads every source.
Large counts in [reference metrics](docs/reference_metrics.md) refer to an
inherited **reference production snapshot**, not this repository's database.

## Implementation order

1. Fix source IDs, document normalization, migration and graph constraints.
2. Implement resumable acquisition, reliable writes and traceable entity links.
3. Align orchestration, dimensions and configuration; validate the pilot end to end.
4. Expand through the eight waves, accepting each source individually.

A source is complete only when its download, load and crossings have separate
execution evidence. Shared names and partial documents must not silently merge
identities. See the [architecture and acceptance criteria](docs/implementation/architecture.md).

## Contributing

Start with the [roadmap](docs/project/README.md) and [contribution guide](CONTRIBUTING.md).
Use a focused branch and PR with the relevant validation results. The initial
configuration runs checks; prior release, deployment, image-publishing and
scheduled ingestion workflows are [archived](docs/history/workflows/README.md).

## Legal & Ethics

The code is licensed under [AGPL-3.0-or-later](LICENSE). Imported Brazil Visible
catalog references retain their [MIT notice](docs/catalogs/brazil_visible_LICENSE.txt).
Upstream origins and modifications are documented in [NOTICE.md](NOTICE.md).

Inherited policy documents remain available as a development baseline:
[ethics](ETHICS.md), [LGPD](LGPD.md), [privacy](PRIVACY.md), [terms](TERMS.md),
[limitations](DISCLAIMER.md), [security](SECURITY.md) and [abuse response](ABUSE_RESPONSE.md).
They do not certify an operating service or inherited governance arrangements.
Access, retention and publication rules must be reviewed for each actual source
and deployment. Connections in public records do not establish wrongdoing.
