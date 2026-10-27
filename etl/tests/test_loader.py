from unittest.mock import MagicMock, patch

import pytest
from neo4j.exceptions import TransientError

from bracc_etl.loader import Neo4jBatchLoader


def make_loader(batch_size=2):
    driver = MagicMock()
    session = driver.session.return_value.__enter__.return_value
    tx = session.begin_transaction.return_value.__enter__.return_value
    result = tx.run.return_value
    result.consume.return_value.counters.nodes_created = 0
    result.consume.return_value.counters.relationships_created = 0
    result.consume.return_value.counters.nodes_deleted = 0
    result.consume.return_value.counters.relationships_deleted = 0
    result.consume.return_value.counters.properties_set = 0
    result.consume.return_value.counters.labels_added = 0
    result.consume.return_value.counters.labels_removed = 0
    return Neo4jBatchLoader(driver, batch_size=batch_size), tx


def test_nodes_filter_and_commit_consumed_results():
    loader, tx = make_loader()
    assert loader.load_nodes("Company", [{"id": "1"}, {"id": ""}, {"id": "2"}], "id") == 2
    tx.run.return_value.consume.assert_called_once()
    tx.commit.assert_called_once()
    assert (loader.metrics.submitted, loader.metrics.rejected, loader.metrics.committed_rows) == (
        3,
        1,
        2,
    )
    assert loader.metrics.attempts == 1


def test_relationships_count_missing_endpoints_and_created():
    loader, tx = make_loader()
    result = tx.run.return_value
    result.single.return_value = {"resolved": 1, "ambiguous": 0}
    result.consume.return_value.counters.relationships_created = 1
    rows = [
        {"source_key": "a", "target_key": "b"},
        {"source_key": "a", "target_key": "missing"},
        {"source_key": ""},
    ]
    assert loader.load_relationships("REL", rows, "A", "id", "B", "id") == 1
    assert (loader.metrics.submitted, loader.metrics.rejected, loader.metrics.committed_rows) == (
        3,
        1,
        2,
    )
    assert (loader.metrics.relationships_resolved, loader.metrics.unresolved) == (1, 1)
    assert loader.metrics.relationships_created == 1


@patch("bracc_etl.loader.time.sleep")
def test_last_batch_failure_propagates_and_preserves_committed_counts(sleep):
    loader, tx = make_loader()
    result = tx.run.return_value
    result.consume.side_effect = [result.consume.return_value] + [TransientError("deadlock")] * 5
    with pytest.raises(TransientError):
        loader.run_query("UNWIND $rows AS row RETURN row", [{"id": i} for i in range(3)])
    assert loader.metrics.submitted == 3
    assert loader.metrics.committed_rows == 2
    assert loader.metrics.attempts == 6
    assert tx.commit.call_count == 1
    assert sleep.call_count == 4


@patch("bracc_etl.loader.time.sleep")
def test_retry_only_counts_committed_write(sleep):
    loader, tx = make_loader()
    result = tx.run.return_value
    result.consume.side_effect = [TransientError("deadlock"), result.consume.return_value]
    result.consume.return_value.counters.nodes_created = 1
    assert loader.run_query_with_retry("RETURN 1", [{"id": 1}]) == 1
    assert (
        loader.metrics.attempts,
        loader.metrics.committed_rows,
        loader.metrics.nodes_created,
    ) == (2, 1, 1)
    sleep.assert_called_once_with(1)


def test_nonpositive_batch_size_is_rejected():
    with pytest.raises(ValueError):
        Neo4jBatchLoader(MagicMock(), batch_size=0)
    loader, _ = make_loader()
    with pytest.raises(ValueError):
        loader.run_query_with_retry("RETURN 1", [], batch_size=0)


def test_explicit_metrics_are_shared_across_threads():
    from concurrent.futures import ThreadPoolExecutor

    from bracc_etl.loader import LoadMetrics

    metrics = LoadMetrics()

    def work(_):
        loader, tx = make_loader()
        loader = Neo4jBatchLoader(loader.driver, metrics=metrics)
        tx.run.return_value.consume.return_value.counters.nodes_created = 1
        loader.load_nodes("Node", [{"id": "x"}], "id")

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(work, range(40)))
    assert (metrics.submitted, metrics.attempts, metrics.verified_rows, metrics.nodes_created) == (
        40,
        40,
        40,
        40,
    )
