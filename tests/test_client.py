"""Tests for the async HTTP client."""

from __future__ import annotations

import httpx
import pytest
import respx

from scrapeadlibrary_mcp.client import ScrapeAdLibraryClient
from scrapeadlibrary_mcp.errors import (
    AuthenticationError,
    CursorError,
    InsufficientCreditsError,
    InvalidParameterError,
    NotFoundError,
    RateLimitError,
    ScrapeAdLibraryError,
    UpstreamError,
)

from .conftest import AD, PAGE, ads_body


async def test_search_ads_params_and_headers(
    mock_api: respx.MockRouter, client: ScrapeAdLibraryClient
):
    route = mock_api.get("/v1/ads/search").respond(
        200, json=ads_body([AD]), headers={"X-Credits-Remaining": "42"}
    )
    data = await client.search_ads(
        q="shoes", country="IT", platforms=["facebook", "threads"], languages="it", limit=10
    )
    assert data["data"][0]["id"] == AD["id"]
    assert client.credits_remaining == 42
    request = route.calls.last.request
    assert dict(request.url.params) == {
        "q": "shoes",
        "country": "IT",
        "platforms": "facebook,threads",
        "languages": "it",
        "limit": "10",
    }
    assert request.headers["X-API-Key"] == "sal_test_key"
    assert request.headers["User-Agent"].startswith("ScrapeAdLibrary-MCP/")


async def test_get_ad(mock_api, client):
    route = mock_api.get("/v1/ads/1", params={"country": "DE"}).respond(
        200, json={"data": AD, "credits_used": 2, "cached": False}
    )
    await client.get_ad("1", country="DE")
    assert route.called


async def test_page_endpoints(mock_api, client):
    mock_api.get("/v1/pages/9").respond(200, json={"data": PAGE, "credits_used": 1})
    ads_route = mock_api.get("/v1/pages/9/ads").respond(200, json=ads_body([AD]))
    search_route = mock_api.get("/v1/pages/search").respond(
        200, json={"data": [], "credits_used": 0}
    )
    assert (await client.get_page("9"))["data"]["name"] == "Nike"
    await client.get_page_ads("9", status="all", cursor="c_1")
    await client.search_pages("nike", limit=5)
    assert dict(ads_route.calls.last.request.url.params) == {"status": "all", "cursor": "c_1"}
    assert dict(search_route.calls.last.request.url.params) == {"q": "nike", "limit": "5"}


@pytest.mark.parametrize(
    ("status", "code", "exc_class"),
    [
        (400, "invalid_parameter", InvalidParameterError),
        (400, "cursor_mismatch", CursorError),
        (401, "invalid_api_key", AuthenticationError),
        (402, "insufficient_credits", InsufficientCreditsError),
        (404, "ad_not_found", NotFoundError),
        (404, "page_not_found", NotFoundError),
        (410, "cursor_expired", CursorError),
        (429, "rate_limit_exceeded", RateLimitError),
        (429, "insufficient_credits_retry_later", RateLimitError),
        (502, "upstream_schema_changed", UpstreamError),
        (503, "upstream_unavailable", UpstreamError),
        (504, "upstream_timeout", UpstreamError),
    ],
)
async def test_error_mapping(mock_api, status, code, exc_class):
    client = ScrapeAdLibraryClient(
        api_key="sal_x", base_url="https://api.scrapeadlibrary.com", max_retries=0
    )
    mock_api.get("/v1/pages/1").respond(status, json={"error": code, "message": "nope"})
    with pytest.raises(exc_class) as exc_info:
        await client.get_page("1")
    assert exc_info.value.code == code
    assert exc_info.value.status_code == status


async def test_retry_after_from_header_and_body(mock_api):
    client = ScrapeAdLibraryClient(
        api_key="sal_x", base_url="https://api.scrapeadlibrary.com", max_retries=0
    )
    mock_api.get("/v1/pages/1").respond(
        429, json={"error": "rate_limit_exceeded", "message": "slow"}, headers={"Retry-After": "5"}
    )
    mock_api.get("/v1/pages/2").respond(
        429, json={"error": "insufficient_credits_retry_later", "message": "wait", "retry_after": 9}
    )
    with pytest.raises(RateLimitError) as e1:
        await client.get_page("1")
    with pytest.raises(RateLimitError) as e2:
        await client.get_page("2")
    assert e1.value.retry_after == 5.0
    assert e2.value.retry_after == 9.0


async def test_retries_temporary_errors(mock_api, client):
    route = mock_api.get("/v1/pages/1")
    route.side_effect = [
        httpx.Response(503, json={"error": "upstream_unavailable", "message": "down"}),
        httpx.Response(200, json={"data": PAGE, "credits_used": 1}),
    ]
    assert (await client.get_page("1"))["data"]["id"] == PAGE["id"]
    assert route.call_count == 2


async def test_does_not_retry_permanent_errors(mock_api, client):
    route = mock_api.get("/v1/pages/1").respond(
        502, json={"error": "upstream_schema_changed", "message": "schema"}
    )
    with pytest.raises(UpstreamError):
        await client.get_page("1")
    assert route.call_count == 1


async def test_network_error(mock_api, client):
    mock_api.get("/v1/pages/1").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(ScrapeAdLibraryError, match="Could not reach"):
        await client.get_page("1")


async def test_non_json_error(mock_api, client):
    mock_api.get("/v1/pages/1").respond(418, text="teapot")
    with pytest.raises(ScrapeAdLibraryError, match="teapot"):
        await client.get_page("1")
