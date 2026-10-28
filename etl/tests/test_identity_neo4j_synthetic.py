"""Run against an explicitly provisioned disposable Neo4j with synthetic data."""

import os
from pathlib import Path

import pytest
from neo4j import GraphDatabase

from bracc_etl.identity.crosswalk import (
    export_crosswalk,
    read_crosswalk,
    restore_crosswalk,
    snapshot_assignments,
)
from bracc_etl.identity.migration import MigrationBlockedError, apply_snapshot, rollback_snapshot


@pytest.fixture
def driver():
    uri = os.getenv("IDENTITY_TEST_NEO4J_URI")
    if not uri:
        pytest.skip("disposable synthetic Neo4j not configured")
    assert uri.startswith("bolt://127.0.0.1:")
    with GraphDatabase.driver(uri, auth=("neo4j", "synthetic-only-password")) as d:
        yield d


def test_migration_collision_edges_alias_and_rollback(driver, tmp_path):
    snapshot = "synthetic-snapshot-v1"
    old_id = "fda78e8c-a1f3-499d-8fb4-8e6f4b7e6436"
    with driver.session() as s:
        s.run(
            "CREATE (a:Company {cnpj:'11.222.333/0001-81', entity_id:$id}), "
            "(b:Company {cnpj:'11222333000181'}), "
            "(p:Partner {name:'synthetic'}), (a)-[:SOCIO_DE]->(p), (p)-[:SOCIO_DE]->(b)",
            id=old_id,
        ).consume()
        before = (
            s.run(
                "MATCH (n) OPTIONAL MATCH ()-[r]->() RETURN "
                "count(DISTINCT n) AS nodes, count(DISTINCT r) AS rels"
            )
            .single()
            .data()
        )
        edges = [
            r.data()
            for r in s.run(
                "MATCH (a)-[r]->(b) RETURN elementId(a) AS a, elementId(r) AS r, elementId(b) AS b"
            )
        ]
        with pytest.raises(MigrationBlockedError, match="collision"):
            s.execute_write(apply_snapshot, snapshot)
        assert (
            s.run("MATCH (n) WHERE n.identity_snapshot IS NOT NULL RETURN count(n) AS n").single()[
                "n"
            ]
            == 0
        )
        s.run("MATCH (b:Company {cnpj:'11222333000181'}) SET b.cnpj = 'invalid'").consume()
        assert s.execute_write(apply_snapshot, snapshot) == {"assigned": 3, "collisions": 0}
        after = (
            s.run(
                "MATCH (n) OPTIONAL MATCH ()-[r]->() RETURN "
                "count(DISTINCT n) AS nodes, count(DISTINCT r) AS rels"
            )
            .single()
            .data()
        )
        assert before == after
        assert edges == [
            r.data()
            for r in s.run(
                "MATCH (a)-[r]->(b) RETURN elementId(a) AS a, elementId(r) AS r, elementId(b) AS b"
            )
        ]
        mappings = [
            r.data()
            for r in s.run(
                "MATCH (n) RETURN elementId(n) AS element, n.identity_legacy_id AS legacy, "
                "n.identity_snapshot AS snapshot, n.entity_id AS id"
            )
        ]
        assert all(
            m["element"] == m["legacy"] and m["snapshot"] == snapshot and m["id"] for m in mappings
        )
        assert len({m["id"] for m in mappings}) == 3
        root = Path(__file__).resolve().parents[2] / "api" / "src" / "bracc" / "queries"

        def query(name: str) -> str:
            return (root / f"{name}.cypher").read_text()

        company = next(m for m in mappings if m["id"] == old_id)
        assert (
            s.run(query("entity_by_element_id"), element_id=company["legacy"]).single()["entity_id"]
            == old_id
        )
        assert (
            s.run(
                query("entity_by_snapshot_alias"), snapshot=snapshot, legacy_id=company["legacy"]
            ).single()["entity_id"]
            == old_id
        )
        assert (
            s.run(query("entity_by_canonical_id"), entity_id=old_id).single()["entity_id"] == old_id
        )
        assert (
            s.run(
                query("entity_lookup"),
                identifier="11222333000181",
                identifier_formatted="11.222.333/0001-81",
            ).single()["entity_id"]
            == old_id
        )
        assert (
            s.run(
                query("search_cnpj"),
                identifier="11222333000181",
                identifier_formatted="11.222.333/0001-81",
                entity_type=None,
                skip=0,
                limit=10,
            ).single()["node_id"]
            == old_id
        )
        assert (
            s.run(query("graph_expand"), entity_id=old_id, depth=1).single()["center_id"] == old_id
        )
        assert s.run(query("node_degree"), entity_id=old_id).single()["degree"] == 1
        forward = s.run(
            query("entity_connections"), entity_id=old_id, depth=1, include_probable=False
        ).single()
        assert forward["center_id"] == old_id
        assert forward["source_id"] == old_id
        partner_id = forward["target_id"]
        reverse = list(
            s.run(
                query("entity_connections"),
                entity_id=partner_id,
                depth=1,
                include_probable=False,
            )
        )
        assert any(
            r["center_id"] == partner_id
            and r["source_id"] == old_id
            and r["target_id"] == partner_id
            for r in reverse
        )
        two_hops = list(
            s.run(
                query("entity_connections"),
                entity_id=old_id,
                depth=2,
                include_probable=False,
            )
        )
        assert len(two_hops) == 2
        assert any(r["source_id"] == partner_id and r["target_id"] != old_id for r in two_hops)
        path = tmp_path / "crosswalk.json"
        assignments = s.execute_read(snapshot_assignments, snapshot)
        export_crosswalk(path, snapshot, assignments)
        with pytest.raises(FileExistsError):
            export_crosswalk(path, snapshot, assignments)
        payload = read_crosswalk(path)
        corrupt = tmp_path / "corrupt.json"
        corrupt.write_bytes(
            path.read_bytes().replace(b"synthetic-snapshot-v1", b"synthetic-snapshot-v2")
        )
        with pytest.raises(ValueError, match="checksum"):
            read_crosswalk(corrupt)
        states = {
            r["legacy"]: r["state"]
            for r in s.run(
                "MATCH (n) RETURN n.identity_legacy_id AS legacy, n.identity_migration AS state"
            )
        }
        s.run("MATCH (n:Partner) SET n.identity_migration = 'existing'").consume()
        with pytest.raises(MigrationBlockedError, match="inconsistent"):
            s.execute_write(rollback_snapshot, snapshot, assignments, states)
        assert (
            s.run(
                "MATCH (n) WHERE n.identity_snapshot = $snapshot RETURN count(n) AS c",
                snapshot=snapshot,
            ).single()["c"]
            == 3
        )
        s.run("MATCH (n:Partner) SET n.identity_migration = 'created'").consume()
        assert s.execute_write(rollback_snapshot, snapshot, assignments, states) == 3
        assert s.run(
            "MATCH (n) WHERE n.entity_id IS NOT NULL RETURN collect(n.entity_id) AS ids"
        ).single()["ids"] == [old_id]
        assert (
            s.run(
                "MATCH (n) OPTIONAL MATCH ()-[r]->() RETURN "
                "count(DISTINCT n) AS nodes, count(DISTINCT r) AS rels"
            )
            .single()
            .data()
            == before
        )
        assert edges == [
            r.data()
            for r in s.run(
                "MATCH (a)-[r]->(b) RETURN elementId(a) AS a, elementId(r) AS r, elementId(b) AS b"
            )
        ]

        # Rebuild is a new synthetic graph. Mapping is supplied by the verified
        # fixture provenance; production needs a durable source crosswalk.
        s.run("MATCH (n) DETACH DELETE n").consume()
        targets = {}
        for mapping in mappings:
            node = s.run("CREATE (n:Company) RETURN elementId(n) AS id").single()["id"]
            targets[mapping["legacy"]] = node
        with pytest.raises(MigrationBlockedError):
            s.execute_write(restore_crosswalk, payload, {})
        assert s.execute_write(restore_crosswalk, payload, targets) == 3
        rebuilt = {
            r["legacy"]: r["id"]
            for r in s.run("MATCH (n) RETURN n.identity_legacy_id AS legacy, n.entity_id AS id")
        }
        assert rebuilt == {m["legacy"]: m["id"] for m in mappings}
