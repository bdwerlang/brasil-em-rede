#!/usr/bin/env bash
# Safe, explicit entry points for local demo bootstrap.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
usage() {
  cat <<'EOF'
Usage:
  scripts/bootstrap_public_demo.sh [--help]
  scripts/bootstrap_public_demo.sh --doctor
  scripts/bootstrap_public_demo.sh --seed-isolated --i-understand-isolated-demo

Default/help/--doctor are read-only. Isolated seeding delegates to
infra/scripts/seed-dev.sh, which creates a fresh random Compose project/volume.
The seed requires DEMO_NEO4J_PASSWORD. No full/download/ETL mode is supported.
Inherited NEO4J_URI, COMPOSE_PROJECT_NAME, DOWNLOAD and PIPELINES do not enable
writes; they are ignored by the wrapper.
EOF
}
fail() { printf 'bootstrap_public_demo: %s\n' "$1" >&2; exit 2; }
if [[ $# -eq 0 || "$1" == "--help" ]]; then
  [[ $# -eq 0 || $# -eq 1 ]] || fail "unexpected arguments"
  usage; exit 0
fi
if [[ "$1" == "--doctor" ]]; then
  [[ $# -eq 1 ]] || fail "--doctor takes no other options"
  exec python3 "$ROOT/scripts/run_bootstrap_all.py" --repo-root "$ROOT" --doctor
fi
[[ "$1" == "--seed-isolated" ]] || fail "unsupported option '$1'; no action taken"
[[ $# -eq 2 && "$2" == "--i-understand-isolated-demo" ]] || fail "isolated seed requires exactly --seed-isolated --i-understand-isolated-demo"
[[ -n "${DEMO_NEO4J_PASSWORD:-}" ]] || fail "set DEMO_NEO4J_PASSWORD explicitly; no fallback is used"
exec env -u NEO4J_URI -u COMPOSE_PROJECT_NAME -u DOWNLOAD -u PIPELINES bash "$ROOT/infra/scripts/seed-dev.sh"
