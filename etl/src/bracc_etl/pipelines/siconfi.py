from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from bracc_etl.base import Pipeline
from bracc_etl.dimensions.crosswalk import PreparedCrosswalk, prepare_crosswalk
from bracc_etl.dimensions.projection import project_siconfi

if TYPE_CHECKING:
    from neo4j import Driver
from bracc_etl.loader import Neo4jBatchLoader
from bracc_etl.transforms import (
    format_cnpj,
    normalize_cnpj,
    normalize_name,
)

logger = logging.getLogger(__name__)


class SiconfiPipeline(Pipeline):
    """ETL pipeline for SICONFI (municipal/state finance declarations).

    Data source: Tesouro Nacional API (apidatalake.tesouro.gov.br).
    Loads MunicipalFinance aggregates and explicit dimension references.
    """

    name = "siconfi"
    source_id = "siconfi"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        dimension_crosswalk: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size, **kwargs)
        self.dimension_crosswalk = dimension_crosswalk
        self._raw: list[dict[str, Any]] = []
        self.finances: list[dict[str, Any]] = []
        self.dimension_observations: list[dict[str, Any]] = []

    def extract(self) -> None:
        siconfi_dir = Path(self.data_dir) / "siconfi"
        all_records: list[dict[str, Any]] = []

        # Read CSV files produced by download_siconfi.py
        csv_files = sorted(siconfi_dir.glob("dca_*.csv"))
        for csv_file in csv_files:
            df = pd.read_csv(csv_file, dtype=str, keep_default_na=False)
            all_records.extend(df.to_dict("records"))  # type: ignore[arg-type]
            logger.info("  Loaded %d records from %s", len(df), csv_file.name)

        # Fallback: also try JSON if present (original API format)
        for json_file in sorted(siconfi_dir.glob("*.json")):
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
                items = data if isinstance(data, list) else data.get("items", [])
                all_records.extend(items)

        if self.limit:
            all_records = all_records[: self.limit]

        self._raw = all_records
        logger.info("Extracted %d SICONFI records", len(self._raw))

    def transform(self) -> None:
        finances: list[dict[str, Any]] = []
        dimension_by_fact: dict[str, dict[str, Any]] = {}
        metadata_by_fact: dict[str, dict[str, str]] = {}
        cnpj_by_fact: dict[str, str] = {}
        prepared: PreparedCrosswalk | None = None

        required = (
            "cod_ibge",
            "exercicio",
            "uf",
            "versao_territorial",
            "tipo_territorio",
            "unidade_sistema",
            "unidade_codigo",
        )

        for row in self._raw:
            cod_ibge = str(row.get("cod_ibge", "")).strip()
            if not cod_ibge:
                continue

            # DCA `instituicao` names the reporting institution, not the municipality.
            municipality = normalize_name(str(row.get("ente", "")))
            institution = normalize_name(str(row.get("instituicao", "")))
            exercicio = str(row.get("exercicio", "")).strip()
            conta = str(row.get("conta", "")).strip()
            coluna = str(row.get("coluna", "")).strip()
            valor = row.get("valor")

            if valor is None or valor == "":
                continue

            try:
                amount = float(str(valor).replace(",", "."))
            except (ValueError, TypeError):
                continue

            id_source = f"{cod_ibge}_{exercicio}_{conta}_{coluna}"
            finance_id = hashlib.sha256(id_source.encode()).hexdigest()[:16]
            cnpj = normalize_cnpj(str(row.get("cnpj") or ""))
            if re.fullmatch(r"[A-Z0-9]{12}[0-9]{2}", cnpj):
                observed_cnpj = format_cnpj(cnpj)
                previous_cnpj = cnpj_by_fact.setdefault(finance_id, observed_cnpj)
                if previous_cnpj != observed_cnpj:
                    raise ValueError("conflicting observed CNPJ for same finance_id")

            finances.append(
                {
                    "finance_id": finance_id,
                    "cod_ibge": cod_ibge,
                    "municipality": municipality,
                    "reporting_institution": institution,
                    "year": exercicio,
                    "account": conta,
                    "column": coluna,
                    "amount": amount,
                    "source": "siconfi",
                    "code_validation_status": "pending",
                    "code_validation_reason": "dimension_metadata_missing",
                    "dimension_status": "pending",
                    "dimension_reason": "projection_not_completed",
                }
            )

            metadata_fields = required + (
                "orgao_jurisdicao",
                "orgao_sistema",
                "orgao_papel",
                "orgao_codigo",
                "orgao_versao",
            )
            known = metadata_by_fact.setdefault(finance_id, {})
            for field in metadata_fields:
                value = row.get(field)
                if isinstance(value, str) and value:
                    if field in known and known[field] != value:
                        raise ValueError(f"conflicting metadata {field} for same finance_id")
                    known[field] = value

        facts_by_id: dict[str, dict[str, Any]] = {}
        status_fields = {
            "code_validation_status",
            "code_validation_reason",
            "dimension_status",
            "dimension_reason",
        }
        for fact in finances:
            fact_id = fact["finance_id"]
            previous = facts_by_id.get(fact_id)
            if previous is None:
                facts_by_id[fact_id] = fact
                continue
            if any(previous[key] != fact[key] for key in fact.keys() - status_fields):
                raise ValueError("conflicting values for same finance_id")
        self.finances = [facts_by_id[key] for key in sorted(facts_by_id)]
        for fact in self.finances:
            if fact["finance_id"] in cnpj_by_fact:
                fact["observed_cnpj"] = cnpj_by_fact[fact["finance_id"]]
        for fact in self.finances:
            finance_id = fact["finance_id"]
            row = metadata_by_fact[finance_id]
            missing = [field for field in required if field not in row]
            if missing:
                fact["dimension_reason"] = "missing_metadata:" + ",".join(missing)
            if not missing:
                if row["tipo_territorio"] not in {"municipio", "uf"}:
                    raise ValueError("tipo_territorio must be municipio or uf")
                dimensions: dict[str, Any] = {
                    "territory": {
                        "system": "IBGE",
                        "type": row["tipo_territorio"],
                        "code": row["cod_ibge"],
                        "territorial_version": row["versao_territorial"],
                        "uf": row["uf"],
                    },
                    "unit": {"system": row["unidade_sistema"], "code": row["unidade_codigo"]},
                    "fiscal_year": {"year": row["exercicio"]},
                }
                body_fields = (
                    "orgao_jurisdicao",
                    "orgao_sistema",
                    "orgao_papel",
                    "orgao_codigo",
                    "orgao_versao",
                )
                if all(isinstance(row.get(field), str) and row[field] for field in body_fields):
                    if row["orgao_papel"] not in {"orgao", "ug", "ente"}:
                        raise ValueError("orgao_papel must be orgao, ug, or ente")
                    dimensions["public_body"] = {
                        "jurisdiction": row["orgao_jurisdicao"],
                        "system": row["orgao_sistema"],
                        "role": row["orgao_papel"],
                        "code": row["orgao_codigo"],
                        "version": row["orgao_versao"],
                    }
                if prepared is None:
                    prepared = prepare_crosswalk(self.dimension_crosswalk)
                check = prepared.validate(
                    [{key: dimensions[key] for key in ("territory", "unit", "fiscal_year")}]
                )[0]
                fact["code_validation_status"] = check["status"]
                fact["code_validation_reason"] = check["reason"]
                dimension_by_fact[finance_id] = dimensions
        for fact in self.finances:
            dimensions = dimension_by_fact.get(fact["finance_id"], {})
            body = dimensions.get("public_body")
            if body is None:
                body_check = {"status": "pending", "reason": "public_body_metadata_missing"}
            else:
                assert prepared is not None
                body_check = prepared.validate([{"public_body": body}])[0]
            fact["territory_unit_validation_status"] = fact["code_validation_status"]
            fact["territory_unit_validation_reason"] = fact["code_validation_reason"]
            if body_check["status"] != "matched_local":
                fact["code_validation_status"] = "pending"
                fact["code_validation_reason"] = "public_body:" + body_check["reason"]
            fact["public_body_validation_status"] = body_check["status"]
            fact["public_body_validation_reason"] = body_check["reason"]

        self.dimension_observations = [
            {"finance_id": key, "dimensions": dimension_by_fact[key]}
            for key in sorted(dimension_by_fact)
        ]
        if len(self.dimension_observations) < len(self.finances):
            logger.warning(
                "SICONFI dimensions pending for %d facts",
                len(self.finances) - len(self.dimension_observations),
            )
        logger.info("Transformed %d finance records", len(self.finances))

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.finances:
            loader.load_nodes("MunicipalFinance", self.finances, key_field="finance_id")

        if self.dimension_observations:
            project_siconfi(self.driver, self.neo4j_database, self.dimension_observations)
        elif self.finances:
            logger.warning("SICONFI dimensions pending: explicit vocabulary metadata unavailable")
