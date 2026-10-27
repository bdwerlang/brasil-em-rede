"""Transactional control catalog operations.

The caller owns connection, commit and rollback. Use a DB-API compatible
PostgreSQL driver and a restricted account with only approved operations.
"""

from datetime import timedelta
from typing import Any, Protocol
from uuid import UUID


class Cursor(Protocol):
    def execute(self, operation: str, parameters: tuple[Any, ...]) -> Any: ...

    def fetchone(self) -> tuple[Any, ...] | None: ...


def acquire_lease(cursor: Cursor, partition: str, owner: UUID, duration: timedelta) -> int | None:
    """Return a fencing token, or None if another worker holds the lease."""
    cursor.execute("SELECT control.acquire_lease(%s, %s, %s)", (partition, owner, duration))
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("lease query returned no row")
    return int(row[0]) if row[0] is not None else None


def finalize_manifest(
    cursor: Cursor, manifest: UUID, partition: str, artifacts: list[UUID], owner: UUID, token: int
) -> None:
    """Register an immutable manifest while its lease remains valid."""
    cursor.execute(
        "SELECT control.finalize_manifest(%s, %s, %s, %s, %s)",
        (manifest, partition, artifacts, owner, token),
    )


def promote_release(
    cursor: Cursor, release: UUID, previous: UUID | None, partition: str, owner: UUID, token: int
) -> None:
    """Compare and swap a verified release; database errors must abort the transaction."""
    cursor.execute(
        "SELECT control.promote_release(%s, %s, %s, %s, %s)",
        (release, previous, partition, owner, token),
    )
