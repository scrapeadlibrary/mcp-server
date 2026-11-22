"""Error mapping from HTTP responses to domain-specific exceptions."""

from __future__ import annotations

from typing import Any

import httpx


class ScrapeAdLibraryError(Exception):
    """Base error for the ScrapeAdLibrary API."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        retry_after: float | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}
        self.retry_after = retry_after
        super().__init__(message)


class AuthenticationError(ScrapeAdLibraryError):
    """Missing or invalid API key (401)."""


class InsufficientCreditsError(ScrapeAdLibraryError):
    """No credits left (402)."""


class InvalidParameterError(ScrapeAdLibraryError):
    """Invalid query parameter (400 ``invalid_parameter``)."""


class CursorError(ScrapeAdLibraryError):
    """Cursor does not match the query (400) or expired (410)."""


class NotFoundError(ScrapeAdLibraryError):
    """Ad or page not found (404)."""


class RateLimitError(ScrapeAdLibraryError):
    """Too many requests (429)."""


class UpstreamError(ScrapeAdLibraryError):
    """The ad data source is temporarily failing (502/503/504)."""


_ERROR_MAP: dict[str, type[ScrapeAdLibraryError]] = {
    "invalid_parameter": InvalidParameterError,
    "cursor_mismatch": CursorError,
    "cursor_expired": CursorError,
    "missing_api_key": AuthenticationError,
    "invalid_api_key": AuthenticationError,
    "insufficient_credits": InsufficientCreditsError,
    "ad_not_found": NotFoundError,
    "page_not_found": NotFoundError,
    "rate_limit_exceeded": RateLimitError,
    "insufficient_credits_retry_later": RateLimitError,
    "upstream_schema_changed": UpstreamError,
    "upstream_unavailable": UpstreamError,
    "upstream_timeout": UpstreamError,
}

_STATUS_MAP: dict[int, type[ScrapeAdLibraryError]] = {
    400: InvalidParameterError,
    401: AuthenticationError,
    402: InsufficientCreditsError,
    404: NotFoundError,
    410: CursorError,
    422: InvalidParameterError,
    429: RateLimitError,
    502: UpstreamError,
    503: UpstreamError,
    504: UpstreamError,
}


def parse_retry_after(response: httpx.Response, body_value: Any = None) -> float | None:
    for value in (response.headers.get("retry-after"), body_value):
        if value is None:
            continue
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            continue
    return None


def raise_for_status(response: httpx.Response) -> None:
    """Raise a domain-specific exception if the response indicates an error."""
    if response.is_success:
        return

    message = f"HTTP {response.status_code}"
    code: str | None = None
    details: dict[str, Any] | None = None
    body_retry_after: Any = None
    try:
        body = response.json()
        if isinstance(body, dict):
            if isinstance(body.get("detail"), dict):  # FastAPI wrapper
                body = body["detail"]
            code = body.get("error") if isinstance(body.get("error"), str) else None
            message = str(body.get("message") or message)
            if isinstance(body.get("details"), dict):
                details = body["details"]
            body_retry_after = body.get("retry_after", (details or {}).get("retry_after"))
    except Exception:
        message = response.text or message

    exc_class = _ERROR_MAP.get(code or "") or _STATUS_MAP.get(
        response.status_code, ScrapeAdLibraryError
    )
    raise exc_class(
        message,
        status_code=response.status_code,
        code=code,
        details=details,
        retry_after=parse_retry_after(response, body_retry_after),
    )
