import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_graph_rejects_invalid_depth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/graph/test-id?depth=5")
    assert response.status_code == 422


@pytest.mark.anyio
async def test_graph_accepts_valid_depth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/graph/test-id?depth=2")
    assert response.status_code != 422


@pytest.mark.anyio
async def test_graph_accepts_entity_types_filter(client: AsyncClient) -> None:
    response = await client.get("/api/v1/graph/test-id?entity_types=person,company")
    assert response.status_code != 422


@pytest.mark.anyio
async def test_graph_uses_canonical_ids_for_nodes_and_edges(client: AsyncClient) -> None:
    from unittest.mock import AsyncMock, patch

    class Node(dict):
        def __init__(self, element_id, **props):
            super().__init__(props)
            self.element_id = element_id
            self.labels = {"Company"}

    class Relationship(dict):
        def __init__(self, start, end):
            super().__init__()
            self.element_id = "rel-1"
            self.start_node = start
            self.end_node = end
            self.type = "SOCIO_DE"

    first = Node(
        "legacy-1",
        entity_id="canonical-1",
        name="A",
        identity_snapshot="private",
        identity_legacy_id="legacy",
    )
    second = Node("legacy-2", name="B")
    record = {
        "nodes": [first, second],
        "relationships": [Relationship(first, second)],
        "center_id": "canonical-1",
    }
    with patch(
        "bracc.routers.graph.execute_query",
        new_callable=AsyncMock,
        side_effect=[[{"degree": 1}], [record]],
    ):
        response = await client.get("/api/v1/graph/canonical-1")
    assert response.status_code == 200
    body = response.json()
    assert body["center_id"] == "canonical-1"
    assert {node["id"] for node in body["nodes"]} == {"canonical-1", "legacy-2"}
    assert body["edges"][0]["source"] == "canonical-1"
    assert body["edges"][0]["target"] == "legacy-2"
    assert all(
        not any(k.startswith("identity_") for k in node["properties"]) for node in body["nodes"]
    )
