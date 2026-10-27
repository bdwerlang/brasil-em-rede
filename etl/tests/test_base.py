import hashlib
import json
from unittest.mock import MagicMock

import pytest

from bracc_etl.base import EmptyLoadEvidence, Pipeline
from bracc_etl.loader import Neo4jBatchLoader
from bracc_etl.source_aliases import UnknownSourceError


class DummyPipeline(Pipeline):
    name = "cnpj"
    source_id = "receita_federal"

    def __init__(self) -> None:
        super().__init__(driver=MagicMock(), data_dir="./data")
        self.extracted = False
        self.transformed = False
        self.loaded = False

    def extract(self) -> None:
        self.extracted = True

    def transform(self) -> None:
        self.transformed = True

    def load(self) -> None:
        self.loaded = True
        session = self.driver.session.return_value.__enter__.return_value
        tx = session.begin_transaction.return_value.__enter__.return_value
        counters = tx.run.return_value.consume.return_value.counters
        counters.nodes_created = 1
        counters.relationships_created = 0
        Neo4jBatchLoader(self.driver).load_nodes("Test", [{"id": "1"}], "id")


def test_pipeline_run_executes_all_stages() -> None:
    pipeline = DummyPipeline()
    pipeline.run()
    assert pipeline.extracted
    assert pipeline.transformed
    assert pipeline.loaded


def test_ingestion_run_stores_all_identities_without_changing_legacy_data_id() -> None:
    pipeline = DummyPipeline()
    original_run_id = pipeline.run_id
    driver = MagicMock()
    pipeline.driver = driver
    pipeline._upsert_ingestion_run(status="running")
    session = driver.session.return_value.__enter__.return_value
    query, params = session.run.call_args.args
    assert params["source_id"] == "cnpj"
    assert params["runner_name"] == "cnpj"
    assert params["provider_id"] == "receita_federal"
    assert params["source_aliases_version"] == 1
    assert params["run_id"] == original_run_id
    assert pipeline.source_id == "receita_federal"
    assert "r.provider_id = $provider_id" in query


def test_unregistered_pipeline_is_rejected() -> None:
    class UnregisteredPipeline(DummyPipeline):
        name = "unknown_source"
        source_id = "unknown_provider"

    with pytest.raises(UnknownSourceError):
        UnregisteredPipeline()


def test_empty_load_requires_evidence_and_records_failure() -> None:
    pipeline = DummyPipeline()
    pipeline.load = lambda: None
    with pytest.raises(ValueError, match="empty load requires evidence"):
        pipeline.run()
    session = pipeline.driver.session.return_value.__enter__.return_value
    assert session.run.call_args.args[1]["status"] == "quality_fail"


def test_empty_load_with_evidence_is_recorded(tmp_path) -> None:
    pipeline = DummyPipeline()
    pipeline.load = lambda: None
    content = json.dumps({"source_id": "cnpj", "record_count": 0}).encode()
    path = tmp_path / "manifest.json"
    path.write_bytes(content)
    pipeline.empty_load_evidence = EmptyLoadEvidence(str(path), hashlib.sha256(content).hexdigest())
    pipeline.run()
    session = pipeline.driver.session.return_value.__enter__.return_value
    params = session.run.call_args.args[1]
    assert params["status"] == "loaded"
    assert params["empty_load_evidence_sha256"] == pipeline.empty_load_evidence.sha256


def test_pipeline_does_not_succeed_when_run_status_cannot_be_persisted() -> None:
    pipeline = DummyPipeline()
    result = pipeline.driver.session.return_value.__enter__.return_value.run.return_value
    result.consume.side_effect = [None, RuntimeError("status unavailable"), None]
    with pytest.raises(RuntimeError, match="status unavailable"):
        pipeline.run()
    assert pipeline.loaded


def test_empty_manifest_hash_must_match(tmp_path) -> None:
    pipeline = DummyPipeline()
    pipeline.load = lambda: None
    path = tmp_path / "manifest.json"
    path.write_text('{"source_id":"cnpj","record_count":0}')
    pipeline.empty_load_evidence = EmptyLoadEvidence(str(path), "0" * 64)
    with pytest.raises(ValueError, match="empty load requires evidence"):
        pipeline.run()
