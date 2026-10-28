import pandas as pd

from bracc_etl.pipelines.tesouro_emendas import TesouroEmendasPipeline
from tests.neo4j_mocks import make_driver


def test_transfer_beneficiaries_preserve_cnpj_without_inventing_digits() -> None:
    pipeline = TesouroEmendasPipeline(driver=make_driver(), data_dir=".")
    pipeline._raw = pd.DataFrame([
        {"OB": "1", "CNPJ do Favorecido": "00.ABC.123/0001-35", "Nome Favorecido": "A"},
        {"OB": "2", "CNPJ do Favorecido": "001234", "Nome Favorecido": "B"},
        {"OB": "3", "CNPJ do Favorecido": "00ABC1230001!5", "Nome Favorecido": "C"},
        {"OB": "4", "CNPJ do Favorecido": "00123456000112", "Nome Favorecido": "D"},
    ])
    pipeline.transform()
    assert len(pipeline.transfers) == 4
    assert {row["cnpj"] for row in pipeline.companies} == {"00ABC123000135", "00123456000112"}
    assert {row["target_key"] for row in pipeline.transfer_rels} == {
        "00ABC123000135", "00123456000112"
    }
