"""MCP tool definitions for ScrapeAdLibrary."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from .client import ScrapeAdLibraryClient
from .errors import RateLimitError, ScrapeAdLibraryError

Status = Literal["active", "inactive", "all"]
AdType = Literal["all", "political"]
MediaType = Literal["all", "image", "video", "meme", "none"]
Match = Literal["any", "exact"]
Sort = Literal["relevance", "impressions"]

BODY_PREVIEW_CHARS = 400


# ---------------------------------------------------------------------------
# Formatting helpers (plain text, compact, easy for an LLM to read)
# ---------------------------------------------------------------------------


def _fmt_int(value: Any) -> str:
    return f"{value:,}" if isinstance(value, int) else "N/A"


def _day(ts: str | None) -> str:
    return ts[:10] if ts else "?"


def _truncate(text: str, limit: int = BODY_PREVIEW_CHARS) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _format_ad(ad: dict[str, Any], index: int | None = None, full: bool = False) -> list[str]:
    page = ad.get("page") or {}
    prefix = f"{index}. " if index is not None else ""
    running = (
        f"active since {_day(ad.get('started_at'))}"
        if ad.get("status") == "active"
        else f"ran {_day(ad.get('started_at'))} → {_day(ad.get('ended_at'))}"
    )
    lines = [
        f"{prefix}Ad {ad.get('id')} — {page.get('name', 'Unknown')} (page {page.get('id', '?')})",
        f"   {running} | format: {ad.get('format', '?')} | "
        f"platforms: {', '.join(ad.get('platforms') or []) or '?'}",
    ]
    body = ad.get("body")
    if body:
        lines.append(f"   Text: {body if full else _truncate(body)}")
    if ad.get("title"):
        lines.append(f"   Headline: {ad['title']}")
    cta = ad.get("cta") or {}
    if cta.get("text") or ad.get("link_url"):
        lines.append(f"   CTA: {cta.get('text') or '-'} → {ad.get('link_url') or '-'}")
    images, videos, cards = ad.get("images") or [], ad.get("videos") or [], ad.get("cards") or []
    if images or videos or cards:
        media = f"   Media: {len(images)} image(s), {len(videos)} video(s), {len(cards)} card(s)"
        first = (videos or images or [{}])[0].get("url")
        if first:
            media += f" — first: {first}"
        lines.append(media)
    if full:
        for i, card in enumerate(cards, 1):
            card_media = (card.get("video") or card.get("image") or {}).get("url") or "-"
            lines.append(
                f"   Card {i}: {card.get('title') or '-'} | {card.get('body') or '-'} | "
                f"{card.get('link_url') or '-'} | media: {card_media}"
            )
    if (ad.get("variants_count") or 1) > 1:
        lines.append(f"   Variants: {ad['variants_count']} ads share this creative")
    political = ad.get("political")
    if political:
        spend = (political.get("spend") or {}).get("text") or "?"
        impressions = (political.get("impressions") or {}).get("text") or "?"
        lines.append(f"   Political: spend {spend}, impressions {impressions}")
        if political.get("disclaimer"):
            lines.append(f"   Disclaimer: {political['disclaimer']}")
    if ad.get("countries"):
        lines.append(f"   Countries: {', '.join(ad['countries'])}")
    if ad.get("url"):
        lines.append(f"   Ad Library: {ad['url']}")
    return lines


def _footer(data: dict[str, Any], credits_remaining: int | None) -> list[str]:
    lines = [""]
    if data.get("has_more") and data.get("next_cursor"):
        lines.append(
            f"More results available: call again with cursor='{data['next_cursor']}' "
            "and exactly the same filters."
        )
    billing = f"Credits used: {data.get('credits_used', 0)}"
    if credits_remaining is not None:
        billing += f" (remaining: {credits_remaining:,})"
    if data.get("cached"):
        billing += " — served from cache"
    lines.append(billing)
    if data.get("media_expires_at"):
        lines.append(f"Media URLs expire at {data['media_expires_at']}: download them before then.")
    return lines


def _format_ads_page(data: dict[str, Any], header: str, credits_remaining: int | None) -> str:
    ads = data.get("data") or []
    if not ads:
        return f"{header}\nNo ads found. (Empty results cost 0 credits.)"
    total = data.get("total_estimate")
    lines = [
        f"{header} — showing {len(ads)}" + (f" of ~{total:,}" if isinstance(total, int) else "")
    ]
    for i, ad in enumerate(ads, 1):
        lines.append("")
        lines.extend(_format_ad(ad, i))
    lines.extend(_footer(data, credits_remaining))
    return "\n".join(lines)


def _format_region(name: str, region: dict[str, Any] | None) -> list[str]:
    if not region:
        return []
    lines = [
        f"{name} transparency: reach {_fmt_int(region.get('reach'))}, "
        f"gender {region.get('gender') or '?'}, "
        f"age {region.get('age_min', '?')}-{region.get('age_max', '?')}"
    ]
    locations = region.get("locations") or []
    if locations:
        locs = [
            f"{loc.get('name')}{' (excluded)' if loc.get('excluded') else ''}" for loc in locations
        ]
        lines.append(f"   Targeted locations: {', '.join(locs)}")
    breakdown = region.get("breakdown") or []
    if breakdown:
        lines.append("   Reach by country / age (male / female / unknown):")
        for row in breakdown[:30]:
            lines.append(
                f"   - {row.get('country')} {row.get('age_range')}: "
                f"{row.get('male', 0)} / {row.get('female', 0)} / {row.get('unknown', 0)}"
            )
        if len(breakdown) > 30:
            lines.append(f"   ({len(breakdown) - 30} more rows omitted)")
    return lines


def _format_page(page: dict[str, Any]) -> list[str]:
    lines = [
        f"**{page.get('name', 'Unknown')}** (page {page.get('id')})",
        f"Category: {page.get('category') or 'N/A'}",
        f"Likes: {_fmt_int(page.get('like_count'))}"
        + (" | verified" if page.get("verified") else ""),
    ]
    ig = page.get("instagram")
    if ig:
        lines.append(
            f"Instagram: @{ig.get('username')} — {_fmt_int(ig.get('followers'))} followers"
            + (" (verified)" if ig.get("verified") else "")
        )
    if page.get("active_ads_estimate") is not None:
        lines.append(f"Active ads (estimate): {_fmt_int(page.get('active_ads_estimate'))}")
    if page.get("deleted"):
        lines.append("This page has been deleted.")
    if page.get("about"):
        lines.append(f"About: {page['about']}")
    if page.get("url"):
        lines.append(f"Ad Library: {page['url']}")
    return lines


def _tool_error(e: ScrapeAdLibraryError) -> ToolError:
    message = e.message
    if isinstance(e, RateLimitError) and e.retry_after is not None:
        message += f" (retry after {int(e.retry_after)}s)"
    return ToolError(message)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP, get_client: Callable[[], ScrapeAdLibraryClient]) -> None:
    """Register all tools on the MCP server instance.

    API errors are raised as ToolError, so the client sees a failed call (isError) with the
    API's message, not a successful result.
    """

    @mcp.tool()
    async def search_ads(
        query: str | None = None,
        page_id: str | None = None,
        country: str = "ALL",
        status: Status = "active",
        ad_type: AdType = "all",
        media_type: MediaType = "all",
        platforms: list[str] | None = None,
        languages: list[str] | None = None,
        active_from: str | None = None,
        active_to: str | None = None,
        match: Match = "any",
        sort: Sort = "relevance",
        limit: int = 10,
        cursor: str | None = None,
    ) -> str:
        """Search the public Meta Ad Library (Facebook, Instagram, Messenger, Audience Network,
        Threads) for ads by keyword and/or advertiser.

        Cost: 1 credit per 10 ads returned, rounded up (limit=10 → 1 credit, limit=50 → 5);
        an empty result or an error costs 0. Keep `limit` small unless the user needs more.

        Args:
            query: Keyword or phrase (1-100 chars). Required unless page_id is given.
            page_id: Restrict to one advertiser (numeric page ID, see search_pages).
            country: ISO-3166 alpha-2 country where the ads ran (e.g. 'IT', 'US') or 'ALL'.
            status: 'active' (default), 'inactive' or 'all'.
            ad_type: 'all' or 'political' (political & issue ads, with spend/impressions).
            media_type: 'all', 'image', 'video', 'meme' or 'none'.
            platforms: Subset of facebook, instagram, messenger, audience_network, threads.
            languages: ISO-639-1 language codes of the ad text (e.g. ['it', 'en']).
            active_from: YYYY-MM-DD; ads running at some point from this date.
            active_to: YYYY-MM-DD; ads running at some point up to this date.
            match: 'any' (all words, default) or 'exact' (exact phrase).
            sort: 'relevance' (default) or 'impressions' (most impressions first).
            limit: Ads per page, 1-50 (default 10).
            cursor: next_cursor from a previous call, to get the next page (same filters).
        """
        if not query and not page_id:
            raise ToolError("Provide a query or a page_id.")
        client = get_client()
        try:
            data = await client.search_ads(
                q=query, page_id=page_id, country=country, status=status, ad_type=ad_type,
                media_type=media_type, platforms=platforms, languages=languages,
                active_from=active_from, active_to=active_to, match=match, sort=sort,
                limit=limit, cursor=cursor,
            )  # fmt: skip
        except ScrapeAdLibraryError as e:
            raise _tool_error(e) from e
        subject = f"'{query}'" if query else f"page {page_id}"
        return _format_ads_page(
            data, f"Ads for {subject} (country {country}, {status})", client.credits_remaining
        )

    @mcp.tool()
    async def get_ad(ad_id: str, country: str | None = None) -> str:
        """Get the full detail of one ad: complete text, all media and carousel cards, the
        advertiser profile, who paid for it (payer/beneficiary), and EU (DSA) / UK transparency
        data (reach, targeted ages, gender, locations, reach breakdown by country and age).

        Cost: 2 credits.

        Args:
            ad_id: Ad Library ID (the numeric `id` returned by search_ads).
            country: ISO-3166 alpha-2 country for transparency data, or 'ALL' (default).
        """
        client = get_client()
        try:
            data = await client.get_ad(ad_id, country=country)
        except ScrapeAdLibraryError as e:
            raise _tool_error(e) from e

        ad = data.get("data") or {}
        lines = _format_ad(ad, full=True)
        if ad.get("removed"):
            lines.append("   NOTE: this ad was taken down by Meta.")
        advertiser = ad.get("advertiser")
        if advertiser:
            lines.append("")
            lines.append("Advertiser:")
            lines.extend(f"   {line}" for line in _format_page(advertiser))
        payers = ad.get("payers") or []
        if payers:
            lines.append("")
            for p in payers:
                lines.append(
                    f"Paid by: {p.get('payer') or '?'} | Beneficiary: {p.get('beneficiary') or '?'}"
                )
        transparency = ad.get("transparency") or {}
        region_lines = _format_region("EU", transparency.get("eu")) + _format_region(
            "UK", transparency.get("uk")
        )
        if region_lines:
            lines.append("")
            lines.extend(region_lines)
        lines.extend(_footer(data, client.credits_remaining))
        return "\n".join(lines)

    @mcp.tool()
    async def get_page(page_id: str) -> str:
        """Get an advertiser's profile: name, category, likes, Instagram account and followers,
        verification, and an estimate of how many ads it is running now.

        Cost: 1 credit.

        Args:
            page_id: Numeric advertiser page ID (from search_ads results or search_pages).
        """
        client = get_client()
        try:
            data = await client.get_page(page_id)
        except ScrapeAdLibraryError as e:
            raise _tool_error(e) from e
        lines = _format_page(data.get("data") or {})
        lines.extend(_footer(data, client.credits_remaining))
        return "\n".join(lines)

    @mcp.tool()
    async def get_page_ads(
        page_id: str,
        country: str = "ALL",
        status: Status = "active",
        media_type: MediaType = "all",
        platforms: list[str] | None = None,
        languages: list[str] | None = None,
        active_from: str | None = None,
        active_to: str | None = None,
        sort: Sort = "relevance",
        limit: int = 10,
        cursor: str | None = None,
    ) -> str:
        """List the ads of one advertiser (competitor), newest and most relevant first.

        Cost: 1 credit per 10 ads returned, rounded up; an empty result costs 0.

        Args:
            page_id: Numeric advertiser page ID (use search_pages to find it from a brand name).
            country: ISO-3166 alpha-2 country or 'ALL' (default).
            status: 'active' (default), 'inactive' or 'all'.
            media_type: 'all', 'image', 'video', 'meme' or 'none'.
            platforms: Subset of facebook, instagram, messenger, audience_network, threads.
            languages: ISO-639-1 language codes.
            active_from: YYYY-MM-DD.
            active_to: YYYY-MM-DD.
            sort: 'relevance' (default) or 'impressions'.
            limit: Ads per page, 1-50 (default 10).
            cursor: next_cursor from a previous call, to get the next page (same filters).
        """
        client = get_client()
        try:
            data = await client.get_page_ads(
                page_id, country=country, status=status, media_type=media_type,
                platforms=platforms, languages=languages, active_from=active_from,
                active_to=active_to, sort=sort, limit=limit, cursor=cursor,
            )  # fmt: skip
        except ScrapeAdLibraryError as e:
            raise _tool_error(e) from e
        return _format_ads_page(
            data, f"Ads of page {page_id} (country {country}, {status})", client.credits_remaining
        )

    @mcp.tool()
    async def search_pages(query: str, country: str | None = None, limit: int = 10) -> str:
        """Find advertisers (Facebook/Instagram pages) that ran ads matching a keyword or brand
        name. Use it to get the page_id needed by get_page and get_page_ads.

        Cost: 1 credit per 10 advertisers returned, rounded up; an empty result costs 0.

        Args:
            query: Brand name or keyword.
            country: ISO-3166 alpha-2 country or 'ALL' (default).
            limit: 1-30 (default 10).
        """
        client = get_client()
        try:
            data = await client.search_pages(query, country=country, limit=limit)
        except ScrapeAdLibraryError as e:
            raise _tool_error(e) from e

        pages = data.get("data") or []
        if not pages:
            return f"No advertisers found for '{query}'. (Empty results cost 0 credits.)"
        lines = [f"Advertisers with ads matching '{query}':"]
        for p in pages:
            categories = ", ".join(p.get("categories") or [])
            lines.append(
                f"- {p.get('name')} (page_id {p.get('id')})"
                + (f" — {categories}" if categories else "")
                + f" — {_fmt_int(p.get('like_count'))} likes, "
                f"{p.get('ads_in_results', '?')} matching ad(s)"
            )
        lines.extend(_footer(data, client.credits_remaining))
        return "\n".join(lines)
