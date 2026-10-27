import hashlib
import json
from unittest.mock import MagicMock

import pandas as pd

from bracc_etl.pipelines.rais import RaisPipeline
from bracc_etl.pipelines.siconfi import SiconfiPipeline


def crosswalk(entries):
    data = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "provenance": {
            "source": "synthetic",
            "version": "v1",
            "artifact_sha256": hashlib.sha256(data.encode()).hexdigest(),
        },
        "entries": entries,
    }


def test_siconfi_optional_crosswalk():
    row = {
        "cod_ibge": "0012345",
        "exercicio": "2022",
        "uf": "SP",
        "versao_territorial": "v1",
        "tipo_territorio": "municipio",
        "unidade_sistema": "test",
        "unidade_codigo": "BRL",
        "valor": "1",
    }
    pipeline = SiconfiPipeline(MagicMock())
    pipeline._raw = [row]
    pipeline.transform()
    assert pipeline.finances[0]["code_validation_status"] == "pending"
    dimensions = pipeline.dimension_observations[0]["dimensions"]
    pipeline.dimension_crosswalk = crosswalk(
        [{key: dimensions[key] for key in ("territory", "unit")}]
    )
    pipeline.transform()
    assert pipeline.finances[0]["code_validation_status"] == "matched_local"
    row["uf"] = "RJ"
    pipeline.transform()
    assert pipeline.finances[0]["code_validation_status"] == "pending"


def test_rais_optional_crosswalk():
    row = {
        "cnae_subclass": "0111301",
        "uf": "SP",
        "ibge_code": "35",
        "territorial_version": "v1",
        "cnae_version": "v2",
        "unit_system": "test",
        "unit_code": "pessoas",
        "exercise": "2022",
    }
    pipeline = RaisPipeline(MagicMock())
    pipeline._from_aggregated(pd.DataFrame([row]))
    assert pipeline.labor_stats[0]["code_validation_status"] == "pending"
    dimensions = pipeline.dimension_observations[0]["dimensions"]
    pipeline.dimension_crosswalk = crosswalk(
        [{key: dimensions[key] for key in ("territory", "activity", "unit")}]
    )
    pipeline._from_aggregated(pd.DataFrame([row]))
    assert pipeline.labor_stats[0]["code_validation_status"] == "matched_local"
    row["cnae_subclass"] = "0011301"
    pipeline._from_aggregated(pd.DataFrame([row]))
    assert pipeline.labor_stats[0]["code_validation_status"] == "pending"


def test_siconfi_duplicate_order_and_conflicting_value():
    from copy import deepcopy

    import pytest

    full = {
        "cod_ibge": "0012345",
        "exercicio": "2022",
        "uf": "SP",
        "versao_territorial": "v1",
        "tipo_territorio": "municipio",
        "unidade_sistema": "test",
        "unidade_codigo": "BRL",
        "valor": "1",
    }
    partial = deepcopy(full)
    del partial["versao_territorial"]
    pipeline = SiconfiPipeline(MagicMock())
    pipeline._raw = [full]
    pipeline.transform()
    dims = pipeline.dimension_observations[0]["dimensions"]
    pipeline.dimension_crosswalk = crosswalk([{key: dims[key] for key in ("territory", "unit")}])
    results = []
    for rows in ([partial, full], [full, partial]):
        pipeline._raw = rows
        pipeline.transform()
        results.append((deepcopy(pipeline.finances), deepcopy(pipeline.dimension_observations)))
        assert pipeline.finances[0]["code_validation_status"] == "matched_local"
    assert results[0] == results[1]
    changed = deepcopy(full)
    changed["valor"] = "2"
    for rows in ([full, changed], [changed, full]):
        pipeline._raw = rows
        with pytest.raises(ValueError, match="conflicting values"):
            pipeline.transform()
    partial["uf"] = "RJ"
    pipeline._raw = [partial, full]
    with pytest.raises(ValueError, match="conflicting metadata"):
        pipeline.transform()


def test_siconfi_duplicate_status_persists_in_disposable_graph():
    import os
    from copy import deepcopy

    import pytest
    from neo4j import GraphDatabase

    uri = os.environ.get("F09_NEO4J_URI")
    if not uri:
        pytest.skip("requires disposable Neo4j")
    driver = GraphDatabase.driver(uri, auth=("neo4j", os.environ["F09_NEO4J_PASSWORD"]))
    try:
        full = {
            "cod_ibge": "0099999",
            "exercicio": "2022",
            "uf": "SP",
            "versao_territorial": "v1",
            "tipo_territorio": "municipio",
            "unidade_sistema": "test",
            "unidade_codigo": "BRL",
            "valor": "1",
        }
        partial = deepcopy(full)
        del partial["versao_territorial"]
        pipeline = SiconfiPipeline(driver)
        pipeline._raw = [full]
        pipeline.transform()
        dims = pipeline.dimension_observations[0]["dimensions"]
        pipeline.dimension_crosswalk = crosswalk(
            [{key: dims[key] for key in ("territory", "unit")}]
        )
        for rows in ([partial, full], [full, partial]):
            pipeline._raw = rows
            pipeline.transform()
            pipeline.load()
            with driver.session() as session:
                result = session.run(
                    "MATCH (f:MunicipalFinance {finance_id: $id}) "
                    "RETURN f.code_validation_status AS status",
                    id=pipeline.finances[0]["finance_id"],
                ).single(strict=True)
                assert result["status"] == "matched_local"
    finally:
        driver.close()
