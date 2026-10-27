#!/usr/bin/env bash
set -euo pipefail
# Runs only in a new networkless disposable container. No host port or existing DB.
root=$(git rev-parse --show-toplevel)
name="bracc-u03-test-${$}-${RANDOM}"
a=$(mktemp -d)
chmod 755 "$a"
mkdir "$a/socket"
chmod 777 "$a/socket"
cleanup() { docker stop -t 10 "$name" >/dev/null 2>&1 || true; docker rm -v "$name" >/dev/null 2>&1 || true; rm -rf "$a"; }
trap cleanup EXIT
docker run -d --name "$name" --network none -v "$a/socket:/var/run/postgresql" -e POSTGRES_PASSWORD=synthetic-only postgres:16-alpine >/dev/null
for _ in {1..60}; do
  if docker exec "$name" pg_isready -U postgres >/dev/null 2>&1; then break; fi
  sleep 1
done
sql() { docker exec -i "$name" psql -X -q -U postgres -v ON_ERROR_STOP=1 "$@"; }
for file in "$root"/infra/postgres/migrations/*.sql; do sql < "$file"; done
sql < "$root/etl/tests/control/fixture.sql"
if sql -c "INSERT INTO control.artifact VALUES ('00000000-0000-0000-0000-000000000009','p','raw/s/../p/' || repeat('a',64),repeat('a',64),'public')" 2>/dev/null; then exit 1; fi
# A worker can call an explicitly granted function but cannot write tables.
sql <<'SQL'
CREATE ROLE u03_test_worker LOGIN;
CREATE ROLE u03_w1 LOGIN;
CREATE ROLE u03_w2 LOGIN;
CREATE ROLE u03_w3 LOGIN;
CREATE ROLE u03_projector LOGIN;
CREATE ROLE u03_reader LOGIN;
GRANT bracc_control_projector TO u03_projector;
GRANT bracc_control_reader TO u03_reader;
GRANT bracc_control_worker TO u03_w1, u03_w2, u03_w3;
INSERT INTO control.worker_identity VALUES ('u03_test_worker','10000000-0000-0000-0000-000000000004'),('u03_w1','10000000-0000-0000-0000-000000000001'),('u03_w2','10000000-0000-0000-0000-000000000002'),('u03_w3','10000000-0000-0000-0000-000000000003');
GRANT USAGE ON SCHEMA control TO u03_test_worker;
GRANT EXECUTE ON FUNCTION control.acquire_lease(text, uuid, interval) TO u03_test_worker;
SQL
if sql -c "SET ROLE u03_test_worker; INSERT INTO control.active_release(release_id) VALUES ('00000000-0000-0000-0000-000000000001')" 2>/dev/null; then exit 1; fi
sql -c "SET SESSION AUTHORIZATION u03_test_worker; SELECT control.acquire_lease('p','10000000-0000-0000-0000-000000000004',interval '1 second')"
sql -c "UPDATE control.partition_lease SET expires_at=clock_timestamp()-interval '1 second' WHERE partition_id='p'; DELETE FROM control.partition_lease WHERE partition_id='p'"
# Concurrent workers: exactly one receives a lease.
sql -Atc "SET SESSION AUTHORIZATION u03_w1; SELECT control.acquire_lease('p','10000000-0000-0000-0000-000000000001',interval '1 hour')" > "$a/one" & first=$!
sql -Atc "SET SESSION AUTHORIZATION u03_w2; SELECT control.acquire_lease('p','10000000-0000-0000-0000-000000000002',interval '1 hour')" > "$a/two" & second=$!
wait "$first"; wait "$second"
[[ $(cat "$a/one" "$a/two" | rg -c '^1$') == 1 ]]
owner=$(sql -Atc "SELECT owner FROM control.partition_lease WHERE partition_id='p'")
if [[ "$owner" == 10000000-0000-0000-0000-000000000001 ]]; then worker=u03_w1; else worker=u03_w2; fi
sql -c "SET SESSION AUTHORIZATION $worker; SELECT control.finalize_manifest('20000000-0000-0000-0000-000000000001','p',ARRAY['00000000-0000-0000-0000-000000000001'::uuid],'$owner',1)"
# Duplicate finalization fails under the same token.
if sql -c "SET SESSION AUTHORIZATION $worker; SELECT control.finalize_manifest('20000000-0000-0000-0000-000000000002','p',ARRAY['00000000-0000-0000-0000-000000000001'::uuid],'$owner',1)" 2>/dev/null; then exit 1; fi
sql -c "UPDATE control.partition_lease SET expires_at=clock_timestamp()-interval '1 second' WHERE partition_id='p'"
sql -c "SET SESSION AUTHORIZATION u03_w3; SELECT control.acquire_lease('p','10000000-0000-0000-0000-000000000003',interval '1 hour')"
if sql -c "SET SESSION AUTHORIZATION $worker; SELECT control.finalize_manifest('20000000-0000-0000-0000-000000000002','p',ARRAY['00000000-0000-0000-0000-000000000001'::uuid],'$owner',1)" 2>/dev/null; then exit 1; fi
# A previous active bundle remains visible through failed promotion.
# This synthetic object has no catalog row and cannot change the pointer.
docker exec "$name" sh -c "printf orphan > /tmp/orphan-object"
sql <<'SQL'
INSERT INTO control.release_bundle(id,status,graph_target,contract_version,identity_version) VALUES ('30000000-0000-0000-0000-000000000001','verified','g1','v1','v1'),('30000000-0000-0000-0000-000000000002','draft','g2','v1','v1');
INSERT INTO control.active_release(release_id) VALUES ('30000000-0000-0000-0000-000000000001');
INSERT INTO control.release_partition VALUES ('30000000-0000-0000-0000-000000000002','p');
INSERT INTO control.release_manifest VALUES ('30000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000001');
UPDATE control.release_bundle SET status='verified' WHERE id='30000000-0000-0000-0000-000000000002';
SQL
if sql -c "SET SESSION AUTHORIZATION $worker; SELECT control.promote_release('30000000-0000-0000-0000-000000000002','30000000-0000-0000-0000-000000000001','p','$owner',1)" 2>/dev/null; then exit 1; fi
[[ $(sql -Atc 'SELECT release_id FROM control.active_release') == 30000000-0000-0000-0000-000000000001 ]]
sql <<'SQL'
SET SESSION AUTHORIZATION u03_w3; SELECT control.finalize_manifest('20000000-0000-0000-0000-000000000002','p',ARRAY['00000000-0000-0000-0000-000000000001'::uuid],'10000000-0000-0000-0000-000000000003',2); RESET SESSION AUTHORIZATION;
INSERT INTO control.release_bundle(id,status,graph_target,contract_version,identity_version) VALUES ('30000000-0000-0000-0000-000000000003','draft','g3','v1','v1');
INSERT INTO control.partition VALUES ('q','d');
INSERT INTO control.artifact VALUES ('00000000-0000-0000-0000-000000000002','q','raw/s/d/q/' || repeat('b',64),repeat('b',64),'public');
SET SESSION AUTHORIZATION u03_w3; SELECT control.acquire_lease('q','10000000-0000-0000-0000-000000000003',interval '1 hour');
SELECT control.finalize_manifest('20000000-0000-0000-0000-000000000003','q',ARRAY['00000000-0000-0000-0000-000000000002'::uuid],'10000000-0000-0000-0000-000000000003',1); RESET SESSION AUTHORIZATION;
INSERT INTO control.release_partition VALUES ('30000000-0000-0000-0000-000000000003','p'),('30000000-0000-0000-0000-000000000003','q');
INSERT INTO control.release_manifest VALUES ('30000000-0000-0000-0000-000000000003','20000000-0000-0000-0000-000000000003');
INSERT INTO control.quality_result VALUES ('40000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000003',true,'{}');
INSERT INTO control.projection_job VALUES ('50000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000003','v1');
INSERT INTO control.outbox VALUES ('60000000-0000-0000-0000-000000000002','50000000-0000-0000-0000-000000000002',clock_timestamp());
INSERT INTO control.release_manifest VALUES ('30000000-0000-0000-0000-000000000003','20000000-0000-0000-0000-000000000002');
INSERT INTO control.quality_result VALUES ('40000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002',true,'{}');
INSERT INTO control.projection_job VALUES ('50000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002','v1');
INSERT INTO control.outbox(id,job_id) VALUES ('60000000-0000-0000-0000-000000000001','50000000-0000-0000-0000-000000000001');
UPDATE control.release_bundle SET status='verified' WHERE id='30000000-0000-0000-0000-000000000003';
SQL
if sql -c "SET SESSION AUTHORIZATION u03_w3; INSERT INTO control.release_manifest VALUES ('30000000-0000-0000-0000-000000000003','20000000-0000-0000-0000-000000000002')" 2>/dev/null; then exit 1; fi
if sql -c "UPDATE control.release_partition SET partition_id='q' WHERE release_id='30000000-0000-0000-0000-000000000003' AND partition_id='p'" 2>/dev/null; then exit 1; fi
promote="SET SESSION AUTHORIZATION u03_w3; SELECT control.promote_release('30000000-0000-0000-0000-000000000003','30000000-0000-0000-0000-000000000001','p','10000000-0000-0000-0000-000000000003',2)"
if sql -c "$promote" 2>/dev/null; then exit 1; fi
[[ $(sql -Atc 'SELECT release_id FROM control.active_release') == 30000000-0000-0000-0000-000000000001 ]]
if sql -c "SET SESSION AUTHORIZATION u03_w1; SELECT control.acquire_lease('q','10000000-0000-0000-0000-000000000003',interval '1 hour')" 2>/dev/null; then exit 1; fi
if sql -c "SET SESSION AUTHORIZATION u03_reader; UPDATE control.outbox SET acknowledged_at=clock_timestamp()" 2>/dev/null; then exit 1; fi
sql -c "SET SESSION AUTHORIZATION u03_reader; SELECT release_id FROM control.active_release"
if sql -c "SET SESSION AUTHORIZATION u03_w3; UPDATE control.outbox SET acknowledged_at=clock_timestamp()" 2>/dev/null; then exit 1; fi
sql -c "SET SESSION AUTHORIZATION u03_projector; UPDATE control.outbox SET acknowledged_at=clock_timestamp() WHERE id='60000000-0000-0000-0000-000000000001'"
# A different partition's expired lease must also block promotion.
sql -c "UPDATE control.partition_lease SET expires_at=clock_timestamp()-interval '1 second' WHERE partition_id='q'"
if sql -c "$promote" 2>/dev/null; then exit 1; fi
[[ $(sql -Atc 'SELECT release_id FROM control.active_release') == 30000000-0000-0000-0000-000000000001 ]]
sql -c "UPDATE control.partition_lease SET expires_at=clock_timestamp()+interval '1 hour' WHERE partition_id='q'"
sql -c "$promote"
if sql -c "$promote" 2>/dev/null; then exit 1; fi
[[ $(sql -Atc 'SELECT release_id FROM control.active_release') == 30000000-0000-0000-0000-000000000003 ]]
# Exercise the shipped psycopg API over the container's isolated Unix socket.
sql -c "INSERT INTO control.partition VALUES ('r','d')"
PYTHONPATH="$root/etl/src" "$root/etl/.venv/bin/python" - "$a/socket" <<'PYAPI'
import sys
import psycopg
from bracc_etl.control.catalog import Catalog
from datetime import timedelta
from uuid import UUID
u = UUID
with psycopg.connect(host=sys.argv[1], user="u03_w3", dbname="postgres") as conn:
    with Catalog(conn).transaction() as catalog:
        token = catalog.lease("r", u("10000000-0000-0000-0000-000000000003"), timedelta(hours=1))
        assert token == 1
        catalog.artifact(u("00000000-0000-0000-0000-000000000003"), "r", "raw/s/d/r/" + "c" * 64, "c" * 64, "public")
        catalog.artifact(u("00000000-0000-0000-0000-000000000004"), "r", "parquet/d/v1/r/" + "d" * 64 + ".parquet", "d" * 64, "public")
        catalog.manifest(u("20000000-0000-0000-0000-000000000004"), "r", [u("00000000-0000-0000-0000-000000000003"), u("00000000-0000-0000-0000-000000000004")], u("10000000-0000-0000-0000-000000000003"), token)
        catalog.quality(u("40000000-0000-0000-0000-000000000003"), u("20000000-0000-0000-0000-000000000004"), True, {})
        catalog.projection(u("50000000-0000-0000-0000-000000000003"), u("60000000-0000-0000-0000-000000000003"), u("20000000-0000-0000-0000-000000000004"), "v1")
        catalog.bundle(u("30000000-0000-0000-0000-000000000004"), "g4", "v1", "v1", [("r", u("20000000-0000-0000-0000-000000000004"))])
with psycopg.connect(host=sys.argv[1], user="u03_projector", dbname="postgres") as conn:
    with Catalog(conn).transaction() as catalog:
        catalog.acknowledge(u("60000000-0000-0000-0000-000000000003"))
with psycopg.connect(host=sys.argv[1], user="u03_w3", dbname="postgres") as conn:
    with Catalog(conn).transaction() as catalog:
        catalog.promote(u("30000000-0000-0000-0000-000000000004"), u("30000000-0000-0000-0000-000000000003"), "r", u("10000000-0000-0000-0000-000000000003"), 1)
with psycopg.connect(host=sys.argv[1], user="u03_reader", dbname="postgres") as conn:
    with Catalog(conn).transaction() as catalog:
        assert str(catalog.active_release()) == "30000000-0000-0000-0000-000000000004"
PYAPI
[[ $(sql -Atc "SELECT count(*) FROM control.manifest_artifact WHERE manifest_id='20000000-0000-0000-0000-000000000004'") == 2 ]]
# A positive result cannot override a failed quality result.
sql <<'SQL'
INSERT INTO control.partition VALUES ('s','d');
INSERT INTO control.artifact VALUES ('00000000-0000-0000-0000-000000000005','s','raw/s/d/s/' || repeat('e',64),repeat('e',64),'public');
SET SESSION AUTHORIZATION u03_w3;
SELECT control.acquire_lease('s','10000000-0000-0000-0000-000000000003',interval '1 hour');
SELECT control.finalize_manifest('20000000-0000-0000-0000-000000000005','s',ARRAY['00000000-0000-0000-0000-000000000005'::uuid],'10000000-0000-0000-0000-000000000003',1);
RESET SESSION AUTHORIZATION;
INSERT INTO control.quality_result VALUES ('40000000-0000-0000-0000-000000000005','20000000-0000-0000-0000-000000000005',true,'{}'),('40000000-0000-0000-0000-000000000006','20000000-0000-0000-0000-000000000005',false,'{}');
INSERT INTO control.projection_job VALUES ('50000000-0000-0000-0000-000000000005','20000000-0000-0000-0000-000000000005','v1');
INSERT INTO control.outbox VALUES ('60000000-0000-0000-0000-000000000005','50000000-0000-0000-0000-000000000005',clock_timestamp());
INSERT INTO control.release_bundle(id,status,graph_target,contract_version,identity_version) VALUES ('30000000-0000-0000-0000-000000000005','draft','g5','v1','v1');
INSERT INTO control.release_partition VALUES ('30000000-0000-0000-0000-000000000005','s');
INSERT INTO control.release_manifest VALUES ('30000000-0000-0000-0000-000000000005','20000000-0000-0000-0000-000000000005');
UPDATE control.release_bundle SET status='verified' WHERE id='30000000-0000-0000-0000-000000000005';
SQL
if sql -c "SET SESSION AUTHORIZATION u03_w3; SELECT control.promote_release('30000000-0000-0000-0000-000000000005','30000000-0000-0000-0000-000000000004','s','10000000-0000-0000-0000-000000000003',1)" 2>/dev/null; then exit 1; fi
if sql -c "INSERT INTO control.quality_result VALUES ('40000000-0000-0000-0000-000000000007','20000000-0000-0000-0000-000000000005',true,'{}')" 2>/dev/null; then exit 1; fi
docker exec "$name" pg_dump -U postgres -Fc -f /tmp/control.dump postgres
docker exec "$name" createdb -U postgres restored
docker exec "$name" pg_restore -U postgres -d restored --exit-on-error /tmp/control.dump
[[ $(sql -d restored -Atc 'SELECT count(*) FROM control.schema_migration') == 3 ]]
[[ $(sql -Atc 'SELECT release_id FROM control.active_release') == $(sql -d restored -Atc 'SELECT release_id FROM control.active_release') ]]
[[ $(sql -Atc "SELECT string_agg(manifest_id::text || ':' || artifact_id::text, ',' ORDER BY manifest_id, artifact_id) FROM control.manifest_artifact") == $(sql -d restored -Atc "SELECT string_agg(manifest_id::text || ':' || artifact_id::text, ',' ORDER BY manifest_id, artifact_id) FROM control.manifest_artifact") ]]
[[ $(sql -Atc "SELECT string_agg(release_id::text || ':' || manifest_id::text, ',' ORDER BY release_id, manifest_id) FROM control.release_manifest") == $(sql -d restored -Atc "SELECT string_agg(release_id::text || ':' || manifest_id::text, ',' ORDER BY release_id, manifest_id) FROM control.release_manifest") ]]
printf 'U03 synthetic integration passed\n'
