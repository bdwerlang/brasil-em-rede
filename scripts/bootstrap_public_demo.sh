#!/usr/bin/env bash
# bootstrap_public_demo.sh - Bootstrap script for public demo purposes
# WARNING: This script DOWNSIZES the Neo4j graph with seed-dev.cypher
# which executes: MATCH (n) DETACH DELETE n
# Use --reset only when intentionally clearing the database.
# Without --reset, this script will still run but will NOT execute seed.

set -euo pipefail

PROFILE="demo"
PIPELINES="${PIPELINES:-cnpj,tse,transparencia,sanctions}"
DOWNLOAD="${DOWNLOAD:-false}"
NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_DATABASE="${NEO4J_DATABASE:-neo4j}"
CNPJ_FILES="${CNPJ_FILES:-1}"
RUN_SEED=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --pipelines)
      PIPELINES="$2"
      shift 2
      ;;
    --download)
      DOWNLOAD="true"
      shift
      ;;
    --no-download)
      DOWNLOAD="false"
      shift
      ;;
    --reset)
      RUN_SEED="true"
      shift
      ;;
    --no-reset)
      RUN_SEED="false"
      shift
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --profile demo|full    Profile mode (default: demo)"
      echo "  --pipelines LIST       Comma-separated pipeline list (default: cnpj,tse,transparencia,sanctions)"
      echo "  --download             Enable download stage"
      echo "  --no-download          Disable download stage"
      echo "  --reset                REQUIRED: Run seed which DETACH DELETES all graph data"
      echo "  --no-reset             Skip seed (safe, no data modification)"
      echo "  --help                 Show this help message"
      echo ""
      echo "WARNING: seed-dev.cypher contains 'MATCH (n) DETACH DELETE n'"
      echo "         This will permanently delete all graph data. Use --reset only when intended."
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ "$PROFILE" != "demo" && "$PROFILE" != "full" ]]; then
  echo "Invalid --profile value: $PROFILE (expected demo|full)" >&2
  exit 1
fi

# Warn if --reset is not explicitly set when running seed
if [[ "$RUN_SEED" == "false" && "$PROFILE" == "demo" ]]; then
  echo "WARNING: Running in demo mode with --no-reset (default)." >&2
  echo "         Seed will be SKIPPED. Use --reset to load demo data (DELETES existing data)." >&2
fi

if [[ -z "${NEO4J_PASSWORD:-}" && -f .env ]]; then
  NEO4J_PASSWORD="$(grep -E '^NEO4J_PASSWORD=' .env | tail -n 1 | cut -d '=' -f2- || true)"
  export NEO4J_PASSWORD
fi

if [[ -z "${NEO4J_PASSWORD:-}" ]]; then
  NEO4J_PASSWORD="changeme"
  export NEO4J_PASSWORD
  echo "NEO4J_PASSWORD was not set; using fallback 'changeme'." >&2
fi

echo "Starting Docker stack (profile=$PROFILE)..."
docker compose -f infra/docker-compose.yml up -d

echo "Waiting for Neo4j container health..."
for _ in $(seq 1 60); do
  if docker exec bracc-neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "RETURN 1" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! docker exec bracc-neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "RETURN 1" >/dev/null 2>&1; then
  echo "Neo4j health check failed." >&2
  exit 1
fi

echo "Waiting for API health endpoint..."
for _ in $(seq 1 60); do
  if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
  echo "API health check failed at http://localhost:8000/health" >&2
  exit 1
fi

if [[ "$RUN_SEED" == "true" ]]; then
  echo "WARNING: Loading deterministic development seed (DELETES existing graph data)..."
  echo "Running: MATCH (n) DETACH DELETE n in seed-dev.cypher" >&2
  NEO4J_URI="$NEO4J_URI" NEO4J_DATABASE="$NEO4J_DATABASE" NEO4J_PASSWORD="$NEO4J_PASSWORD" bash infra/scripts/seed-dev.sh
else
  echo "Skipping seed (graph remains unmodified)." >&2
fi

if [[ "$PROFILE" == "full" ]]; then
  if ! command -v uv >/dev/null 2>&1; then
    echo "uv is required for full profile." >&2
    exit 1
  fi

  echo "Preparing ETL environment..."
  (cd etl && uv sync)

  if [[ "$DOWNLOAD" == "true" ]]; then
    echo "Running optional download stage..."
    if [[ "$PIPELINES" == *"cnpj"* ]]; then
      (cd etl && uv run bracc-etl download --output-dir ../data/cnpj --files "$CNPJ_FILES" --skip-existing)
    fi
    if [[ "$PIPELINES" == *"comprasnet"* ]]; then
      python3 scripts/download_comprasnet.py 2024
    fi
    if [[ "$PIPELINES" == *"datasus"* ]]; then
      python3 scripts/download_datasus.py
    fi
  fi

  echo "Running ETL pipelines: $PIPELINES"
  IFS=',' read -r -a pipeline_array <<< "$PIPELINES"
  for source in "${pipeline_array[@]}"; do
    source="$(echo "$source" | xargs)"
    if [[ -z "$source" ]]; then
      continue
    fi
    echo "- ETL source: $source"
    (cd etl && uv run bracc-etl run --source "$source" --neo4j-uri "$NEO4J_URI" --neo4j-password "$NEO4J_PASSWORD" --neo4j-database "$NEO4J_DATABASE" --data-dir ../data)
  done
fi

seed_nodes="$(docker exec bracc-neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "MATCH (n) RETURN count(n) AS c" --format plain 2>/dev/null | tail -n 1 | tr -d '[:space:]')"

echo "Bootstrap complete."
echo "- API: http://localhost:8000/health"
echo "- Frontend: http://localhost:3000"
echo "- Neo4j Browser: http://localhost:7474"
echo "- Current graph node count: ${seed_nodes:-unknown}"