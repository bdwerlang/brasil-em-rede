"""Static contract for the two Neo4j schema entry points."""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / 'infra/neo4j/init.cypher'
API = ROOT / 'api/src/bracc/queries/schema_init.cypher'


def test_schema_entrypoints_are_identical():
    assert INFRA.read_text() == API.read_text()


def test_literal_pipeline_node_keys_have_constraints():
    schema = INFRA.read_text()
    keys = set(re.findall(r'FOR \(\w+:(\w+)\) REQUIRE \w+\.(\w+) IS UNIQUE', schema))
    missing = set()
    for path in (ROOT / 'etl/src/bracc_etl/pipelines').glob('*.py'):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != 'load_nodes' or not node.args or not isinstance(node.args[0], ast.Constant):
                continue
            key = next((kw.value.value for kw in node.keywords if kw.arg == 'key_field' and isinstance(kw.value, ast.Constant)), None)
            if key and (node.args[0].value, key) not in keys:
                missing.add((path.name, node.args[0].value, key))
    # Alternate Person keys require identity reconciliation before uniqueness.
    assert missing == {
        ("transferegov.py", "Person", "author_key"),
        ("transparencia.py", "Person", "author_key"),
        ("tse.py", "Person", "sq_candidato"),
    }


def test_explicit_dimension_keys():
    keys = set(re.findall(r"FOR \(\w+:(\w+)\) REQUIRE \w+\.(\w+) IS UNIQUE", INFRA.read_text()))
    assert {("Territory", "territory_id"), ("PublicBody", "public_body_id"),
            ("EconomicActivity", "activity_id"), ("Unit", "unit_id"),
            ("FiscalYear", "fiscal_year_id")} <= keys


def test_person_identity_constraints_are_scoped_to_snapshot_and_label():
    schema = INFRA.read_text()
    assert re.search(r'FOR \(p:Person\) REQUIRE p\.entity_id IS UNIQUE', schema)
    assert re.search(
        r'FOR \(p:Person\) REQUIRE \(p\.identity_snapshot, p\.identity_legacy_id\) IS UNIQUE',
        schema,
    )
    assert not re.search(r'FOR \(p:Person\) REQUIRE p\.(author_key|sq_candidato) IS UNIQUE', schema)
