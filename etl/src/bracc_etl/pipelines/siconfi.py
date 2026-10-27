from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from bracc_etl.base import Pipeline
from bracc_etl.dimensions.projection import project_siconfi

if TYPE_CHECKING:
    from neo4j import Driver
from bracc_etl.loader import Neo4jBatchLoader
from bracc_etl.transforms import (
    deduplicate_rows,
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
        **kwargs: Any,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size, **kwargs)
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
        dimension_observations: list[dict[str, Any]] = []
        dimension_by_fact: dict[str, dict[str, Any]] = {}

        for row in self._raw:
            cod_ibge = str(row.get("cod_ibge", "")).strip()
            if not cod_ibge:
                continue

            # CSV uses "instituicao", API JSON uses "ente"
            ente = normalize_name(str(row.get("instituicao", "") or row.get("ente", "")))
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

            finances.append(
                {
                    "finance_id": finance_id,
                    "cod_ibge": cod_ibge,
                    "municipality": ente,
                    "year": exercicio,
                    "account": conta,
                    "column": coluna,
                    "amount": amount,
                    "source": "siconfi",
                    "dimension_status": "pending",
                    "dimension_reason": "projection_not_completed",
                }
            )

            required = (
                "cod_ibge",
                "exercicio",
                "uf",
                "versao_territorial",
                "tipo_territorio",
                "unidade_sistema",
                "unidade_codigo",
            )
            missing = [
                field for field in required if not isinstance(row.get(field), str) or not row[field]
            ]
            if missing:
                finances[-1]["dimension_reason"] = "missing_metadata:" + ",".join(missing)
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
                if finance_id in dimension_by_fact and dimension_by_fact[finance_id] != dimensions:
                    raise ValueError("conflicting dimensions for same finance_id")
                if finance_id not in dimension_by_fact:
                    dimension_by_fact[finance_id] = dimensions
                    dimension_observations.append(
                        {"finance_id": finance_id, "dimensions": dimensions}
                    )

        self.finances = deduplicate_rows(finances, ["finance_id"])
        self.dimension_observations = dimension_observations
        if len(dimension_observations) < len(self.finances):
            logger.warning(
                "SICONFI dimensions pending for %d facts",
                len(self.finances) - len(dimension_observations),
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
