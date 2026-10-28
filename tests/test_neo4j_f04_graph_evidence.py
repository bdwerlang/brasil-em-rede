"""Opt-in integration evidence using a Neo4j container owned by this test."""
import importlib.util
import os
from pathlib import Path

import pytest

neo4j = pytest.importorskip("neo4j")
Neo4jContainer = pytest.importorskip("testcontainers.neo4j").Neo4jContainer
pytestmark = pytest.mark.skipif(
    os.getenv("F04_RUN_NEO4J_INTEGRATION") != "1", reason="requires Docker integration opt-in"
)
ROOT = Path(__file__).resolve().parents[1]


def statements(text):
    import re

    return [s.strip() for s in re.sub(r"//[^\n]*", "", text).split(";") if s.strip()]


def apply(session, text):
    for statement in statements(text):
        session.run(statement).consume()


def catalog(session):
    return [tuple(r.values()) for r in session.run(
        "SHOW CONSTRAINTS YIELD name, type, entityType, labelsOrTypes, properties "
        "RETURN name, type, entityType, labelsOrTypes, properties ORDER BY name"
    )]


def fingerprint(session):
    return [tuple(r.values()) for r in session.run(
        "MATCH (n) OPTIONAL MATCH (n)-[r]->(m) "
        "RETURN labels(n), properties(n), type(r), labels(m), properties(m) "
        "ORDER BY labels(n), properties(n).cnpj, properties(n).transfer_id"
    )]


def preflight(session):
    spec = importlib.util.spec_from_file_location("f04_preflight", ROOT / "infra/neo4j/preflight.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return session.execute_read(module.run, module.definitions(module.SCHEMA.read_text()))


def test_clean_upgrade_preflight_and_reingestion():
    container = Neo4jContainer("neo4j:5.26.21-community")
    container.with_env("NEO4J_server_memory_heap_initial__size", "256m")
    container.with_env("NEO4J_server_memory_heap_max__size", "512m")
    container.with_env("NEO4J_server_memory_pagecache_size", "128m")
    driver = None
    try:
        container.start()
        driver = neo4j.GraphDatabase.driver(
            container.get_connection_url(), auth=(container.username, container.password)
        )
        schema = (ROOT / "infra/neo4j/init.cypher").read_text()
        # Minimal legacy fixture: preexisting constraint and outdated fulltext index.
        legacy = """
        CREATE CONSTRAINT company_cnpj_unique IF NOT EXISTS
          FOR (n:Company) REQUIRE n.cnpj IS UNIQUE;
        CREATE FULLTEXT INDEX entity_search IF NOT EXISTS
          FOR (n:Person) ON EACH [n.name];
        """
        with driver.session() as session:
            assert session.run("MATCH (n) RETURN count(n) AS n").single()["n"] == 0
            assert session.run("SHOW CONSTRAINTS YIELD name RETURN count(*) AS n").single()["n"] == 0
            apply(session, schema)
            session.run("CALL db.awaitIndexes(120)").consume()
            clean = catalog(session)
            before = fingerprint(session)
            assert preflight(session) == []
            assert fingerprint(session) == before and catalog(session) == clean
            # The real batch loader executes two node loads and a relationship load twice.
            import sys
            sys.path.insert(0, str(ROOT / "etl/src"))
            from bracc_etl.loader import Neo4jBatchLoader

            loader = Neo4jBatchLoader(driver)
            for _ in range(2):
                loader.load_nodes("Company", [{"cnpj": "synthetic-company"}], "cnpj")
                loader.load_nodes("Payment", [{"transfer_id": "synthetic-payment"}], "transfer_id")
                assert loader.load_relationships("PAGO_PARA", [{"source_key": "synthetic-payment", "target_key": "synthetic-company"}], "Payment", "transfer_id", "Company", "cnpj") == 1
            assert session.run("MATCH (n) RETURN count(n) AS n").single()["n"] == 2
            assert session.run("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"] == 1
            # Remove only test data and schema from this explicitly disposable database.
            session.run("MATCH (n) DETACH DELETE n").consume()
            for row in session.run("SHOW CONSTRAINTS YIELD name RETURN name"):
                session.run(f"DROP CONSTRAINT `{row['name']}`").consume()
            for row in session.run("SHOW INDEXES YIELD name, owningConstraint RETURN name, owningConstraint"):
                if not row['owningConstraint']:
                    session.run(f"DROP INDEX `{row['name']}`").consume()
            apply(session, legacy)
            session.run("CREATE (:Company {cnpj:'synthetic-company'})").consume()
            session.run("CREATE (:Payment {transfer_id:'synthetic-payment'})").consume()
            legacy_issues = preflight(session)
            assert legacy_issues == ["entity_search: conflito de nome ou definição"]
            # Duplicate new key and schema-name collision must be reported without mutation.
            session.run("CREATE (:Person {entity_id:'duplicate'}), (:Person {entity_id:'duplicate'})").consume()
            session.run("CREATE INDEX person_entity_id_unique FOR (n:Company) ON (n.name)").consume()
            snapshot = fingerprint(session)
            old_catalog = catalog(session)
            issues = preflight(session)
            assert any("person_entity_id_unique" in issue for issue in issues)
            assert any("grupos de chaves duplicadas" in issue for issue in issues)
            assert fingerprint(session) == snapshot and catalog(session) == old_catalog
            session.run("MATCH (n:Person) DETACH DELETE n").consume()
            session.run("DROP INDEX person_entity_id_unique").consume()
            # Legacy fulltext differs; constraint comparison concerns constraints only.
            apply(session, schema)
            assert catalog(session) == clean
            for _ in range(2):
                loader.load_nodes("Company", [{"cnpj": "synthetic-company"}], "cnpj")
                loader.load_nodes("Payment", [{"transfer_id": "synthetic-payment"}], "transfer_id")
                assert loader.load_relationships("PAGO_PARA", [{"source_key": "synthetic-payment", "target_key": "synthetic-company"}], "Payment", "transfer_id", "Company", "cnpj") == 1
            assert session.run("MATCH (n) RETURN count(n) AS n").single()["n"] == 2
            assert session.run("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"] == 1
    finally:
        if driver is not None:
            driver.close()
        container.stop()
