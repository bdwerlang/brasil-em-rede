"""Immutable, checksummed identity map for a single frozen Neo4j snapshot.

Only opaque UUIDs and Neo4j element IDs are serialized; no source documents or
names belong here. Targets on rebuild must come from an independently verified
mapping of original element IDs to nodes in the candidate graph.
"""

import hashlib
import hmac
import json
import re
from pathlib import Path
from typing import Any
from uuid import UUID

from bracc_etl.identity.legacy import Assignment
from bracc_etl.identity.migration import LABELS, MigrationBlockedError, plan_snapshot

_ELEMENT_ID = re.compile(r"[0-9]+:[0-9a-fA-F-]{36}:[0-9]+\Z")
_SNAPSHOT = re.compile(r"[A-Za-z0-9_-]{1,80}\Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "ascii"
    )


def _validate(snapshot: str, rows: list[dict[str, str]]) -> None:
    if not _SNAPSHOT.fullmatch(snapshot) or not isinstance(rows, list):
        raise ValueError("invalid crosswalk")
    aliases, ids = set(), set()
    for row in rows:
        if set(row) != {"legacy_id", "entity_id"} or not _ELEMENT_ID.fullmatch(row["legacy_id"]):
            raise ValueError("invalid crosswalk entry")
        ident = str(UUID(row["entity_id"]))
        if ident != row["entity_id"] or row["legacy_id"] in aliases or ident in ids:
            raise ValueError("duplicate or invalid crosswalk entry")
        aliases.add(row["legacy_id"])
        ids.add(ident)


def export_crosswalk(path: Path, snapshot: str, assignments: list[Assignment]) -> str:
    if any(a.snapshot != snapshot for a in assignments):
        raise ValueError("snapshot mismatch")
    rows = sorted(
        ({"legacy_id": a.legacy_id, "entity_id": a.entity_id} for a in assignments),
        key=lambda x: x["legacy_id"],
    )
    _validate(snapshot, rows)
    payload = {"version": 1, "snapshot": snapshot, "entries": rows}
    digest = hashlib.sha256(_canonical(payload)).hexdigest()
    envelope = {"payload": payload, "sha256": digest}
    # Exclusive creation prevents accidental overwrite of an approved map.
    with path.open("xb") as stream:
        stream.write(_canonical(envelope) + b"\n")
    return digest


def read_crosswalk(path: Path) -> dict[str, Any]:
    envelope = json.loads(path.read_bytes())
    if set(envelope) != {"payload", "sha256"}:
        raise ValueError("invalid crosswalk envelope")
    payload = envelope["payload"]
    digest = hashlib.sha256(_canonical(payload)).hexdigest()
    if not isinstance(envelope["sha256"], str) or not hmac.compare_digest(
        digest, envelope["sha256"]
    ):
        raise ValueError("crosswalk checksum mismatch")
    if set(payload) != {"version", "snapshot", "entries"} or payload["version"] != 1:
        raise ValueError("unsupported crosswalk")
    _validate(payload["snapshot"], payload["entries"])
    return dict(payload)


def snapshot_assignments(tx: Any, snapshot: str) -> list[Assignment]:
    rows = tx.run(
        "MATCH (n) WHERE n.identity_snapshot = $snapshot "
        "RETURN n.identity_legacy_id AS legacy_id, n.entity_id AS entity_id",
        snapshot=snapshot,
    )
    return [Assignment(snapshot, r["legacy_id"], r["entity_id"]) for r in rows]


def restore_crosswalk(tx: Any, payload: dict[str, Any], targets: dict[str, str]) -> int:
    """Restore using a complete, externally verified alias->candidate element ID map."""
    if set(payload) != {"version", "snapshot", "entries"} or payload["version"] != 1:
        raise ValueError("unsupported crosswalk")
    snapshot, rows = payload["snapshot"], payload["entries"]
    _validate(snapshot, rows)
    aliases = {r["legacy_id"] for r in rows}
    if set(targets) != aliases or len(set(targets.values())) != len(targets):
        raise MigrationBlockedError("incomplete or ambiguous rebuild mapping")
    _, collisions = plan_snapshot(tx, snapshot)
    if collisions:
        raise MigrationBlockedError(f"{len(collisions)} strong identifier collision(s)")
    target_ids = list(targets.values())
    if any(not _ELEMENT_ID.fullmatch(x) for x in target_ids):
        raise MigrationBlockedError("invalid rebuild target")
    occupied = tx.run(
        "MATCH (n) WHERE n.entity_id IN $ids OR n.identity_snapshot IS NOT NULL "
        "OR n.identity_legacy_id IS NOT NULL OR n.identity_migration IS NOT NULL "
        "RETURN count(n) AS count",
        ids=[r["entity_id"] for r in rows],
    ).single()["count"]
    if occupied:
        raise MigrationBlockedError("identity properties already present")
    mapped = [{**r, "target_id": targets[r["legacy_id"]]} for r in rows]
    count = tx.run(
        "UNWIND $rows AS row MATCH (n) WHERE elementId(n) = row.target_id "
        "AND n.entity_id IS NULL AND any(label IN labels(n) WHERE label IN $labels) "
        "SET n.entity_id = row.entity_id, n.identity_snapshot = $snapshot, "
        "n.identity_legacy_id = row.legacy_id, n.identity_migration = 'created' "
        "RETURN count(n) AS count",
        rows=mapped,
        snapshot=snapshot,
        labels=list(LABELS),
    ).single()["count"]
    if count != len(rows):
        raise MigrationBlockedError("rebuild target missing or occupied")
    return int(count)
