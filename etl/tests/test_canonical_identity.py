import pytest

from bracc_etl.identity.legacy import LegacyEntity, propose


def test_collisions_do_not_merge_and_existing_id_survives():
    original = "fda78e8c-a1f3-499d-8fb4-8e6f4b7e6436"
    rows = [
        LegacyEntity("a", "Company", "11.222.333/0001-81", original),
        LegacyEntity("b", "Company", "11222333000181"),
        LegacyEntity("c", "Person", "***.123.456-**"),
        LegacyEntity("d", "Person", "***.123.456-**"),
    ]
    assignments, collisions = propose("snapshot-1", rows)
    assert assignments[0].entity_id == original
    assert len({a.entity_id for a in assignments}) == 4
    assert [(c.namespace, c.legacy_ids) for c in collisions] == [
        ("br:cnpj:establishment", ("a", "b"))
    ]
    rebuilt, _ = propose(
        "snapshot-1", [LegacyEntity(a.legacy_id, "", entity_id=a.entity_id) for a in assignments]
    )
    assert rebuilt == assignments


def test_duplicate_aliases_and_canonical_ids_fail_closed():
    with pytest.raises(ValueError):
        propose("snapshot", [LegacyEntity("same", "Person"), LegacyEntity("same", "Person")])
    ident = "fda78e8c-a1f3-499d-8fb4-8e6f4b7e6436"
    with pytest.raises(ValueError):
        propose(
            "snapshot",
            [
                LegacyEntity("a", "Person", entity_id=ident),
                LegacyEntity("b", "Person", entity_id=ident),
            ],
        )


def test_crosswalk_rejects_invalid_and_duplicate_entries(tmp_path):
    from bracc_etl.identity.crosswalk import export_crosswalk, read_crosswalk
    from bracc_etl.identity.legacy import Assignment

    snapshot = "fixture-v1"
    alias = "4:12345678-1234-1234-1234-123456789abc:1"
    ident = "fda78e8c-a1f3-499d-8fb4-8e6f4b7e6436"
    with pytest.raises(ValueError):
        export_crosswalk(tmp_path / "invalid.json", snapshot, [Assignment(snapshot, "cpf", ident)])
    with pytest.raises(ValueError):
        export_crosswalk(
            tmp_path / "duplicate.json",
            snapshot,
            [Assignment(snapshot, alias, ident), Assignment(snapshot, alias, ident)],
        )
    path = tmp_path / "valid.json"
    export_crosswalk(path, snapshot, [Assignment(snapshot, alias, ident)])
    data = path.read_bytes()
    assert b"cpf" not in data and b"cnpj" not in data
    path.write_bytes(data.replace(b"fixture-v1", b"fixture-v2"))
    with pytest.raises(ValueError, match="checksum"):
        read_crosswalk(path)
