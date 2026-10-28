"""Build a non-destructive identity proposal for one frozen snapshot.

The caller must persist the returned UUIDs and snapshot alias map before using
it. This module deliberately performs no database writes or identity merges.
"""

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID, uuid4

from bracc_etl.transforms.document_formatting import (
    normalize_cnpj,
    validate_cnpj,
    validate_cpf,
)


@dataclass(frozen=True)
class LegacyEntity:
    legacy_id: str
    kind: str
    document: str | None = None
    entity_id: str | None = None


@dataclass(frozen=True)
class Assignment:
    snapshot: str
    legacy_id: str
    entity_id: str


@dataclass(frozen=True)
class Collision:
    # Do not publish this value: it may contain a personal document.
    namespace: str
    value: str
    legacy_ids: tuple[str, ...]


def propose(
    snapshot: str, entities: list[LegacyEntity]
) -> tuple[list[Assignment], list[Collision]]:
    """Assign opaque IDs per node; report strong-document collisions separately.

    An existing ID is retained; callers must restore this map on rebuild.
    Duplicate identifiers are never used to fuse nodes. Only valid full CPF and
    CNPJ are considered; masked values, names and roots do not establish identity.
    """
    if not snapshot or len({e.legacy_id for e in entities}) != len(entities):
        raise ValueError("snapshot and distinct legacy IDs required")
    if any(not e.legacy_id for e in entities):
        raise ValueError("legacy ID required")
    ids = [str(UUID(e.entity_id)) if e.entity_id else str(uuid4()) for e in entities]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate canonical ID")
    assignments = [
        Assignment(snapshot, e.legacy_id, ident) for e, ident in zip(entities, ids, strict=True)
    ]
    index: dict[tuple[str, str], list[str]] = defaultdict(list)
    for entity in entities:
        raw = entity.document or ""
        if entity.kind == "Person" and validate_cpf(raw):
            value = raw.strip().replace(".", "").replace("-", "")
            index[("br:cpf", value)].append(entity.legacy_id)
        elif entity.kind == "Company" and validate_cnpj(raw):
            index[("br:cnpj:establishment", normalize_cnpj(raw))].append(entity.legacy_id)
    collisions = [
        Collision(ns, value, tuple(sorted(legacy_ids)))
        for (ns, value), legacy_ids in sorted(index.items())
        if len(legacy_ids) > 1
    ]
    return assignments, collisions
