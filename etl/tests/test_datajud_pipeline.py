from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from bracc_etl.pipelines.datajud import DatajudPipeline

FIXTURES = Path(__file__).parent / "fixtures"


def _make_pipeline() -> DatajudPipeline:
    return DatajudPipeline(driver=MagicMock(), data_dir=str(FIXTURES))


class TestDatajudMetadata:
    def test_name(self) -> None:
        assert DatajudPipeline.name == "datajud"

    def test_source_id(self) -> None:
        assert DatajudPipeline.source_id == "datajud"


class TestDatajudTransform:
    def test_transform_counts(self) -> None:
        pipeline = _make_pipeline()
        pipeline.extract()
        pipeline.transform()

        assert len(pipeline.cases) == 2
        assert len(pipeline.persons) == 1
        assert len(pipeline.companies) == 2

    def test_party_relationships(self) -> None:
        pipeline = _make_pipeline()
        pipeline.extract()
        pipeline.transform()

        assert len(pipeline.person_case_rels) == 1
        assert len(pipeline.company_case_rels) == 2


class TestDatajudLoad:
    def test_load_no_raise(self) -> None:
        pipeline = _make_pipeline()
        pipeline.extract()
        pipeline.transform()
        pipeline.load()


def test_party_cnpj_preserves_letters_and_never_becomes_cpf() -> None:
    import pandas as pd

    pipeline = _make_pipeline()
    pipeline._raw_parties = pd.DataFrame([
        {"judicial_case_id": "case-1", "party_name": "Example",
         "party_cpf": "ABC12345678901", "party_cnpj": "00ABC123000135"},
        {"judicial_case_id": "case-2", "party_name": "Invalid",
         "party_cpf": "ABC12345678901", "party_cnpj": "00ABC1230001!5"},
    ])
    pipeline._transform_parties()
    assert pipeline.persons == []
    assert pipeline.companies == [{"cnpj": "00.ABC.123/0001-35", "razao_social": "EXAMPLE"}]
    assert pipeline.company_case_rels[0]["source_key"] == "00.ABC.123/0001-35"
