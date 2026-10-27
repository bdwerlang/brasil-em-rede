"""Read-only validation for bootstrap inputs and declared commands."""
from __future__ import annotations

import ast
import json
import shlex
import tomllib
from pathlib import Path


def runner_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "PIPELINES":
            if isinstance(node.value, ast.Dict):
                return {key.value for key in node.value.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)}
    raise ValueError("PIPELINES dictionary not found")


def cnpj_command_available(root: Path) -> bool:
    """Inspect the declared entry point and Click registration without importing ETL."""
    try:
        with (root / "etl/pyproject.toml").open("rb") as file:
            entrypoint = tomllib.load(file)["project"]["scripts"]["bracc-etl"]
        if entrypoint != "bracc_etl.runner:cli":
            return False
        tree = ast.parse((root / "etl/src/bracc_etl/runner.py").read_text(encoding="utf-8"))
        cli = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "cli")
        download = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "download")
        def decorators(node: ast.FunctionDef, owner: str, name: str) -> list[ast.Call]:
            return [d for d in node.decorator_list if isinstance(d, ast.Call)
                    and isinstance(d.func, ast.Attribute) and isinstance(d.func.value, ast.Name)
                    and d.func.value.id == owner and d.func.attr == name]
        if not decorators(cli, "click", "group") or not decorators(download, "cli", "command"):
            return False
        options = {arg.value for d in decorators(download, "click", "option")
                   for arg in d.args if isinstance(arg, ast.Constant) and isinstance(arg.value, str)}
        return {"--output-dir", "--files", "--skip-existing/--no-skip-existing"} <= options
    except (OSError, KeyError, SyntaxError, StopIteration, tomllib.TOMLDecodeError):
        return False


def diagnose(root: Path, contract: dict, registry_ids: set[str]) -> list[str]:
    errors: list[str] = []
    sources = contract.get("sources")
    if not isinstance(sources, list) or any(not isinstance(s, dict) for s in sources):
        return ["sources must be a list of objects"]
    ids = [s.get("pipeline_id") for s in sources]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        errors.append("source IDs must be nonempty and unique")
    ids_set = {i for i in ids if isinstance(i, str) and i}
    if len(ids_set) != contract.get("expected_implemented_count"):
        errors.append("contract count mismatch")
    if ids_set != registry_ids:
        errors.append(f"registry mismatch: missing={sorted(registry_ids - ids_set)} extra={sorted(ids_set - registry_ids)}")
    try:
        aliases = json.loads((root / "config/source_aliases.json").read_text(encoding="utf-8"))["sources"]
        mapping = {row["source_id"]: row.get("runner_name") for row in aliases}
        runners = runner_names(root / "etl/src/bracc_etl/runner.py")
        resolved = {mapping.get(i) for i in ids_set}
        missing = sorted(i for i in ids_set if not mapping.get(i) or mapping[i] not in runners)
        if missing or resolved != runners:
            errors.append(f"runner mismatch: unresolved={missing} unrepresented={sorted(runners - resolved)}")
    except (OSError, ValueError, KeyError, SyntaxError, TypeError) as exc:
        errors.append(f"cannot inspect aliases/runner: {exc}")
    for source in sources:
        name = source.get("pipeline_id", "?")
        mode = source.get("acquisition_mode")
        patterns = source.get("required_inputs", [])
        if not isinstance(patterns, list) or not patterns or any(not isinstance(p, str) or not p or Path(p).is_absolute() or '..' in Path(p).parts for p in patterns):
            errors.append(f"{name}: invalid required inputs")
        elif mode != "blocked_external":
            for pattern in patterns:
                if not any(root.glob(pattern)):
                    errors.append(f"{name}: missing input {pattern}")
        if mode not in {"file_manifest", "script_download", "blocked_external"}:
            errors.append(f"{name}: unsupported acquisition mode {mode}")
        if mode == "script_download":
            commands = source.get("download_commands", [])
            if not commands:
                errors.append(f"{name}: missing download command")
            for command in commands:
                # Supported contract command is the existing CNPJ CLI, with its real options.
                try:
                    tokens = shlex.split(command)
                except (ValueError, TypeError):
                    tokens = []
                if tokens != ["cd", "/workspace/etl", "&&", "bracc-etl", "download", "--output-dir", "../data/cnpj", "--files", "10", "--skip-existing"] or not cnpj_command_available(root):
                    errors.append(f"{name}: unsupported or missing download command")
    return errors
