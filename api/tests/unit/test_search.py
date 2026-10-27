import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_search_rejects_short_query(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search?q=a")
    assert response.status_code == 422


@pytest.mark.anyio
async def test_search_rejects_missing_query(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search")
    assert response.status_code == 422


@pytest.mark.anyio
async def test_search_rejects_invalid_page(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search?q=test&page=0")
    assert response.status_code == 422


@pytest.mark.anyio
async def test_search_rejects_oversized_page(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search?q=test&size=200")
    assert response.status_code == 422


@pytest.mark.anyio
async def test_search_alphanumeric_cnpj_uses_exact_forms(client: AsyncClient) -> None:
    from unittest.mock import AsyncMock, patch

    with (
        patch(
            "bracc.routers.search.execute_query",
            new_callable=AsyncMock,
            return_value=[
                {
            "node": {"cnpj": "00.ABC.123/0001-35", "razao_social": "Example"},
                    "node_labels": ["Company"],
                    "node_id": "4:company:1",
                    "score": 1.0,
            "document_id": "00.ABC.123/0001-35",
                }
            ],
        ) as query,
        patch(
            "bracc.routers.search.execute_query_single",
            new_callable=AsyncMock,
            return_value={"total": 1},
        ),
    ):
        response = await client.get("/api/v1/search", params={"q": "00abc123000135"})
    assert response.status_code == 200
    assert response.json()["results"][0]["document"] == "00.ABC.123/0001-35"
    assert query.await_args.args[1] == "search_cnpj"
    assert query.await_args.args[2]["identifier"] == "00ABC123000135"
    assert query.await_args.args[2]["identifier_formatted"] == "00.ABC.123/0001-35"


@pytest.mark.anyio
async def test_search_hides_identity_metadata(client: AsyncClient) -> None:
    from unittest.mock import AsyncMock, patch

    row = {
        "node": {
            "name": "Example",
            "identity_snapshot": "private",
            "identity_legacy_id": "legacy",
            "identity_migration": "created",
        },
        "node_labels": ["Company"],
        "node_id": "canonical",
        "score": 1.0,
        "document_id": None,
    }
    with (
        patch("bracc.routers.search.execute_query", new_callable=AsyncMock, return_value=[row]),
        patch(
            "bracc.routers.search.execute_query_single",
            new_callable=AsyncMock,
            return_value={"total": 1},
        ),
    ):
        response = await client.get("/api/v1/search?q=example")
    assert response.status_code == 200
    assert not any(k.startswith("identity_") for k in response.json()["results"][0]["properties"])
