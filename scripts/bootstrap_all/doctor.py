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


def runner_import_issues(root: Path, path: Path) -> list[str]:
    """Check that every statically imported pipeline class has a physical module."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    issues: list[str] = []
    available = {
        node.name for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        available.update(alias.asname or alias.name for alias in node.names)
        if not node.module or not node.module.startswith("bracc_etl.pipelines."):
            continue
        relative = Path(*node.module.split(".")[2:]).with_suffix(".py")
        module_path = root / "etl/src/bracc_etl/pipelines" / relative
        if not module_path.is_file():
            issues.append(f"missing pipeline module {node.module}")
            continue
        try:
            module_tree = ast.parse(module_path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError) as exc:
            issues.append(f"cannot inspect pipeline module {node.module}: {exc}")
            continue
        defined = {
            item.name for item in module_tree.body
            if isinstance(item, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        defined.update(
            target.id for item in module_tree.body
            if isinstance(item, (ast.Assign, ast.AnnAssign))
            for target in (item.targets if isinstance(item, ast.Assign) else [item.target])
            if isinstance(target, ast.Name)
        )
        for imported in node.names:
            if imported.name not in defined:
                issues.append(f"missing {imported.name} in pipeline module {node.module}")
    for node in tree.body:
        if not isinstance(node, ast.AnnAssign) or not isinstance(node.target, ast.Name) or node.target.id != "PIPELINES":
            continue
        if isinstance(node.value, ast.Dict):
            for value in node.value.values:
                if isinstance(value, ast.Name) and value.id not in available:
                    issues.append(f"PIPELINES references undefined class {value.id}")
    return issues


def runner_registry_issues(path: Path) -> list[str]:
    """Reject duplicate literal keys that Python would silently overwrite."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "PIPELINES":
            if isinstance(node.value, ast.Dict):
                keys = [key.value for key in node.value.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)]
                if len(keys) != len(set(keys)):
                    return ["PIPELINES contains duplicate keys"]
    return []


def click_command_available(root: Path, command: str, required_options: set[str]) -> bool:
    """Inspect the declared entry point and Click command without importing ETL."""
    try:
        with (root / "etl/pyproject.toml").open("rb") as file:
            entrypoint = tomllib.load(file)["project"]["scripts"]["bracc-etl"]
        if entrypoint != "bracc_etl.runner:cli":
            return False
        tree = ast.parse((root / "etl/src/bracc_etl/runner.py").read_text(encoding="utf-8"))
        cli = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "cli")
        target = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == command)
        def decorators(node: ast.FunctionDef, owner: str, name: str) -> list[ast.Call]:
            return [d for d in node.decorator_list if isinstance(d, ast.Call)
                    and isinstance(d.func, ast.Attribute) and isinstance(d.func.value, ast.Name)
                    and d.func.value.id == owner and d.func.attr == name]
        if not decorators(cli, "click", "group") or not decorators(target, "cli", "command"):
            return False
        options = {arg.value for d in decorators(target, "click", "option")
                   for arg in d.args if isinstance(arg, ast.Constant) and isinstance(arg.value, str)}
        return required_options <= options
    except (OSError, KeyError, SyntaxError, StopIteration, tomllib.TOMLDecodeError):
        return False


def cnpj_command_available(root: Path) -> bool:
    return click_command_available(
        root,
        "download",
        {"--output-dir", "--files", "--skip-existing/--no-skip-existing"},
    )


def diagnose(root: Path, contract: dict, registry_ids: set[str], *, check_inputs: bool = True) -> list[str]:
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
        if not isinstance(aliases, list) or any(not isinstance(row, dict) for row in aliases):
            raise ValueError("aliases sources must be a list")
        mapping = {row["source_id"]: row.get("runner_name") for row in aliases}
        runner_path = root / "etl/src/bracc_etl/runner.py"
        runners = runner_names(runner_path)
        errors.extend(runner_import_issues(root, runner_path))
        errors.extend(runner_registry_issues(runner_path))
        if not click_command_available(
            root,
            "run",
            {"--source", "--neo4j-uri", "--neo4j-user", "--neo4j-password", "--neo4j-database", "--data-dir", "--linking-tier"},
        ):
            errors.append("ETL run command is missing or lacks required bootstrap options")
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
        elif check_inputs and mode != "blocked_external":
            for pattern in patterns:
                if not any(path.is_file() for path in root.glob(pattern)):
                    errors.append(f"{name}: missing input {pattern}")
        if mode not in {"file_manifest", "script_download", "blocked_external"}:
            errors.append(f"{name}: unsupported acquisition mode {mode}")
        if mode != "script_download" and source.get("download_commands"):
            errors.append(f"{name}: download commands require script_download mode")
        if mode == "script_download":
            commands = source.get("download_commands", [])
            if not isinstance(commands, list) or any(not isinstance(command, str) for command in commands):
                errors.append(f"{name}: download_commands must be a list of strings")
                continue
            if not commands:
                errors.append(f"{name}: missing download command")
            for command in commands:
                # Supported contract command is the existing CNPJ CLI, with its real options.
                try:
                    tokens = shlex.split(command)
                except (ValueError, TypeError):
                    tokens = []
                # CNPJ has specific command format and requires CLI availability
                if name == "cnpj":
                    expected = ["cd", "/workspace/etl", "&&", "bracc-etl", "download", "--output-dir", "../data/cnpj", "--files", "10", "--skip-existing"]
                    if tokens != expected or not cnpj_command_available(root):
                        errors.append(f"{name}: unsupported or missing download command")
                # Other sources: validate command is parseable (format check for shell syntax)
                elif not tokens:
                    errors.append(f"{name}: invalid download command syntax")
    return errors
