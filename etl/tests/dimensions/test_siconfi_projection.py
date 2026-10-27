import os
from unittest.mock import MagicMock

import pytest
from neo4j import GraphDatabase

from bracc_etl.pipelines.siconfi import SiconfiPipeline


def observation():
    return {
        "cod_ibge": "0123456",
        "exercicio": "2022",
        "uf": "SP",
        "versao_territorial": "2022",
        "tipo_territorio": "municipio",
        "unidade_sistema": "SICONFI",
        "unidade_codigo": "BRL",
        "conta": "receita",
        "coluna": "valor",
        "valor": "100",
        "orgao_jurisdicao": "SP",
        "orgao_sistema": "fonte",
        "orgao_papel": "ug",
        "orgao_codigo": "000123",
        "orgao_versao": "2022",
        "cnpj": "12345678000190",
    }


def pipeline_for(row):
    pipeline = SiconfiPipeline(MagicMock())
    pipeline._raw = [row]
    pipeline.transform()
    return pipeline


def test_explicit_dimensions_preserve_identifiers():
    pipeline = pipeline_for(observation())
    dimensions = pipeline.dimension_observations[0]["dimensions"]
    assert dimensions["territory"]["code"] == "0123456"
    assert dimensions["territory"]["uf"] == "SP"
    assert dimensions["fiscal_year"]["year"] == "2022"
    assert dimensions["unit"]["code"] == "BRL"
    assert dimensions["public_body"]["code"] == "000123"
    assert pipeline.finances[0]["dimension_status"] == "pending"
    assert pipeline.finances[0]["dimension_reason"] == "projection_not_completed"
    assert not hasattr(pipeline, "municipality_rels")


def test_missing_metadata_remains_pending():
    row = observation()
    del row["versao_territorial"]
    pending = pipeline_for(row)
    assert pending.dimension_observations == []
    assert pending.finances[0]["dimension_status"] == "pending"
    assert pending.finances[0]["dimension_reason"] == "missing_metadata:versao_territorial"
    row = observation()
    del row["orgao_codigo"]
    assert "public_body" not in pipeline_for(row).dimension_observations[0]["dimensions"]


@pytest.mark.skipif(not os.environ.get("F09_NEO4J_URI"), reason="requires disposable Neo4j")
def test_load_twice_without_entities():
    driver = GraphDatabase.driver(
        os.environ["F09_NEO4J_URI"], auth=("neo4j", os.environ["F09_NEO4J_PASSWORD"])
    )
    try:
        pipeline = SiconfiPipeline(driver)
        pipeline._raw = [observation()]
        pipeline.transform()
        pipeline.load()
        pipeline.load()
        incomplete = observation()
        incomplete["conta"] = "despesa"
        del incomplete["versao_territorial"]
        pipeline._raw = [incomplete]
        pipeline.transform()
        pipeline.load()
        with driver.session() as session:
            statuses = session.run(
                "MATCH (n:MunicipalFinance) RETURN n.account AS account, "
                "n.dimension_status AS status, n.dimension_reason AS reason"
            ).data()
            nodes = session.run("MATCH (n) RETURN labels(n) AS labels, count(n) AS count").data()
            links = session.run("MATCH (:MunicipalFinance)-[r]->() RETURN count(r) AS n").single(
                strict=True
            )["n"]
        assert {tuple(n["labels"]): n["count"] for n in nodes} == {
            ("MunicipalFinance",): 2,
            ("Territory",): 1,
            ("Unit",): 1,
            ("FiscalYear",): 1,
            ("PublicBody",): 1,
        }
        assert links == 4
        assert {r["account"]: (r["status"], r["reason"]) for r in statuses} == {
            "receita": ("projected", ""),
            "despesa": ("pending", "missing_metadata:versao_territorial"),
        }
    finally:
        driver.close()


def test_conflicting_dimensions_for_same_fact_fail():
    first = observation()
    second = observation()
    second["unidade_codigo"] = "USD"
    pipeline = SiconfiPipeline(MagicMock())
    pipeline._raw = [first, second]
    with pytest.raises(ValueError, match="conflicting dimensions"):
        pipeline.transform()
