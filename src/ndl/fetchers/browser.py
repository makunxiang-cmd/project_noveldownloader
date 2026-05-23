"""Optional browser-backed fetcher implementation."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

from ndl.core.errors import BrowserError, HTTPError, NDLError, RateLimitedError
from ndl.fetchers._common import backoff_delay, resolve_headers
from ndl.fetchers._robots import RobotsChecker
from ndl.fetchers._throttle import HostThrottle
from ndl.rules.schema import BrowserSearchRule, SourceRule


class BrowserSession(Protocol):
    """Small adapter boundary for a browser runtime session."""

    async def get_html(self, url: str) -> tuple[int | None, str]:
        """Navigate to `url` and return the response status and rendered HTML."""

    async def download_bytes(self, url: str, selector: str) -> tuple[int | None, bytes]:
        """Navigate to `url`, click `selector`, and return downloaded bytes."""

    async def search_html(
        self, search: BrowserSearchRule, keyword: str
    ) -> tuple[int | None, str, str]:
        """Submit a browser-backed search form and return status, HTML, and final URL."""

    async def aclose(self) -> None:
        """Release browser resources."""


BrowserSessionFactory = Callable[[SourceRule, dict[str, str], float], Awaitable[BrowserSession]]
_BROWSER_INSTALL_DETAIL = (
    "Install with `pip install 'ndl-storykit[browser]'` or `uv sync --extra browser`, "
    "then run `playwright install chromium`."
)


@dataclass(frozen=True)
class BrowserRuntimeDiagnostic:
    """Result of checking the optional browser runtime."""

    ok: bool
    message: str
    detail: str | None = None


class BrowserFetcher:
    """Fetcher that returns rendered HTML through an optional Playwright runtime."""

    def __init__(
        self,
        rule: SourceRule,
        *,
        session_factory: BrowserSessionFactory | None = None,
        timeout: float | None = None,
    ) -> None:
        self._rule = rule
        self._session_factory = session_factory or _playwright_session
        self._timeout = timeout or (rule.fetcher.browser.navigation_timeout_ms / 1000)
        self._session: BrowserSession | None = None
        self._robots_client: httpx.AsyncClient | None = None
        self._throttles: dict[str, HostThrottle] = {}
        self._headers = resolve_headers(rule)
        self._robots: RobotsChecker | None = None
        if rule.fetcher.robots.respect:
            self._robots_client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)
            self._robots = RobotsChecker(
                client=self._robots_client,
                user_agent=self._headers["User-Agent"],
            )

    async def __aenter__(self) -> BrowserFetcher:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the browser session if it has been started."""
        if self._session is not None:
            await self._session.aclose()
            self._session = None
        if self._robots_client is not None:
            await self._robots_client.aclose()
            self._robots_client = None

    async def get(self, url: str, *, encoding: str | None = None) -> str:
        """Render `url` and return the page HTML."""
        del encoding
        if self._robots is not None:
            await self._robots.check(url)
        async with self._throttle_for(url).slot():
            return await self._fetch_with_retry(url)

    async def get_download_bytes(self, url: str, selector: str) -> bytes:
        """Render `url`, click `selector`, and return downloaded bytes."""
        if self._robots is not None:
            await self._robots.check(url)
        async with self._throttle_for(url).slot():
            return await self._download_with_retry(url, selector)

    async def get_search_html(
        self,
        search: BrowserSearchRule,
        keyword: str,
    ) -> tuple[str, str]:
        """Submit a browser-backed search form and return rendered HTML plus base URL."""
        if self._robots is not None:
            await self._robots.check(search.navigate_url)
        async with self._throttle_for(search.navigate_url).slot():
            return await self._search_with_retry(search, keyword)

    async def _ensure_session(self) -> BrowserSession:
        if self._session is None:
            self._session = await self._session_factory(self._rule, self._headers, self._timeout)
        return self._session

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

    async def _fetch_with_retry(self, url: str) -> str:
        retry = self._rule.fetcher.retry
        last_exc: NDLError | None = None
        for attempt in range(retry.attempts):
            try:
                status_code, html = await (await self._ensure_session()).get_html(url)
            except BrowserError as exc:
                last_exc = exc
            else:
                if status_code == 429:
                    last_exc = RateLimitedError(
                        "Upstream rate-limited the request (HTTP 429).",
                        detail=f"URL: {url}",
                    )
                elif status_code is not None and status_code >= 500:
                    last_exc = HTTPError(url, status_code)
                elif status_code is not None and status_code >= 400:
                    raise HTTPError(url, status_code)
                else:
                    return html
            if attempt + 1 < retry.attempts:
                await asyncio.sleep(backoff_delay(retry, attempt))
        assert last_exc is not None
        raise last_exc

    async def _download_with_retry(self, url: str, selector: str) -> bytes:
        retry = self._rule.fetcher.retry
        last_exc: NDLError | None = None
        for attempt in range(retry.attempts):
            try:
                status_code, content = await (await self._ensure_session()).download_bytes(
                    url, selector
                )
            except BrowserError as exc:
                last_exc = exc
            else:
                if status_code == 429:
                    last_exc = RateLimitedError(
                        "Upstream rate-limited the request (HTTP 429).",
                        detail=f"URL: {url}",
                    )
                elif status_code is not None and status_code >= 500:
                    last_exc = HTTPError(url, status_code)
                elif status_code is not None and status_code >= 400:
                    raise HTTPError(url, status_code)
                else:
                    return content
            if attempt + 1 < retry.attempts:
                await asyncio.sleep(backoff_delay(retry, attempt))
        assert last_exc is not None
        raise last_exc

    async def _search_with_retry(
        self,
        search: BrowserSearchRule,
        keyword: str,
    ) -> tuple[str, str]:
        retry = self._rule.fetcher.retry
        last_exc: NDLError | None = None
        for attempt in range(retry.attempts):
            try:
                status_code, html, final_url = await (await self._ensure_session()).search_html(
                    search, keyword
                )
            except BrowserError as exc:
                last_exc = exc
            else:
                if status_code == 429:
                    last_exc = RateLimitedError(
                        "Upstream rate-limited the request (HTTP 429).",
                        detail=f"URL: {search.navigate_url}",
                    )
                elif status_code is not None and status_code >= 500:
                    last_exc = HTTPError(search.navigate_url, status_code)
                elif status_code is not None and status_code >= 400:
                    raise HTTPError(search.navigate_url, status_code)
                else:
                    return html, final_url
            if attempt + 1 < retry.attempts:
                await asyncio.sleep(backoff_delay(retry, attempt))
        assert last_exc is not None
        raise last_exc


async def _playwright_session(
    rule: SourceRule,
    headers: dict[str, str],
    timeout: float,
) -> BrowserSession:
    try:
        from playwright.async_api import Error as PlaywrightError
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise BrowserError(
            "Browser fetcher requires the optional Playwright dependency.",
            detail=_BROWSER_INSTALL_DETAIL,
        ) from exc

    manager = async_playwright()
    playwright: Any | None = None
    browser: Any | None = None
    context: Any | None = None
    try:
        playwright = await manager.start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=headers["User-Agent"],
            extra_http_headers={
                key: value for key, value in headers.items() if key.lower() != "user-agent"
            },
            viewport={
                "width": rule.fetcher.browser.viewport.width,
                "height": rule.fetcher.browser.viewport.height,
            },
            java_script_enabled=rule.fetcher.browser.javascript_enabled,
        )
    except (PlaywrightError, PlaywrightTimeoutError) as exc:
        await _safe_aclose(context)
        await _safe_aclose(browser)
        await _safe_stop_playwright(playwright)
        raise BrowserError(
            "Browser runtime failed to start.",
            detail=f"Rule: {rule.id}\n{exc}\n\n{_BROWSER_INSTALL_DETAIL}",
        ) from exc

    return _PlaywrightBrowserSession(
        playwright=playwright,
        browser=browser,
        context=context,
        timeout_ms=timeout * 1000,
        wait_until=rule.fetcher.browser.wait_until,
        wait_for_selector=rule.fetcher.browser.wait_for_selector,
        extra_wait_ms=rule.fetcher.browser.extra_wait_ms,
        error_types=(PlaywrightError, PlaywrightTimeoutError),
    )


class _PlaywrightBrowserSession:
    def __init__(
        self,
        *,
        playwright: Any,
        browser: Any,
        context: Any,
        timeout_ms: float,
        wait_until: str,
        wait_for_selector: str | None,
        extra_wait_ms: int,
        error_types: tuple[type[Exception], ...],
    ) -> None:
        self._playwright = playwright
        self._browser = browser
        self._context = context
        self._timeout_ms = timeout_ms
        self._wait_until = wait_until
        self._wait_for_selector = wait_for_selector
        self._extra_wait_ms = extra_wait_ms
        self._error_types = error_types

    async def get_html(self, url: str) -> tuple[int | None, str]:
        page = await self._context.new_page()
        try:
            response = await page.goto(
                url,
                wait_until=self._wait_until,
                timeout=self._timeout_ms,
            )
            if self._wait_for_selector is not None:
                await page.wait_for_selector(self._wait_for_selector, timeout=self._timeout_ms)
            if self._extra_wait_ms:
                await page.wait_for_timeout(self._extra_wait_ms)
            status_code = None if response is None else response.status
            html = await page.content()
        except self._error_types as exc:
            raise BrowserError(
                "Browser fetch failed.",
                detail=f"URL: {url}\n{exc}",
            ) from exc
        finally:
            await page.close()
        return status_code, html

    async def download_bytes(self, url: str, selector: str) -> tuple[int | None, bytes]:
        page = await self._context.new_page()
        try:
            response = await page.goto(
                url,
                wait_until=self._wait_until,
                timeout=self._timeout_ms,
            )
            if self._wait_for_selector is not None:
                await page.wait_for_selector(self._wait_for_selector, timeout=self._timeout_ms)
            if self._extra_wait_ms:
                await page.wait_for_timeout(self._extra_wait_ms)
            async with page.expect_download(timeout=self._timeout_ms) as download_info:
                await page.locator(selector).click(timeout=self._timeout_ms)
            download = await download_info.value
            download_path = await download.path()
            status_code = None if response is None else response.status
            return status_code, Path(download_path).read_bytes()
        except self._error_types as exc:
            raise BrowserError(
                "Browser download failed.",
                detail=f"URL: {url}\nSelector: {selector}\n{exc}",
            ) from exc
        finally:
            await page.close()

    async def search_html(
        self,
        search: BrowserSearchRule,
        keyword: str,
    ) -> tuple[int | None, str, str]:
        page = await self._context.new_page()
        try:
            response = await page.goto(
                search.navigate_url,
                wait_until=self._wait_until,
                timeout=self._timeout_ms,
            )
            await page.fill(search.input_selector, keyword, timeout=self._timeout_ms)
            await page.locator(search.submit_selector).click(timeout=self._timeout_ms)
            if search.wait_for_url is not None:
                await page.wait_for_url(search.wait_for_url, timeout=self._timeout_ms)
            if search.wait_for_selector is not None:
                await page.wait_for_selector(
                    search.wait_for_selector,
                    timeout=self._timeout_ms,
                )
            if self._extra_wait_ms:
                await page.wait_for_timeout(self._extra_wait_ms)
            status_code = None if response is None else response.status
            html = await page.content()
            return status_code, html, page.url
        except self._error_types as exc:
            raise BrowserError(
                "Browser search failed.",
                detail=(
                    f"URL: {search.navigate_url}\n"
                    f"Input selector: {search.input_selector}\n"
                    f"Submit selector: {search.submit_selector}\n{exc}"
                ),
            ) from exc
        finally:
            await page.close()

    async def aclose(self) -> None:
        await self._context.close()
        await self._browser.close()
        await self._playwright.stop()


async def check_browser_runtime() -> BrowserRuntimeDiagnostic:
    """Check whether Playwright and Chromium are available for browser rules."""
    try:
        from playwright.async_api import Error as PlaywrightError
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except ImportError:
        return BrowserRuntimeDiagnostic(
            ok=False,
            message="Playwright is not installed.",
            detail=_BROWSER_INSTALL_DETAIL,
        )

    manager = async_playwright()
    playwright: Any | None = None
    browser: Any | None = None
    try:
        playwright = await manager.start()
        browser = await playwright.chromium.launch(headless=True)
    except (PlaywrightError, PlaywrightTimeoutError) as exc:
        return BrowserRuntimeDiagnostic(
            ok=False,
            message="Playwright Chromium is not available.",
            detail=f"{exc}\n\n{_BROWSER_INSTALL_DETAIL}",
        )
    finally:
        await _safe_aclose(browser)
        await _safe_stop_playwright(playwright)

    return BrowserRuntimeDiagnostic(ok=True, message="Playwright Chromium is available.")


async def _safe_aclose(resource: Any | None) -> None:
    if resource is None:
        return
    with contextlib.suppress(Exception):
        await resource.close()


async def _safe_stop_playwright(playwright: Any | None) -> None:
    if playwright is None:
        return
    with contextlib.suppress(Exception):
        await playwright.stop()
