"""Search results page parser turning HTML into SearchResult objects."""

from __future__ import annotations

from selectolax.parser import HTMLParser

from ndl.core.errors import SelectorNotFoundError
from ndl.core.models import SearchResult
from ndl.parsers._common import extract_text
from ndl.rules.schema import SourceRule


def parse_search(rule: SourceRule, html: str, *, base_url: str) -> list[SearchResult]:
    """Parse a search results page into a list of SearchResult objects.

    ``rule.search`` must be non-None; callers are responsible for the guard.
    """
    search = rule.search
    assert search is not None  # guaranteed by SearchService

    root = HTMLParser(html)
    container = root.css_first(search.results_container)
    if container is None:
        raise SelectorNotFoundError(search.results_container)

    results: list[SearchResult] = []
    for item in container.css(search.items):
        title = extract_text(search.fields.title, item, base_url=base_url)
        author: str | None = None
        if search.fields.author is not None:
            try:
                author = extract_text(search.fields.author, item, base_url=base_url)
            except SelectorNotFoundError:
                author = None
        url = extract_text(search.fields.url, item, base_url=base_url)
        results.append(
            SearchResult(
                title=title,
                author=author,
                url=url,
                source_rule_id=rule.id,
                source_name=rule.name,
            )
        )
    return results
