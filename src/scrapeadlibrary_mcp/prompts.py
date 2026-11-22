"""MCP prompt templates for common ad research workflows."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    """Register prompt templates on the MCP server."""

    @mcp.prompt()
    async def competitor_ad_research(competitor: str, country: str = "ALL") -> str:
        """Analyse the ads a competitor is running right now.

        Args:
            competitor: Brand name or advertiser page ID (e.g. 'Nike' or '15087023444')
            country: ISO-3166 alpha-2 country (e.g. 'IT') or 'ALL'
        """
        find = (
            f"1. `{competitor}` is a page ID: use it directly.\n"
            if competitor.isdigit()
            else f"1. Call `search_pages` with query `{competitor}` and pick the official page "
            f"(most likes / matching ads); note its `page_id`.\n"
        )
        return (
            f"Please research the ads currently run by **{competitor}** (country: {country}).\n\n"
            f"Steps (keep credit use low: lists cost 1 credit per 10 ads, details 2):\n"
            f"{find}"
            f"2. Call `get_page` for the profile (category, likes, Instagram, active ads).\n"
            f'3. Call `get_page_ads` with `country="{country}"`, `status="active"`, `limit=20`.\n'
            f"4. Call `get_ad` on the 2-3 most distinctive ads (long-running ones first) for full "
            f"text, carousel cards and EU reach/targeting.\n"
            f"5. Report:\n"
            f"   - **Overview**: how many active ads, platforms, formats (image/video/carousel)\n"
            f"   - **Messaging**: recurring hooks, offers, claims, tone\n"
            f"   - **Calls to action and landing pages**\n"
            f"   - **Longest-running ads** (likely the best performers) and why they may work\n"
            f"   - **Audience** signals from EU transparency (ages, gender, countries, reach)\n"
            f"   - **Takeaways**: 3-5 ideas the user could test\n"
        )

    @mcp.prompt()
    async def keyword_market_scan(keyword: str, country: str = "ALL") -> str:
        """Map who advertises on a keyword and how.

        Args:
            keyword: Product, category or topic (e.g. 'protein powder')
            country: ISO-3166 alpha-2 country or 'ALL'
        """
        return (
            f"Please scan the ad market for **{keyword}** (country: {country}).\n\n"
            f"Steps:\n"
            f'1. Call `search_ads` with query `{keyword}`, `country="{country}"`, `limit=30`.\n'
            f"2. Call `search_pages` with query `{keyword}` to list the advertisers.\n"
            f"3. Report:\n"
            f"   - **Top advertisers** and how many ads each runs\n"
            f"   - **Formats and platforms** in use\n"
            f"   - **Common angles** (price, quality, urgency, social proof...)\n"
            f"   - **Standout ads** (with their Ad Library links)\n"
            f"   - **Gaps or opportunities** for a new advertiser\n"
        )

    @mcp.prompt()
    async def analyze_ad(ad_id: str) -> str:
        """Deep-dive into one ad: creative, copy, targeting and reach.

        Args:
            ad_id: Ad Library ID (e.g. '1550534860016399')
        """
        return (
            f"Please analyse ad `{ad_id}`.\n\n"
            f"Steps:\n"
            f"1. Call `get_ad` for `{ad_id}` (2 credits).\n"
            f"2. Report:\n"
            f"   - **Advertiser** and who paid for the ad\n"
            f"   - **Creative**: format, headline, body copy, cards, call to action, landing page\n"
            f"   - **Run time** and platforms\n"
            f"   - **Audience**: EU/UK reach, ages, gender, locations, breakdown highlights\n"
            f"   - **Why it might work** and what could be improved\n"
        )
