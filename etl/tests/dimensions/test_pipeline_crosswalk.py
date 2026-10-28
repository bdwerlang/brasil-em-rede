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
        "cod_ibge": "3550308",
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
    assert pipeline.finances[0]["territory_unit_validation_reason"] == "crosswalk_unavailable"
    dimensions = pipeline.dimension_observations[0]["dimensions"]
    pipeline.dimension_crosswalk = crosswalk(
        [{key: dimensions[key] for key in ("territory", "unit", "fiscal_year")}]
    )
    pipeline.transform()
    assert pipeline.finances[0]["territory_unit_validation_status"] == "matched_local"
    wrong_exercise = {key: dimensions[key] for key in ("territory", "unit", "fiscal_year")}
    wrong_exercise["fiscal_year"] = {"year": "2021"}
    pipeline.dimension_crosswalk = crosswalk([wrong_exercise])
    pipeline.transform()
    assert pipeline.finances[0]["territory_unit_validation_status"] == "pending"
    row.update(cod_ibge="3365500", uf="RJ")
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
    assert pipeline.labor_stats[0]["code_validation_reason"] == "crosswalk_unavailable"
    dimensions = pipeline.dimension_observations[0]["dimensions"]
    pipeline.dimension_crosswalk = crosswalk(
        [{key: dimensions[key] for key in ("territory", "activity", "unit", "fiscal_year")}]
    )
    pipeline._from_aggregated(pd.DataFrame([row]))
    assert pipeline.labor_stats[0]["code_validation_status"] == "matched_local"
    wrong_exercise = {
        key: dimensions[key] for key in ("territory", "activity", "unit", "fiscal_year")
    }
    wrong_exercise["fiscal_year"] = {"year": "2021"}
    pipeline.dimension_crosswalk = crosswalk([wrong_exercise])
    pipeline._from_aggregated(pd.DataFrame([row]))
    assert pipeline.labor_stats[0]["code_validation_status"] == "pending"
    row["cnae_subclass"] = "0011301"
    pipeline._from_aggregated(pd.DataFrame([row]))
    assert pipeline.labor_stats[0]["code_validation_status"] == "pending"


def test_siconfi_duplicate_order_and_conflicting_value():
    from copy import deepcopy

    import pytest

    full = {
        "cod_ibge": "3550308",
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
    pipeline.dimension_crosswalk = crosswalk(
        [{key: dims[key] for key in ("territory", "unit", "fiscal_year")}]
    )
    results = []
    for rows in ([partial, full], [full, partial]):
        pipeline._raw = rows
        pipeline.transform()
        results.append((deepcopy(pipeline.finances), deepcopy(pipeline.dimension_observations)))
        assert pipeline.finances[0]["territory_unit_validation_status"] == "matched_local"
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
            "cod_ibge": "3550308",
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
            [{key: dims[key] for key in ("territory", "unit", "fiscal_year")}]
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
                assert result["status"] == "pending"
    finally:
        driver.close()


def test_siconfi_body_crosswalk_independent_and_duplicates():
    from copy import deepcopy

    row = {
        "cod_ibge": "3550308",
        "exercicio": "2022",
        "uf": "SP",
        "versao_territorial": "v1",
        "tipo_territorio": "municipio",
        "unidade_sistema": "test",
        "unidade_codigo": "BRL",
        "valor": "1",
        "orgao_jurisdicao": "SP",
        "orgao_sistema": "test",
        "orgao_papel": "ug",
        "orgao_codigo": "00012",
        "orgao_versao": "v1",
    }
    pipeline = SiconfiPipeline(MagicMock())
    pipeline._raw = [row]
    pipeline.transform()
    assert pipeline.finances[0]["public_body_validation_status"] == "pending"
    assert pipeline.finances[0]["public_body_validation_reason"] == "crosswalk_unavailable"
    assert pipeline.finances[0]["territory_unit_validation_status"] == "pending"
    assert pipeline.finances[0]["territory_unit_validation_reason"] == "crosswalk_unavailable"
    dims = pipeline.dimension_observations[0]["dimensions"]
    pipeline.dimension_crosswalk = crosswalk(
        [{key: dims[key] for key in ("territory", "unit", "fiscal_year")}]
    )
    pipeline.transform()
    assert pipeline.finances[0]["territory_unit_validation_status"] == "matched_local"
    assert pipeline.finances[0]["territory_unit_validation_reason"] == ""
    assert pipeline.finances[0]["public_body_validation_status"] == "pending"
    pipeline.dimension_crosswalk = crosswalk([dims])
    partial = deepcopy(row)
    for key in ("orgao_jurisdicao", "orgao_sistema", "orgao_papel", "orgao_codigo", "orgao_versao"):
        del partial[key]
    body_only = deepcopy(row)
    del body_only["versao_territorial"]
    for rows in ([partial, body_only], [body_only, partial]):
        pipeline._raw = rows
        pipeline.transform()
        assert pipeline.finances[0]["public_body_validation_status"] == "matched_local"
        assert pipeline.finances[0]["code_validation_status"] == "matched_local"
    pipeline._raw = [partial]
    pipeline.transform()
    assert pipeline.finances[0]["public_body_validation_reason"] == "public_body_metadata_missing"
    for field, value in (
        ("orgao_papel", "ente"),
        ("orgao_codigo", "00013"),
        ("orgao_versao", "v2"),
    ):
        altered = deepcopy(row)
        altered[field] = value
        pipeline._raw = [altered]
        pipeline.transform()
        assert pipeline.finances[0]["public_body_validation_status"] == "pending"


def test_siconfi_body_status_persists_in_disposable_graph():
    import os

    import pytest
    from neo4j import GraphDatabase

    uri = os.environ.get("F09_NEO4J_URI")
    if not uri:
        pytest.skip("requires disposable Neo4j")
    driver = GraphDatabase.driver(uri, auth=("neo4j", os.environ["F09_NEO4J_PASSWORD"]))
    try:
        row = {
            "cod_ibge": "3550308",
            "exercicio": "2022",
            "uf": "SP",
            "versao_territorial": "v1",
            "tipo_territorio": "municipio",
            "unidade_sistema": "test",
            "unidade_codigo": "BRL",
            "valor": "1",
            "orgao_jurisdicao": "SP",
            "orgao_sistema": "test",
            "orgao_papel": "ug",
            "orgao_codigo": "00012",
            "orgao_versao": "v1",
        }
        pipeline = SiconfiPipeline(driver)
        pipeline._raw = [row]
        pipeline.transform()
        dims = pipeline.dimension_observations[0]["dimensions"]
        pipeline.dimension_crosswalk = crosswalk(
            [{key: dims[key] for key in ("territory", "unit", "fiscal_year")}]
        )
        pipeline.transform()
        pipeline.load()
        with driver.session() as session:
            result = session.run(
                "MATCH (f:MunicipalFinance {finance_id: $id}) "
                "RETURN f.code_validation_status AS overall, "
                "f.public_body_validation_status AS body",
                id=pipeline.finances[0]["finance_id"],
            ).single(strict=True)
            assert (result["overall"], result["body"]) == ("pending", "pending")
        pipeline.dimension_crosswalk = crosswalk([dims])
        pipeline.transform()
        pipeline.load()
        with driver.session() as session:
            result = session.run(
                "MATCH (f:MunicipalFinance {finance_id: $id}) "
                "RETURN f.code_validation_status AS overall, "
                "f.public_body_validation_status AS body",
                id=pipeline.finances[0]["finance_id"],
            ).single(strict=True)
            assert (result["overall"], result["body"]) == ("matched_local", "matched_local")
    finally:
        driver.close()


def test_crosswalk_prepared_once_and_only_for_complete_metadata(monkeypatch):
    import pytest

    from bracc_etl.dimensions.crosswalk import CrosswalkError, prepare_crosswalk
    from bracc_etl.pipelines import rais, siconfi

    rais_row = {
        "cnae_subclass": "0111301", "uf": "SP", "ibge_code": "35",
        "territorial_version": "v1", "cnae_version": "v2", "unit_system": "test",
        "unit_code": "pessoas", "exercise": "2022",
    }
    siconfi_row = {
        "cod_ibge": "3550308", "exercicio": "2022", "uf": "SP",
        "versao_territorial": "v1", "tipo_territorio": "municipio",
        "unidade_sistema": "test", "unidade_codigo": "BRL", "valor": "1",
        "orgao_jurisdicao": "SP", "orgao_sistema": "test", "orgao_papel": "ug",
        "orgao_codigo": "00012", "orgao_versao": "v1",
    }
    for module, pipeline, row, incomplete, run in (
        (rais, RaisPipeline(MagicMock()), rais_row, "ibge_code",
         lambda p, rows: p._from_aggregated(pd.DataFrame(rows))),
        (siconfi, SiconfiPipeline(MagicMock()), siconfi_row, "versao_territorial",
         lambda p, rows: (setattr(p, "_raw", rows), p.transform())),
    ):
        calls = []

        def prepare(table, calls=calls):
            calls.append(table)
            return prepare_crosswalk(table)

        monkeypatch.setattr(module, "prepare_crosswalk", prepare)
        run(pipeline, [row, row])
        assert calls == [None]
        calls.clear()
        pipeline.dimension_crosswalk = {}
        partial = {key: value for key, value in row.items() if key != incomplete}
        run(pipeline, [partial])
        assert calls == []
        with pytest.raises(CrosswalkError):
            run(pipeline, [row])
        assert calls == [{}]

    pipeline = SiconfiPipeline(MagicMock())
    pipeline._raw = [siconfi_row]
    pipeline.transform()
    dimensions = pipeline.dimension_observations[0]["dimensions"]
    pipeline.dimension_crosswalk = crosswalk([dimensions])
    calls.clear()
    another = dict(siconfi_row, conta="another")
    pipeline._raw = [siconfi_row, another]
    pipeline.transform()
    assert calls == [pipeline.dimension_crosswalk]
    assert all(fact["code_validation_status"] == "matched_local" for fact in pipeline.finances)


def test_structural_ibge_validation_runs_without_crosswalk():
    import pytest

    siconfi_driver = MagicMock()
    siconfi = SiconfiPipeline(siconfi_driver)
    siconfi._raw = [
        {
            "cod_ibge": "3350308",
            "exercicio": "2023",
            "uf": "SP",
            "versao_territorial": "v1",
            "tipo_territorio": "municipio",
            "unidade_sistema": "test",
            "unidade_codigo": "BRL",
            "valor": "1",
        }
    ]
    with pytest.raises(ValueError, match="matching UF prefix"):
        siconfi.transform()
    siconfi_driver.session.assert_not_called()

    rais = RaisPipeline(MagicMock())
    invalid_rais_row = {
        "cnae_subclass": "0111301",
        "uf": "SP",
        "ibge_code": "99",
        "territorial_version": "v1",
        "cnae_version": "2.0",
        "unit_system": "test",
        "unit_code": "pessoas",
        "exercise": "2022",
    }
    with pytest.raises(ValueError, match="UF code"):
        rais._from_aggregated(pd.DataFrame([invalid_rais_row]))
