#!/usr/bin/env bash
# Create a fresh, isolated demo graph and load fixtures into it.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${DEMO_NEO4J_PASSWORD:?Set DEMO_NEO4J_PASSWORD}"
# A random project name ensures every run has a distinct Compose volume.
DEMO_ID="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
PROJECT="bracc-demo-${DEMO_ID}"
VOLUME="${PROJECT}_demo-data"
if docker volume inspect "$VOLUME" >/dev/null 2>&1; then
  echo "Refusing to use an existing demo volume." >&2
  exit 1
fi
COMPOSE=(docker compose --project-name "$PROJECT" --file "${SCRIPT_DIR}/../docker-compose.demo.yml")
"${COMPOSE[@]}" up -d --wait neo4j
"${COMPOSE[@]}" exec -T neo4j sh -c 'exec cypher-shell -u neo4j -p "$DEMO_DB_PASSWORD"' < "${SCRIPT_DIR}/seed-dev.cypher"
echo "Demo fixture loaded into isolated project ${PROJECT}."
