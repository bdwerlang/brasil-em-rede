import os
from unittest.mock import MagicMock

import pandas as pd
import pytest
from neo4j import GraphDatabase

from bracc_etl.dimensions.projection import project_rais
from bracc_etl.pipelines.rais import RaisPipeline


def make_pipeline():
    pipeline = RaisPipeline(MagicMock())
    pipeline._from_aggregated(
        pd.DataFrame(
            [
                {
                    "cnae_subclass": "0111301",
                    "uf": "SP",
                    "ibge_code": "35",
                    "territorial_version": "2022",
                    "cnae_version": "2.0",
                    "unit_system": "RAIS",
                    "unit_code": "vinculos",
                    "exercise": "2022",
                }
            ]
        )
    )
    return pipeline


def test_rais_requires_explicit_metadata():
    pipeline = make_pipeline()
    assert len(pipeline.dimension_observations) == 1
    pipeline._from_aggregated(pd.DataFrame([{"cnae_subclass": "0111301", "uf": "SP"}]))
    assert pipeline.dimension_observations == []


def test_rais_rejects_wrong_exercise():
    pipeline = make_pipeline()
    with pytest.raises(ValueError, match="exercise"):
        pipeline._from_aggregated(
            pd.DataFrame(
                [
                    {
                        "cnae_subclass": "0111301",
                        "uf": "SP",
                        "ibge_code": "35",
                        "territorial_version": "2022",
                        "cnae_version": "2.0",
                        "unit_system": "RAIS",
                        "unit_code": "vinculos",
                        "exercise": "2023",
                    }
                ]
            )
        )


@pytest.mark.skipif(not os.environ.get("F09_NEO4J_URI"), reason="requires disposable Neo4j")
def test_rais_projection_idempotent_in_disposable_graph():
    driver = GraphDatabase.driver(
        os.environ["F09_NEO4J_URI"], auth=("neo4j", os.environ["F09_NEO4J_PASSWORD"])
    )
    try:
        pipeline = make_pipeline()
        with driver.session() as session:
            session.run(
                "CREATE (:LaborStats {stats_id: $id})", id=pipeline.labor_stats[0]["stats_id"]
            ).consume()
        project_rais(driver, "neo4j", pipeline.dimension_observations)
        project_rais(driver, "neo4j", pipeline.dimension_observations)
        with driver.session() as session:
            record = session.run("MATCH (n) RETURN labels(n) AS labels, count(n) AS count").data()
            relations = session.run("MATCH (:LaborStats)-[r]->() RETURN count(r) AS n").single()[
                "n"
            ]
        counts = {tuple(row["labels"]): row["count"] for row in record}
        assert counts == {
            ("LaborStats",): 1,
            ("Territory",): 1,
            ("EconomicActivity",): 1,
            ("Unit",): 1,
            ("FiscalYear",): 1,
        }
        assert relations == 4
    finally:
        driver.close()


def test_rais_rejects_conflicting_duplicates_before_load():
    pipeline = make_pipeline()
    row = {
        "cnae_subclass": "0111301",
        "uf": "SP",
        "ibge_code": "35",
        "territorial_version": "2022",
        "cnae_version": "2.0",
        "unit_system": "RAIS",
        "unit_code": "vinculos",
        "exercise": "2022",
    }
    for records in (
        [row, {**row, "territorial_version": "2023"}],
        [{**row, "territorial_version": "2023"}, row],
    ):
        with pytest.raises(ValueError, match="Conflicting RAIS aggregate"):
            pipeline._from_aggregated(pd.DataFrame(records))
        assert pipeline.labor_stats == []
        assert pipeline.dimension_observations == []


@pytest.mark.parametrize("with_metadata", [True, False])
def test_rais_deduplicates_identical_aggregates(with_metadata):
    row = {"cnae_subclass": "0111301", "uf": "SP", "total_employees": "5"}
    if with_metadata:
        row.update(
            {
                "ibge_code": "35",
                "territorial_version": "2022",
                "cnae_version": "2.0",
                "unit_system": "RAIS",
                "unit_code": "vinculos",
                "exercise": "2022",
            }
        )
    pipeline = RaisPipeline(MagicMock())
    pipeline._from_aggregated(pd.DataFrame([row, row]))
    assert len(pipeline.labor_stats) == 1
    assert len(pipeline.dimension_observations) == int(with_metadata)


def test_rais_rejects_duplicate_with_different_values_or_partial_metadata():
    row = {"cnae_subclass": "0111301", "uf": "SP", "total_employees": "5"}
    pipeline = RaisPipeline(MagicMock())
    for changed in ({"total_employees": "6"}, {"ibge_code": "35"}):
        with pytest.raises(ValueError, match="Conflicting RAIS aggregate"):
            pipeline._from_aggregated(pd.DataFrame([row, {**row, **changed}]).fillna(""))
        assert pipeline.labor_stats == []
        assert pipeline.dimension_observations == []
