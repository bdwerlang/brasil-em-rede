from unittest.mock import MagicMock

import pytest

from bracc_etl.base import Pipeline
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
