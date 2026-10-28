#!/usr/bin/env bash
set -euo pipefail

# Disposable U03 database only: networkless container + Unix socket, always removed.
root=$(git rev-parse --show-toplevel)
if [[ -n "${BRACC_TEST_PYTHON:-}" ]]; then
  bridge_python=$BRACC_TEST_PYTHON
elif [[ -x "$root/etl/.venv/bin/python" ]]; then
  bridge_python="$root/etl/.venv/bin/python"
else
  bridge_python=$(command -v python3 || true)
fi
if [[ -z "$bridge_python" || ! -x "$bridge_python" ]]; then
  echo "Python interpreter unavailable; set BRACC_TEST_PYTHON" >&2
  exit 2
fi
if ! "$bridge_python" -c 'import psycopg' >/dev/null 2>&1; then
  echo "psycopg is missing; install ETL control extra or set BRACC_TEST_PYTHON" >&2
  exit 2
fi
name="bracc-acq-bridge-${$}-${RANDOM}"
image="bracc-acq-bridge-${$}-${RANDOM}:test"
tmp=$(mktemp -d)
chmod 755 "$tmp"
mkdir "$tmp/socket"
chmod 777 "$tmp/socket"
cleanup() {
  docker stop -t 5 "$name" >/dev/null 2>&1 || true
  docker rm -v "$name" >/dev/null 2>&1 || true
  docker image rm "$image" >/dev/null 2>&1 || true
  rm -rf "$tmp"
}
trap cleanup EXIT

docker build -t "$image" "$root/infra/postgres" >/dev/null
docker run -d --name "$name" --network none \
  -v "$tmp/socket:/var/run/postgresql" -e POSTGRES_PASSWORD=synthetic-only "$image" >/dev/null
ready=false
for _ in {1..60}; do
  if docker logs "$name" 2>&1 | grep -Fq 'PostgreSQL init process complete; ready for start up.' &&
    docker exec "$name" pg_isready -U postgres >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done
[[ "$ready" == true ]]
for file in "$root"/infra/postgres/migrations/*.sql; do
  docker exec -i "$name" psql -X -q -U postgres -v ON_ERROR_STOP=1 < "$file"
done
docker exec -i "$name" psql -X -q -U postgres -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO control.source VALUES ('cnpj','public');
INSERT INTO control.dataset VALUES ('cnpj','cnpj','v1','public'),('other','cnpj','v1','public');
INSERT INTO control.partition VALUES ('2026-01','cnpj');
SQL
PYTHONPATH="$root/etl/src" "$bridge_python" "$root/etl/tests/control/acquisition_bridge_postgres.py" "$tmp/socket"
