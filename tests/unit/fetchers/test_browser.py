"""Unit tests for the optional browser fetcher."""

from __future__ import annotations

import builtins
import sys
import textwrap
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
import pytest
import respx

from ndl.core.errors import BrowserError, HTTPError, RobotsBlockedError
from ndl.fetchers.browser import (
    BrowserFetcher,
    _playwright_session,
    _PlaywrightBrowserSession,
    check_browser_runtime,
)
from ndl.rules.loader import load_rule_file
from ndl.rules.schema import SourceRule

RULE_YAML = """
id: browser_test
name: Browser Test
version: 1.0.0
author: Tests
url_patterns:
  - pattern: "https://site.test/*"
    type: glob
fetcher:
  type: browser
  headers:
    User-Agent: "ndl-browser-test/1.0"
  rate_limit:
    min_interval_ms: 500
    max_concurrency: 1
  retry:
    attempts: 3
    backoff: fixed
  robots:
    respect: false
    ignore_justification: "test fixture"
  encoding: auto
index:
  novel:
    title: { selector: "h1" }
    author: { selector: ".author" }
  chapter_list:
    container: "#chapters"
    items: "a"
    title: { selector: "self" }
    url: { selector: "self", attr: "href" }
chapter:
  title: { selector: "h1" }
  content: { selector: "#content", attr: "html" }
"""


class FakeBrowserSession:
    def __init__(
        self,
        responses: list[tuple[int | None, str]],
        *,
        downloads: list[tuple[int | None, bytes]] | None = None,
    ) -> None:
        self.responses = responses
        self.download_responses = downloads or []
        self.urls: list[str] = []
        self.downloads: list[tuple[str, str]] = []
        self.closed = False

    async def get_html(self, url: str) -> tuple[int | None, str]:
        self.urls.append(url)
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]

    async def download_bytes(self, url: str, selector: str) -> tuple[int | None, bytes]:
        self.downloads.append((url, selector))
        if len(self.download_responses) > 1:
            return self.download_responses.pop(0)
        return self.download_responses[0]

    async def aclose(self) -> None:
        self.closed = True


class FakePlaywrightResponse:
    status = 200


class FakePlaywrightPage:
    def __init__(self, *, download_path: Path | None = None) -> None:
        self.goto_calls: list[dict[str, object]] = []
        self.wait_selectors: list[dict[str, object]] = []
        self.wait_timeouts: list[int] = []
        self.download_timeouts: list[float] = []
        self.clicked_selectors: list[dict[str, object]] = []
        self._download_path = download_path
        self.closed = False

    async def goto(self, url: str, *, wait_until: str, timeout: float) -> FakePlaywrightResponse:
        self.goto_calls.append({"url": url, "wait_until": wait_until, "timeout": timeout})
        return FakePlaywrightResponse()

    async def wait_for_selector(self, selector: str, *, timeout: float) -> None:
        self.wait_selectors.append({"selector": selector, "timeout": timeout})

    async def wait_for_timeout(self, milliseconds: int) -> None:
        self.wait_timeouts.append(milliseconds)

    async def content(self) -> str:
        return "<html>ready</html>"

    def expect_download(self, *, timeout: float) -> FakeDownloadContext:
        assert self._download_path is not None
        self.download_timeouts.append(timeout)
        return FakeDownloadContext(self._download_path)

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(self, selector)

    async def close(self) -> None:
        self.closed = True


class FakeDownload:
    def __init__(self, path: Path) -> None:
        self._path = path

    async def path(self) -> str:
        return str(self._path)


class FakeDownloadContext:
    def __init__(self, path: Path) -> None:
        self._path = path

    async def __aenter__(self) -> FakeDownloadContext:
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        return None

    @property
    def value(self) -> object:
        async def _value() -> FakeDownload:
            return FakeDownload(self._path)

        return _value()


class FakeLocator:
    def __init__(self, page: FakePlaywrightPage, selector: str) -> None:
        self._page = page
        self._selector = selector

    async def click(self, *, timeout: float) -> None:
        self._page.clicked_selectors.append({"selector": self._selector, "timeout": timeout})


class FakePlaywrightContext:
    def __init__(self, page: FakePlaywrightPage) -> None:
        self.page = page
        self.closed = False

    async def new_page(self) -> FakePlaywrightPage:
        return self.page

    async def close(self) -> None:
        self.closed = True


class FakeClosable:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True

    async def stop(self) -> None:
        self.closed = True


class FakePlaywrightError(Exception):
    pass


class FakePlaywrightTimeoutError(FakePlaywrightError):
    pass


def install_fake_playwright(
    monkeypatch: pytest.MonkeyPatch,
    async_playwright: Any,
) -> None:
    playwright_module = ModuleType("playwright")
    async_api_module = ModuleType("playwright.async_api")
    async_api_module.Error = FakePlaywrightError
    async_api_module.TimeoutError = FakePlaywrightTimeoutError
    async_api_module.async_playwright = async_playwright
    monkeypatch.setitem(sys.modules, "playwright", playwright_module)
    monkeypatch.setitem(sys.modules, "playwright.async_api", async_api_module)


@pytest.fixture
def rule(tmp_path: Path) -> SourceRule:
    path = tmp_path / "rule.yaml"
    path.write_text(textwrap.dedent(RULE_YAML), encoding="utf-8")
    return load_rule_file(path)


@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip real sleeping in throttle checks."""

    async def _instant(_seconds: float) -> None:
        return None

    monkeypatch.setattr("ndl.fetchers._throttle.asyncio.sleep", _instant)
    monkeypatch.setattr("ndl.fetchers.browser.asyncio.sleep", _instant)


@pytest.mark.asyncio
async def test_get_returns_rendered_html_and_reuses_session(rule: SourceRule) -> None:
    session = FakeBrowserSession([(200, "<html><body>rendered</body></html>")])
    factory_calls: list[tuple[SourceRule, dict[str, str], float]] = []

    async def session_factory(
        source_rule: SourceRule, headers: dict[str, str], timeout: float
    ) -> FakeBrowserSession:
        factory_calls.append((source_rule, headers, timeout))
        return session

    async with BrowserFetcher(rule, session_factory=session_factory, timeout=12.0) as fetcher:
        first = await fetcher.get("https://site.test/page")
        second = await fetcher.get("https://site.test/next")

    assert first == "<html><body>rendered</body></html>"
    assert second == "<html><body>rendered</body></html>"
    assert session.urls == ["https://site.test/page", "https://site.test/next"]
    assert session.closed is True
    assert len(factory_calls) == 1
    assert factory_calls[0][0] is rule
    assert factory_calls[0][1]["User-Agent"] == "ndl-browser-test/1.0"
    assert factory_calls[0][2] == 12.0


@pytest.mark.asyncio
async def test_get_raises_http_error_for_bad_status(rule: SourceRule) -> None:
    session = FakeBrowserSession([(404, "not found")])

    async def session_factory(
        _source_rule: SourceRule, _headers: dict[str, str], _timeout: float
    ) -> FakeBrowserSession:
        return session

    async with BrowserFetcher(rule, session_factory=session_factory) as fetcher:
        with pytest.raises(HTTPError) as info:
            await fetcher.get("https://site.test/missing")

    assert info.value.status_code == 404
    assert session.closed is True


@pytest.mark.asyncio
async def test_get_retries_5xx_then_returns_rendered_html(rule: SourceRule) -> None:
    session = FakeBrowserSession([(503, "busy"), (200, "ok")])

    async def session_factory(
        _source_rule: SourceRule, _headers: dict[str, str], _timeout: float
    ) -> FakeBrowserSession:
        return session

    async with BrowserFetcher(rule, session_factory=session_factory) as fetcher:
        body = await fetcher.get("https://site.test/flaky")

    assert body == "ok"
    assert session.urls == ["https://site.test/flaky", "https://site.test/flaky"]


@pytest.mark.asyncio
async def test_get_download_bytes_clicks_selector(rule: SourceRule) -> None:
    session = FakeBrowserSession([(200, "unused")], downloads=[(200, b"archive")])

    async def session_factory(
        _source_rule: SourceRule, _headers: dict[str, str], _timeout: float
    ) -> FakeBrowserSession:
        return session

    async with BrowserFetcher(rule, session_factory=session_factory) as fetcher:
        content = await fetcher.get_download_bytes("https://site.test/book", "a.download")

    assert content == b"archive"
    assert session.downloads == [("https://site.test/book", "a.download")]
    assert session.closed is True


@pytest.mark.asyncio
async def test_get_uses_browser_navigation_timeout_from_rule(tmp_path: Path) -> None:
    yaml = RULE_YAML.replace(
        "  encoding: auto\n",
        "  encoding: auto\n"
        "  browser:\n"
        "    navigation_timeout_ms: 15000\n"
        "    wait_until: domcontentloaded\n"
        "    wait_for_selector: '#ready'\n"
        "    extra_wait_ms: 250\n"
        "    viewport:\n"
        "      width: 1024\n"
        "      height: 768\n"
        "    javascript_enabled: false\n",
    )
    path = tmp_path / "rule.yaml"
    path.write_text(textwrap.dedent(yaml), encoding="utf-8")
    rule = load_rule_file(path)
    session = FakeBrowserSession([(200, "ok")])
    seen_timeouts: list[float] = []

    async def session_factory(
        _source_rule: SourceRule, _headers: dict[str, str], timeout: float
    ) -> FakeBrowserSession:
        seen_timeouts.append(timeout)
        return session

    async with BrowserFetcher(rule, session_factory=session_factory) as fetcher:
        await fetcher.get("https://site.test/page")

    assert seen_timeouts == [15.0]
    assert rule.fetcher.browser.wait_until == "domcontentloaded"
    assert rule.fetcher.browser.wait_for_selector == "#ready"
    assert rule.fetcher.browser.extra_wait_ms == 250
    assert rule.fetcher.browser.viewport.width == 1024
    assert rule.fetcher.browser.javascript_enabled is False


@pytest.mark.asyncio
async def test_playwright_session_uses_rule_browser_wait_controls() -> None:
    page = FakePlaywrightPage()
    context = FakePlaywrightContext(page)
    browser = FakeClosable()
    playwright = FakeClosable()
    session = _PlaywrightBrowserSession(
        playwright=playwright,
        browser=browser,
        context=context,
        timeout_ms=15000,
        wait_until="domcontentloaded",
        wait_for_selector="#ready",
        extra_wait_ms=250,
        error_types=(RuntimeError,),
    )

    status, html = await session.get_html("https://site.test/page")
    await session.aclose()

    assert status == 200
    assert html == "<html>ready</html>"
    assert page.goto_calls == [
        {
            "url": "https://site.test/page",
            "wait_until": "domcontentloaded",
            "timeout": 15000,
        }
    ]
    assert page.wait_selectors == [{"selector": "#ready", "timeout": 15000}]
    assert page.wait_timeouts == [250]
    assert page.closed is True
    assert context.closed is True
    assert browser.closed is True
    assert playwright.closed is True


@pytest.mark.asyncio
async def test_playwright_session_downloads_bytes_from_selector(tmp_path: Path) -> None:
    archive_path = tmp_path / "archive.txt"
    archive_path.write_bytes(b"archive bytes")
    page = FakePlaywrightPage(download_path=archive_path)
    context = FakePlaywrightContext(page)
    browser = FakeClosable()
    playwright = FakeClosable()
    session = _PlaywrightBrowserSession(
        playwright=playwright,
        browser=browser,
        context=context,
        timeout_ms=15000,
        wait_until="domcontentloaded",
        wait_for_selector="#ready",
        extra_wait_ms=250,
        error_types=(RuntimeError,),
    )

    status, content = await session.download_bytes("https://site.test/book", "a.download")
    await session.aclose()

    assert status == 200
    assert content == b"archive bytes"
    assert page.goto_calls == [
        {
            "url": "https://site.test/book",
            "wait_until": "domcontentloaded",
            "timeout": 15000,
        }
    ]
    assert page.wait_selectors == [{"selector": "#ready", "timeout": 15000}]
    assert page.wait_timeouts == [250]
    assert page.download_timeouts == [15000]
    assert page.clicked_selectors == [{"selector": "a.download", "timeout": 15000}]
    assert page.closed is True
    assert context.closed is True
    assert browser.closed is True
    assert playwright.closed is True


@pytest.mark.asyncio
async def test_playwright_session_closes_started_playwright_not_manager(
    rule: SourceRule,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = FakePlaywrightPage()
    context = FakePlaywrightContext(page)

    class FakeBrowser(FakeClosable):
        async def new_context(self, **_kwargs: object) -> FakePlaywrightContext:
            return context

    class FakeChromium:
        def __init__(self, browser: FakeBrowser) -> None:
            self.browser = browser

        async def launch(self, *, headless: bool) -> FakeBrowser:
            assert headless is True
            return self.browser

    class FakeStartedPlaywright:
        def __init__(self, browser: FakeBrowser) -> None:
            self.chromium = FakeChromium(browser)
            self.stopped = False

        async def stop(self) -> None:
            self.stopped = True

    class FakeManager:
        def __init__(self, playwright: FakeStartedPlaywright) -> None:
            self.playwright = playwright
            self.started = False

        async def start(self) -> FakeStartedPlaywright:
            self.started = True
            return self.playwright

    browser = FakeBrowser()
    playwright = FakeStartedPlaywright(browser)
    manager = FakeManager(playwright)
    install_fake_playwright(monkeypatch, lambda: manager)

    session = await _playwright_session(rule, {"User-Agent": "ndl-test"}, 30.0)
    status, html = await session.get_html("https://site.test/page")
    await session.aclose()

    assert status == 200
    assert html == "<html>ready</html>"
    assert manager.started is True
    assert not hasattr(manager, "stop")
    assert page.closed is True
    assert context.closed is True
    assert browser.closed is True
    assert playwright.stopped is True


@pytest.mark.asyncio
async def test_playwright_session_failure_stops_started_playwright(
    rule: SourceRule,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeChromium:
        async def launch(self, *, headless: bool) -> object:
            assert headless is True
            raise FakePlaywrightError("launch failed")

    class FakeStartedPlaywright:
        def __init__(self) -> None:
            self.chromium = FakeChromium()
            self.stopped = False

        async def stop(self) -> None:
            self.stopped = True

    class FakeManager:
        def __init__(self, playwright: FakeStartedPlaywright) -> None:
            self.playwright = playwright

        async def start(self) -> FakeStartedPlaywright:
            return self.playwright

    playwright = FakeStartedPlaywright()
    install_fake_playwright(monkeypatch, lambda: FakeManager(playwright))

    with pytest.raises(BrowserError) as info:
        await _playwright_session(rule, {"User-Agent": "ndl-test"}, 30.0)

    assert "Browser runtime failed to start." in info.value.user_message()
    assert playwright.stopped is True


@pytest.mark.asyncio
@respx.mock
async def test_get_blocks_when_robots_disallows(tmp_path: Path) -> None:
    yaml = RULE_YAML.replace("respect: false", "respect: true").replace(
        '    ignore_justification: "test fixture"\n', ""
    )
    path = tmp_path / "rule.yaml"
    path.write_text(textwrap.dedent(yaml), encoding="utf-8")
    rule = load_rule_file(path)
    session = FakeBrowserSession([(200, "should not render")])

    async def session_factory(
        _source_rule: SourceRule, _headers: dict[str, str], _timeout: float
    ) -> FakeBrowserSession:
        return session

    respx.get("https://site.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /\n")
    )

    async with BrowserFetcher(rule, session_factory=session_factory) as fetcher:
        with pytest.raises(RobotsBlockedError):
            await fetcher.get("https://site.test/page")

    assert session.urls == []


@pytest.mark.asyncio
async def test_default_session_factory_reports_missing_playwright(
    rule: SourceRule, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "playwright.async_api":
            raise ImportError("missing playwright")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(BrowserError) as info:
        await _playwright_session(rule, {"User-Agent": "ndl-test"}, 30.0)

    assert "pip install 'ndl-storykit[browser]'" in info.value.user_message()
    assert "playwright install chromium" in info.value.user_message()


@pytest.mark.asyncio
async def test_safe_close_swallows_errors() -> None:
    from ndl.fetchers.browser import _safe_aclose, _safe_stop_playwright

    class Boom:
        async def close(self) -> None:
            raise RuntimeError("close failed")

        async def stop(self) -> None:
            raise RuntimeError("stop failed")

    await _safe_aclose(None)
    await _safe_aclose(Boom())
    await _safe_stop_playwright(None)
    await _safe_stop_playwright(Boom())


@pytest.mark.asyncio
async def test_browser_runtime_check_reports_missing_playwright(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "playwright.async_api":
            raise ImportError("missing playwright")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    diagnostic = await check_browser_runtime()

    assert diagnostic.ok is False
    assert diagnostic.message == "Playwright is not installed."
    assert diagnostic.detail is not None
    assert "uv sync --extra browser" in diagnostic.detail
    assert "playwright install chromium" in diagnostic.detail


@pytest.mark.asyncio
async def test_browser_runtime_check_stops_started_playwright(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeChromium:
        def __init__(self, browser: FakeClosable) -> None:
            self.browser = browser

        async def launch(self, *, headless: bool) -> FakeClosable:
            assert headless is True
            return self.browser

    class FakeStartedPlaywright:
        def __init__(self, browser: FakeClosable) -> None:
            self.chromium = FakeChromium(browser)
            self.stopped = False

        async def stop(self) -> None:
            self.stopped = True

    class FakeManager:
        def __init__(self, playwright: FakeStartedPlaywright) -> None:
            self.playwright = playwright

        async def start(self) -> FakeStartedPlaywright:
            return self.playwright

    browser = FakeClosable()
    playwright = FakeStartedPlaywright(browser)
    install_fake_playwright(monkeypatch, lambda: FakeManager(playwright))

    diagnostic = await check_browser_runtime()

    assert diagnostic.ok is True
    assert browser.closed is True
    assert playwright.stopped is True
