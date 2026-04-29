"""Tests for selector DSL execution."""

from __future__ import annotations

import pytest
from selectolax.parser import HTMLParser

from ndl.core.errors import EmptyContentError, SelectorNotFoundError
from ndl.rules.schema import CleanRule, Selector
from ndl.rules.selector import clean_html_content, extract_selector

HTML = """
<article>
  <h1> Example Title </h1>
  <a class="chapter" href="/chapter/1"> Chapter 1 </a>
  <span class="status">Completed</span>
  <div id="content">
    <p>First paragraph.</p>
    <p class="ad">Advertisement</p>
    <p>Second paragraph.</p>
  </div>
</article>
"""


def test_extract_selector_reads_and_maps_text() -> None:
    parser = HTMLParser(HTML)
    selector = Selector(selector=".status", map={"Completed": "completed"})

    assert extract_selector(selector, parser) == "completed"


def test_extract_selector_resolves_relative_urls() -> None:
    parser = HTMLParser(HTML)
    selector = Selector(selector=".chapter", attr="href", resolve="relative")

    assert extract_selector(selector, parser, base_url="https://example.test/book/1") == (
        "https://example.test/chapter/1"
    )


def test_extract_selector_uses_default_for_missing_node() -> None:
    parser = HTMLParser(HTML)
    selector = Selector(selector=".missing", default="fallback")

    assert extract_selector(selector, parser) == "fallback"


def test_extract_selector_raises_for_missing_required_node() -> None:
    parser = HTMLParser(HTML)

    with pytest.raises(SelectorNotFoundError):
        extract_selector(Selector(selector=".missing"), parser)


def test_clean_html_content_removes_ads_and_normalizes_paragraphs() -> None:
    content = clean_html_content(
        HTML,
        CleanRule(remove_selectors=[".ad"], min_paragraph_length=2),
    )

    assert "Advertisement" not in content
    assert (
        content
        == "Example Title\n\nChapter 1\n\nCompleted\n\nFirst paragraph.\n\nSecond paragraph."
    )


def test_clean_html_content_rejects_empty_result() -> None:
    with pytest.raises(EmptyContentError):
        clean_html_content("<div><p>x</p></div>", CleanRule(min_paragraph_length=2))
