import logging
import os
import re
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from neo4j import Driver
from neo4j.exceptions import TransientError

logger = logging.getLogger(__name__)
_SAFE_KEY = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_MAX_RETRIES = 5


@dataclass
class LoadMetrics:
    """Cumulative counts for this loader; writes count only committed transactions."""

    _lock: Any = field(default_factory=RLock, repr=False, compare=False)
    failed_batches: int = 0
    direct_updates: int = 0
    untracked_writes: int = 0
    submitted: int = 0
    attempts: int = 0  # batch executions, including retries
    rejected: int = 0  # rows missing required keys
    committed_rows: int = 0  # accepted input rows in committed batches
    verified_rows: int = 0  # input rows resolved by node/relationship loaders
    generic_updates: int = 0  # database update operations from arbitrary queries
    nodes_created: int = 0
    relationships_created: int = 0
    nodes_deleted: int = 0
    relationships_deleted: int = 0
    properties_set: int = 0
    labels_added: int = 0
    labels_removed: int = 0
    relationships_resolved: int = 0  # input rows with both endpoints
    unresolved: int = 0  # relationship rows without both endpoints


_active_load: ContextVar[tuple[Driver, LoadMetrics] | None] = ContextVar(
    "active_load", default=None
)
_active_metrics_lock = RLock()
_active_metrics_by_driver: dict[int, LoadMetrics] = {}


def register_active_metrics(driver: Driver, metrics: LoadMetrics) -> None:
    """Make a run's metrics discoverable by loaders created in worker threads."""
    with _active_metrics_lock:
        key = id(driver)
        current = _active_metrics_by_driver.get(key)
        if current is not None and current is not metrics:
            raise RuntimeError("concurrent pipeline runs cannot share one Neo4j driver")
        _active_metrics_by_driver[key] = metrics


def unregister_active_metrics(driver: Driver, metrics: LoadMetrics) -> None:
    with _active_metrics_lock:
        if _active_metrics_by_driver.get(id(driver)) is metrics:
            del _active_metrics_by_driver[id(driver)]


def active_metrics_for_driver(driver: Driver) -> LoadMetrics | None:
    with _active_metrics_lock:
        return _active_metrics_by_driver.get(id(driver))


class Neo4jBatchLoader:
    """Bulk loader with one atomic transaction per batch."""

    def __init__(
        self,
        driver: Driver,
        batch_size: int = 10_000,
        neo4j_database: str | None = None,
        metrics: LoadMetrics | None = None,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        self.driver = driver
        self.batch_size = batch_size
        self.neo4j_database = neo4j_database or os.getenv("NEO4J_DATABASE", "neo4j")
        active = _active_load.get()
        registered = active_metrics_for_driver(driver)
        self.metrics = (
            metrics
            if metrics is not None
            else active[1]
            if active is not None and active[0] is driver
            else registered
            if registered is not None
            else LoadMetrics()
        )
        self._total_written = 0

    def _run_batch_once(
        self, query: str, batch: list[dict[str, Any]], relationship: bool = False
    ) -> tuple[Any, int]:
        with (
            self.driver.session(database=self.neo4j_database) as session,
            session.begin_transaction() as tx,
        ):
            result = tx.run(query, {"rows": batch})
            resolved = 0
            if relationship:
                record = result.single(strict=True)
                resolved = record["resolved"]
                if record["ambiguous"] or not 0 <= resolved <= len(batch):
                    raise ValueError("relationship endpoint matches are not unique")
            summary = result.consume()
            tx.commit()
        return summary.counters, resolved

    def _run_batches(
        self,
        query: str,
        rows: list[dict[str, Any]],
        batch_size: int | None = None,
        relationship: bool = False,
        nodes: bool = False,
    ) -> int:
        size = self.batch_size if batch_size is None else batch_size
        if size <= 0:
            raise ValueError("batch_size must be positive")
        total = 0
        for i in range(0, len(rows), size):
            batch = rows[i : i + size]
            for attempt in range(_MAX_RETRIES):
                with self.metrics._lock:
                    self.metrics.attempts += 1
                try:
                    counters, resolved = self._run_batch_once(query, batch, relationship)
                    break
                except TransientError:
                    if attempt == _MAX_RETRIES - 1:
                        with self.metrics._lock:
                            self.metrics.failed_batches += 1
                        raise
                    wait = 2**attempt
                    logger.warning(
                        "Transient failure in batch %d; retrying in %ds", i // size, wait
                    )
                    time.sleep(wait)
                except Exception:
                    with self.metrics._lock:
                        self.metrics.failed_batches += 1
                    raise
            with self.metrics._lock:
                self.metrics.committed_rows += len(batch)
                self.metrics.nodes_created += counters.nodes_created
                self.metrics.relationships_created += counters.relationships_created
                self.metrics.nodes_deleted += counters.nodes_deleted
                self.metrics.relationships_deleted += counters.relationships_deleted
                self.metrics.properties_set += counters.properties_set
                self.metrics.labels_added += counters.labels_added
                self.metrics.labels_removed += counters.labels_removed
                if relationship:
                    self.metrics.verified_rows += resolved
                    self.metrics.relationships_resolved += resolved
                    self.metrics.unresolved += len(batch) - resolved
                    total += resolved
                elif nodes:
                    self.metrics.verified_rows += len(batch)
                    total += len(batch)
                else:
                    self.metrics.generic_updates += (
                        counters.nodes_created
                        + counters.relationships_created
                        + counters.nodes_deleted
                        + counters.relationships_deleted
                        + counters.properties_set
                        + counters.labels_added
                        + counters.labels_removed
                    )
                    total += len(batch)
            self._total_written += len(batch)
        return total

    def run_query_with_retry(
        self, query: str, rows: list[dict[str, Any]], batch_size: int = 500
    ) -> int:
        """Return committed input rows, not matched rows or writes.

        Arbitrary Cypher cannot establish per-input matches. Inspect metrics for
        actual database update counters; idempotent writes can have zero updates.
        """
        with self.metrics._lock:
            self.metrics.submitted += len(rows)
        return self._run_batches(query, rows, batch_size)

    def load_nodes(self, label: str, rows: list[dict[str, Any]], key_field: str) -> int:
        with self.metrics._lock:
            self.metrics.submitted += len(rows)
        accepted = [r for r in rows if r.get(key_field)]
        with self.metrics._lock:
            self.metrics.rejected += len(rows) - len(accepted)
        all_keys: set[str] = set()
        for row in accepted:
            all_keys.update(row.keys())
        all_keys.discard(key_field)
        all_keys = {key for key in all_keys if _SAFE_KEY.match(key)}
        props = ", ".join(f"n.{key} = row.{key}" for key in sorted(all_keys))
        set_clause = f"SET {props}" if props else ""
        query = (
            f"UNWIND $rows AS row MERGE (n:{label} {{{key_field}: row.{key_field}}}) {set_clause}"
        )
        return self._run_batches(query, accepted, nodes=True)

    def load_relationships(
        self,
        rel_type: str,
        rows: list[dict[str, Any]],
        source_label: str,
        source_key: str,
        target_label: str,
        target_key: str,
        properties: list[str] | None = None,
    ) -> int:
        with self.metrics._lock:
            self.metrics.submitted += len(rows)
        accepted = [r for r in rows if r.get("source_key") and r.get("target_key")]
        with self.metrics._lock:
            self.metrics.rejected += len(rows) - len(accepted)
        props = ""
        if properties:
            props = "SET " + ", ".join(f"r.{p} = row.{p}" for p in properties)
        query = (
            "UNWIND range(0, size($rows) - 1) AS idx WITH idx, $rows[idx] AS row "
            f"OPTIONAL MATCH (source:{source_label} {{{source_key}: row.source_key}}) "
            "WITH idx, row, collect(DISTINCT source) AS sources "
            f"OPTIONAL MATCH (target:{target_label} {{{target_key}: row.target_key}}) "
            "WITH idx, row, sources, collect(DISTINCT target) AS targets "
            "FOREACH (a IN CASE WHEN size(sources) = 1 AND size(targets) = 1 "
            "THEN sources ELSE [] END | "
            "FOREACH (b IN targets | "
            f"MERGE (a)-[r:{rel_type}]->(b) {props})) "
            "RETURN sum(CASE WHEN size(sources) = 1 AND size(targets) = 1 "
            "THEN 1 ELSE 0 END) AS resolved, "
            "sum(CASE WHEN size(sources) > 1 OR size(targets) > 1 "
            "THEN 1 ELSE 0 END) AS ambiguous"
        )
        return self._run_batches(query, accepted, relationship=True)

    def run_query(self, query: str, rows: list[dict[str, Any]]) -> int:
        """Return committed input rows, not matched rows or writes; see metrics."""
        with self.metrics._lock:
            self.metrics.submitted += len(rows)
        return self._run_batches(query, rows)
