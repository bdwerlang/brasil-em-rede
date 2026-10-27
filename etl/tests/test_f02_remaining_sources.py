"""Regression fixtures for CNPJ handling in previously untested source paths."""
from pathlib import Path

import pytest

from bracc_etl.pipelines.datajud import DatajudPipeline
from bracc_etl.pipelines.inep import InepPipeline
from bracc_etl.pipelines.mides import MidesPipeline
from bracc_etl.pipelines.pgfn import PgfnPipeline
from bracc_etl.pipelines.renuncias import RenunciasPipeline
from bracc_etl.pipelines.siconfi import SiconfiPipeline
from tests.neo4j_mocks import make_driver

FIXTURES = Path(__file__).parent / "fixtures"
RAW = "00ABC123000135"
FORMATTED = "00.ABC.123/0001-35"


@pytest.mark.parametrize("pipeline_class,attribute,column,output", [
    (RenunciasPipeline, "_raw", "CNPJ", "company_rels"),
    (MidesPipeline, "_raw_bids", "cnpj_fornecedor", "bid_company_rels"),
    (DatajudPipeline, "_raw_parties", "party_cnpj", "company_case_rels"),
])
def test_dataframe_sources_preserve_cnpj(pipeline_class, attribute, column, output) -> None:
    pipeline = pipeline_class(driver=make_driver(), data_dir=str(FIXTURES))
    pipeline.extract()
    frame = getattr(pipeline, attribute)
    assert not frame.empty
    frame.loc[frame.index[0], column] = RAW
    if pipeline_class is DatajudPipeline:
        frame.loc[frame.index[0], "party_cpf"] = ""
    pipeline.transform()
    assert FORMATTED in repr(getattr(pipeline, output))


def test_siconfi_preserves_alphanumeric_company() -> None:
    pipeline = SiconfiPipeline(driver=make_driver(), data_dir=str(FIXTURES))
    pipeline.extract()
    pipeline._raw[0]["cnpj"] = RAW
    pipeline.transform()
    assert FORMATTED in repr(pipeline.municipality_rels)


def test_inep_preserves_alphanumeric_company() -> None:
    pipeline = InepPipeline(driver=make_driver(), data_dir=str(FIXTURES))
    pipeline.extract()
    pipeline._raw_rows[0]["NU_CNPJ_ESCOLA_PRIVADA"] = RAW
    pipeline.transform()
    assert FORMATTED in repr(pipeline.school_company_links)


def test_pgfn_preserves_alphanumeric_company(tmp_path: Path) -> None:
    directory = tmp_path / "pgfn"
    directory.mkdir()
    source = next((FIXTURES / "pgfn").glob("*.csv"))
    data = source.read_text(encoding="latin-1").replace("11222333000181", RAW)
    (directory / source.name).write_text(data, encoding="latin-1")
    pipeline = PgfnPipeline(driver=make_driver(), data_dir=str(tmp_path))
    pipeline.extract()
    pipeline.transform()
    assert FORMATTED in repr(pipeline.relationships)
