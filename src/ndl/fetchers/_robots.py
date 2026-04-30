"""robots.txt fetching and access policy enforcement."""

from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from ndl.core.errors import RobotsBlockedError


class RobotsChecker:
    """Cache robots.txt per host and enforce can_fetch for the bound user agent."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        user_agent: str,
        timeout: float = 10.0,
    ) -> None:
        self._client = client
        self._user_agent = user_agent
        self._timeout = timeout
        self._cache: dict[str, RobotFileParser] = {}

    async def check(self, url: str) -> None:
        """Raise RobotsBlockedError if the URL is disallowed for our user agent."""
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._cache.get(origin)
        if parser is None:
            parser = await self._fetch_robots(origin)
            self._cache[origin] = parser
        if not parser.can_fetch(self._user_agent, url):
            raise RobotsBlockedError(
                "robots.txt disallows fetching this URL.",
                detail=f"URL: {url}\nUser-Agent: {self._user_agent}",
            )

    async def _fetch_robots(self, origin: str) -> RobotFileParser:
        parser = RobotFileParser()
        try:
            response = await self._client.get(
                f"{origin}/robots.txt",
                timeout=self._timeout,
                follow_redirects=True,
            )
        except httpx.HTTPError:
            parser.parse([])
            return parser
        if response.status_code == 200:
            parser.parse(response.text.splitlines())
        else:
            parser.parse([])
        return parser
