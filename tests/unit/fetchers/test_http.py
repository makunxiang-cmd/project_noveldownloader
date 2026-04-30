"""Unit tests for the HTTP fetcher."""

from __future__ import annotations

import textwrap
from pathlib import Path

import httpx
import pytest
import respx

from ndl.core.errors import HTTPError, NetworkError, RateLimitedError, RobotsBlockedError
from ndl.fetchers import HttpFetcher
from ndl.rules.loader import load_rule_file
from ndl.rules.schema import SourceRule

RULE_YAML = """
id: http_test
name: HTTP Test
version: 1.0.0
author: Tests
url_patterns:
  - pattern: "https://site.test/*"
    type: glob
fetcher:
  type: http
  headers:
    User-Agent: "ndl-test/1.0"
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


@pytest.fixture
def rule(tmp_path: Path) -> SourceRule:
    path = tmp_path / "rule.yaml"
    path.write_text(textwrap.dedent(RULE_YAML), encoding="utf-8")
    return load_rule_file(path)


@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip real sleeping in throttle and retry backoff to keep tests fast."""

    async def _instant(_seconds: float) -> None:
        return None

    monkeypatch.setattr("ndl.fetchers._throttle.asyncio.sleep", _instant)
    monkeypatch.setattr("ndl.fetchers.http.asyncio.sleep", _instant)


@pytest.mark.asyncio
@respx.mock
async def test_get_returns_decoded_text_with_auto_encoding(rule: SourceRule) -> None:
    respx.get("https://site.test/page").mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            text="<h1>页面</h1>",
        )
    )
    async with HttpFetcher(rule) as fetcher:
        body = await fetcher.get("https://site.test/page")

    assert body == "<h1>页面</h1>"


@pytest.mark.asyncio
@respx.mock
async def test_get_decodes_with_explicit_gbk(rule: SourceRule) -> None:
    payload = "<h1>简体中文</h1>".encode("gbk")
    respx.get("https://site.test/page").mock(return_value=httpx.Response(200, content=payload))
    async with HttpFetcher(rule) as fetcher:
        body = await fetcher.get("https://site.test/page", encoding="gbk")

    assert body == "<h1>简体中文</h1>"


@pytest.mark.asyncio
@respx.mock
async def test_get_retries_on_5xx_then_succeeds(rule: SourceRule) -> None:
    route = respx.get("https://site.test/page").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(200, text="ok"),
        ]
    )
    async with HttpFetcher(rule) as fetcher:
        body = await fetcher.get("https://site.test/page")

    assert body == "ok"
    assert route.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_get_raises_after_exhausting_retries(rule: SourceRule) -> None:
    respx.get("https://site.test/page").mock(return_value=httpx.Response(503))
    async with HttpFetcher(rule) as fetcher:
        with pytest.raises(HTTPError) as info:
            await fetcher.get("https://site.test/page")

    assert info.value.status_code == 503


@pytest.mark.asyncio
@respx.mock
async def test_get_does_not_retry_on_4xx(rule: SourceRule) -> None:
    route = respx.get("https://site.test/page").mock(return_value=httpx.Response(404))
    async with HttpFetcher(rule) as fetcher:
        with pytest.raises(HTTPError) as info:
            await fetcher.get("https://site.test/page")

    assert info.value.status_code == 404
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_get_raises_rate_limited_on_429(rule: SourceRule) -> None:
    respx.get("https://site.test/page").mock(return_value=httpx.Response(429))
    async with HttpFetcher(rule) as fetcher:
        with pytest.raises(RateLimitedError):
            await fetcher.get("https://site.test/page")


@pytest.mark.asyncio
@respx.mock
async def test_get_wraps_network_errors_into_network_error(rule: SourceRule) -> None:
    respx.get("https://site.test/page").mock(side_effect=httpx.ConnectError("boom"))
    async with HttpFetcher(rule) as fetcher:
        with pytest.raises(NetworkError):
            await fetcher.get("https://site.test/page")


@pytest.mark.asyncio
@respx.mock
async def test_get_sends_user_agent_from_rule(rule: SourceRule) -> None:
    route = respx.get("https://site.test/page").mock(return_value=httpx.Response(200, text="ok"))
    async with HttpFetcher(rule) as fetcher:
        await fetcher.get("https://site.test/page")

    assert route.calls.last.request.headers["user-agent"] == "ndl-test/1.0"


@pytest.mark.asyncio
@respx.mock
async def test_get_blocks_when_robots_disallows(tmp_path: Path) -> None:
    yaml = RULE_YAML.replace("respect: false", "respect: true").replace(
        '    ignore_justification: "test fixture"\n', ""
    )
    path = tmp_path / "rule.yaml"
    path.write_text(textwrap.dedent(yaml), encoding="utf-8")
    rule = load_rule_file(path)

    respx.get("https://site.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /\n")
    )

    async with HttpFetcher(rule) as fetcher:
        with pytest.raises(RobotsBlockedError):
            await fetcher.get("https://site.test/page")
