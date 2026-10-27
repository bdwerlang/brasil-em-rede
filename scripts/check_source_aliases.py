#!/usr/bin/env python3
"""Check catalog/runner identities without importing pipelines or ETL dependencies."""

from __future__ import annotations

import argparse
import ast
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "etl/src"))

from bracc_etl.source_aliases import load_source_aliases  # noqa: E402


def pipeline_metadata(runner_path: Path) -> dict[str, tuple[str, str]]:
    tree = ast.parse(runner_path.read_text(encoding="utf-8"))
    imports = {
        alias.asname or alias.name: (node.module.rsplit(".", 1)[-1], alias.name)
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("bracc_etl.pipelines.")
        for alias in node.names
    }
    mappings = [
        node.value
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "PIPELINES"
    ]
    if len(mappings) != 1 or not isinstance(mappings[0], ast.Dict):
        raise ValueError("Cannot locate the runner PIPELINES mapping")
    metadata: dict[str, tuple[str, str]] = {}
    for key, value in zip(mappings[0].keys, mappings[0].values, strict=True):
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            raise ValueError("Pipeline runner key must be a literal string")
        if not isinstance(value, ast.Name) or value.id not in imports:
            raise ValueError(f"Pipeline class must have an explicit module import: {key.value}")
        module, class_name = imports[value.id]
        path = runner_path.parent / "pipelines" / f"{module}.py"
        classes = [
            node for node in ast.parse(path.read_text(encoding="utf-8")).body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        ]
        if len(classes) != 1 or key.value in metadata:
            raise ValueError(f"Duplicate or absent pipeline: {key.value}")
        attributes = {
            target.id: node.value.value
            for node in classes[0].body
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
            for target in node.targets
            if isinstance(target, ast.Name) and target.id in {"name", "source_id"}
        }
        name, provider = attributes.get("name"), attributes.get("source_id")
        if name != key.value or not isinstance(provider, str):
            raise ValueError(f"Pipeline metadata does not match runner: {key.value}")
        metadata[key.value] = (name, provider)
    return metadata


def check_source_aliases(
    registry_path: Path,
    runner_path: Path,
    aliases_path: Path,
    packaged_path: Path,
    *,
    check_packaged: bool = True,
) -> tuple[int, int]:
    aliases = load_source_aliases(aliases_path)
    with registry_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    catalog = {row["source_id"]: row for row in rows}
    if len(catalog) != len(rows):
        raise ValueError("Duplicate catalog source_id")
    if set(catalog) != {source.source_id for source in aliases.sources}:
        raise ValueError("Source map must cover exactly the catalog entries")
    metadata = pipeline_metadata(runner_path)
    runners = {source.runner_name for source in aliases.sources if source.runner_name is not None}
    if runners != set(metadata):
        raise ValueError("Source map and runnable pipeline set disagree")
    for identity in aliases.sources:
        row = catalog[identity.source_id]
        implemented = row["implementation_state"] == "implemented"
        expected = row["pipeline_id"] if implemented else None
        if identity.runner_name != expected:
            raise ValueError(
                f"Source map implementation differs from catalog: {identity.source_id}"
            )
        if identity.runner_name is not None:
            aliases.for_pipeline(*metadata[identity.runner_name])
    if check_packaged and aliases_path.read_bytes() != packaged_path.read_bytes():
        raise ValueError(
            "Packaged alias map is stale; run scripts/check_source_aliases.py --sync-package"
        )
    return len(catalog), len(metadata)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--sync-package", action="store_true", help="Update packaged map after validation"
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()
    aliases_path = root / "config/source_aliases.json"
    packaged_path = root / "etl/src/bracc_etl/data/source_aliases.json"
    try:
        catalog, runners = check_source_aliases(
            root / "docs/source_registry_br_v1.csv", root / "etl/src/bracc_etl/runner.py",
            aliases_path, packaged_path, check_packaged=not args.sync_package,
        )
        if args.sync_package:
            packaged_path.parent.mkdir(parents=True, exist_ok=True)
            packaged_path.write_bytes(aliases_path.read_bytes())
    except (ValueError, OSError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(f"PASS: source aliases catalog={catalog} runners={runners}; packaged map matches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
