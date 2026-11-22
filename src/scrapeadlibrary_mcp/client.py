"""Async HTTP client for the ScrapeAdLibrary REST API."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from . import BRAND_NAME, DEFAULT_BASE_URL, __version__
from .errors import ScrapeAdLibraryError, parse_retry_after, raise_for_status

DEFAULT_TIMEOUT = 60.0
MAX_RETRIES = 2
MAX_RETRY_DELAY = 30.0
RETRY_STATUSES = frozenset({429, 500, 503, 504})
_sleep = asyncio.sleep  # patched in tests


def _csv(value: list[str] | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value or None
    return ",".join(v for v in value if v) or None


def _compact(**params: Any) -> dict[str, Any] | None:
    cleaned = {k: v for k, v in params.items() if v is not None}
    return cleaned or None


class ScrapeAdLibraryClient:
    """Async wrapper around the ScrapeAdLibrary REST API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        max_retries: int = MAX_RETRIES,
    ):
        self.max_retries = max_retries
        self.credits_remaining: int | None = None
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={
                "X-API-Key": api_key,
                "Accept": "application/json",
                "User-Agent": f"{BRAND_NAME}-MCP/{__version__}",
            },
            timeout=DEFAULT_TIMEOUT,
        )

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        attempt = 0
        while True:
            try:
                response = await self._client.get(path, params=params)
            except httpx.TransportError as exc:
                if attempt >= self.max_retries:
                    raise ScrapeAdLibraryError(
                        f"Could not reach the {BRAND_NAME} API: {exc}"
                    ) from exc
                await _sleep(0.5 * 2**attempt)
                attempt += 1
                continue
            if response.status_code in RETRY_STATUSES and attempt < self.max_retries:
                delay = parse_retry_after(response)
                await _sleep(min(delay if delay is not None else 0.5 * 2**attempt, MAX_RETRY_DELAY))
                attempt += 1
                continue
            raise_for_status(response)
            remaining = response.headers.get("x-credits-remaining")
            self.credits_remaining = int(remaining) if remaining and remaining.isdigit() else None
            return response.json()

    # -- Ads --

    async def search_ads(
        self,
        q: str | None = None,
        page_id: str | None = None,
        country: str | None = None,
        status: str | None = None,
        ad_type: str | None = None,
        media_type: str | None = None,
        platforms: list[str] | str | None = None,
        languages: list[str] | str | None = None,
        active_from: str | None = None,
        active_to: str | None = None,
        match: str | None = None,
        sort: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return await self._get(
            "/v1/ads/search",
            _compact(
                q=q, page_id=page_id, country=country, status=status, ad_type=ad_type,
                media_type=media_type, platforms=_csv(platforms), languages=_csv(languages),
                active_from=active_from, active_to=active_to, match=match, sort=sort,
                limit=limit, cursor=cursor,
            ),
        )  # fmt: skip

    async def get_ad(self, ad_id: str, country: str | None = None) -> dict[str, Any]:
        return await self._get(f"/v1/ads/{ad_id}", _compact(country=country))

    # -- Pages --

    async def get_page(self, page_id: str) -> dict[str, Any]:
        return await self._get(f"/v1/pages/{page_id}")

    async def get_page_ads(
        self,
        page_id: str,
        country: str | None = None,
        status: str | None = None,
        ad_type: str | None = None,
        media_type: str | None = None,
        platforms: list[str] | str | None = None,
        languages: list[str] | str | None = None,
        active_from: str | None = None,
        active_to: str | None = None,
        sort: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return await self._get(
            f"/v1/pages/{page_id}/ads",
            _compact(
                country=country, status=status, ad_type=ad_type, media_type=media_type,
                platforms=_csv(platforms), languages=_csv(languages), active_from=active_from,
                active_to=active_to, sort=sort, limit=limit, cursor=cursor,
            ),
        )  # fmt: skip

    async def search_pages(
        self, q: str, country: str | None = None, limit: int | None = None
    ) -> dict[str, Any]:
        return await self._get("/v1/pages/search", _compact(q=q, country=country, limit=limit))

    async def close(self) -> None:
        await self._client.aclose()
