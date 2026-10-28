import hashlib
import json
from copy import deepcopy

import pytest

from bracc_etl.dimensions.crosswalk import CrosswalkError, validate_crosswalk


def test_requires_provenance_and_preserves_code():
    row = {
        "territory": {
            "system": "IBGE",
            "type": "uf",
            "code": "35",
            "territorial_version": "v1",
            "uf": "SP",
        }
    }
    assert validate_crosswalk([row], None)[0] == {
        "status": "pending",
        "reason": "crosswalk_unavailable",
    }
    invalid = deepcopy(row)
    invalid["territory"].update(code="99", uf="SP")
    with pytest.raises(ValueError, match="UF code"):
        validate_crosswalk([invalid], None)
    with pytest.raises(CrosswalkError):
        validate_crosswalk([row], {"entries": [row]})
    table = {
        "provenance": {
            "source": "synthetic",
            "version": "v1",
            "artifact_sha256": hashlib.sha256(
                json.dumps(
                    [row], ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode()
            ).hexdigest(),
        },
        "entries": [deepcopy(row)],
    }
    assert validate_crosswalk([row], table)[0]["status"] == "matched_local"
    row["territory"]["code"] = "1"
    with pytest.raises(ValueError, match="UF code"):
        validate_crosswalk([row], table)


def _table(entries):
    checksum = hashlib.sha256(
        json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "provenance": {"source": "synthetic", "version": "v1", "artifact_sha256": checksum},
        "entries": entries,
    }


def test_prepared_batch_equivalence_and_snapshot(monkeypatch):
    from bracc_etl.dimensions import crosswalk as module

    row = {"unit": {"system": "SI", "code": "kg"}}
    missing = {"unit": {"system": "SI", "code": "m"}}
    table = _table([deepcopy(row)])
    observations = [row, missing, {}, row]
    expected = validate_crosswalk(observations, table)
    original = module.materialize
    calls = []

    def tracked(rows):
        calls.append(rows)
        return original(rows)

    monkeypatch.setattr(module, "materialize", tracked)
    prepared = module.prepare_crosswalk(table)
    table["entries"][0]["unit"]["code"] = "changed"
    assert prepared.validate(observations) == expected
    assert prepared.validate(observations) == expected
    assert len(calls) == 1 + 2 * len(observations)
    with pytest.raises(CrosswalkError):
        module.prepare_crosswalk(table)


def test_prepared_missing_table_matches_compatibility_api():
    from bracc_etl.dimensions.crosswalk import prepare_crosswalk

    rows = [{}, {"unit": {"system": "SI", "code": "kg"}}]
    assert prepare_crosswalk(None).validate(rows) == validate_crosswalk(rows, None)
    assert prepare_crosswalk(None).validate([]) == []
    with pytest.raises(ValueError, match="unit must be an object"):
        prepare_crosswalk(None).validate([{"unit": "invalid"}])


@pytest.mark.parametrize(
    "table",
    [
        {"entries": []},
        {"provenance": {"source": "s", "version": "v", "artifact_sha256": "x"}, "entries": []},
        _table([{"unit": "invalid"}]),
        _table(
            [
                {
                    "territory": {
                        "system": "IBGE",
                        "type": "uf",
                        "code": "35",
                        "territorial_version": "v1",
                        "uf": "SP",
                    }
                },
                {
                    "territory": {
                        "system": "IBGE",
                        "type": "uf",
                        "code": "35",
                        "territorial_version": "v1",
                        "uf": "RJ",
                    }
                },
            ]
        ),
    ],
)
def test_preparation_rejects_invalid_or_conflicting_tables(table):
    from bracc_etl.dimensions.crosswalk import prepare_crosswalk

    with pytest.raises(CrosswalkError):
        prepare_crosswalk(table)
    with pytest.raises(CrosswalkError):
        validate_crosswalk([], table)
