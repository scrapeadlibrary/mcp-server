# Installing the ScrapeAdLibrary MCP server (for AI agents)

The server runs locally over stdio and is published on PyPI as `scrapeadlibrary-mcp`.

## 1. Requirements

- `uv` (provides `uvx`): `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `brew install uv`). Alternatively Python 3.10+ and `pip install scrapeadlibrary-mcp`.
- A ScrapeAdLibrary API key (starts with `sal_`). Ask the user for it; they can create one (free tier included) at https://scrapeadlibrary.com/dashboard/api-keys. Never invent a key.

## 2. MCP client configuration

Add this server to the client's MCP settings (for Cline: `cline_mcp_settings.json`), replacing the key:

```json
{
  "mcpServers": {
    "scrapeadlibrary": {
      "command": "uvx",
      "args": ["scrapeadlibrary-mcp"],
      "env": {
        "SCRAPEADLIBRARY_API_KEY": "sal_your_api_key"
      }
    }
  }
}
```

Without uv, use `"command": "scrapeadlibrary-mcp"` after `pip install scrapeadlibrary-mcp`.

## 3. Check it works

After the client restarts the server it should list 5 tools: `search_ads`, `get_ad`, `get_page`, `get_page_ads`, `search_pages`. Try `search_pages` with `query` `nike` and `limit` 5 (1 credit).

An `Invalid API key` error means the key is wrong or revoked; `Insufficient credits` means the credits are used up (top up at https://scrapeadlibrary.com/dashboard/billing).
