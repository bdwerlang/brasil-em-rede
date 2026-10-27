import pandas as pd
import pytest

from bracc_etl.pipelines.camara_inquiries import _extract_cnpjs as camara_extract
from bracc_etl.pipelines.dou import _extract_cnpjs as dou_extract
from bracc_etl.pipelines.querido_diario import _extract_cnpjs_with_spans
from bracc_etl.pipelines.senado_cpis import _extract_cnpjs as senado_extract
from bracc_etl.schemas.dou import company_rels_schema
from bracc_etl.schemas.pgfn import deve_relationship_schema
from bracc_etl.schemas.transparencia import contracts_schema
from bracc_etl.schemas.tse import donations_schema


@pytest.mark.parametrize("extract", [camara_extract, dou_extract, senado_extract])
def test_text_extractors_preserve_cnpj(extract) -> None:
    assert extract("Empresa 00.ABC.123/0001-35") == ["00.ABC.123/0001-35"]
    assert extract("Empresa 00ABC123000135") == ["00.ABC.123/0001-35"]


def test_gazette_extractor_preserves_cnpj() -> None:
    assert _extract_cnpjs_with_spans("Empresa 00.ABC.123/0001-35")[0][0] == "00.ABC.123/0001-35"


@pytest.mark.parametrize("schema,column", [
    (company_rels_schema, "source_key"),
    (deve_relationship_schema, "source_key"),
    (contracts_schema, "cnpj"),
    (donations_schema, "donor_doc"),
])
@pytest.mark.parametrize("document", ["00.ABC.123/0001-35", "00ABC123000135", "11222333000181"])
def test_document_schema_accepts_cnpj(schema, column, document) -> None:
    schema.select_columns([column]).validate(pd.DataFrame({column: [document]}))


def test_sanctions_keeps_partial_cpf_as_observation_only() -> None:
    from unittest.mock import MagicMock

    from bracc_etl.pipelines.sanctions import SanctionsPipeline

    pipeline = SanctionsPipeline(driver=MagicMock(), data_dir=".")
    rows = pd.DataFrame([{
        "cpf_cnpj": "***.123.456-**", "nome": "Pessoa", "data_inicio": "",
        "data_fim": "", "motivo": "",
    }])
    sanctions, entities = pipeline._process_rows(rows, "CEIS")
    assert len(sanctions) == 1
    assert entities == []


@pytest.mark.parametrize("module,class_name,column", [
    ("bcb", "BcbPipeline", "CNPJ"),
    ("bndes", "BndesPipeline", "cnpj"),
    ("cepim", "CepimPipeline", "CNPJ ENTIDADE"),
    ("cvm_funds", "CvmFundsPipeline", "CNPJ_FUNDO"),
    ("datasus", "DatasusPipeline", "numero_cnpj_entidade"),
    ("ibama", "IbamaPipeline", "CPF_CNPJ_EMBARGADO"),
    ("leniency", "LeniencyPipeline", "cnpj"),
    ("camara", "CamaraPipeline", "txtCNPJCPF"),
    ("senado", "SenadoPipeline", "CNPJ_CPF"),
])
def test_source_pipeline_preserves_alphanumeric_document(module, class_name, column) -> None:
    from importlib import import_module
    from pathlib import Path
    from unittest.mock import MagicMock

    pipeline_class = getattr(import_module(f"bracc_etl.pipelines.{module}"), class_name)
    pipeline = pipeline_class(driver=MagicMock(), data_dir=str(Path(__file__).parent / "fixtures"))
    if module in {"camara", "senado"}:
        fixture = "camara_ceap.csv" if module == "camara" else "senado_ceaps.csv"
        pipeline._raw = pd.read_csv(
            Path(__file__).parent / "fixtures" / fixture, sep=";", dtype=str,
            encoding="latin-1", keep_default_na=False, skiprows=1 if module == "senado" else 0,
        )
    else:
        pipeline.extract()
    assert not pipeline._raw.empty
    pipeline._raw.loc[pipeline._raw.index[0], column] = "00ABC123000135"
    pipeline.transform()
    outputs = [value for value in vars(pipeline).values() if isinstance(value, list)]
    assert "00.ABC.123/0001-35" in repr(outputs)


@pytest.mark.parametrize("module,class_name,attribute,column", [
    ("holdings", "HoldingsPipeline", "_raw", "cnpj_empresa"),
    ("transferegov", "TransferegovPipeline", "_raw_favorecidos", "Código do Favorecido"),
    ("transparencia", "TransparenciaPipeline", "_raw_contratos", "cnpj_contratada"),
    ("tse", "TSEPipeline", "_raw_doacoes", "cpf_cnpj_doador"),
    ("tcu", "TcuPipeline", "_raw_inidoneos", "CPF_CNPJ"),
])
def test_additional_source_pipeline_alphanumeric(module, class_name, attribute, column) -> None:
    from importlib import import_module
    from pathlib import Path
    from unittest.mock import MagicMock

    pipeline_class = getattr(import_module(f"bracc_etl.pipelines.{module}"), class_name)
    pipeline = pipeline_class(driver=MagicMock(), data_dir=str(Path(__file__).parent / "fixtures"))
    fixture_dir = Path(__file__).parent / "fixtures"
    if module == "transparencia":
        for part in ("contratos", "servidores", "emendas"):
            setattr(pipeline, f"_raw_{part}", pd.read_csv(
                fixture_dir / f"transparencia_{part}.csv", dtype=str, keep_default_na=False
            ))
    elif module == "tse":
        for part in ("candidatos", "doacoes"):
            setattr(pipeline, f"_raw_{part}", pd.read_csv(
                fixture_dir / f"tse_{part}.csv", encoding="latin-1", dtype=str
            ))
    else:
        pipeline.extract()
    frame = getattr(pipeline, attribute)
    assert not frame.empty
    frame.loc[frame.index[0], column] = "00ABC123000135"
    pipeline.transform()
    outputs = [value for value in vars(pipeline).values() if isinstance(value, list)]
    assert "00.ABC.123/0001-35" in repr(outputs)


def test_opensanctions_does_not_interpret_cnpj_as_cpf() -> None:
    from bracc_etl.pipelines.opensanctions import _extract_cpf

    assert _extract_cpf({"properties": {"taxNumber": ["ABC12345678901"]}}) is None
    assert _extract_cpf({"properties": {"taxNumber": ["00123456789"]}}) == "001.234.567-89"


def test_format_cnpj_does_not_format_invalid_characters() -> None:
    from bracc_etl.transforms import format_cnpj

    assert format_cnpj("00ABC1230001!5") == "00ABC1230001!5"


def test_siop_cnpj_does_not_create_person() -> None:
    from pathlib import Path
    from unittest.mock import MagicMock

    from bracc_etl.pipelines.siop import SiopPipeline

    pipeline = SiopPipeline(driver=MagicMock(), data_dir=".")
    pipeline._raw = pd.read_csv(
        Path(__file__).parent / "fixtures" / "siop" / "emendas.csv",
        dtype=str, sep=";", keep_default_na=False,
    ).iloc[:1].copy()
    pipeline._raw.loc[:, "CPF/CNPJ AUTOR"] = "ABC12345678901"
    pipeline.transform()
    assert len(pipeline.amendments) == 1
    assert not pipeline.authors
