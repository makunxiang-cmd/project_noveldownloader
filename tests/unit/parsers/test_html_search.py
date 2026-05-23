"""Unit tests for the search results HTML parser."""

from __future__ import annotations

import pytest

from ndl.core.errors import SelectorNotFoundError
from ndl.parsers.html_search import parse_search
from tests.rule_fixtures import load_example_static_rule

RULE = load_example_static_rule()

BASE_URL = "https://example-novels.test/search?q=test"

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

SEARCH_HTML_NO_AUTHOR = """
<html><body>
<div id="search-results">
  <div class="result-item">
    <span class="result-title">Romance of the Three Kingdoms</span>
    <a class="result-link" href="/book/3">View</a>
  </div>
</div>
</body></html>
"""

EMPTY_RESULTS_HTML = """
<html><body>
<div id="search-results">
</div>
</body></html>
"""

MISSING_CONTAINER_HTML = """
<html><body><p>No results section.</p></body></html>
"""


def test_parse_search_returns_all_items() -> None:
    results = parse_search(RULE, SEARCH_HTML, base_url=BASE_URL)
    assert len(results) == 2


def test_parse_search_extracts_fields() -> None:
    results = parse_search(RULE, SEARCH_HTML, base_url=BASE_URL)
    first = results[0]
    assert first.title == "Journey to the West"
    assert first.author == "Wu Cheng'en"
    assert first.url == "https://example-novels.test/book/1"
    assert first.source_rule_id == "example_static"
    assert first.source_name == "Public Domain Static Site Example"


def test_parse_search_second_result() -> None:
    results = parse_search(RULE, SEARCH_HTML, base_url=BASE_URL)
    second = results[1]
    assert second.title == "Dream of the Red Chamber"
    assert second.author == "Cao Xueqin"
    assert second.url == "https://example-novels.test/book/2"


def test_parse_search_missing_author_falls_back_to_none() -> None:
    results = parse_search(RULE, SEARCH_HTML_NO_AUTHOR, base_url=BASE_URL)
    assert len(results) == 1
    assert results[0].author is None
    assert results[0].title == "Romance of the Three Kingdoms"


def test_parse_search_empty_container_returns_empty_list() -> None:
    results = parse_search(RULE, EMPTY_RESULTS_HTML, base_url=BASE_URL)
    assert results == []


def test_parse_search_missing_container_raises() -> None:
    with pytest.raises(SelectorNotFoundError):
        parse_search(RULE, MISSING_CONTAINER_HTML, base_url=BASE_URL)
