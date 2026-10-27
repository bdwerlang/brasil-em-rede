"""Versioned source identities, independent of ETL dependencies and host paths."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

SCHEMA_VERSION = 1
_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]*")
_FIELDS = {"source_id", "runner_name", "provider_id", "legacy_aliases"}


class UnknownSourceError(ValueError):
    """The identifier has no unambiguous entry in this map version."""


class UnimplementedSourceError(ValueError):
    """A catalog source exists but has no runnable pipeline."""


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def _identifier(value: object, field: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid {field}: {value!r}")
    return value


@dataclass(frozen=True)
class SourceIdentity:
    source_id: str
    runner_name: str | None
    provider_id: str | None
    legacy_aliases: tuple[str, ...]


class SourceAliases:
    def __init__(self, document: object) -> None:
        if not isinstance(document, dict) or set(document) != {"schema_version", "sources"}:
            raise ValueError("Expected source map with schema_version and sources")
        version = document["schema_version"]
        if type(version) is not int or version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported source alias schema version: {version!r}")
        rows = document["sources"]
        if not isinstance(rows, list) or not rows:
            raise ValueError("Source map must contain a nonempty sources list")
        self._sources: dict[str, SourceIdentity] = {}
        self._aliases: dict[str, SourceIdentity] = {}
        for row in rows:
            if not isinstance(row, dict) or set(row) != _FIELDS:
                raise ValueError(f"Invalid source map entry: {row!r}")
            source_id = _identifier(row["source_id"], "source_id")
            if source_id in self._sources:
                raise ValueError(f"Duplicate source_id: {source_id}")
            runner = row["runner_name"]
            provider = row["provider_id"]
            if (runner is None) != (provider is None):
                raise ValueError(
                    f"runner_name and provider_id must both be null or set: {source_id}"
                )
            runner_name = None if runner is None else _identifier(runner, "runner_name")
            provider_id = None if provider is None else _identifier(provider, "provider_id")
            legacy = row["legacy_aliases"]
            if not isinstance(legacy, list):
                raise ValueError(f"legacy_aliases must be a list: {source_id}")
            aliases = tuple(_identifier(alias, "legacy_alias") for alias in legacy)
            names = {source_id, runner_name, provider_id} - {None}
            if len(set(aliases)) != len(aliases) or set(aliases) & names:
                raise ValueError(f"Duplicate legacy alias: {source_id}")
            identity = SourceIdentity(source_id, runner_name, provider_id, aliases)
            for name in (*names, *aliases):
                if name is None:
                    continue
                if name in self._aliases:
                    other = self._aliases[name].source_id
                    raise ValueError(f"Ambiguous alias {name!r}: {other} and {source_id}")
                self._aliases[name] = identity
            self._sources[source_id] = identity

    @property
    def sources(self) -> tuple[SourceIdentity, ...]:
        return tuple(self._sources.values())

    def resolve(self, identifier: str, *, require_runner: bool = False) -> SourceIdentity:
        try:
            identity = self._aliases[identifier]
        except KeyError:
            raise UnknownSourceError(f"Unknown source ID or alias: {identifier!r}") from None
        if require_runner and identity.runner_name is None:
            raise UnimplementedSourceError(
                f"Source {identity.source_id!r} has no implemented runner"
            )
        return identity

    def for_pipeline(self, runner_name: str, provider_id: str) -> SourceIdentity:
        identity = self.resolve(runner_name, require_runner=True)
        if identity.runner_name != runner_name or identity.provider_id != provider_id:
            raise ValueError(
                f"Pipeline identity disagrees with source map: {runner_name}/{provider_id}"
            )
        return identity

    def for_run(self, record: Mapping[str, object]) -> SourceIdentity:
        """Interpret old source_id-only runs and verify explicitly stored identities."""
        version = record.get("source_aliases_version")
        if version is not None and (type(version) is not int or version != SCHEMA_VERSION):
            raise ValueError(f"Unsupported historical source alias version: {version!r}")
        identity = self.resolve(_identifier(record.get("source_id"), "historical source_id"))
        for field in ("runner_name", "provider_id"):
            value = record.get(field)
            if value is not None and value != getattr(identity, field):
                raise ValueError(
                    f"Conflicting historical {field} for {identity.source_id}: {value!r}"
                )
        return identity


def load_source_aliases(path: Path) -> SourceAliases:
    return SourceAliases(
        json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_json_object)
    )


@lru_cache(maxsize=1)
def source_aliases() -> SourceAliases:
    """Use the validated package copy, also available in wheels and ETL images."""
    resource = files("bracc_etl").joinpath("data/source_aliases.json")
    return SourceAliases(
        json.loads(resource.read_text(encoding="utf-8"), object_pairs_hook=_unique_json_object)
    )
