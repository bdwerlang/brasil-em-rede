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
