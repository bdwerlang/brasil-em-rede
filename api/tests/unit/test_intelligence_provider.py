from unittest.mock import AsyncMock, patch

import pytest
from pytest import MonkeyPatch

from bracc.config import settings
from bracc.services import intelligence_provider as provider_module


def test_falls_back_to_community_when_full_modules_missing(
    monkeypatch: MonkeyPatch,
) -> None:
    original_tier = settings.product_tier
    try:
        monkeypatch.setattr(settings, "product_tier", "full")
        monkeypatch.setattr(
            provider_module,
            "_full_modules_available",
            lambda: False,
        )
        provider_module._PROVIDER_CACHE.clear()

        provider = provider_module.get_default_provider()

        assert isinstance(provider, provider_module.CommunityIntelligenceProvider)
    finally:
        provider_module._PROVIDER_CACHE.clear()
        settings.product_tier = original_tier


def test_keeps_full_when_modules_are_available(
    monkeypatch: MonkeyPatch,
) -> None:
    original_tier = settings.product_tier
    try:
        monkeypatch.setattr(settings, "product_tier", "full")
        monkeypatch.setattr(
            provider_module,
            "_full_modules_available",
            lambda: True,
        )
        provider_module._PROVIDER_CACHE.clear()

        provider = provider_module.get_default_provider()

        assert isinstance(provider, provider_module.FullIntelligenceProvider)
    finally:
        provider_module._PROVIDER_CACHE.clear()
        settings.product_tier = original_tier


def test_community_provider_exposes_exactly_8_patterns() -> None:
    provider = provider_module.CommunityIntelligenceProvider()
    pattern_ids = [row["id"] for row in provider.list_patterns()]
    assert len(pattern_ids) == 8
    assert set(pattern_ids) == set(provider_module.COMMUNITY_PATTERN_IDS)


def test_community_patterns_have_query_files() -> None:
    from bracc.services.neo4j_service import CypherLoader

    for query_name in provider_module.COMMUNITY_PATTERN_QUERIES.values():
        try:
            CypherLoader.load(query_name)
        finally:
            CypherLoader.clear_cache()


@pytest.mark.anyio
async def test_community_provider_enforces_public_evidence_fields() -> None:
    provider = provider_module.CommunityIntelligenceProvider()
    fake_session = object()

    with (
        patch(
            "bracc.services.intelligence_provider.execute_query_single",
            new_callable=AsyncMock,
            return_value={
                "entity_labels": ["Company"],
                "e": {"cnpj": "11.111.111/0001-11"},
            },
        ),
        patch(
            "bracc.services.intelligence_provider.execute_query",
            new_callable=AsyncMock,
            return_value=[
                {
                    "pattern_id": "debtor_contracts",
                    "cnpj": "11.111.111/0001-11",
                    "company_name": "Empresa Teste",
                    "amount_total": 1000.0,
                    "window_start": "2024-01-01",
                    "window_end": "2024-12-31",
                    "evidence_refs": ["contract:1", "debt:2"],
                }
            ],
        ),
    ):
        results = await provider.run_pattern(
            fake_session,  # type: ignore[arg-type]
            pattern_id="debtor_contracts",
            entity_id="c1",
            lang="pt",
        )

    assert len(results) == 1
    payload = results[0].data
    assert payload["evidence_refs"]
    assert "risk_signal" in payload


@pytest.mark.anyio
@pytest.mark.parametrize(
    "identifier,by_element",
    [
        ("00abc123000135", None),
        ("4:company:1", {"entity_labels": ["Company"], "e": {"cnpj": "00.ABC.123/0001-35"}}),
    ],
)
async def test_alphanumeric_company_analysis(identifier: str, by_element: object) -> None:
    provider = provider_module.CommunityIntelligenceProvider()
    with (
        patch.object(
            provider_module, "execute_query_single", new_callable=AsyncMock, return_value=by_element
        ),
        patch.object(
            provider_module,
            "execute_query",
            new_callable=AsyncMock,
            return_value=[{"evidence_refs": ["contract:1"], "company_name": "Example"}],
        ) as query,
    ):
        result = await provider.run_pattern(
            object(),
            pattern_id="debtor_contracts",
            entity_id=identifier,  # type: ignore[arg-type]
        )
    assert len(result) == 1
    assert query.await_args.args[2]["company_identifier"] == "00ABC123000135"
    assert query.await_args.args[2]["company_identifier_formatted"] == "00.ABC.123/0001-35"


@pytest.mark.anyio
@pytest.mark.parametrize("identifier", ["00ABC123000135", "4:company:1"])
async def test_alphanumeric_company_patterns_endpoint(client, monkeypatch, identifier: str) -> None:
    from bracc.dependencies import get_intelligence_provider
    from bracc.main import app

    monkeypatch.setattr(settings, "patterns_enabled", True)
    monkeypatch.setattr(settings, "public_mode", False)
    app.dependency_overrides[get_intelligence_provider] = lambda: (
        provider_module.CommunityIntelligenceProvider()
    )
    by_element = (
        {"entity_labels": ["Company"], "e": {"cnpj": "00.ABC.123/0001-35"}}
        if identifier.startswith("4:")
        else None
    )
    try:
        with (
            patch.object(
                provider_module,
                "execute_query_single",
                new_callable=AsyncMock,
                return_value=by_element,
            ),
            patch.object(
                provider_module,
                "execute_query",
                new_callable=AsyncMock,
                return_value=[{"evidence_refs": ["contract:1"], "company_name": "Example"}],
            ) as query,
        ):
            response = await client.get(f"/api/v1/patterns/{identifier}/debtor_contracts")
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert query.await_args.args[2]["company_identifier"] == "00ABC123000135"
    finally:
        app.dependency_overrides.pop(get_intelligence_provider, None)
