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
            "code": "01",
            "territorial_version": "v1",
            "uf": "SP",
        }
    }
    assert validate_crosswalk([row], None)[0]["status"] == "pending"
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
    assert validate_crosswalk([row], table)[0]["status"] == "pending"
