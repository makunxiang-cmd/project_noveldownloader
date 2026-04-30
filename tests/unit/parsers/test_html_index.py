"""Unit tests for the index page parser."""

from __future__ import annotations

import textwrap

import pytest

from ndl.core.errors import SelectorNotFoundError
from ndl.parsers.html_index import parse_index
from ndl.rules.loader import load_rule_file
from ndl.rules.schema import SourceRule

INDEX_HTML = """
<!doctype html>
<html><body>
  <h1 class="book-title"> 测试小说 </h1>
  <span class="author">某作者</span>
  <span class="status">Ongoing</span>
  <ol id="chapters">
    <li><a href="/book/1/c/1">第一章</a></li>
    <li><a href="/book/1/c/2">第二章</a></li>
  </ol>
</body></html>
"""

RULE_YAML = """
id: index_test
name: Index Test
version: 1.0.0
author: Tests
url_patterns:
  - pattern: "https://t.test/*"
    type: glob
index:
  novel:
    title: { selector: "h1.book-title" }
    author: { selector: ".author" }
    status:
      selector: ".status"
      map:
        Ongoing: ongoing
        Completed: completed
  chapter_list:
    container: "#chapters"
    items: "li > a"
    title: { selector: "self" }
    url: { selector: "self", attr: "href", resolve: "relative" }
chapter:
  title: { selector: "h1" }
  content: { selector: "#content", attr: "html" }
"""


def _rule(tmp_path, body: str = RULE_YAML) -> SourceRule:
    path = tmp_path / "rule.yaml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return load_rule_file(path)


def test_parse_index_returns_metadata_and_zero_based_stubs(tmp_path) -> None:
    rule = _rule(tmp_path)

    novel, stubs = parse_index(rule, INDEX_HTML, source_url="https://t.test/book/1")

    assert novel.title == "测试小说"
    assert novel.author == "某作者"
    assert novel.status == "ongoing"
    assert novel.source_rule_id == rule.id
    assert novel.summary is None
    assert novel.cover_url is None
    assert [stub.index for stub in stubs] == [0, 1]
    assert stubs[0].title == "第一章"
    assert stubs[1].url == "https://t.test/book/1/c/2"


def test_parse_index_falls_back_to_unknown_for_unmapped_status(tmp_path) -> None:
    rule = _rule(tmp_path)
    html = INDEX_HTML.replace(">Ongoing<", ">Frozen<")

    novel, _ = parse_index(rule, html, source_url="https://t.test/book/1")

    assert novel.status == "unknown"


def test_parse_index_raises_when_chapter_container_missing(tmp_path) -> None:
    rule = _rule(tmp_path)
    html = INDEX_HTML.replace('id="chapters"', 'id="other"')

    with pytest.raises(SelectorNotFoundError):
        parse_index(rule, html, source_url="https://t.test/book/1")


RULE_YAML_NO_STATUS = """
id: index_test
name: Index Test
version: 1.0.0
author: Tests
url_patterns:
  - pattern: "https://t.test/*"
    type: glob
index:
  novel:
    title: { selector: "h1.book-title" }
    author: { selector: ".author" }
  chapter_list:
    container: "#chapters"
    items: "li > a"
    title: { selector: "self" }
    url: { selector: "self", attr: "href", resolve: "relative" }
chapter:
  title: { selector: "h1" }
  content: { selector: "#content", attr: "html" }
"""


def test_parse_index_status_unknown_when_selector_missing_from_rule(tmp_path) -> None:
    rule = _rule(tmp_path, body=RULE_YAML_NO_STATUS)

    novel, _ = parse_index(rule, INDEX_HTML, source_url="https://t.test/book/1")

    assert novel.status == "unknown"
