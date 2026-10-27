"""Container readiness probe; /health remains the process liveness endpoint."""
import json
import sys
from urllib.request import urlopen


def ready() -> bool:
    from bracc.services.source_registry import load_source_registry

    entries = load_source_registry()
    if not entries or any(not entry.id for entry in entries):
        return False
    with urlopen("http://127.0.0.1:8000/api/v1/meta/health", timeout=3) as response:
        return json.load(response).get("neo4j") == "connected"


if __name__ == "__main__":
    try:
        sys.exit(0 if ready() else 1)
    except Exception:
        # Do not print URLs, credentials or exception contents into container logs.
        sys.exit(1)
