"""Transactional operations for the PostgreSQL control catalog."""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import timedelta
from typing import Any
from uuid import UUID

# psycopg is installed only with the optional control extra.
from psycopg import Connection  # type: ignore[import-not-found,unused-ignore]
from psycopg.types.json import Jsonb  # type: ignore[import-not-found,unused-ignore]


class Catalog:
    """A caller supplies an authenticated connection and manages its lifetime."""

    def __init__(self, connection: Connection[Any]) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self) -> Iterator["Catalog"]:
        """Commit the group atomically, or roll it back when an operation fails."""
        with self.connection.transaction():
            yield self

    def artifact(self, artifact: UUID, partition: str, key: str, sha256: str, access: str) -> None:
        self.connection.execute(
            "INSERT INTO control.artifact VALUES (%s, %s, %s, %s, %s)",
            (artifact, partition, key, sha256, access),
        )

    def manifest(
        self, manifest: UUID, partition: str, artifacts: list[UUID], owner: UUID, token: int
    ) -> None:
        self.connection.execute(
            "SELECT control.finalize_manifest(%s, %s, %s, %s, %s)",
            (manifest, partition, artifacts, owner, token),
        )

    def quality(self, result: UUID, manifest: UUID, passed: bool, evidence: dict[str, Any]) -> None:
        self.connection.execute(
            "INSERT INTO control.quality_result VALUES (%s, %s, %s, %s)",
            (result, manifest, passed, Jsonb(evidence)),
        )

    def projection(self, job: UUID, outbox: UUID, manifest: UUID, version: str) -> None:
        self.connection.execute(
            "INSERT INTO control.projection_job VALUES (%s, %s, %s)", (job, manifest, version)
        )
        self.connection.execute(
            "INSERT INTO control.outbox (id, job_id) VALUES (%s, %s)", (outbox, job)
        )

    def acknowledge(self, outbox: UUID) -> None:
        result = self.connection.execute(
            "UPDATE control.outbox SET acknowledged_at = clock_timestamp() "
            "WHERE id = %s AND acknowledged_at IS NULL",
            (outbox,),
        )
        if result.rowcount != 1:
            raise ValueError("outbox missing or already acknowledged")

    def bundle(
        self, release: UUID, graph: str, contract: str, identity: str,
        members: Sequence[tuple[str, UUID]],
    ) -> None:
        if not members:
            raise ValueError("release requires partitions")
        self.connection.execute(
            "INSERT INTO control.release_bundle "
            "(id, status, graph_target, contract_version, identity_version) "
            "VALUES (%s, 'draft', %s, %s, %s)",
            (release, graph, contract, identity),
        )
        for partition, manifest in members:
            self.connection.execute(
                "INSERT INTO control.release_partition VALUES (%s, %s)", (release, partition)
            )
            self.connection.execute(
                "INSERT INTO control.release_manifest VALUES (%s, %s)", (release, manifest)
            )
        self.connection.execute(
            "UPDATE control.release_bundle SET status = 'verified' WHERE id = %s", (release,)
        )

    def lease(self, partition: str, owner: UUID, duration: timedelta) -> int | None:
        row = self.connection.execute(
            "SELECT control.acquire_lease(%s, %s, %s)", (partition, owner, duration)
        ).fetchone()
        if row is None:
            raise RuntimeError("lease query returned no row")
        return int(row[0]) if row[0] is not None else None

    def promote(
        self, release: UUID, previous: UUID | None, partition: str, owner: UUID, token: int
    ) -> None:
        self.connection.execute(
            "SELECT control.promote_release(%s, %s, %s, %s, %s)",
            (release, previous, partition, owner, token),
        )

    def active_release(self) -> UUID | None:
        row = self.connection.execute("SELECT release_id FROM control.active_release").fetchone()
        return UUID(str(row[0])) if row else None
