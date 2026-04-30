"""Unit tests for the robots.txt checker."""

from __future__ import annotations

import httpx
import pytest
import respx

from ndl.core.errors import RobotsBlockedError
from ndl.fetchers._robots import RobotsChecker


@pytest.mark.asyncio
@respx.mock
async def test_robots_allows_when_can_fetch_returns_true() -> None:
    respx.get("https://site.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /\n")
    )
    async with httpx.AsyncClient() as client:
        checker = RobotsChecker(client=client, user_agent="ndl-test")
        await checker.check("https://site.test/page")


@pytest.mark.asyncio
@respx.mock
async def test_robots_raises_when_disallowed() -> None:
    respx.get("https://site.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
    )
    async with httpx.AsyncClient() as client:
        checker = RobotsChecker(client=client, user_agent="ndl-test")
        with pytest.raises(RobotsBlockedError):
            await checker.check("https://site.test/private/page")


@pytest.mark.asyncio
@respx.mock
async def test_robots_treats_404_as_allow_all() -> None:
    respx.get("https://site.test/robots.txt").mock(return_value=httpx.Response(404))
    async with httpx.AsyncClient() as client:
        checker = RobotsChecker(client=client, user_agent="ndl-test")
        await checker.check("https://site.test/anything")


@pytest.mark.asyncio
@respx.mock
async def test_robots_treats_network_error_as_allow_all() -> None:
    respx.get("https://site.test/robots.txt").mock(side_effect=httpx.ConnectError("boom"))
    async with httpx.AsyncClient() as client:
        checker = RobotsChecker(client=client, user_agent="ndl-test")
        await checker.check("https://site.test/anything")


@pytest.mark.asyncio
@respx.mock
async def test_robots_caches_per_host() -> None:
    route = respx.get("https://site.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /\n")
    )
    async with httpx.AsyncClient() as client:
        checker = RobotsChecker(client=client, user_agent="ndl-test")
        await checker.check("https://site.test/a")
        await checker.check("https://site.test/b")

    assert route.call_count == 1
