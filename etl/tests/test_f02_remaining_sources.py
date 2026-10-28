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


def test_siconfi_preserves_observed_cnpj_without_company_link() -> None:
    pipeline = SiconfiPipeline(driver=make_driver(), data_dir=str(FIXTURES))
    pipeline.extract()
    pipeline._raw[0]["cnpj"] = RAW
    pipeline.transform()
    assert pipeline.finances[0]["observed_cnpj"] == FORMATTED
    assert not hasattr(pipeline, "municipality_rels")


def test_siconfi_reconciles_observed_cnpj_and_rejects_conflicts() -> None:
    pipeline = SiconfiPipeline(driver=make_driver(), data_dir=str(FIXTURES))
    pipeline.extract()
    without_cnpj = pipeline._raw[0].copy()
    without_cnpj.pop("cnpj", None)
    row = without_cnpj.copy()
    row["cnpj"] = RAW
    for records in ([without_cnpj, row], [row, without_cnpj]):
        pipeline._raw = records
        pipeline.transform()
        assert pipeline.finances[0]["observed_cnpj"] == FORMATTED
    conflicting = row.copy()
    conflicting["cnpj"] = "11ABC123000135"
    pipeline._raw = [row, conflicting]
    with pytest.raises(ValueError, match="conflicting observed CNPJ"):
        pipeline.transform()


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


@pytest.mark.parametrize(
    "document,expected",
    [
        ("00ABC123000135", "00.ABC.123/0001-35"),
        ("00.ABC.123/0001-35", "00.ABC.123/0001-35"),
        ("00123456000199", "00.123.456/0001-99"),
        ("00ABC1230001!5", ""),
        ("00ABC1230001AA", ""),
    ],
)
def test_cvm_secondary_documents_are_structural(document, expected) -> None:
    from bracc_etl.pipelines.cvm_funds import CvmFundsPipeline

    pipeline = CvmFundsPipeline(driver=make_driver(), data_dir=str(FIXTURES))
    pipeline.extract()
    pipeline._raw = pipeline._raw.iloc[:1].copy()
    pipeline._raw.loc[:, "CNPJ_FUNDO"] = RAW
    pipeline._raw.loc[:, "CNPJ_ADMIN"] = document
    pipeline._raw.loc[:, "CPF_CNPJ_GESTOR"] = document
    pipeline._raw.loc[:, "PF_PJ_GESTOR"] = "PJ"
    pipeline._raw.loc[:, "SIT"] = "EM FUNCIONAMENTO"
    pipeline.transform()
    assert pipeline.funds[0]["administrator_cnpj"] == expected
    assert pipeline.funds[0]["manager_cnpj"] == expected
    assert bool(pipeline.admin_rels) == bool(expected)
    assert bool(pipeline.manager_rels) == bool(expected)
    pipeline._raw.loc[:, "PF_PJ_GESTOR"] = "PF"
    pipeline.transform()
    assert not pipeline.manager_rels


def test_holdings_secondary_and_inep_maintainer() -> None:
    from bracc_etl.pipelines.holdings import HoldingsPipeline

    pipeline = HoldingsPipeline(driver=make_driver(), data_dir=str(FIXTURES))
    pipeline.extract()
    pipeline._raw = pipeline._raw.iloc[:1].copy()
    pipeline._raw.loc[:, "cnpj_empresa"] = RAW
    pipeline._raw.loc[:, "cnpj_socia"] = "00123456000199"
    pipeline.transform()
    assert pipeline.holding_rels == [{"source_key": "00.123.456/0001-99", "target_key": FORMATTED}]
    pipeline._raw.loc[:, "cnpj_socia"] = "00ABC1230001!5"
    pipeline.transform()
    assert not pipeline.holding_rels

    school = InepPipeline(driver=make_driver(), data_dir=str(FIXTURES))
    school.extract()
    school._raw_rows = school._raw_rows[:1]
    school._raw_rows[0]["NU_CNPJ_ESCOLA_PRIVADA"] = RAW
    school._raw_rows[0]["NU_CNPJ_MANTENEDORA"] = "00123456000199"
    school.transform()
    assert {r["source_key"] for r in school.school_company_links} == {
        FORMATTED,
        "00.123.456/0001-99",
    }
    school._raw_rows[0]["NU_CNPJ_MANTENEDORA"] = "00ABC1230001!5"
    school.transform()
    assert [r["source_key"] for r in school.school_company_links] == [FORMATTED]
