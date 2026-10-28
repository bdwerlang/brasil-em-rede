"""Project explicitly supplied dimensions and RAIS references in one transaction."""

from typing import Any

from neo4j import Driver, ManagedTransaction

from .materialize import materialize

_KEYS = {
    "Territory": "territory_id",
    "PublicBody": "public_body_id",
    "EconomicActivity": "activity_id",
    "Unit": "unit_id",
    "FiscalYear": "fiscal_year_id",
}
_RELATIONS = {
    "territory": ("Territory", "territory_id", "IN_TERRITORY"),
    "public_body": ("PublicBody", "public_body_id", "REFERENCES_BODY"),
    "activity": ("EconomicActivity", "activity_id", "IN_ACTIVITY"),
    "unit": ("Unit", "unit_id", "MEASURED_IN"),
    "fiscal_year": ("FiscalYear", "fiscal_year_id", "IN_FISCAL_YEAR"),
}


def project_rais(driver: Driver, database: str | None, observations: list[dict[str, Any]]) -> None:
    """Create dimensions and links to existing LaborStats in a transaction.

    Call only after LaborStats nodes exist; no implicit identifiers or entities.
    Schema constraints must be installed separately to protect concurrent writers.
    """
    _project(driver, database, observations, "LaborStats", "stats_id")


def project_siconfi(
    driver: Driver, database: str | None, observations: list[dict[str, Any]]
) -> None:
    """Project explicit dimensions onto existing MunicipalFinance facts."""
    _project(driver, database, observations, "MunicipalFinance", "finance_id")


def _project(
    driver: Driver,
    database: str | None,
    observations: list[dict[str, Any]],
    fact_label: str,
    fact_key: str,
) -> None:
    result = materialize([item["dimensions"] for item in observations])

    def write(tx: ManagedTransaction) -> None:
        for record in result["dimensions"]:
            props = dict(record)
            label = props.pop("kind")
            key = _KEYS[label]
            query = f"MERGE (n:{label} {{{key}: $id}}) ON CREATE SET n += $props RETURN n"
            existing = tx.run(query, id=props[key], props=props).single(strict=True)["n"]
            if any(existing.get(k) != v for k, v in props.items()):
                raise ValueError(f"Conflicting existing {label} dimension: {props[key]}")
        for item, refs in zip(observations, result["references"], strict=True):
            for name, identity in refs.items():
                label, key, relation = _RELATIONS[name]
                query = (
                    f"MATCH (s:{fact_label} {{{fact_key}: $fact_id}}) "
                    f"MATCH (d:{label} {{{key}: $id}}) "
                    f"MERGE (s)-[:{relation}]->(d) RETURN count(s) AS matched"
                )
                if (
                    tx.run(query, fact_id=item[fact_key], id=identity).single(strict=True)[
                        "matched"
                    ]
                    != 1
                ):
                    raise ValueError(f"{fact_label} missing or duplicated")
            if fact_label == "MunicipalFinance":
                complete = "public_body" in refs
                tx.run(
                    "MATCH (s:MunicipalFinance {finance_id: $fact_id}) "
                    "SET s.dimension_status = $status, s.dimension_reason = $reason",
                    fact_id=item[fact_key],
                    status="projected" if complete else "partial",
                    reason="" if complete else "missing_public_body_metadata",
                ).consume()

    with driver.session(database=database) as session:
        session.execute_write(write)
