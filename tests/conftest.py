"""Shared fixtures for MCP server tests."""

from __future__ import annotations

import copy
from typing import Any

import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scrapeadlibrary_mcp.client import ScrapeAdLibraryClient
from scrapeadlibrary_mcp.tools import register_tools

BASE_URL = "https://api.scrapeadlibrary.com"

AD: dict[str, Any] = {
    "id": "1550534860016399",
    "url": "https://www.facebook.com/ads/library/?id=1550534860016399",
    "page": {"id": "115939511520844", "name": "Perfect themes", "is_person": False},
    "status": "active",
    "started_at": "2026-05-19T07:00:00Z",
    "ended_at": None,
    "platforms": ["facebook", "instagram"],
    "format": "video",
    "body": "Download our themes today",
    "title": "Perfect themes",
    "caption": None,
    "link_url": "https://example.com/app",
    "link_description": None,
    "cta": {"text": "Install now", "type": "install_mobile_app"},
    "images": [],
    "videos": [{"type": "video", "url": "https://scontent.example/v.mp4"}],
    "cards": [],
    "variants_count": 3,
    "collation_id": None,
    "categories": [],
    "countries": ["IT"],
    "political": None,
    "contains_ai_generated_media": False,
}

PAGE: dict[str, Any] = {
    "id": "15087023444",
    "name": "Nike",
    "is_person": False,
    "category": "Sportswear Store",
    "like_count": 39000000,
    "instagram": {"username": "nike", "followers": 300000000, "verified": True},
    "verified": True,
    "about": "Just do it",
    "deleted": False,
    "active_ads_estimate": 14386,
    "url": "https://www.facebook.com/ads/library/?view_all_page_id=15087023444",
}


def ad(ad_id: str = AD["id"], **overrides: Any) -> dict[str, Any]:
    data = copy.deepcopy(AD)
    data.update(id=ad_id, **overrides)
    return data


def ads_body(ads: list[dict[str, Any]], has_more: bool = False, next_cursor: str | None = None):
    return {
        "data": ads,
        "total_estimate": 6780,
        "has_more": has_more,
        "next_cursor": next_cursor,
        "credits_used": -(-len(ads) // 10),
        "cached": False,
        "media_expires_at": "2026-11-25T18:00:00Z",
    }


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def _no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("scrapeadlibrary_mcp.client._sleep", _no_sleep)


@pytest.fixture
def mock_api():
    """respx mock router scoped to the API base URL."""
    with respx.mock(base_url=BASE_URL) as router:
        yield router


@pytest.fixture
def client():
    return ScrapeAdLibraryClient(api_key="sal_test_key", base_url=BASE_URL)


@pytest.fixture
def tools(client):
    """Tool functions of a FastMCP instance with the tools registered."""
    server = FastMCP("test")
    register_tools(server, lambda: client)
    return {name: tool.fn for name, tool in server._tool_manager._tools.items()}
