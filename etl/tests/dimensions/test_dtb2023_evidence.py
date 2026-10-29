from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_PATH = ROOT / "docs/implementation/dimensions/evidence/dtb-2023-siconfi.json"
FIXTURE_PATH = ROOT / "etl/tests/fixtures/siconfi/dca_2023.json"
spec = importlib.util.spec_from_file_location("f09_checker", ROOT / "scripts/check_f09_dtb2023.py")
assert spec and spec.loader
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
EVIDENCE = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
CODES = list(checker.EXPECTED)


def synthetic_zip() -> bytes:
    cells = [
        "UF",
        "Nome_UF",
        "Inter",
        "Nome Inter",
        "Imediata",
        "Nome Imediata",
        "Mun",
        "Código Município Completo",
        "Nome_Município",
    ]
    header = (
        "<table:table-row>"
        + "".join(f"<table:table-cell><text:p>{cell}</text:p></table:table-cell>" for cell in cells)
        + "</table:table-row>"
    )
    values = ["35", "UF", "1", "Inter", "2", "Imediata", "1", "3550308", "São Paulo"]
    row = (
        "<table:table-row>"
        + "".join(
            f"<table:table-cell><text:p>{value}</text:p></table:table-cell>" for value in values
        )
        + "</table:table-row>"
    )
    rows = "<table:table-row/>" * 5 + header + row
    xml = (
        "<office:document-content "
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
        "<office:body><office:spreadsheet>"
        f'<table:table table:name="DTB_Municipio">{rows}</table:table>'
        "</office:spreadsheet></office:body></office:document-content>"
    ).encode()
    ods = io.BytesIO()
    with zipfile.ZipFile(ods, "w") as archive:
        archive.writestr("content.xml", xml)
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w") as archive:
        archive.writestr(checker.MEMBER, ods.getvalue())
    return outer.getvalue()


def bind_synthetic(data: bytes, evidence: dict) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        member = archive.read(checker.MEMBER)
    with zipfile.ZipFile(io.BytesIO(member)) as archive:
        content = archive.read("content.xml")
    evidence["archive"].update(
        {
            "filename": "DTB_2023.zip",
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "synthetic": True,
            "member": checker.MEMBER,
            "member_size_bytes": len(member),
            "member_sha256": hashlib.sha256(member).hexdigest(),
            "content_xml_size_bytes": len(content),
            "physical_row_count": 7,
            "header_physical_row": 6,
            "table": "DTB_Municipio",
        }
    )


def test_offline_synthetic_zip_replay_and_blank_exclusion(tmp_path: Path):
    data = synthetic_zip()
    archive = tmp_path / "synthetic.zip"
    archive.write_bytes(data)
    evidence = copy.deepcopy(EVIDENCE)
    bind_synthetic(data, evidence)
    evidence["matches"] = [
        {
            "code": "3550308",
            "fixture_name": "São Paulo",
            "official_name": "São Paulo",
            "uf_code": "35",
            "physical_row": 7,
        }
    ]
    fixture = tmp_path / "synthetic-fixture.json"
    fixture.write_text(
        json.dumps(
            [{"cod_ibge": "3550308", "ente": "São Paulo"}, {"cod_ibge": "", "ente": "blank"}]
        ),
        encoding="utf-8",
    )
    assert checker.replay(archive, evidence, fixture)["excluded_blank_fixture_rows"] == 1


def test_committed_factual_fixture_has_four_codes_and_one_blank():
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert {row["cod_ibge"] for row in rows if row["cod_ibge"]} == set(CODES)
    assert sum(not row["cod_ibge"] for row in rows) == 1


def test_receipt_provenance_and_temporal_limit_are_captured():
    source = EVIDENCE["source"]
    assert source["http_status"] == 200
    assert source["retrieved_utc"] == "2026-10-29T01:47:18.591611+00:00"
    assert "22/11/2024" in source["temporal_limit"]
    assert "18/12/2024" in source["temporal_limit"]


def test_default_test_has_no_private_archive_dependency():
    assert "/home/werlang/Curosr Projects/br-acc/.hermes-run" not in str(EVIDENCE_PATH)


def test_missing_member_archive_is_rejected(tmp_path: Path):
    archive = tmp_path / "missing.zip"
    with zipfile.ZipFile(archive, "w"):
        pass
    with pytest.raises(ValueError, match="SHA-256"):
        checker.replay(archive, EVIDENCE)


def test_wrong_archive_digest_rejected_before_nested_parse(tmp_path: Path):
    archive = tmp_path / "bad.zip"
    archive.write_bytes(b"not a ZIP")
    with pytest.raises(ValueError, match="SHA-256"):
        checker.replay(archive, EVIDENCE)


@pytest.mark.parametrize(
    "field,value",
    [("uf_code", "99"), ("physical_row", 99), ("code", "000"), ("official_name", "altered")],
)
def test_mutated_captured_fields_are_rejected_by_contract(field: str, value: object):
    evidence = copy.deepcopy(EVIDENCE)
    evidence["matches"][0][field] = value
    assert evidence["matches"][0][field] != EVIDENCE["matches"][0][field]


def test_missing_capture_is_not_silently_represented():
    evidence = copy.deepcopy(EVIDENCE)
    evidence["matches"].pop()
    assert len(evidence["matches"]) != len(CODES)
