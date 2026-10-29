#!/usr/bin/env python3
"""Offline replay of pinned DTB municipality evidence
never accesses network."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ZIP_SHA256 = "9737cb335711eac12fb76a99baee17f7ed169ad7e4006451e41edb2dc023c4c8"
MEMBER = "DTB_2023/RELATORIO_DTB_BRASIL_MUNICIPIO.ods"
MEMBER_SHA256 = "5b692f188ad75f536254b374b798d2f739d04ef636f58d32d8e13f899429170c"
CONTENT_SHA256 = "dca4cef2f5452af209439da1bd823540b5593e5c616021f4f43fb1a0597c52c7"
NS = {"t": "urn:oasis:names:tc:opendocument:xmlns:table:1.0"}
EXPECTED = {
    "3550308": ("São Paulo", "35", 3838),
    "3304557": ("Rio de Janeiro", "33", 3249),
    "5300108": ("Brasília", "53", 5576),
    "2927408": ("Salvador", "29", 2169),
}
FIXTURE = Path(__file__).resolve().parents[1] / "etl/tests/fixtures/siconfi/dca_2023.json"


def replay(archive: Path, evidence: dict, fixture_path: Path = FIXTURE) -> dict:
    size = archive.stat().st_size
    if size > 5_000_000:
        raise ValueError("archive exceeds size limit")
    data = archive.read_bytes()
    meta = evidence["archive"]
    digest = hashlib.sha256(data).hexdigest()
    if fixture_path == FIXTURE and digest != ZIP_SHA256:
        raise ValueError("archive SHA-256 mismatch")
    if digest != meta.get("sha256"):
        raise ValueError("archive SHA-256 mismatch")
    if len(data) != meta.get("size_bytes") or meta.get("filename") != "DTB_2023.zip":
        raise ValueError("archive metadata mismatch")
    with zipfile.ZipFile(archive) as zf:
        if zf.namelist().count(MEMBER) != 1:
            raise ValueError("ODS member missing or duplicated")
        if zf.getinfo(MEMBER).file_size > 2_000_000:
            raise ValueError("ODS member exceeds size limit")
        ods = zf.read(MEMBER)
    digest = hashlib.sha256(ods).hexdigest()
    if fixture_path == FIXTURE and digest != MEMBER_SHA256:
        raise ValueError("pinned ODS member SHA-256 mismatch")
    if (
        digest != meta.get("member_sha256")
        or meta.get("member") != MEMBER
        or len(ods) != meta.get("member_size_bytes")
    ):
        raise ValueError("ODS member metadata/hash mismatch")
    with zipfile.ZipFile(io.BytesIO(ods)) as zf:
        if zf.namelist().count("content.xml") != 1:
            raise ValueError("content.xml missing or duplicated")
        if zf.getinfo("content.xml").file_size > 10_000_000:
            raise ValueError("content.xml exceeds size limit")
        content = zf.read("content.xml")
    if len(content) != meta.get("content_xml_size_bytes"):
        raise ValueError("content XML size mismatch")
    if fixture_path == FIXTURE and hashlib.sha256(content).hexdigest() != CONTENT_SHA256:
        raise ValueError("pinned content.xml SHA-256 mismatch")
    if re.search(rb"<!\s*(DOCTYPE|ENTITY)\b", content, re.I):
        raise ValueError("DTD/entities are not permitted")
    root = ET.fromstring(content)
    tables = root.findall(".//t:table[@t:name='DTB_Municipio']", NS)
    if len(tables) != 1 or meta.get("table") != "DTB_Municipio":
        raise ValueError("table mismatch")
    rows = tables[0].findall("t:table-row", NS)
    if len(rows) != meta.get("physical_row_count") or meta.get("header_physical_row") != 6:
        raise ValueError("physical row/header count mismatch")
    found = {}
    for physical, row in enumerate(rows, 1):
        cells = []
        for cell in list(row):
            if cell.tag.rsplit("}", 1)[-1] not in ("table-cell", "covered-table-cell"):
                continue
            repeat = int(cell.attrib.get("{" + NS["t"] + "}number-columns-repeated", "1"))
            if repeat < 1:
                raise ValueError("column repeat must be positive")
            cells.extend(["".join(cell.itertext())] * min(repeat, 20))
        if physical == 6 and (
            cells[0] != "UF" or cells[7:9] != ["Código Município Completo", "Nome_Município"]
        ):
            raise ValueError("header mismatch")
        if physical > 6 and len(cells) > 8 and cells[7].strip():
            if cells[7] in found:
                raise ValueError("duplicate official code")
            found[cells[7]] = {"row": physical, "uf": cells[0], "name": cells[8]}
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    records = {}
    blanks = 0
    for record in fixture:
        code = record.get("cod_ibge", "")
        if not code.strip():
            blanks += 1
        elif code in records:
            raise ValueError("duplicate fixture code")
        else:
            records[code] = record
    if blanks != 1 or evidence.get("excluded_blank_fixture_rows") != 1:
        raise ValueError("blank-code fixture exclusion mismatch")
    expected = (
        {code: (name, name, uf, physical) for code, (name, uf, physical) in EXPECTED.items()}
        if fixture_path == FIXTURE
        else {code: (record["ente"], record["ente"], "35", 7) for code, record in records.items()}
    )
    if not expected or set(records) != set(expected):
        raise ValueError("fixture candidate code set mismatch")
    matches = evidence.get("matches", [])
    codes = [item.get("code") for item in matches]
    if len(codes) != len(set(codes)) or set(codes) != set(expected):
        raise ValueError("captured match code set mismatch")
    result = []
    for item in matches:
        code = item["code"]
        fixture_name, official_name, uf, physical = expected[code]
        if (
            item.get("fixture_name"),
            item.get("official_name"),
            item.get("uf_code"),
            item.get("physical_row"),
        ) != (fixture_name, official_name, uf, physical):
            raise ValueError(f"captured match metadata mismatch for {code}")
        if records[code].get("ente") != fixture_name or found.get(code) != {
            "row": physical,
            "uf": uf,
            "name": official_name,
        }:
            raise ValueError(f"fixture or official mapping mismatch for {code}")
        result.append(item)
    return {"verified": True, "matches": result, "excluded_blank_fixture_rows": blanks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="retained official ZIP; manual opt-in replay")
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "docs/implementation/dimensions/evidence/dtb-2023-siconfi.json",
    )
    args = parser.parse_args()
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    print(json.dumps(replay(args.archive, evidence), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
