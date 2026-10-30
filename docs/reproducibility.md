# Reproducibility

## Public demo bootstrap (safe default)

The public wrapper is deliberately read-only by default. Its supported invocations are:

```bash
bash scripts/bootstrap_public_demo.sh --help
bash scripts/bootstrap_public_demo.sh --doctor
```

`--doctor` checks prerequisites without starting Docker; missing inputs are reported with exit code 1. Legacy `--profile`, `--download`, `--pipelines`, full-profile, and reset options are unsupported and fail closed. The wrapper does not expose an API or browser endpoint.

Seeding is a separate, explicit opt-in and requires `DEMO_NEO4J_PASSWORD`:

```bash
DEMO_NEO4J_PASSWORD='set-locally' bash scripts/bootstrap_public_demo.sh --seed-isolated --i-understand-isolated-demo
```

The seed script creates a fresh random Compose project and volume; it does not target the shared stack. Do not infer that a seed was run from these instructions.

## Separate operational workflows

`make bootstrap-all` and `make bootstrap-all-noninteractive` invoke heavy bootstrap workflows, not the public wrapper's read-only check or isolated demo. BYO-data ETL commands likewise access the configured database and data directory. Each is a separate operational workflow requiring specific approval before execution. Some pipelines also have external credentials and source preconditions; runtimes and availability vary.

## BYO-Data Ingestion

Use ETL directly:

```bash
cd etl
uv sync
uv run bracc-etl sources
uv run bracc-etl run --source cnpj --neo4j-password "$NEO4J_PASSWORD" --data-dir ../data
```

## What This Does Not Reproduce Automatically

- Production-scale graph counters (see `docs/reference_metrics.md` for reference production snapshot).
- Guaranteed success for every external source in every run (blocked/failing sources are explicitly reported).
- Private/institutional modules outside public boundary.
