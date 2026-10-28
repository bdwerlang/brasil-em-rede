-- Run in the same PostgreSQL session as migration 004. Load reviewed mappings
-- using parameterized INSERT or COPY before running the migration.
-- Evidence references must identify independently retained evidence; do not
-- include secrets or personal data. Temporary tables disappear on disconnect.
CREATE TEMP TABLE u03_attempt_backfill (
    attempt_id uuid PRIMARY KEY,
    partition_id text NOT NULL,
    owner uuid NOT NULL,
    token bigint NOT NULL CHECK (token > 0),
    evidence_ref text NOT NULL CHECK (length(btrim(evidence_ref)) > 0)
);
CREATE TEMP TABLE u03_manifest_backfill (
    manifest_id uuid PRIMARY KEY,
    attempt_id uuid NOT NULL,
    evidence_ref text NOT NULL CHECK (length(btrim(evidence_ref)) > 0)
);
