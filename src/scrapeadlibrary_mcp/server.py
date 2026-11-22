"""ScrapeAdLibrary MCP Server entry point."""

from __future__ import annotations

import os
import sys

from mcp.server.fastmcp import FastMCP

from . import API_KEY_ENV, BASE_URL_ENV, BRAND_NAME, BRAND_SITE, DEFAULT_BASE_URL
from .client import ScrapeAdLibraryClient
from .prompts import register_prompts
from .resources import register_resources
from .tools import register_tools

mcp = FastMCP(
    BRAND_NAME,
    instructions=(
        "Search the public Meta Ad Library (Facebook, Instagram, Messenger, Audience Network, "
        "Threads): find ads by keyword or advertiser, read full ad details with EU/UK "
        "transparency data, and look up advertiser pages. Every call spends the user's credits: "
        "lists cost 1 credit per 10 results, an ad detail 2, a page profile 1. Use small limits "
        "and only fetch details when needed."
    ),
)

# Lazy-init client so import doesn't fail without env var (tests, --help, etc.)
_client: ScrapeAdLibraryClient | None = None


def _get_client() -> ScrapeAdLibraryClient:
    global _client
    if _client is None:
        api_key = os.environ.get(API_KEY_ENV, "")
        if not api_key:
            print(
                f"Error: {API_KEY_ENV} environment variable is required.\n"
                f"Get your API key at {BRAND_SITE}",
                file=sys.stderr,
            )
            sys.exit(1)
        base_url = os.environ.get(BASE_URL_ENV, DEFAULT_BASE_URL)
        _client = ScrapeAdLibraryClient(api_key=api_key, base_url=base_url)
    return _client


# Register components — tools get a lazy client reference
register_tools(mcp, _get_client)
register_resources(mcp)
register_prompts(mcp)


def main() -> None:
    """Run the MCP server (stdio transport)."""
    # Force client init to fail fast if key is missing
    _get_client()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
