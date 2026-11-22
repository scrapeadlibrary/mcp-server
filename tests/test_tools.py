"""Tests for MCP tool handlers."""

from __future__ import annotations

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from .conftest import AD, PAGE, ad, ads_body

AD_DETAIL = {
    **AD,
    "advertiser": PAGE,
    "payers": [{"payer": "Company Ltd", "beneficiary": "person:1a2b3c4d"}],
    "transparency": {
        "eu": {
            "reach": 65104,
            "gender": "all",
            "age_min": 21,
            "age_max": 65,
            "locations": [{"name": "Italy", "type": "country", "excluded": False}],
            "breakdown": [
                {"country": "IT", "age_range": "18-24", "male": 31, "female": 1, "unknown": 0}
            ],
        },
        "uk": None,
    },
    "cards": [
        {"title": "Card A", "body": "Body A", "link_url": "https://example.com/a", "image": None}
    ],
    "about": None,
    "removed": False,
}


async def test_search_ads(mock_api, tools):
    route = mock_api.get("/v1/ads/search").respond(
        200,
        json=ads_body([ad("1"), ad("2")], has_more=True, next_cursor="c_next"),
        headers={"X-Credits-Remaining": "1234"},
    )
    result = await tools["search_ads"](query="themes", country="IT", platforms=["instagram"])
    assert "Ad 1 — Perfect themes" in result
    assert "Ad 2" in result
    assert "of ~6,780" in result
    assert "Install now → https://example.com/app" in result
    assert "https://scontent.example/v.mp4" in result
    assert "Variants: 3" in result
    assert "cursor='c_next'" in result
    assert "Credits used: 1 (remaining: 1,234)" in result
    assert "Media URLs expire at 2026-11-25T18:00:00Z" in result
    params = dict(route.calls.last.request.url.params)
    assert params["q"] == "themes"
    assert params["platforms"] == "instagram"
    assert params["limit"] == "10"


async def test_search_ads_political(mock_api, tools):
    political = {
        "spend": {"lower": 7000, "upper": 8000, "currency": "EUR", "text": "€7K - €8K"},
        "impressions": {"text": ">1M"},
        "reach": None,
        "disclaimer": "Paid for by Example",
    }
    mock_api.get("/v1/ads/search").respond(200, json=ads_body([ad(political=political)]))
    result = await tools["search_ads"](query="vote", ad_type="political")
    assert "spend €7K - €8K, impressions >1M" in result
    assert "Paid for by Example" in result


async def test_search_ads_empty(mock_api, tools):
    mock_api.get("/v1/ads/search").respond(200, json=ads_body([]))
    result = await tools["search_ads"](query="zzzz")
    assert "No ads found" in result
    assert "cost 0 credits" in result


async def test_search_ads_requires_query_or_page(tools):
    with pytest.raises(ToolError, match="query or a page_id"):
        await tools["search_ads"]()


async def test_search_ads_error(mock_api, tools):
    mock_api.get("/v1/ads/search").respond(
        402, json={"error": "insufficient_credits", "message": "Insufficient credits"}
    )
    with pytest.raises(ToolError, match="Insufficient credits"):
        await tools["search_ads"](query="x")


async def test_rate_limit_error_mentions_retry(mock_api, client, tools):
    client.max_retries = 0
    mock_api.get("/v1/ads/search").respond(
        429,
        json={"error": "rate_limit_exceeded", "message": "Too many"},
        headers={"Retry-After": "12"},
    )
    with pytest.raises(ToolError, match=r"retry after 12s"):
        await tools["search_ads"](query="x")


async def test_get_ad(mock_api, tools):
    mock_api.get("/v1/ads/1550534860016399").respond(
        200, json={"data": AD_DETAIL, "credits_used": 2, "cached": True}
    )
    result = await tools["get_ad"](ad_id="1550534860016399")
    assert "Text: Download our themes today" in result
    assert "Card 1: Card A | Body A | https://example.com/a" in result
    assert "**Nike**" in result
    assert "Beneficiary: person:1a2b3c4d" in result
    assert "EU transparency: reach 65,104, gender all, age 21-65" in result
    assert "Targeted locations: Italy" in result
    assert "IT 18-24: 31 / 1 / 0" in result
    assert "Credits used: 2" in result
    assert "served from cache" in result


async def test_get_ad_not_found(mock_api, tools):
    mock_api.get("/v1/ads/0").respond(
        404, json={"error": "ad_not_found", "message": "Ad not found"}
    )
    with pytest.raises(ToolError, match="Ad not found"):
        await tools["get_ad"](ad_id="0")


async def test_get_page(mock_api, tools):
    mock_api.get("/v1/pages/15087023444").respond(
        200, json={"data": PAGE, "credits_used": 1, "cached": False}
    )
    result = await tools["get_page"](page_id="15087023444")
    assert "**Nike** (page 15087023444)" in result
    assert "Likes: 39,000,000 | verified" in result
    assert "@nike — 300,000,000 followers (verified)" in result
    assert "Active ads (estimate): 14,386" in result


async def test_get_page_ads(mock_api, tools):
    route = mock_api.get("/v1/pages/15087023444/ads").respond(
        200, json=ads_body([ad("7", status="inactive", ended_at="2026-06-01T00:00:00Z")])
    )
    result = await tools["get_page_ads"](page_id="15087023444", status="all", limit=5)
    assert "Ads of page 15087023444" in result
    assert "ran 2026-05-19 → 2026-06-01" in result
    assert "q" not in route.calls.last.request.url.params
    assert route.calls.last.request.url.params["limit"] == "5"


async def test_search_pages(mock_api, tools):
    mock_api.get("/v1/pages/search").respond(
        200,
        json={
            "data": [
                {
                    "id": "15087023444",
                    "name": "Nike",
                    "is_person": False,
                    "profile_picture_url": None,
                    "categories": ["Sportswear Store"],
                    "like_count": 39000000,
                    "ads_in_results": 4,
                }
            ],
            "credits_used": 1,
            "cached": False,
        },
    )
    result = await tools["search_pages"](query="nike")
    assert (
        "- Nike (page_id 15087023444) — Sportswear Store — 39,000,000 likes, 4 matching" in result
    )


async def test_search_pages_empty(mock_api, tools):
    mock_api.get("/v1/pages/search").respond(200, json={"data": [], "credits_used": 0})
    assert "No advertisers found" in await tools["search_pages"](query="zzz")
