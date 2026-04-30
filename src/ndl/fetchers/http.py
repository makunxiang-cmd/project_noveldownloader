"""HTTP fetcher implementation backed by httpx."""

from __future__ import annotations

import asyncio
from types import TracebackType
from urllib.parse import urlparse

import httpx

from ndl.core.errors import HTTPError, NDLError, NetworkError, RateLimitedError
from ndl.fetchers._robots import RobotsChecker
from ndl.fetchers._throttle import HostThrottle
from ndl.rules.schema import RetryRule, SourceRule


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
        self._user_agent = rule.fetcher.headers.get("User-Agent", f"ndl/{rule.id}")
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
        for attempt in range(retry.attempts):
            try:
                response = await self._client.get(url, headers=self._rule.fetcher.headers)
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
                elif response.status_code >= 500:
                    last_exc = HTTPError(url, response.status_code)
                elif response.status_code >= 400:
                    raise HTTPError(url, response.status_code)
                else:
                    return response
            if attempt + 1 < retry.attempts:
                await asyncio.sleep(_backoff_delay(retry, attempt))
        assert last_exc is not None
        raise last_exc

    def _decode(self, response: httpx.Response, encoding: str | None) -> str:
        chosen = encoding or self._rule.fetcher.encoding
        if chosen == "auto":
            return response.text
        return response.content.decode(chosen, errors="replace")


def _backoff_delay(retry: RetryRule, attempt: int) -> float:
    if retry.backoff == "fixed":
        return 1.0
    return 2.0**attempt
