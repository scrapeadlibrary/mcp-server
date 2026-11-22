"""MCP resource definitions — static documentation exposed to AI clients."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import API_KEY_ENV, API_KEY_PREFIX, BRAND_NAME, BRAND_SITE, DEFAULT_BASE_URL, RESOURCE_SCHEME


def register_resources(mcp: FastMCP) -> None:
    """Register documentation resources on the MCP server."""

    @mcp.resource(f"{RESOURCE_SCHEME}://docs/api-reference")
    async def api_reference() -> str:
        """Complete API reference: endpoints, parameters, objects, errors."""
        return API_REFERENCE

    @mcp.resource(f"{RESOURCE_SCHEME}://docs/quickstart")
    async def quickstart() -> str:
        """Getting started with the MCP server."""
        return QUICKSTART

    @mcp.resource(f"{RESOURCE_SCHEME}://docs/pricing")
    async def pricing() -> str:
        """Pricing and credit costs per tool."""
        return PRICING

    @mcp.resource(f"{RESOURCE_SCHEME}://docs/examples")
    async def examples() -> str:
        """Common research workflows."""
        return EXAMPLES


# ---------------------------------------------------------------------------
# Static content
# ---------------------------------------------------------------------------

API_REFERENCE = f"""\
# {BRAND_NAME} API Reference

Base URL: `{DEFAULT_BASE_URL}`

Authentication: `X-API-Key: {API_KEY_PREFIX}xxx` header
or `Authorization: Bearer {API_KEY_PREFIX}xxx`.
Timestamps are ISO-8601 UTC. Every successful response has `X-Credits-Used` and
`X-Credits-Remaining` headers. Failed requests cost 0 credits.

---

## GET /v1/ads/search
Search ads in the public Meta Ad Library. Cost: 1 credit per 10 ads returned (rounded up;
an empty result costs 0).

| Parameter | Default | Description |
|---|---|---|
| q | — | Keyword (1-100 chars); required unless `page_id` is given |
| page_id | — | Restrict to one advertiser page |
| country | `ALL` | ISO-3166 alpha-2 or `ALL` |
| status | `active` | `active`, `inactive`, `all` |
| ad_type | `all` | `all`, `political` (political & issue ads) |
| media_type | `all` | `all`, `image`, `video`, `meme`, `none` |
| platforms | all | csv of `facebook,instagram,messenger,audience_network,threads` |
| languages | all | csv of ISO-639-1 codes |
| active_from / active_to | — | `YYYY-MM-DD`: ads running at some point in the window |
| match | `any` | `any`, `exact` (exact phrase) |
| sort | `relevance` | `relevance`, `impressions` |
| limit | 30 | 1-50 |
| cursor | — | `next_cursor` of the previous page; other params must be identical |

**Response:** `data` (list of Ad), `total_estimate`, `has_more`, `next_cursor`, `credits_used`,
`cached`, `media_expires_at`.

## GET /v1/pages/{{page_id}}/ads
Ads of one advertiser. Same parameters as search except `q`/`page_id`. Same response and cost.

## GET /v1/ads/{{ad_id}}
Full ad detail. Query: `country` (default `ALL`). Cost: 2 credits.
**Response:** `data` (AdDetail), `credits_used`, `cached`, `media_expires_at`.

## GET /v1/pages/{{page_id}}
Advertiser profile. Cost: 1 credit. **Response:** `data` (Page), `credits_used`, `cached`.

## GET /v1/pages/search
Advertisers that ran ads matching `q` (deduplicated by page). Query: `q` (required), `country`
(default `ALL`), `limit` 1-30 (default 10). Cost: 1 credit per 10 results (empty = 0).
**Response:** `data` (list of PageSummary), `credits_used`, `cached`.

---

## Objects

**Ad**: `id`, `url` (Ad Library link), `page` {{`id`, `name`, `profile_picture_url`, `is_person`,
`categories`, `like_count`}}, `status` (`active`/`inactive`), `started_at`, `ended_at`, `platforms`,
`format` (`image`, `video`, `carousel`, `dco`, `dpa`, `text`, `other`), `body`, `title`, `caption`,
`link_url`, `link_description`, `cta` {{`text`, `type`}}, `images` [Media], `videos` [Media],
`cards` [Card], `variants_count`, `collation_id`, `categories`, `countries`,
`political` ({{`spend` {{`lower`, `upper`, `currency`, `text`}}, `impressions` {{`text`}},
`reach` {{`text`}}, `disclaimer`}} or null), `contains_ai_generated_media`.

**Media**: `type` (`image`/`video`), `url`, `preview_url`, `sd_url`, `expires_at`. Media URLs are
signed CDN links that expire (usually within a few days).

**Card** (carousel): `title`, `body`, `caption`, `link_url`, `cta`, `image`, `video`.

**AdDetail** = Ad + `advertiser` (Page), `payers` [{{`payer`, `beneficiary`}}],
`transparency` {{`eu`, `uk`}} (each null or {{`reach`, `gender`, `age_min`, `age_max`,
`locations` [{{`name`, `type`, `excluded`}}], `breakdown` [{{`country`, `age_range`, `male`,
`female`, `unknown`}}]}}), `about`, `removed`.

**Page**: `id`, `name`, `is_person`, `category`, `like_count`, `instagram` {{`username`,
`followers`, `verified`}}, `verified`, `profile_picture_url`, `cover_photo_url`, `about`,
`deleted`, `active_ads_estimate`, `url`.

**PageSummary**: `id`, `name`, `is_person`, `profile_picture_url`, `categories`, `like_count`,
`ads_in_results`.

Privacy: for person profiles (`is_person: true`) the profile picture is never returned, and
payer/beneficiary names of natural persons are pseudonymised as `person:<hash>`.

---

## Error Codes

| HTTP | `error` |
|---|---|
| 400 | `invalid_parameter` (details.param), `cursor_mismatch` |
| 401 | `missing_api_key`, `invalid_api_key` |
| 402 | `insufficient_credits` |
| 404 | `ad_not_found`, `page_not_found` |
| 410 | `cursor_expired` (restart from the first page) |
| 429 | `rate_limit_exceeded`, `insufficient_credits_retry_later` (with `Retry-After`) |
| 502 | `upstream_schema_changed` |
| 503 | `upstream_unavailable` |
| 504 | `upstream_timeout` |
| 500 | `internal_server_error` |

Error body: `{{"error": "<code>", "message": "<human-readable>", "details": {{...}}}}`
"""

QUICKSTART = f"""\
# {BRAND_NAME} MCP — Quick Start

## 1. Get an API Key

Sign up at {BRAND_SITE} and create an API key from the dashboard.
Keys start with `{API_KEY_PREFIX}`.

## 2. Configure your MCP client

### Claude Desktop / Cursor / Cline

```json
{{
  "mcpServers": {{
    "scrapeadlibrary": {{
      "command": "uvx",
      "args": ["scrapeadlibrary-mcp"],
      "env": {{
        "{API_KEY_ENV}": "{API_KEY_PREFIX}your_key_here"
      }}
    }}
  }}
}}
```

### Claude Code

```bash
claude mcp add scrapeadlibrary -e {API_KEY_ENV}={API_KEY_PREFIX}your_key_here \\
  -- uvx scrapeadlibrary-mcp
```

## 3. Try it out

Ask your AI assistant:
- "Show me active video ads about 'protein powder' running in Italy"
- "Which advertisers are running ads for 'running shoes' in the US?"
- "Analyse the current ads of Nike: formats, messages, calls to action"
- "Get the EU reach and targeting of ad 1550534860016399"

## Alternatives

```bash
npx scrapeadlibrary-mcp                              # npm wrapper (needs uv or Python 3.10+)
pip install scrapeadlibrary-mcp && scrapeadlibrary-mcp       # pip
```
"""

PRICING = f"""\
# {BRAND_NAME} Pricing

## Credit cost per tool
| Tool | Endpoint | Cost |
|---|---|---|
| `search_ads` | `GET /v1/ads/search` | 1 credit per 10 ads returned (rounded up) |
| `get_page_ads` | `GET /v1/pages/{{id}}/ads` | 1 credit per 10 ads returned (rounded up) |
| `search_pages` | `GET /v1/pages/search` | 1 credit per 10 advertisers returned (rounded up) |
| `get_ad` | `GET /v1/ads/{{id}}` | 2 credits |
| `get_page` | `GET /v1/pages/{{id}}` | 1 credit |

Examples: 10 ads = 1 credit, 30 ads = 3 credits, 50 ads = 5 credits.

## What's free
- Empty results and failed requests (any 4xx/5xx) cost 0 credits.
- `/health` needs no authentication.

## Balance
Every response carries the `X-Credits-Remaining` header; the tools print it after each call.
Buy credits at {BRAND_SITE}/pricing. With 0 credits the API answers `402 insufficient_credits`.
"""

EXAMPLES = """\
# Common Workflows

## Competitor ad research
1. `search_pages` with the competitor's brand name → get its `page_id`
2. `get_page` for the profile (category, likes, Instagram, active ads estimate)
3. `get_page_ads` (status `active`, limit 10-30) to see the current creatives
4. `get_ad` on the 2-3 most interesting ads for full text, cards, EU reach and targeting
5. Summarise: formats, hooks, offers, calls to action, landing pages, how long ads have run

## Market scan for a keyword
1. `search_ads` with the keyword and the target `country` (limit 20)
2. Group ads by advertiser and format; note long-running ads (started long ago, still active)
3. `search_pages` with the same keyword to list the advertisers

## Political & issue ads
1. `search_ads` with `ad_type="political"` and a country
2. Read spend and impressions ranges and the "paid for by" disclaimer
3. `get_ad` for payer/beneficiary and EU transparency

## Track changes over time
Use `active_from` / `active_to` to compare which ads ran in different periods.

## Paging through results
Each list returns `next_cursor` when more results exist: call the same tool again with
`cursor` and exactly the same filters (otherwise `cursor_mismatch`). Cursors expire after a while
(`cursor_expired`: restart from the first page).
"""
