"""Identity backfill for a frozen, isolated Neo4j snapshot.

Run only with writers stopped. The identity properties are kept on each legacy
node, so no node or relationship is recreated. A successful transaction is the
persisted mapping; retain the candidate snapshot for rebuilds and rollback.
"""

from typing import Any

from bracc_etl.identity.legacy import Assignment, LegacyEntity, propose

LABELS = (
    "Person",
    "Partner",
    "Company",
    "Contract",
    "Sanction",
    "Election",
    "Amendment",
    "Finance",
    "Embargo",
    "Health",
    "Education",
    "Convenio",
    "LaborStats",
    "PublicOffice",
)


class MigrationBlockedError(RuntimeError):
    """Preconditions failed; no identifying values are included in the message."""


def plan_snapshot(tx: Any, snapshot: str) -> tuple[list[Assignment], list[Any]]:
    records = list(
        tx.run(
            "MATCH (n) WHERE any(label IN labels(n) WHERE label IN $labels) "
            "RETURN elementId(n) AS legacy_id, labels(n) AS labels, "
            "n.cpf AS cpf, n.cnpj AS cnpj, n.entity_id AS entity_id",
            labels=list(LABELS),
        )
    )
    entities = []
    for r in records:
        labels = r["labels"]
        kind = "Person" if "Person" in labels else "Company" if "Company" in labels else "Other"
        entities.append(
            LegacyEntity(
                r["legacy_id"], kind, r["cpf"] if kind == "Person" else r["cnpj"], r["entity_id"]
            )
        )
    return propose(snapshot, entities)


def apply_snapshot(tx: Any, snapshot: str) -> dict[str, int]:
    """Plan and persist atomically; collisions abort without any writes.

    Collision values may be sensitive: never log or publish them. The exception
    reports only a count. Existing identity properties require manual review.
    """
    if not snapshot:
        raise ValueError("snapshot required")
    assignments, collisions = plan_snapshot(tx, snapshot)
    if collisions:
        raise MigrationBlockedError(f"{len(collisions)} strong identifier collision(s)")
    occupied = tx.run(
        "MATCH (n) WHERE n.identity_snapshot IS NOT NULL OR n.identity_legacy_id IS NOT NULL "
        "OR n.identity_migration IS NOT NULL RETURN count(n) AS count"
    ).single()["count"]
    if occupied:
        raise MigrationBlockedError("identity migration properties already present")
    rows = [{"legacy_id": a.legacy_id, "entity_id": a.entity_id} for a in assignments]
    # Pre-existing canonical IDs must be unique across all nodes, including nodes
    # outside the migration allowlist; otherwise transition lookup is ambiguous.
    ids = [a.entity_id for a in assignments]
    conflicting = tx.run(
        "MATCH (n) WHERE n.entity_id IN $ids RETURN n.entity_id AS id, count(n) AS count", ids=ids
    )
    if any(r["count"] > 1 for r in conflicting):
        raise MigrationBlockedError("duplicate canonical ID")
    result = tx.run(
        "UNWIND $rows AS row MATCH (n) WHERE elementId(n) = row.legacy_id "
        "SET n.identity_migration = CASE WHEN n.entity_id IS NULL "
        "THEN 'created' ELSE 'existing' END, "
        "n.entity_id = row.entity_id, n.identity_snapshot = $snapshot, "
        "n.identity_legacy_id = row.legacy_id "
        "RETURN count(n) AS count",
        rows=rows,
        snapshot=snapshot,
    ).single()["count"]
    if result != len(rows):
        raise MigrationBlockedError("snapshot changed during migration")
    return {"assigned": result, "collisions": 0}


def rollback_snapshot(
    tx: Any, snapshot: str, expected: list[Assignment], expected_states: dict[str, str]
) -> int:
    """Remove only properties introduced by this migration, preserving old IDs."""
    if not snapshot:
        raise ValueError("snapshot required")
    if any(a.snapshot != snapshot for a in expected):
        raise MigrationBlockedError("rollback snapshot mismatch")
    expected_map = {a.legacy_id: a.entity_id for a in expected}
    if len(expected_map) != len(expected) or len(set(expected_map.values())) != len(expected):
        raise MigrationBlockedError("duplicate rollback mapping")
    if set(expected_states) != set(expected_map) or any(
        state not in ("created", "existing") for state in expected_states.values()
    ):
        raise MigrationBlockedError("invalid rollback state manifest")
    records = list(
        tx.run(
            "MATCH (n) WHERE n.identity_snapshot = $snapshot "
            "RETURN n.identity_legacy_id AS legacy_id, n.entity_id AS entity_id, "
            "n.identity_migration AS migration",
            snapshot=snapshot,
        )
    )
    actual = {r["legacy_id"]: r["entity_id"] for r in records}
    if (
        len(actual) != len(records)
        or actual != expected_map
        or any(r["migration"] != expected_states.get(r["legacy_id"]) for r in records)
    ):
        raise MigrationBlockedError("inconsistent rollback metadata")
    result = tx.run(
        "MATCH (n) WHERE n.identity_snapshot = $snapshot "
        "WITH collect(n) AS nodes "
        "FOREACH (n IN nodes | "
        "  SET n.entity_id = CASE WHEN n.identity_migration = 'created' "
        "THEN null ELSE n.entity_id END "
        "  REMOVE n.identity_snapshot, n.identity_legacy_id, n.identity_migration) "
        "RETURN size(nodes) AS count",
        snapshot=snapshot,
    ).single()
    return int(result["count"])
