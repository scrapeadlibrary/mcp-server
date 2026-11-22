# ScrapeAdLibrary MCP Server

<!-- mcp-name: com.scrapeadlibrary/scrapeadlibrary -->

An [MCP](https://modelcontextprotocol.io) server that lets AI assistants (Claude Desktop, Claude
Code, Cursor, Cline...) search the public Meta Ad Library (Facebook, Instagram, Messenger, Audience
Network, Threads) through the [ScrapeAdLibrary](https://scrapeadlibrary.com) API: competitor ads, creatives,
advertisers, political ad spend, EU (DSA) reach and targeting.

## Features

**5 Tools** — search ads, ad detail, advertiser profile, advertiser's ads, advertiser search

**4 Documentation Resources** — API reference, quickstart, pricing, workflow examples

**3 Prompt Templates** — competitor ad research, keyword market scan, single ad analysis

## Connect without installing (Claude, ChatGPT, Claude Code)

The same tools are available as a hosted remote MCP server with OAuth sign-in: no API key to copy,
nothing to install. Add this URL as a custom connector and sign in with your ScrapeAdLibrary account:

```
https://api.scrapeadlibrary.com/mcp
```

- **Claude** (web, Desktop, mobile): Customize → Connectors → Add custom connector.
- **ChatGPT**: chatgpt.com/plugins → Add custom MCP server → OAuth.
- **Claude Code**: `claude mcp add --transport http scrapeadlibrary https://api.scrapeadlibrary.com/mcp`,
  then `/mcp` to sign in.

Calls use your account's credits with the API's pricing. Step-by-step guide:
[scrapeadlibrary.com/docs/mcp](https://scrapeadlibrary.com/docs/mcp).

## Quick Start (local server with an API key)

### 1. Get an API Key

Sign up at [scrapeadlibrary.com](https://scrapeadlibrary.com) and create an API key (starts with `sal_`).

### 2. Configure Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "scrapeadlibrary": {
      "command": "uvx",
      "args": ["scrapeadlibrary-mcp"],
      "env": {
        "SCRAPEADLIBRARY_API_KEY": "sal_your_key_here"
      }
    }
  }
}
```

### 3. Use it

Ask Claude:
- "What ads is Nike running in Italy right now? Summarise their messaging."
- "Show me active video ads about 'protein powder' in the US, sorted by impressions"
- "Which advertisers run ads for 'running shoes'?"
- "Get the EU reach and targeting of ad 1550534860016399"

## Configuration for Other Clients

### Cursor

Add the same JSON block to `.cursor/mcp.json`.

### Claude Code

```bash
claude mcp add scrapeadlibrary -e SCRAPEADLIBRARY_API_KEY=sal_your_key_here -- uvx scrapeadlibrary-mcp
```

## Installation Alternatives

### pip

```bash
pip install scrapeadlibrary-mcp
SCRAPEADLIBRARY_API_KEY=sal_xxx scrapeadlibrary-mcp
```

### npx

```bash
SCRAPEADLIBRARY_API_KEY=sal_xxx npx scrapeadlibrary-mcp
```

(The npm package is a thin wrapper: it runs the Python server via `uvx`, or `python3 -m` as a
fallback.)

### Docker

```bash
docker build -t scrapeadlibrary-mcp .
docker run -i --rm -e SCRAPEADLIBRARY_API_KEY=sal_xxx scrapeadlibrary-mcp
```

## Tools

| Tool | Description | Cost | Key defaults |
|------|-------------|------|--------------|
| `search_ads` | Search ads by keyword and/or advertiser, with country, status, media, platform, language, date filters | 1 credit per 10 ads | limit=10, status=active |
| `get_ad` | Full ad: text, media, cards, advertiser, payer/beneficiary, EU/UK transparency | 2 credits | — |
| `get_page` | Advertiser profile: category, likes, Instagram, active ads estimate | 1 credit | — |
| `get_page_ads` | Ads of one advertiser | 1 credit per 10 ads | limit=10, status=active |
| `search_pages` | Advertisers that ran ads matching a keyword | 1 credit per 10 results | limit=10 |

Empty results and errors cost 0 credits. Lists return a `cursor` to fetch the next page.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SCRAPEADLIBRARY_API_KEY` | Yes | Your API key (starts with `sal_`) |
| `SCRAPEADLIBRARY_BASE_URL` | No | Override API base URL (default: `https://api.scrapeadlibrary.com`) |

## Development

```bash
uv venv && uv pip install -e ".[dev]"
.venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

Test with MCP Inspector:

```bash
SCRAPEADLIBRARY_API_KEY=sal_xxx .venv/bin/mcp dev dev_server.py
```

`assets/logo-400.png` is still the placeholder logo inherited from the template: replace it with
the final brand logo before publishing to registries.

## License

MIT
