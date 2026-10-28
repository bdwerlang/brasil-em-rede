"""Offline coverage for the preflight's schema parsing and catalog checks."""
import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'infra/neo4j/preflight.py'
spec = importlib.util.spec_from_file_location('preflight', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_schema_parses_constraints_and_fulltext():
    items = module.definitions(module.SCHEMA.read_text())
    assert any(i['name'] == 'offshore_entity_id_unique' for i in items)
    fulltext = next(i for i in items if i['name'] == 'entity_search')
    assert 'Person' in fulltext['labels'] and 'SourceDocument' in fulltext['labels']
    assert 'name' in fulltext['properties'] and 'url' in fulltext['properties']
    composite = next(i for i in items if i['name'] == 'person_snapshot_alias_unique')
    assert composite['properties'] == ['identity_snapshot', 'identity_legacy_id']
