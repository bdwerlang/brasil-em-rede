import pytest

from bracc_etl.dimensions import DimensionError, materialize


def row():
    return {
        "territory": {
            "system": "IBGE",
            "type": "municipio",
            "code": "0012345",
            "territorial_version": "2022",
            "uf": "SP",
        },
        "public_body": {
            "jurisdiction": "SP",
            "system": "SIAFI",
            "role": "UG",
            "code": "000123",
            "version": "2024",
        },
        "activity": {"classification": "CNAE", "version": "2.0", "code": "0111301"},
        "unit": {"system": "ISO4217", "code": "BRL"},
        "fiscal_year": {"year": "2024"},
        "aggregate": {"value": 10, "category": "pessoas"},
    }


def test_materializes_explicit_dimensions_and_preserves_codes():
    result = materialize([row(), row()])
    assert len(result["dimensions"]) == 5
    assert result["references"][0] == result["references"][1]
    by_kind = {item["kind"]: item for item in result["dimensions"]}
    assert by_kind["Territory"]["territory_id"] == "IBGE:municipio:0012345:2022"
    assert by_kind["Territory"]["uf"] == "SP"
    assert by_kind["EconomicActivity"]["code"] == "0111301"
    assert by_kind["PublicBody"]["code"] == "000123"
    assert by_kind["FiscalYear"]["year"] == "2024"
    assert by_kind["Unit"]["code"] == "BRL"
    assert not {"Person", "Company"} & by_kind.keys()


def test_versions_roles_and_units_stay_distinct():
    a, b = row(), row()
    b["territory"]["territorial_version"] = "2023"
    b["public_body"]["role"] = "orgao"
    b["unit"] = {"system": "IBGE", "code": "pessoas"}
    result = materialize([a, b])
    assert len(result["dimensions"]) == 8
    assert result["references"][0] != result["references"][1]


def test_conflicting_uf_is_rejected():
    a, b = row(), row()
    b["territory"]["uf"] = "RJ"
    with pytest.raises(DimensionError, match="conflicting"):
        materialize([a, b])


@pytest.mark.parametrize("field,value", [("code", 123), ("code", "01:2"), ("uf", "sp")])
def test_invalid_territory_rejected(field, value):
    record = row()
    record["territory"][field] = value
    with pytest.raises(DimensionError):
        materialize([record])


def test_invalid_year_rejected():
    record = row()
    record["fiscal_year"]["year"] = "24"
    with pytest.raises(DimensionError):
        materialize([record])
