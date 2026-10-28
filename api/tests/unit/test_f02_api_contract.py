from unittest.mock import AsyncMock, patch

import pytest

from bracc.config import settings
from bracc.dependencies import get_intelligence_provider
from bracc.main import app
from bracc.services import intelligence_provider


class Node(dict):
    labels = {"Company"}
    element_id = "4:company:1"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "raw,formatted",
    [
        ("00123456000199", "00.123.456/0001-99"),
        ("00ABC123000135", "00.ABC.123/0001-35"),
        ("ABC12345678901", "AB.C12.345/6789-01"),
    ],
)
async def test_company_api_contract(client, monkeypatch, raw, formatted):
    monkeypatch.setattr(settings, "patterns_enabled", True)
    monkeypatch.setattr(settings, "public_mode", False)
    app.dependency_overrides[get_intelligence_provider] = lambda: (
        intelligence_provider.CommunityIntelligenceProvider()
    )
    node = Node(cnpj=raw, razao_social="Example")
    try:
        with (
            patch(
                "bracc.routers.search.execute_query",
                new_callable=AsyncMock,
                return_value=[
                    {
                        "node": node,
                        "node_labels": ["Company"],
                        "node_id": node.element_id,
                        "score": 1.0,
                        "document_id": raw,
                    }
                ],
            ),
            patch(
                "bracc.routers.search.execute_query_single",
                new_callable=AsyncMock,
                return_value={"total": 1},
            ),
        ):
            search = await client.get("/api/v1/search", params={"q": raw})
        assert search.status_code == 200
        result = search.json()["results"][0]
        assert result["id"] == node.element_id and result["document"] == raw
        result_id = result["id"]

        with patch(
            "bracc.routers.entity.execute_query",
            new_callable=AsyncMock,
            return_value=[{
                "e": node,
                "entity_labels": ["Company"],
                "entity_id": node.element_id,
            }],
        ) as lookup:
            entity = await client.get(f"/api/v1/entity/{raw}")
        assert entity.status_code == 200
        assert entity.json()["id"] == result_id
        assert entity.json()["properties"]["cnpj"] == raw
        assert lookup.await_args.args[2] == {"identifier": raw, "identifier_formatted": formatted}

        with patch(
            "bracc.routers.entity.execute_query",
            new_callable=AsyncMock,
            return_value=[{
                "e": node,
                "entity_labels": ["Company"],
                "entity_id": node.element_id,
            }],
        ) as by_id:
            entity_by_id = await client.get(f"/api/v1/entity/by-element-id/{result_id}")
        assert entity_by_id.status_code == 200
        assert entity_by_id.json()["properties"]["cnpj"] == raw
        assert by_id.await_args.args[2] == {"element_id": result_id}

        with (
            patch.object(
                intelligence_provider,
                "execute_query_single",
                new_callable=AsyncMock,
                return_value={
                    "e": node,
                    "entity_labels": ["Company"],
                },
            ),
            patch.object(
                intelligence_provider,
                "execute_query",
                new_callable=AsyncMock,
                return_value=[
                    {
                        "evidence_refs": ["contract:1"],
                        "company_name": "Example",
                    }
                ],
            ) as analysis_query,
        ):
            analysis = await client.get(f"/api/v1/patterns/{result_id}/debtor_contracts")
        assert analysis.status_code == 200 and analysis.json()["total"] == 1
        assert analysis_query.await_args.args[2]["company_identifier"] == raw
        assert analysis_query.await_args.args[2]["company_identifier_formatted"] == formatted

        with patch(
            "bracc.routers.graph.execute_query",
            new_callable=AsyncMock,
            side_effect=[
                [{"degree": 0}],
                [{"nodes": [node], "relationships": [], "center_id": node.element_id}],
            ],
        ):
            graph = await client.get(f"/api/v1/graph/{result_id}")
        assert graph.status_code == 200
        assert graph.json()["nodes"][0]["document_id"] == raw
    finally:
        app.dependency_overrides.pop(get_intelligence_provider, None)
