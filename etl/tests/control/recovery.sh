#!/usr/bin/env bash
set -euo pipefail
umask 077

# Destructive source-loss rehearsal using only uniquely named disposable
# networkless containers and synthetic PostgreSQL/filesystem data.
root=$(git rev-parse --show-toplevel)
tmp_root="$root/.hermes-run/tmp"
log_dir="$root/.hermes-run/logs"
log_file="$log_dir/U03-recovery-evidence.log"
mkdir -p "$tmp_root"
mkdir -p "$log_dir"
run_id="${$}-${RANDOM}"
run_dir="$tmp_root/u03-recovery-$run_id"
source_name="bracc-u03-recovery-source-$run_id"
restore_name="bracc-u03-recovery-restore-$run_id"
image="bracc-u03-recovery-image-$run_id:test"
mkdir -m 700 "$run_dir"
source_store="$run_dir/source-storage"
restore_store="$run_dir/restored-storage"
bundle="$run_dir/backup"
mkdir -m 700 "$source_store" "$bundle"
source_exists=false
restore_exists=false
image_exists=false
cleanup() {
  if [[ "$restore_exists" == true ]]; then docker rm -f "$restore_name" >/dev/null 2>&1 || true; fi
  if [[ "$source_exists" == true ]]; then docker rm -f "$source_name" >/dev/null 2>&1 || true; fi
  if [[ "$image_exists" == true ]]; then docker image rm "$image" >/dev/null 2>&1 || true; fi
  case "$run_dir" in "$tmp_root"/u03-recovery-*) rm -rf -- "$run_dir" ;; esac
}
trap 'status=$?; cleanup; exit "$status"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

exec > >(tee "$log_file") 2>&1

wait_ready() {
  local name=$1
  for _ in {1..90}; do
    if docker logs "$name" 2>&1 | grep -Fq 'PostgreSQL init process complete; ready for start up.' &&
      docker exec "$name" pg_isready -U postgres >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  echo "PostgreSQL did not become ready: $name" >&2
  return 1
}
start_cluster() {
  local name=$1
  docker run -d --name "$name" --network none -e POSTGRES_HOST_AUTH_METHOD=trust "$image" >/dev/null
  if [[ "$name" == "$source_name" ]]; then source_exists=true; else restore_exists=true; fi
  wait_ready "$name"
}
sql() { docker exec -i "$source_name" psql -X -q -U postgres -v ON_ERROR_STOP=1 "$@"; }
restored_sql() { docker exec -i "$restore_name" psql -X -q -U postgres -d restored -v ON_ERROR_STOP=1 "$@"; }

# Every migration runs against a newly created source cluster.
docker build -t "$image" "$root/infra/postgres" >/dev/null
image_exists=true
start_cluster "$source_name"
for migration in "$root"/infra/postgres/migrations/*.sql; do sql < "$migration"; done

# Distinct synthetic worker, projector, reader and app-schema state.
sql <<'SQL'
CREATE ROLE u03_recovery_worker LOGIN INHERIT;
CREATE ROLE u03_recovery_projector LOGIN INHERIT;
CREATE ROLE u03_recovery_reader LOGIN INHERIT;
GRANT bracc_control_worker TO u03_recovery_worker;
GRANT bracc_control_projector TO u03_recovery_projector;
GRANT bracc_control_reader TO u03_recovery_reader;
INSERT INTO control.worker_identity VALUES ('u03_recovery_worker','10000000-0000-0000-0000-000000000001');
INSERT INTO control.source VALUES ('src','public');
INSERT INTO control.dataset VALUES ('ds','src','v1','public');
INSERT INTO control.partition VALUES ('part-a','ds'),('part-b','ds'),('access-probe','ds');
INSERT INTO control.run VALUES ('70000000-0000-0000-0000-000000000001','recovery-run');
INSERT INTO control.run_attempt(id,run_id,partition_id,owner,token) VALUES
 ('80000000-0000-0000-0000-000000000001','70000000-0000-0000-0000-000000000001','part-a','10000000-0000-0000-0000-000000000001',1),
 ('80000000-0000-0000-0000-000000000002','70000000-0000-0000-0000-000000000001','part-b','10000000-0000-0000-0000-000000000001',1);
INSERT INTO control.partition_lease VALUES
 ('part-a','10000000-0000-0000-0000-000000000001',1,'2099-01-01T00:00:00Z'),
 ('part-b','10000000-0000-0000-0000-000000000001',1,'2099-01-01T00:00:00Z');
INSERT INTO app.users VALUES ('90000000-0000-0000-0000-000000000001');
INSERT INTO app.investigations VALUES ('90000000-0000-0000-0000-000000000002','90000000-0000-0000-0000-000000000001');
INSERT INTO app.annotations VALUES ('90000000-0000-0000-0000-000000000003','90000000-0000-0000-0000-000000000002','synthetic recovery annotation');
SQL

raw_bytes='synthetic raw recovery object v1\n'
parquet_bytes='PAR1synthetic parquet recovery object v1'
printf '%b' "$raw_bytes" > "$source_store/raw-src.tmp"
printf '%b' "$parquet_bytes" > "$source_store/parquet-src.tmp"
raw_hash=$(sha256sum "$source_store/raw-src.tmp" | cut -d' ' -f1)
parquet_hash=$(sha256sum "$source_store/parquet-src.tmp" | cut -d' ' -f1)
mkdir -p "$source_store/raw/src/ds/part-a" "$source_store/parquet/ds/v1/part-b"
mv "$source_store/raw-src.tmp" "$source_store/raw/src/ds/part-a/$raw_hash"
mv "$source_store/parquet-src.tmp" "$source_store/parquet/ds/v1/part-b/$parquet_hash.parquet"

sql <<SQL
INSERT INTO control.artifact VALUES
 ('00000000-0000-0000-0000-000000000001','part-a','raw/src/ds/part-a/$raw_hash','$raw_hash','public'),
 ('00000000-0000-0000-0000-000000000002','part-b','parquet/ds/v1/part-b/$parquet_hash.parquet','$parquet_hash','public');
INSERT INTO control.acquisition(id,artifact_id) VALUES
 ('b0000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000001'),
 ('b0000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000002');
INSERT INTO control.partition_manifest(id,partition_id,token,run_attempt_id) VALUES
 ('20000000-0000-0000-0000-000000000001','part-a',1,'80000000-0000-0000-0000-000000000001'),
 ('20000000-0000-0000-0000-000000000002','part-b',1,'80000000-0000-0000-0000-000000000002');
INSERT INTO control.manifest_artifact VALUES
 ('20000000-0000-0000-0000-000000000001','part-a','00000000-0000-0000-0000-000000000001'),
 ('20000000-0000-0000-0000-000000000002','part-b','00000000-0000-0000-0000-000000000002');
INSERT INTO control.quality_result VALUES
 ('40000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',true,'{"fixture":"synthetic-a"}'),
 ('40000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000002',true,'{"fixture":"synthetic-b"}');
INSERT INTO control.projection_job VALUES
 ('50000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','projection-v1'),
 ('50000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000002','projection-v1');
INSERT INTO control.outbox VALUES
 ('60000000-0000-0000-0000-000000000001','50000000-0000-0000-0000-000000000001','2099-01-01T00:00:00Z'),
 ('60000000-0000-0000-0000-000000000002','50000000-0000-0000-0000-000000000002',NULL);
INSERT INTO control.release_bundle VALUES
 ('30000000-0000-0000-0000-000000000001','draft','synthetic-graph-prior','v1','identity-v1','2026-01-01T00:00:00Z'),
 ('30000000-0000-0000-0000-000000000002','draft','synthetic-graph-active','v1','identity-v1','2026-01-02T00:00:00Z');
INSERT INTO control.release_partition VALUES
 ('30000000-0000-0000-0000-000000000001','part-a'),
 ('30000000-0000-0000-0000-000000000002','part-a');
INSERT INTO control.release_manifest VALUES
 ('30000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001'),
 ('30000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000001');
UPDATE control.release_bundle SET status='verified';
INSERT INTO control.active_release VALUES (true,'30000000-0000-0000-0000-000000000002');
INSERT INTO control.entity VALUES ('a0000000-0000-0000-0000-000000000001');
INSERT INTO control.identifier VALUES ('synthetic','test','entity-1','a0000000-0000-0000-0000-000000000001');
INSERT INTO control.identity_decision VALUES ('a1000000-0000-0000-0000-000000000001','a0000000-0000-0000-0000-000000000001','identity-v1','{"source":"synthetic"}');
SQL

# Inventories include every control/app table, role attributes, memberships and schema DDL.
write_db_inventory() {
  local container=$1 output=$2 database=$3
  : > "$output"
  while IFS= read -r table; do
    printf 'TABLE|%s\n' "$table" >> "$output"
    docker exec "$container" psql -X -q -U postgres -d "$database" -Atc \
      "COPY (SELECT 'ROW|'||row_to_json(t)::text FROM $table AS t ORDER BY row_to_json(t)::text) TO STDOUT" >> "$output"
  done < <(docker exec "$container" psql -X -q -U postgres -d "$database" -Atc \
    "SELECT quote_ident(schemaname)||'.'||quote_ident(tablename) FROM pg_tables WHERE schemaname IN ('control','app') ORDER BY schemaname,tablename")
  docker exec "$container" psql -X -q -U postgres -d "$database" -Atc \
    "SELECT 'ROLE|'||rolname||'|'||rolsuper||'|'||rolinherit||'|'||rolcreaterole||'|'||rolcreatedb||'|'||rolcanlogin||'|'||rolreplication||'|'||rolbypassrls||'|'||rolconnlimit||'|'||coalesce(rolvaliduntil::text,'')||'|'||coalesce(array_to_string(rolconfig,','),'') FROM pg_roles WHERE rolname LIKE 'bracc_control_%' OR rolname LIKE 'u03_recovery_%' ORDER BY rolname" >> "$output"
  docker exec "$container" psql -X -q -U postgres -d "$database" -Atc \
    "SELECT 'MEMBER|'||parent.rolname||'|'||member.rolname||'|'||m.admin_option FROM pg_auth_members m JOIN pg_roles parent ON parent.oid=m.roleid JOIN pg_roles member ON member.oid=m.member WHERE parent.rolname LIKE 'bracc_control_%' OR member.rolname LIKE 'u03_recovery_%' ORDER BY 1" >> "$output"
  docker exec "$container" pg_dump -U postgres -d "$database" --schema-only -n control -n app |
    sed '/^\\restrict /d; /^\\unrestrict /d' | sha256sum | cut -d' ' -f1 | sed 's/^/SCHEMA_SHA256|/' >> "$output"
}
write_object_inventory() {
  local db_container=$1 storage=$2 output=$3 database=${4:-postgres}
  local expected_hash actual_hash
  : > "$output"
  while IFS='|' read -r key expected_hash; do
    [[ -n "$key" ]] || continue
    [[ -f "$storage/$key" ]] || { echo "missing object: $key" >&2; return 1; }
    actual_hash=$(sha256sum "$storage/$key" | cut -d' ' -f1)
    [[ "$actual_hash" == "$expected_hash" ]] || { echo "catalog hash mismatch: $key" >&2; return 1; }
    printf '%s|%s\n' "$key" "$actual_hash" >> "$output"
  done < <(docker exec "$db_container" psql -X -q -U postgres -d "$database" -Atc "SELECT object_key || chr(124) || sha256 FROM control.artifact ORDER BY object_key")
  local actual="$run_dir/actual-objects.tmp"
  local unsupported
  unsupported=$(find "$storage" ! -type d ! -type f -print -quit)
  [[ -z "$unsupported" ]] || { echo "unsupported storage entry: $unsupported" >&2; return 1; }
  while IFS= read -r -d '' file; do
    local key=${file#"$storage"/}
    printf '%s|%s\n' "$key" "$(sha256sum "$file" | cut -d' ' -f1)" >> "$actual"
  done < <(find "$storage" -type f -print0 | sort -z)
  sort -o "$output" "$output"
  sort -o "$actual" "$actual"
  diff -u "$output" "$actual"
  rm -f "$actual"
}

write_db_inventory "$source_name" "$run_dir/before-db.inventory" postgres
write_object_inventory "$source_name" "$source_store" "$run_dir/before-objects.inventory"
docker exec "$source_name" pg_dumpall -U postgres --globals-only > "$bundle/globals.sql"
chmod 600 "$bundle/globals.sql"
docker exec "$source_name" pg_dump -U postgres -Fc postgres > "$bundle/catalog.dump"
tar --sort=name --mtime='@0' --owner=0 --group=0 --numeric-owner -cf "$bundle/storage.tar" -C "$source_store" .
cp "$run_dir/before-db.inventory" "$bundle/before-db.inventory"
cp "$run_dir/before-objects.inventory" "$bundle/before-objects.inventory"
chmod 600 "$bundle/catalog.dump" "$bundle/storage.tar"
(
  cd "$bundle"
  sha256sum globals.sql catalog.dump storage.tar > SHA256SUMS
  sha256sum before-db.inventory before-objects.inventory >> SHA256SUMS
)
chmod 600 "$bundle/SHA256SUMS"
[[ $(stat -c '%a' "$bundle/globals.sql") == 600 ]]
[[ $(stat -c '%a' "$bundle/catalog.dump") == 600 ]]
[[ $(stat -c '%a' "$bundle/storage.tar") == 600 ]]
(cd "$bundle" && sha256sum --check SHA256SUMS)

# Prove source is present before the destructive phase, then remove it and its storage.
if docker inspect "$source_name" >/dev/null 2>&1; then
  echo 'PASS: red-phase assertion detects available source before failure injection'
else
  echo 'FAIL: source unexpectedly absent before backup' >&2
  exit 1
fi
docker rm -f "$source_name" >/dev/null
source_exists=false
rm -rf -- "$source_store"
[[ ! -e "$source_store" ]]
if docker inspect "$source_name" >/dev/null 2>&1; then
  echo 'FAIL: source cluster still exists after simulated failure' >&2
  exit 1
fi
echo 'PASS: simulated source loss removed the source cluster and source storage'

# From this point onward, every restore input is read only from the backup bundle.
docker run -d --name "$restore_name" --network none -e POSTGRES_HOST_AUTH_METHOD=trust "$image" >/dev/null
restore_exists=true
wait_ready "$restore_name"
sed '/^CREATE ROLE postgres;$/d' "$bundle/globals.sql" > "$run_dir/globals-restore.sql"
chmod 600 "$run_dir/globals-restore.sql"
docker exec -i "$restore_name" psql -X -q -U postgres -d postgres -v ON_ERROR_STOP=1 < "$run_dir/globals-restore.sql"
docker exec "$restore_name" createdb -U postgres restored
docker exec -i "$restore_name" pg_restore -U postgres -d restored --exit-on-error < "$bundle/catalog.dump"
mkdir -m 700 "$restore_store"
tar -xf "$bundle/storage.tar" -C "$restore_store"

write_db_inventory "$restore_name" "$run_dir/after-db.inventory" restored
write_object_inventory "$restore_name" "$restore_store" "$run_dir/after-objects.inventory" restored
diff -u "$bundle/before-db.inventory" "$run_dir/after-db.inventory"
diff -u "$bundle/before-objects.inventory" "$run_dir/after-objects.inventory"
[[ $(restored_sql -Atc 'SELECT count(*) FROM control.schema_migration') == 5 ]]
[[ $(restored_sql -Atc 'SELECT release_id FROM control.active_release') == 30000000-0000-0000-0000-000000000002 ]]
[[ $(restored_sql -Atc "SELECT count(*) FROM control.release_bundle WHERE status='verified'") == 2 ]]
[[ $(restored_sql -Atc 'SELECT count(*) FROM app.annotations') == 1 ]]
[[ $(restored_sql -Atc "SELECT count(*) FROM control.outbox WHERE id='60000000-0000-0000-0000-000000000002' AND acknowledged_at IS NULL") == 1 ]]
[[ $(restored_sql -Atc "SELECT count(*) FROM control.release_manifest WHERE manifest_id='20000000-0000-0000-0000-000000000002'") == 0 ]]
echo 'PASS: deterministic control/app/role inventory, migrations, active+prior releases, and object catalog/hash inventory match'

# Verify expected post-restore behavior without relying on the lost source.
restored_sql -c "SET SESSION AUTHORIZATION u03_recovery_reader; SELECT release_id FROM control.active_release; RESET SESSION AUTHORIZATION"
if restored_sql -c "SET SESSION AUTHORIZATION u03_recovery_reader; UPDATE control.outbox SET acknowledged_at=clock_timestamp(); RESET SESSION AUTHORIZATION" >/dev/null 2>&1; then
  echo 'FAIL: reader unexpectedly updated outbox' >&2; exit 1
fi
if restored_sql -c "SET SESSION AUTHORIZATION u03_recovery_worker; UPDATE control.active_release SET release_id=release_id; RESET SESSION AUTHORIZATION" >/dev/null 2>&1; then
  echo 'FAIL: worker unexpectedly updated active release directly' >&2; exit 1
fi
privileges=$(restored_sql -Atc "SELECT has_function_privilege('u03_recovery_worker','control.acquire_lease(text,uuid,interval)','EXECUTE') || '|' || has_table_privilege('u03_recovery_worker','control.active_release','UPDATE') || '|' || has_table_privilege('u03_recovery_reader','control.active_release','SELECT') || '|' || has_column_privilege('u03_recovery_projector','control.outbox','acknowledged_at','UPDATE')")
[[ "$privileges" == 'true|false|true|true' ]]
[[ $(restored_sql -Atc "SELECT owner FROM control.worker_identity WHERE login='u03_recovery_worker'") == 10000000-0000-0000-0000-000000000001 ]]
restored_sql -c "SET SESSION AUTHORIZATION u03_recovery_projector; UPDATE control.outbox SET acknowledged_at=clock_timestamp() WHERE id='60000000-0000-0000-0000-000000000002' AND acknowledged_at IS NULL; RESET SESSION AUTHORIZATION"
[[ $(restored_sql -Atc "SELECT count(*) FROM control.outbox WHERE id='60000000-0000-0000-0000-000000000002' AND acknowledged_at IS NOT NULL") == 1 ]]
restored_sql -c "SET SESSION AUTHORIZATION u03_recovery_worker; SELECT control.acquire_lease('access-probe','10000000-0000-0000-0000-000000000001',interval '1 hour'); RESET SESSION AUTHORIZATION"
echo 'PASS: restored reader/worker/projector identities and least-privilege behavior verified'
printf 'U03 synthetic destructive recovery passed; source-loss, globals+DB restore, and storage reconciliation verified.\n'
printf 'LOG: %s\n' "$log_file"
printf 'INTERIM: Correções revistas; status=awaiting_review. Validações: bash -n etl/tests/control/recovery.sh; bash etl/tests/control/recovery.sh; git diff --check; verificações de caminho e whitespace.\n'
