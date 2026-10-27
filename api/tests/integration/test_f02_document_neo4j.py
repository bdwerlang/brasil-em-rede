"""F02 against an explicitly supplied disposable Neo4j, without project seeds."""
import os

import pytest
from httpx import ASGITransport, AsyncClient
from neo4j import AsyncGraphDatabase

from bracc.config import settings
from bracc.dependencies import get_intelligence_provider
from bracc.main import app
from bracc.services.intelligence_provider import CommunityIntelligenceProvider


@pytest.mark.integration
@pytest.mark.anyio
@pytest.mark.parametrize("stored", ["00ABC123000135", "00.ABC.123/0001-35"])
async def test_alphanumeric_documents_on_disposable_neo4j(monkeypatch, stored: str) -> None:
    uri = os.environ["F02_NEO4J_URI"]
    driver = AsyncGraphDatabase.driver(uri, auth=None)
    monkeypatch.setattr(settings, "patterns_enabled", True)
    monkeypatch.setattr(settings, "public_mode", False)
    app.state.neo4j_driver = driver
    app.dependency_overrides[get_intelligence_provider] = lambda: CommunityIntelligenceProvider()
    try:
        async with driver.session() as session:
            # Each invocation owns a fresh synthetic Company and its synthetic evidence.
            result = await session.run(
                "CREATE (c:Company {cnpj: $cnpj, razao_social: 'Fixture', f02_fixture: true}) "
                "CREATE (d:Finance {type:'divida_ativa', finance_id:'fixture-debt', "
                "value:1.0, f02_fixture:true}) "
                "CREATE (t:Contract {contract_id:'fixture-contract', value:2.0, f02_fixture:true}) "
                "CREATE (c)-[:DEVE]->(d), (c)-[:VENCEU]->(t) RETURN elementId(c) AS id",
                cnpj=stored,
            )
            entity_id = (await result.single())["id"]
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            search = await client.get("/api/v1/search", params={"q": "00abc123000135"})
            assert search.status_code == 200
            assert search.json()["results"][0]["document"] == stored
            assert search.json()["total"] == 1
            entity = await client.get("/api/v1/entity/00ABC123000135")
            assert entity.status_code == 200
            assert entity.json()["id"] == entity_id
            for identifier in ("00ABC123000135", entity_id):
                response = await client.get(f"/api/v1/patterns/{identifier}/debtor_contracts")
                assert response.status_code == 200
                assert response.json()["total"] == 1
                assert response.json()["patterns"][0]["data"]["evidence_count"] == 2
    finally:
        app.dependency_overrides.pop(get_intelligence_provider, None)
        async with driver.session() as session:
            await session.run("MATCH (n) WHERE n.f02_fixture = true DETACH DELETE n")
        await driver.close()
