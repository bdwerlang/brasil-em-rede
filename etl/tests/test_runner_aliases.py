from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from bracc_etl.pipelines.cnpj import CNPJPipeline
from bracc_etl.runner import cli


@pytest.mark.parametrize(
    ("source", "message"),
    [("does_not_exist", "Unknown source"), ("cadin", "has no implemented runner")],
)
def test_invalid_source_fails_before_driver(source: str, message: str) -> None:
    with patch("bracc_etl.runner.GraphDatabase.driver") as driver:
        result = CliRunner().invoke(cli, ["run", "--source", source, "--neo4j-password", "unused"])
    assert result.exit_code != 0
    assert message in result.output
    driver.assert_not_called()


def test_legacy_alias_dispatches_runner_and_hooks_by_runner_name() -> None:
    with (
        patch("bracc_etl.runner.GraphDatabase.driver") as driver,
        patch.object(CNPJPipeline, "run") as run,
        patch("bracc_etl.runner.run_post_load_hooks") as hooks,
    ):
        result = CliRunner().invoke(
            cli, ["run", "--source", "receita_federal", "--neo4j-password", "unused"]
        )
    assert result.exit_code == 0, result.output
    run.assert_called_once()
    assert hooks.call_args.kwargs["source"] == "cnpj"
    driver.return_value.close.assert_called_once()


def test_status_reads_old_alias_and_reports_unmapped_or_conflicting_runs() -> None:
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value.run.return_value = [
        {"latest": {"source_id": "receita_federal", "status": "legacy_latest",
                    "started_at": "2026-10-27T12:00:00Z", "run_id": "old-id"}},
        {"latest": {"source_id": "cnpj", "status": "canonical_older",
                    "started_at": "2026-10-26T12:00:00Z", "run_id": "new-id"}},
        {"latest": {"source_id": "retired_unknown", "run_id": "unmapped-id"}},
        {"latest": {"source_id": "pncp_bids", "runner_name": "comprasnet",
                    "run_id": "conflicting-id"}},
    ]
    with patch("bracc_etl.runner.GraphDatabase.driver", return_value=driver):
        result = CliRunner().invoke(cli, ["sources", "--status", "--neo4j-password", "unused"])
    assert result.exit_code == 0, result.output
    assert "legacy_latest" in result.output
    assert "canonical_older" not in result.output
    assert "Unmapped ingestion run unmapped-id" in result.stderr
    assert "Conflicting historical runner_name" in result.stderr
    query = driver.session.return_value.__enter__.return_value.run.call_args.args[0]
    assert "WITH r ORDER BY r.started_at DESC, r.run_id DESC" in query
    assert "ORDER BY latest.started_at DESC, latest.run_id DESC" in query
    driver.close.assert_called_once()
