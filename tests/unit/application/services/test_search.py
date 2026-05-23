"""Unit tests for the search service."""

from __future__ import annotations

import asyncio

import pytest

from ndl.application.container import ServiceContainer
from ndl.application.services.search import SearchService
from ndl.core.errors import NetworkError
from ndl.rules.loader import load_builtin_rules
from ndl.rules.schema import SourceRule

SEARCH_HTML = """
<html><body>
<div id="search-results">
  <div class="result-item">
    <span class="result-title">Journey to the West</span>
    <span class="result-author">Wu Cheng'en</span>
    <a class="result-link" href="/book/1">View</a>
  </div>
  <div class="result-item">
    <span class="result-title">Dream of the Red Chamber</span>
    <span class="result-author">Cao Xueqin</span>
    <a class="result-link" href="/book/2">View</a>
  </div>
</div>
</body></html>
"""

EMPTY_HTML = """
<html><body>
<div id="search-results"></div>
</body></html>
"""


class FakeFetcher:
    def __init__(self, body: str) -> None:
        self.requests: list[str] = []
        self.post_requests: list[tuple[str, dict[str, str]]] = []
        self._body = body

    async def get(self, url: str, *, encoding: str | None = None) -> str:
        await asyncio.sleep(0)
        self.requests.append(url)
        return self._body

    async def post(
        self,
        url: str,
        *,
        data: dict[str, str],
        encoding: str | None = None,
    ) -> str:
        await asyncio.sleep(0)
        self.post_requests.append((url, data))
        return self._body

    async def aclose(self) -> None:
        pass


class FakeBrowserSearchFetcher:
    def __init__(self, body: str, *, final_url: str) -> None:
        self.searches: list[tuple[str, str, str]] = []
        self._body = body
        self._final_url = final_url
        self.closed = False

    async def get(self, url: str, *, encoding: str | None = None) -> str:
        raise AssertionError(f"browser search should not call get({url})")

    async def get_search_html(self, search: object, keyword: str) -> tuple[str, str]:
        self.searches.append(
            (
                getattr(search, "navigate_url", ""),
                getattr(search, "input_selector", ""),
                keyword,
            )
        )
        return self._body, self._final_url

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_search_returns_results_from_rule_with_search() -> None:
    rule = next(r for r in load_builtin_rules() if r.id == "example_static")
    fetcher = FakeFetcher(SEARCH_HTML)
    service = SearchService(rules=[rule], fetcher_factory=lambda _r: fetcher)

    outcome = await service.search("west")

    assert len(outcome.results) == 2
    assert outcome.results[0].title == "Journey to the West"
    assert outcome.results[1].title == "Dream of the Red Chamber"
    assert outcome.failures == []


@pytest.mark.asyncio
async def test_search_url_encodes_keyword() -> None:
    rule = next(r for r in load_builtin_rules() if r.id == "example_static")
    fetcher = FakeFetcher(EMPTY_HTML)
    service = SearchService(rules=[rule], fetcher_factory=lambda _r: fetcher)

    await service.search("red chamber")

    assert fetcher.requests == ["https://example-novels.test/search?q=red+chamber"]


@pytest.mark.asyncio
async def test_search_posts_form_body_with_raw_keyword() -> None:
    rule = _post_search_rule()
    fetcher = FakeFetcher(SEARCH_HTML)
    service = SearchService(rules=[rule], fetcher_factory=lambda _r: fetcher)

    outcome = await service.search("red chamber")

    assert len(outcome.results) == 2
    assert fetcher.requests == []
    assert fetcher.post_requests == [
        ("https://example-novels.test/search.html", {"s": "red chamber"})
    ]


@pytest.mark.asyncio
async def test_search_uses_browser_search_flow() -> None:
    rule = _browser_search_rule()
    fetcher = FakeBrowserSearchFetcher(
        SEARCH_HTML,
        final_url="https://example-novels.test/results?q=west",
    )
    service = SearchService(rules=[rule], fetcher_factory=lambda _r: fetcher)

    outcome = await service.search("west")

    assert len(outcome.results) == 2
    assert outcome.results[0].url == "https://example-novels.test/book/1"
    assert fetcher.searches == [("https://example-novels.test/", "input[name='searchkey']", "west")]
    assert fetcher.closed is True


@pytest.mark.asyncio
async def test_search_skips_rules_without_search_block() -> None:
    rule = next(r for r in load_builtin_rules() if r.id == "example_static")
    rule_no_search = rule.model_copy(update={"id": "no_search", "search": None})
    fetcher = FakeFetcher(SEARCH_HTML)
    calls: list[str] = []

    def factory(_r: object) -> FakeFetcher:
        calls.append(getattr(_r, "id", ""))
        return fetcher

    service = SearchService(rules=[rule_no_search], fetcher_factory=factory)
    outcome = await service.search("anything")

    assert outcome.results == []
    assert outcome.failures == []
    assert calls == []


@pytest.mark.asyncio
async def test_search_filters_by_rule_ids() -> None:
    rule = next(r for r in load_builtin_rules() if r.id == "example_static")
    fetcher = FakeFetcher(EMPTY_HTML)
    service = SearchService(rules=[rule], fetcher_factory=lambda _r: fetcher)

    outcome = await service.search("west", rule_ids=["other_rule"])

    assert outcome.results == []
    assert outcome.failures == []
    assert fetcher.requests == []


@pytest.mark.asyncio
async def test_search_returns_empty_list_when_no_results() -> None:
    rule = next(r for r in load_builtin_rules() if r.id == "example_static")
    fetcher = FakeFetcher(EMPTY_HTML)
    service = SearchService(rules=[rule], fetcher_factory=lambda _r: fetcher)

    outcome = await service.search("nothing")

    assert outcome.results == []
    assert outcome.failures == []


@pytest.mark.asyncio
async def test_search_deduplicates_results_by_rule_and_url() -> None:
    rule = next(r for r in load_builtin_rules() if r.id == "example_static")
    duplicate_html = SEARCH_HTML.replace('/book/2">View', '/book/1">View')
    fetcher = FakeFetcher(duplicate_html)
    service = SearchService(rules=[rule], fetcher_factory=lambda _r: fetcher)

    outcome = await service.search("west")

    assert [result.url for result in outcome.results] == ["https://example-novels.test/book/1"]


@pytest.mark.asyncio
async def test_search_service_via_container() -> None:
    rule = next(r for r in load_builtin_rules() if r.id == "example_static")
    fetcher = FakeFetcher(SEARCH_HTML)
    container = ServiceContainer(
        rules=[rule],
        fetcher_factory=lambda _r: fetcher,
    )

    service = container.search_service()
    outcome = await service.search("west")

    assert len(outcome.results) == 2
    assert all(r.source_rule_id == "example_static" for r in outcome.results)


class FailingFetcher:
    """Fetcher that raises NDLError on every call."""

    async def get(self, url: str, *, encoding: str | None = None) -> str:
        raise NetworkError("Simulated network failure.", detail=f"URL: {url}")

    async def aclose(self) -> None:
        pass


@pytest.mark.asyncio
async def test_search_collects_failures_without_dropping_successes() -> None:
    base_rule = next(r for r in load_builtin_rules() if r.id == "example_static")
    failing_rule = base_rule.model_copy(update={"id": "broken_rule"})
    ok_fetcher = FakeFetcher(SEARCH_HTML)
    fail_fetcher = FailingFetcher()

    def factory(rule: object) -> object:
        rid = getattr(rule, "id", "")
        return fail_fetcher if rid == "broken_rule" else ok_fetcher

    service = SearchService(rules=[failing_rule, base_rule], fetcher_factory=factory)
    outcome = await service.search("west")

    assert len(outcome.results) == 2
    assert len(outcome.failures) == 1
    assert outcome.failures[0].rule_id == "broken_rule"
    assert "Simulated network failure." in outcome.failures[0].message


@pytest.mark.asyncio
async def test_search_returns_only_failures_when_all_sources_fail() -> None:
    base_rule = next(r for r in load_builtin_rules() if r.id == "example_static")
    service = SearchService(rules=[base_rule], fetcher_factory=lambda _r: FailingFetcher())

    outcome = await service.search("west")

    assert outcome.results == []
    assert [failure.rule_id for failure in outcome.failures] == ["example_static"]


def _post_search_rule() -> SourceRule:
    base = next(r for r in load_builtin_rules() if r.id == "example_static")
    data = base.model_dump(mode="json")
    data["search"] = {
        "method": "POST",
        "url_template": "https://example-novels.test/search.html",
        "body": {"s": "{keyword}"},
        "results_container": "#search-results",
        "items": ".result-item",
        "fields": {
            "title": {"selector": ".result-title"},
            "author": {"selector": ".result-author"},
            "url": {"selector": ".result-link", "attr": "href", "resolve": "relative"},
        },
    }
    return SourceRule.model_validate(data)


def _browser_search_rule() -> SourceRule:
    base = next(r for r in load_builtin_rules() if r.id == "example_static")
    data = base.model_dump(mode="json")
    fetcher = data["fetcher"]
    assert isinstance(fetcher, dict)
    fetcher["type"] = "browser"
    data["search"] = {
        "url_template": "https://example-novels.test/",
        "browser": {
            "navigate_url": "https://example-novels.test/",
            "input_selector": "input[name='searchkey']",
            "submit_selector": ".btn-tosearch",
            "wait_for_selector": "#search-results",
        },
        "results_container": "#search-results",
        "items": ".result-item",
        "fields": {
            "title": {"selector": ".result-title"},
            "author": {"selector": ".result-author"},
            "url": {"selector": ".result-link", "attr": "href", "resolve": "relative"},
        },
    }
    return SourceRule.model_validate(data)
