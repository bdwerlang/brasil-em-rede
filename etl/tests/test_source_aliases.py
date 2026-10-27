import csv
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bracc_etl.runner import PIPELINES
from bracc_etl.source_aliases import (
    SourceAliases,
    UnimplementedSourceError,
    UnknownSourceError,
    load_source_aliases,
    source_aliases,
)

ROOT = Path(__file__).resolve().parents[2]


def _entry(
    source: str,
    runner: str | None = None,
    provider: str | None = None,
    legacy: list[str] | None = None,
) -> dict[str, object]:
    return {
        "source_id": source,
        "runner_name": runner,
        "provider_id": provider,
        "legacy_aliases": legacy or [],
    }


def test_catalog_coverage_and_package_copy() -> None:
    aliases = load_source_aliases(ROOT / "config/source_aliases.json")
    with (ROOT / "docs/source_registry_br_v1.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == len(aliases.sources) == 169
    assert {row["source_id"] for row in rows} == {s.source_id for s in aliases.sources}
    assert aliases.sources == source_aliases().sources
    assert {s.runner_name for s in aliases.sources if s.runner_name} == set(PIPELINES)
    for row in rows:
        identity = aliases.resolve(row["source_id"])
        if row["implementation_state"] == "implemented":
            assert identity.runner_name == row["pipeline_id"]
        else:
            assert identity.runner_name is None and identity.provider_id is None
            with pytest.raises(UnimplementedSourceError):
                aliases.resolve(row["source_id"], require_runner=True)


@pytest.mark.parametrize("runner_name", sorted(PIPELINES))
def test_every_pipeline_resolves_and_keeps_legacy_metadata(runner_name: str) -> None:
    cls = PIPELINES[runner_name]
    pipeline = cls(driver=MagicMock())
    aliases = source_aliases()
    identity = aliases.for_pipeline(cls.name, cls.source_id)
    assert pipeline.source_identity == identity
    assert pipeline.name == identity.runner_name == runner_name
    assert pipeline.source_id == identity.provider_id
    assert aliases.resolve(identity.source_id) == identity
    assert aliases.resolve(cls.source_id) == identity
    record = {"source_id": cls.source_id, "run_id": "unchanged"}
    assert aliases.for_run(record) == identity
    assert record == {"source_id": cls.source_id, "run_id": "unchanged"}


def test_registered_legacy_alias_resolves_without_adding_implementation() -> None:
    aliases = SourceAliases({"schema_version": 1, "sources": [_entry("future", legacy=["old"])]})
    assert aliases.resolve("old").source_id == "future"
    with pytest.raises(UnimplementedSourceError):
        aliases.resolve("old", require_runner=True)


@pytest.mark.parametrize("identifier", ["unknown_source", "", "CNPJ", " cnpj", "cnpj "])
def test_unknown_or_modified_identifier_is_an_explicit_error(identifier: str) -> None:
    with pytest.raises(UnknownSourceError, match="Unknown source"):
        source_aliases().resolve(identifier)


@pytest.mark.parametrize(
    ("entries", "message"),
    [
        ([_entry("one"), _entry("one")], "Duplicate source_id"),
        ([_entry("one", "shared", "provider_one"),
          _entry("two", "shared", "provider_two")], "Ambiguous alias"),
        ([_entry("one", "runner_one", "shared"),
          _entry("two", "runner_two", "shared")], "Ambiguous alias"),
        ([_entry("one", legacy=["two"]), _entry("two")], "Ambiguous alias"),
        ([_entry("one", legacy=["old"]), _entry("two", legacy=["old"])], "Ambiguous alias"),
        ([_entry("one", legacy=["old", "old"])], "Duplicate legacy alias"),
        ([_entry("one", legacy=["one"])], "Duplicate legacy alias"),
        ([_entry("one", "runner", None)], "must both be null or set"),
        ([_entry("one", None, "provider")], "must both be null or set"),
        ([_entry("ONE")], "Invalid source_id"),
    ],
)
def test_duplicates_collisions_and_invalid_entries_fail(
    entries: list[dict[str, object]], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        SourceAliases({"schema_version": 1, "sources": entries})


@pytest.mark.parametrize("document", [{}, {"schema_version": 2, "sources": []},
                                      {"schema_version": True, "sources": []},
                                      {"schema_version": 1, "sources": []}])
def test_invalid_or_future_schema_fails(document: object) -> None:
    with pytest.raises(ValueError):
        SourceAliases(document)


def test_duplicate_json_fields_fail_before_overwriting(tmp_path: Path) -> None:
    path = tmp_path / "aliases.json"
    path.write_text('{"schema_version": 2, "schema_version": 1, "sources": []}')
    with pytest.raises(ValueError, match="Duplicate JSON field"):
        load_source_aliases(path)


def test_pipeline_drift_and_conflicting_historical_metadata_fail() -> None:
    aliases = source_aliases()
    with pytest.raises(ValueError, match="disagrees"):
        aliases.for_pipeline("cnpj", "wrong_provider")
    for field, value in [("runner_name", "comprasnet"), ("provider_id", "comprasnet"),
                         ("source_aliases_version", 2)]:
        with pytest.raises(ValueError):
            aliases.for_run({"source_id": "pncp_bids", field: value})


def test_pncp_contracts_and_bids_remain_different_sources() -> None:
    aliases = source_aliases()
    contracts = aliases.for_pipeline("comprasnet", "comprasnet")
    bids = aliases.for_pipeline("pncp", "pncp_bids")
    assert contracts.source_id == "comprasnet"
    assert bids.source_id == "pncp"
    assert contracts != bids
    assert aliases.for_run({"source_id": "pncp_bids"}) == bids
    assert aliases.for_run({"source_id": "comprasnet"}) == contracts
