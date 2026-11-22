"""Integration tests — verify the MCP server registers all components."""

from __future__ import annotations

import importlib
import os
from unittest.mock import patch

import pytest
from mcp.server.fastmcp import FastMCP


@pytest.fixture
def server():
    """Import server module with a fake API key set."""
    with patch.dict(os.environ, {"SCRAPEADLIBRARY_API_KEY": "sal_test_integration"}):
        import scrapeadlibrary_mcp.server as srv_mod

        importlib.reload(srv_mod)
        yield srv_mod.mcp


def test_server_has_tools(server: FastMCP):
    tools = server._tool_manager._tools
    assert set(tools) == {"search_ads", "get_ad", "get_page", "get_page_ads", "search_pages"}


def test_tool_descriptions_mention_credits(server: FastMCP):
    for tool in server._tool_manager._tools.values():
        assert "credit" in (tool.description or "").lower(), tool.name


def test_tool_schemas_expose_enums(server: FastMCP):
    schema = server._tool_manager._tools["search_ads"].parameters
    assert set(schema["properties"]["status"]["enum"]) == {"active", "inactive", "all"}
    assert schema["properties"]["limit"]["default"] == 10


def test_server_has_resources(server: FastMCP):
    actual = {str(k) for k in server._resource_manager._resources}
    assert {
        "scrapeadlibrary://docs/api-reference",
        "scrapeadlibrary://docs/quickstart",
        "scrapeadlibrary://docs/pricing",
        "scrapeadlibrary://docs/examples",
    } <= actual


def test_server_has_prompts(server: FastMCP):
    prompts = server._prompt_manager._prompts
    assert {"competitor_ad_research", "keyword_market_scan", "analyze_ad"} <= set(prompts)


async def test_competitor_prompt_by_name_and_id(server: FastMCP):
    fn = server._prompt_manager._prompts["competitor_ad_research"].fn
    by_name = await fn(competitor="Nike", country="IT")
    assert "search_pages" in by_name and 'country="IT"' in by_name
    by_id = await fn(competitor="15087023444")
    assert "use it directly" in by_id


async def test_resources_content(server: FastMCP):
    resources = {str(k): v for k, v in server._resource_manager._resources.items()}
    pricing = await resources["scrapeadlibrary://docs/pricing"].fn()
    assert "2 credits" in pricing and "cost 0 credits" in pricing
    reference = await resources["scrapeadlibrary://docs/api-reference"].fn()
    assert "/v1/ads/search" in reference and "rate_limit_exceeded" in reference


def test_missing_api_key_exits(monkeypatch):
    monkeypatch.delenv("SCRAPEADLIBRARY_API_KEY", raising=False)
    import scrapeadlibrary_mcp.server as srv_mod

    importlib.reload(srv_mod)
    with pytest.raises(SystemExit):
        srv_mod._get_client()
