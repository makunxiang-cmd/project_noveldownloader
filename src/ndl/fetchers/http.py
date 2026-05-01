"""HTTP fetcher implementation backed by httpx."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from types import TracebackType
from urllib.parse import urlparse

import httpx

from ndl.core.errors import HTTPError, NDLError, NetworkError, RateLimitedError
from ndl.fetchers._robots import RobotsChecker
from ndl.fetchers._throttle import HostThrottle
from ndl.rules.schema import RetryRule, SourceRule

_RETRY_AFTER_CAP_SECONDS = 60.0


class HttpFetcher:
    """Async HTTP fetcher honoring rule retry, rate-limit, and robots policy."""

    def __init__(
        self,
        rule: SourceRule,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._rule = rule
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout, follow_redirects=True)
        self._throttles: dict[str, HostThrottle] = {}
        self._headers = _resolve_headers(rule)
        self._user_agent = self._headers["User-Agent"]
        self._robots: RobotsChecker | None = (
            RobotsChecker(client=self._client, user_agent=self._user_agent)
            if rule.fetcher.robots.respect
            else None
        )

    async def __aenter__(self) -> HttpFetcher:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying httpx client when this fetcher owns it."""
        if self._owns_client:
            await self._client.aclose()

    async def get(self, url: str, *, encoding: str | None = None) -> str:
        """Fetch `url` honoring the rule's policies and return decoded text."""
        if self._robots is not None:
            await self._robots.check(url)
        async with self._throttle_for(url).slot():
            response = await self._fetch_with_retry(url)
        return self._decode(response, encoding)

    def _throttle_for(self, url: str) -> HostThrottle:
        host = urlparse(url).netloc
        throttle = self._throttles.get(host)
        if throttle is None:
            limit = self._rule.fetcher.rate_limit
            throttle = HostThrottle(
                min_interval_ms=limit.min_interval_ms,
                max_concurrency=limit.max_concurrency,
            )
            self._throttles[host] = throttle
        return throttle

    async def _fetch_with_retry(self, url: str) -> httpx.Response:
        retry = self._rule.fetcher.retry
        last_exc: NDLError | None = None
        next_delay: float | None = None
        for attempt in range(retry.attempts):
            next_delay = None
            try:
                response = await self._client.get(url, headers=self._headers)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = NetworkError(
                    "Network error while fetching URL.",
                    detail=f"URL: {url}\n{exc}",
                )
            else:
                if response.status_code == 429:
                    last_exc = RateLimitedError(
                        "Upstream rate-limited the request (HTTP 429).",
                        detail=f"URL: {url}",
                    )
                    next_delay = _retry_after_seconds(response)
                elif response.status_code >= 500:
                    last_exc = HTTPError(url, response.status_code)
                elif response.status_code >= 400:
                    raise HTTPError(url, response.status_code)
                else:
                    return response
            if attempt + 1 < retry.attempts:
                delay = next_delay if next_delay is not None else _backoff_delay(retry, attempt)
                await asyncio.sleep(delay)
        assert last_exc is not None
        raise last_exc

    def _decode(self, response: httpx.Response, encoding: str | None) -> str:
        chosen = encoding or self._rule.fetcher.encoding
        if chosen == "auto":
            return response.text
        return response.content.decode(chosen, errors="replace")


def _resolve_headers(rule: SourceRule) -> dict[str, str]:
    """Return request headers with a guaranteed User-Agent matching robots checks."""
    headers = dict(rule.fetcher.headers)
    if not any(key.lower() == "user-agent" for key in headers):
        headers["User-Agent"] = f"ndl/{rule.id}"
    return headers


def _retry_after_seconds(response: httpx.Response) -> float | None:
    """Parse a Retry-After header (delta-seconds or HTTP-date), capped at 60s."""
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    raw = raw.strip()
    try:
        seconds = float(raw)
    except ValueError:
        try:
            target = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return None
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
        seconds = (target - datetime.now(timezone.utc)).total_seconds()
    if seconds <= 0:
        return 0.0
    return min(seconds, _RETRY_AFTER_CAP_SECONDS)


def _backoff_delay(retry: RetryRule, attempt: int) -> float:
    if retry.backoff == "fixed":
        return 1.0
    return 2.0**attempt
