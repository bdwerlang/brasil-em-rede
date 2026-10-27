#!/usr/bin/env python3
"""Ensure implemented pipelines in registry match runnable ETL pipelines."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from check_source_aliases import REPO_ROOT, check_source_aliases, pipeline_metadata


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def parse_registry_implemented(path: Path) -> set[str]:
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    implemented = {
        (row.get("pipeline_id") or "").strip()
        for row in rows
        if parse_bool(row.get("in_universe_v1", ""))
        and (row.get("implementation_state") or "").strip() == "implemented"
    }
    implemented.discard("")
    return implemented


def parse_runner_pipelines(path: Path) -> set[str]:
    return set(pipeline_metadata(path))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check implemented pipeline contracts")
    parser.add_argument("--registry-path", default="docs/source_registry_br_v1.csv")
    parser.add_argument("--runner-path", default="etl/src/bracc_etl/runner.py")
    args = parser.parse_args()

    implemented = parse_registry_implemented(Path(args.registry_path))
    runner = parse_runner_pipelines(Path(args.runner_path))

    missing = sorted(implemented - runner)
    extra = sorted(runner - implemented)

    print(f"implemented={len(implemented)} runner={len(runner)}")

    if missing or extra:
        print("FAIL")
        if missing:
            print(f"- implemented_not_in_runner={missing}")
        if extra:
            print(f"- runner_not_marked_implemented={extra}")
        return 1

    try:
        sources, runners = check_source_aliases(
            Path(args.registry_path),
            Path(args.runner_path),
            REPO_ROOT / "config/source_aliases.json",
            REPO_ROOT / "etl/src/bracc_etl/data/source_aliases.json",
        )
    except (ValueError, OSError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(f"source_aliases={sources} mapped_runners={runners}")
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
