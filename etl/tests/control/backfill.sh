#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel)
name="bracc-u03-backfill-${$}-${RANDOM}"
image="bracc-u03-backfill-image-${$}-${RANDOM}:test"
a=$(mktemp -d)
cleanup() { docker stop -t 10 "$name" >/dev/null 2>&1 || true; docker rm -v "$name" >/dev/null 2>&1 || true; docker image rm "$image" >/dev/null 2>&1 || true; rm -rf "$a"; }
trap cleanup EXIT
docker build -t "$image" "$root/infra/postgres" >/dev/null
docker run -d --name "$name" --network none -e POSTGRES_PASSWORD=synthetic-only "$image" >/dev/null
ready=false
for _ in {1..60}; do
  if docker logs "$name" 2>&1 | grep -Fq 'PostgreSQL init process complete; ready for start up.' && docker exec "$name" pg_isready -U postgres >/dev/null 2>&1; then ready=true; break; fi
  sleep 1
done
[[ "$ready" == true ]]
sql() { docker exec -i "$name" psql -X -q -U postgres -v ON_ERROR_STOP=1 "$@"; }
for file in "$root"/infra/postgres/migrations/00{1,2,3}_*.sql; do sql < "$file"; done
sql <<'SQL'
INSERT INTO control.source VALUES ('s','public');
INSERT INTO control.dataset VALUES ('d','s','v1','public');
INSERT INTO control.partition VALUES ('p','d');
INSERT INTO control.run VALUES ('70000000-0000-0000-0000-000000000001','legacy');
INSERT INTO control.run_attempt(id,run_id) VALUES ('80000000-0000-0000-0000-000000000001','70000000-0000-0000-0000-000000000001');
INSERT INTO control.partition_manifest(id,partition_id,token) VALUES ('20000000-0000-0000-0000-000000000001','p',7);
INSERT INTO control.release_bundle(id,status,graph_target,contract_version,identity_version) VALUES ('30000000-0000-0000-0000-000000000001','verified','g','v','v');
INSERT INTO control.active_release(release_id) VALUES ('30000000-0000-0000-0000-000000000001');
SQL
# Missing mappings must roll back every DDL change and leave the active release intact.
if sql < "$root/infra/postgres/migrations/004_manifest_attempt.sql" > "$a/missing.log" 2>&1; then exit 1; fi
rg -q 'reviewed backfill mappings required' "$a/missing.log"
[[ $(sql -Atc "SELECT count(*) FROM control.schema_migration") == 3 ]]
[[ $(sql -Atc "SELECT count(*) FROM information_schema.columns WHERE table_schema='control' AND table_name='run_attempt' AND column_name='owner'") == 0 ]]
[[ $(sql -Atc 'SELECT release_id FROM control.active_release') == 30000000-0000-0000-0000-000000000001 ]]
# Incomplete mapping and a wrong fencing token both abort the whole migration.
cat "$root/infra/postgres/backfill/004_prepare.sql" > "$a/case.sql"
cat >> "$a/case.sql" <<'SQL'
INSERT INTO u03_attempt_backfill VALUES ('80000000-0000-0000-0000-000000000001','p','10000000-0000-0000-0000-000000000001',7,'synthetic-attempt-evidence');
SQL
cat "$root/infra/postgres/migrations/004_manifest_attempt.sql" >> "$a/case.sql"
if sql < "$a/case.sql" > "$a/partial.log" 2>&1; then exit 1; fi
rg -q 'backfill mappings must cover exactly' "$a/partial.log"
[[ $(sql -Atc 'SELECT count(*) FROM control.schema_migration') == 3 ]]
cat "$root/infra/postgres/backfill/004_prepare.sql" > "$a/case.sql"
cat >> "$a/case.sql" <<'SQL'
INSERT INTO u03_attempt_backfill VALUES ('80000000-0000-0000-0000-000000000001','p','10000000-0000-0000-0000-000000000001',8,'synthetic-attempt-evidence');
INSERT INTO u03_manifest_backfill VALUES ('20000000-0000-0000-0000-000000000001','80000000-0000-0000-0000-000000000001','synthetic-manifest-evidence');
SQL
cat "$root/infra/postgres/migrations/004_manifest_attempt.sql" >> "$a/case.sql"
if sql < "$a/case.sql" > "$a/mismatch.log" 2>&1; then exit 1; fi
rg -q 'manifest and attempt mapping disagree' "$a/mismatch.log"
[[ $(sql -Atc 'SELECT count(*) FROM control.schema_migration') == 3 ]]
[[ $(sql -Atc "SELECT count(*) FROM information_schema.columns WHERE table_schema='control' AND table_name='partition_manifest' AND column_name='run_attempt_id'") == 0 ]]
if sql -c "UPDATE control.partition_manifest SET token=8" >/dev/null 2>&1; then exit 1; fi
# Reviewed complete mapping migrates existing IDs and preserves the pointer.
cat "$root/infra/postgres/backfill/004_prepare.sql" > "$a/case.sql"
cat >> "$a/case.sql" <<'SQL'
INSERT INTO u03_attempt_backfill VALUES ('80000000-0000-0000-0000-000000000001','p','10000000-0000-0000-0000-000000000001',7,'synthetic-attempt-evidence');
INSERT INTO u03_manifest_backfill VALUES ('20000000-0000-0000-0000-000000000001','80000000-0000-0000-0000-000000000001','synthetic-manifest-evidence');
SQL
cat "$root/infra/postgres/migrations/004_manifest_attempt.sql" >> "$a/case.sql"
sql < "$a/case.sql"
[[ $(sql -Atc 'SELECT count(*) FROM control.schema_migration') == 4 ]]
[[ $(sql -Atc "SELECT run_attempt_id FROM control.partition_manifest WHERE id='20000000-0000-0000-0000-000000000001'") == 80000000-0000-0000-0000-000000000001 ]]
[[ $(sql -Atc 'SELECT release_id FROM control.active_release') == 30000000-0000-0000-0000-000000000001 ]]
[[ $(sql -Atc 'SELECT count(*) FROM control.manifest_backfill_evidence') == 1 ]]
if sql -c "UPDATE control.partition_manifest SET token=8" > /dev/null 2>&1; then exit 1; fi
if sql -c "UPDATE control.attempt_backfill_evidence SET evidence_ref='changed'" > /dev/null 2>&1; then exit 1; fi
printf 'U03 legacy backfill passed\n'
