"""Search service that queries rule-defined search endpoints."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from ndl.core.errors import NDLError
from ndl.core.models import SearchResult
from ndl.core.protocols import Fetcher
from ndl.parsers.html_search import parse_search
from ndl.rules.schema import SourceRule

FetcherFactory = Callable[[SourceRule], Fetcher]

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchFailure:
    """A single rule's failure during a multi-source search."""

    rule_id: str
    source_name: str
    message: str


@dataclass(frozen=True)
class SearchOutcome:
    """Aggregated outcome of one multi-source search call."""

    results: list[SearchResult] = field(default_factory=list)
    failures: list[SearchFailure] = field(default_factory=list)


class SearchService:
    """Search across all rules that declare a search endpoint."""

    def __init__(
        self,
        *,
        rules: list[SourceRule],
        fetcher_factory: FetcherFactory,
    ) -> None:
        self._rules = rules
        self._fetcher_factory = fetcher_factory

    async def search(
        self,
        keyword: str,
        *,
        rule_ids: list[str] | None = None,
    ) -> SearchOutcome:
        """Return aggregated results plus per-source failures from a multi-rule search."""
        candidates = [
            rule
            for rule in self._rules
            if rule.enabled
            and rule.search is not None
            and (rule_ids is None or rule.id in rule_ids)
        ]
        tasks = [asyncio.create_task(self._search_one_safely(rule, keyword)) for rule in candidates]
        results: list[SearchResult] = []
        failures: list[SearchFailure] = []
        try:
            gathered = await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        for rule_results, rule_failure in gathered:
            results.extend(rule_results)
            if rule_failure is not None:
                failures.append(rule_failure)
        return SearchOutcome(results=results, failures=failures)

    async def _search_one_safely(
        self,
        rule: SourceRule,
        keyword: str,
    ) -> tuple[list[SearchResult], SearchFailure | None]:
        try:
            return await self._search_one(rule, keyword), None
        except NDLError as exc:
            _log.warning("search failed for rule %s: %s", rule.id, exc.user_message())
            return [], SearchFailure(
                rule_id=rule.id,
                source_name=rule.name,
                message=exc.user_message(),
            )

    async def _search_one(self, rule: SourceRule, keyword: str) -> list[SearchResult]:
        assert rule.search is not None
        search_url = rule.search.url_template.format(keyword=quote_plus(keyword))
        fetcher = self._fetcher_factory(rule)
        try:
            html = await fetcher.get(search_url)
        finally:
            await fetcher.aclose()
        return parse_search(rule, html, base_url=search_url)
