"""Tests for CPF masking middleware and helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from bracc.middleware.cpf_masking import (
    _collect_pep_cpfs,
    _is_pep_record,
    mask_cpfs_in_json,
    mask_formatted_cpf,
    mask_raw_cpf,
)

if TYPE_CHECKING:
    from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Unit tests for pure helper functions
# ---------------------------------------------------------------------------


class TestMaskFormattedCPF:
    def test_basic(self) -> None:
        assert mask_formatted_cpf("123.456.789-00") == "***.***.789-00"

    def test_another(self) -> None:
        assert mask_formatted_cpf("000.111.222-33") == "***.***.222-33"


class TestMaskRawCPF:
    def test_basic(self) -> None:
        assert mask_raw_cpf("12345678900") == "*******8900"

    def test_zeros(self) -> None:
        assert mask_raw_cpf("00000000000") == "*******0000"


class TestIsPepRecord:
    def test_explicit_is_pep_true(self) -> None:
        assert _is_pep_record({"name": "Joao", "cpf": "12345678900", "is_pep": True})

    def test_explicit_is_pep_false(self) -> None:
        assert not _is_pep_record({"name": "Joao", "cpf": "12345678900", "is_pep": False})

    @pytest.mark.parametrize(
        "role",
        [
            "deputado",
            "senador",
            "vereador",
            "prefeito",
            "governador",
            "presidente",
            "ministro",
            "Deputada",
            "SENADORA",
            "Ministra",
        ],
    )
    def test_political_role(self, role: str) -> None:
        assert _is_pep_record({"name": "X", "cpf": "11111111111", "role": role})

    def test_cargo_field(self) -> None:
        assert _is_pep_record({"name": "X", "cpf": "11111111111", "cargo": "Deputado"})

    @pytest.mark.parametrize(
        "role",
        [
            "Deputado Federal",
            "deputado federal",
            "DEPUTADO FEDERAL",
            "Senador da Republica",
            "senadora da republica",
            "Vereador Suplente",
            "Ministro de Estado",
            "Governadora do Estado de Sao Paulo",
            "Presidente da Republica",
        ],
    )
    def test_compound_role_detected_as_pep(self, role: str) -> None:
        """Compound PEP roles like 'deputado federal' must be detected via substring match."""
        assert _is_pep_record({"name": "X", "cpf": "11111111111", "role": role})

    def test_compound_cargo_detected_as_pep(self) -> None:
        """Compound PEP cargo like 'Deputado Federal' must be detected via substring match."""
        assert _is_pep_record({"name": "X", "cpf": "11111111111", "cargo": "Deputado Federal"})

    def test_non_pep_role(self) -> None:
        assert not _is_pep_record({"name": "X", "cpf": "11111111111", "role": "assessor"})

    def test_no_role_no_is_pep(self) -> None:
        assert not _is_pep_record({"name": "X", "cpf": "11111111111"})


class TestCollectPepCpfs:
    def test_flat_pep(self) -> None:
        data = {"cpf": "123.456.789-00", "is_pep": True}
        assert _collect_pep_cpfs(data) == {"12345678900"}

    def test_flat_non_pep(self) -> None:
        data = {"cpf": "123.456.789-00", "is_pep": False}
        assert _collect_pep_cpfs(data) == set()

    def test_nested_list(self) -> None:
        data = {
            "results": [
                {"cpf": "11111111111", "role": "deputado"},
                {"cpf": "22222222222", "role": "assessor"},
            ]
        }
        peps = _collect_pep_cpfs(data)
        assert "11111111111" in peps
        assert "22222222222" not in peps

    def test_deeply_nested(self) -> None:
        data = {"a": {"b": {"c": [{"cpf": "33333333333", "is_pep": True}]}}}
        assert "33333333333" in _collect_pep_cpfs(data)

    def test_compound_role_collected(self) -> None:
        """Compound roles like 'Deputado Federal' must be recognized in the walk."""
        data = {
            "results": [
                {"cpf": "11111111111", "role": "Deputado Federal"},
                {"cpf": "22222222222", "role": "assessor parlamentar"},
            ]
        }
        peps = _collect_pep_cpfs(data)
        assert "11111111111" in peps
        assert "22222222222" not in peps


# ---------------------------------------------------------------------------
# Unit tests for mask_cpfs_in_json
# ---------------------------------------------------------------------------


class TestMaskCpfsInJson:
    def test_formatted_cpf_masked(self) -> None:
        text = '{"cpf": "123.456.789-00"}'
        result = mask_cpfs_in_json(text)
        assert "***.***.789-00" in result
        assert "123.456" not in result

    def test_raw_cpf_masked(self) -> None:
        text = '{"cpf": "12345678900"}'
        result = mask_cpfs_in_json(text)
        assert "*******8900" in result
        assert "1234567" not in result

    def test_pep_cpf_not_masked(self) -> None:
        text = '{"cpf": "12345678900"}'
        result = mask_cpfs_in_json(text, pep_cpfs={"12345678900"})
        assert "12345678900" in result

    def test_pep_formatted_cpf_not_masked(self) -> None:
        text = '{"cpf": "123.456.789-00"}'
        result = mask_cpfs_in_json(text, pep_cpfs={"12345678900"})
        assert "123.456.789-00" in result

    def test_cnpj_not_masked(self) -> None:
        """CNPJ has 14 digits and must never be masked."""
        text = '{"cnpj": "12.345.678/0001-90"}'
        result = mask_cpfs_in_json(text)
        assert "12.345.678/0001-90" in result

    def test_raw_cnpj_not_masked(self) -> None:
        """Raw 14-digit CNPJ must not be matched by the 11-digit CPF regex."""
        text = '{"cnpj": "12345678000190"}'
        result = mask_cpfs_in_json(text)
        assert "12345678000190" in result

    def test_multiple_cpfs(self) -> None:
        text = json.dumps({
            "people": [
                {"name": "A", "cpf": "111.222.333-44"},
                {"name": "B", "cpf": "555.666.777-88"},
            ]
        })
        result = mask_cpfs_in_json(text)
        assert "***.***.333-44" in result
        assert "***.***.777-88" in result

    def test_mixed_pep_and_non_pep(self) -> None:
        text = json.dumps({
            "people": [
                {"name": "A", "cpf": "111.222.333-44"},
                {"name": "B", "cpf": "555.666.777-88"},
            ]
        })
        result = mask_cpfs_in_json(text, pep_cpfs={"11122233344"})
        assert "111.222.333-44" in result  # PEP: not masked
        assert "***.***.777-88" in result  # Non-PEP: masked

    def test_empty_string(self) -> None:
        assert mask_cpfs_in_json("") == ""

    def test_no_cpfs(self) -> None:
        text = '{"name": "hello"}'
        assert mask_cpfs_in_json(text) == text

    def test_null_cpf_value(self) -> None:
        text = '{"cpf": null}'
        assert mask_cpfs_in_json(text) == text

    def test_cpf_in_nested_json(self) -> None:
        text = json.dumps({
            "entity": {
                "details": {
                    "personal": {"cpf": "987.654.321-00"}
                }
            }
        })
        result = mask_cpfs_in_json(text)
        assert "***.***.321-00" in result

    def test_short_digit_sequence_not_masked(self) -> None:
        """A 6-digit number should NOT be treated as CPF."""
        text = '{"partial": "123456"}'
        result = mask_cpfs_in_json(text)
        assert "123456" in result

    def test_non_json_text_passthrough(self) -> None:
        text = "This is plain text with no CPFs."
        assert mask_cpfs_in_json(text) == text


# ---------------------------------------------------------------------------
# Integration tests via the ASGI app
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_health_not_masked(client: AsyncClient) -> None:
    """Non-CPF JSON responses pass through unchanged."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_alphanumeric_cnpj_does_not_get_cpf_masked() -> None:
    text = '{"cnpj":"ABC12345678901","cpf":"12345678901"}'
    result = mask_cpfs_in_json(text)
    assert '"cnpj":"ABC12345678901"' in result
    assert '"cpf":"*******8901"' in result


@pytest.mark.parametrize("text,expected", [
    ("X12345678901", "X*******8901"),
    ("12345678901X", "*******8901X"),
    ("prefix12345678901suffix", "prefix*******8901suffix"),
    ("ABC12345678901", "ABC*******8901"),
    ("00123456789012", "00123456789012"),
])
def test_cpf_adjacent_to_letters_and_complete_cnpj(text: str, expected: str) -> None:
    assert mask_cpfs_in_json(text) == expected


def test_pep_cpf_adjacent_to_letters_remains_visible() -> None:
    assert mask_cpfs_in_json("X12345678901", {"12345678901"}) == "X12345678901"


def test_structured_cnpj_context_and_nested_lists() -> None:
    data = {"cnpj": "ABC12345678901", "text": "ABC12345678901", "nested": [
        {"company_cnpj": "ABC12345678901", "description": "X12345678901"},
        {"cnpj": ["ABC12345678901", "12345678901"]},
    ]}
    result = json.loads(mask_cpfs_in_json(json.dumps(data)))
    assert result["cnpj"] == "ABC12345678901"
    assert result["text"] == "ABC*******8901"
    assert result["nested"][0] == {
        "company_cnpj": "ABC12345678901", "description": "X*******8901"
    }
    assert result["nested"][1]["cnpj"] == ["ABC12345678901", "*******8901"]


@pytest.mark.anyio
async def test_asgi_masks_ambiguous_text_and_sets_content_length() -> None:
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from bracc.middleware.cpf_masking import CPFMaskingMiddleware

    app = FastAPI()
    app.add_middleware(CPFMaskingMiddleware)

    @app.get("/sample")
    async def sample() -> dict[str, object]:
        return {"cnpj": "ABC12345678901", "text": "ABC12345678901",
                "pep": {"cpf": "12345678901", "is_pep": True}}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/sample")
    assert response.json()["cnpj"] == "ABC12345678901"
    # The same CPF is explicitly marked PEP in this response.
    assert response.json()["pep"]["cpf"] == "12345678901"
    assert int(response.headers["content-length"]) == len(response.content)


@pytest.mark.anyio
async def test_asgi_masks_non_pep_text() -> None:
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from bracc.middleware.cpf_masking import CPFMaskingMiddleware

    app = FastAPI()
    app.add_middleware(CPFMaskingMiddleware)

    @app.get("/sample")
    async def sample() -> dict[str, str]:
        return {"cnpj": "ABC12345678901", "text": "ABC12345678901"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/sample")
    assert response.json() == {"cnpj": "ABC12345678901", "text": "ABC*******8901"}
    assert int(response.headers["content-length"]) == len(response.content)
