"""Materialize explicit dimension references without connecting to a database."""

from copy import deepcopy
from typing import Any, TypedDict


class Materialized(TypedDict):
    dimensions: list[dict[str, str]]
    references: list[dict[str, str]]


class DimensionError(ValueError):
    """An incomplete or conflicting dimension observation."""


IBGE_UF_CODES = {
    "11": "RO",
    "12": "AC",
    "13": "AM",
    "14": "RR",
    "15": "PA",
    "16": "AP",
    "17": "TO",
    "21": "MA",
    "22": "PI",
    "23": "CE",
    "24": "RN",
    "25": "PB",
    "26": "PE",
    "27": "AL",
    "28": "SE",
    "29": "BA",
    "31": "MG",
    "32": "ES",
    "33": "RJ",
    "35": "SP",
    "41": "PR",
    "42": "SC",
    "43": "RS",
    "50": "MS",
    "51": "MT",
    "52": "GO",
    "53": "DF",
}


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or ":" in value:
        raise DimensionError(f"{field} must be nonempty text without ':' or surrounding whitespace")
    return value


def _dimension(
    kind: str, observation: dict[str, Any], fields: tuple[str, ...], id_field: str
) -> dict[str, str]:
    parts = [_text(observation.get(field), field) for field in fields]
    result = {field: value for field, value in zip(fields, parts, strict=True)}
    result[id_field] = ":".join(parts)
    result["kind"] = kind
    return result


def materialize(rows: list[dict[str, Any]]) -> Materialized:
    """Return unique dimension records and per-row references from explicit input.

    The caller supplies authoritative codes and versions as text. This function
    neither validates membership in an official vocabulary nor infers identities.
    """
    definitions = {
        "territory": (
            "Territory",
            ("system", "type", "code", "territorial_version"),
            "territory_id",
        ),
        "public_body": (
            "PublicBody",
            ("jurisdiction", "system", "role", "code", "version"),
            "public_body_id",
        ),
        "activity": ("EconomicActivity", ("classification", "version", "code"), "activity_id"),
        "unit": ("Unit", ("system", "code"), "unit_id"),
        "fiscal_year": ("FiscalYear", ("year",), "fiscal_year_id"),
    }
    dimensions: dict[tuple[str, str], dict[str, str]] = {}
    references: list[dict[str, str]] = []
    for row in rows:
        refs: dict[str, str] = {}
        for key, (kind, fields, id_field) in definitions.items():
            if key not in row:
                continue
            value = row[key]
            if not isinstance(value, dict):
                raise DimensionError(f"{key} must be an object")
            record = _dimension(kind, value, fields, id_field)
            if key == "territory":
                uf = _text(value.get("uf"), "uf")
                if len(uf) != 2 or not uf.isascii() or not uf.isupper() or not uf.isalpha():
                    raise DimensionError("uf must be two uppercase ASCII letters")
                record["uf"] = uf
                if value["system"] == "IBGE" and value["type"] == "municipio":
                    code = record["code"]
                    if (
                        len(code) != 7
                        or not code.isascii()
                        or not code.isdigit()
                        or IBGE_UF_CODES.get(code[:2]) != uf
                    ):
                        raise DimensionError(
                            "IBGE municipality code must be 7 digits with matching UF prefix"
                        )
                elif value["system"] == "IBGE" and value["type"] == "uf":
                    if IBGE_UF_CODES.get(record["code"]) != uf:
                        raise DimensionError("IBGE UF code must match the UF abbreviation")
            if key == "fiscal_year" and (
                len(record["year"]) != 4
                or not record["year"].isascii()
                or not record["year"].isdigit()
            ):
                raise DimensionError("year must be four ASCII digits")
            identity = (kind, record[id_field])
            if identity in dimensions and dimensions[identity] != record:
                raise DimensionError(f"conflicting dimension: {identity}")
            dimensions[identity] = record
            refs[key] = record[id_field]
        references.append(refs)
    return {
        "dimensions": [deepcopy(dimensions[key]) for key in sorted(dimensions)],
        "references": references,
    }
