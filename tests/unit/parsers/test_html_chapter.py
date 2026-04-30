"""Unit tests for the chapter page parser."""

from __future__ import annotations

import textwrap

import pytest

from ndl.core.errors import EmptyContentError
from ndl.parsers.html_chapter import parse_chapter
from ndl.rules.loader import load_rule_file
from ndl.rules.schema import SourceRule

CHAPTER_HTML = """
<!doctype html>
<html><body>
  <h1 class="title">  第一章: 黎明  </h1>
  <article id="body">
    <p>第一段。</p>
    <p class="ad">广告 ad block</p>
    <p>第二段。</p>
  </article>
</body></html>
"""

RULE_YAML = """
id: chapter_test
name: Chapter Test
version: 1.0.0
author: Tests
url_patterns:
  - pattern: "https://t.test/*"
    type: glob
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
  title: { selector: "h1.title" }
  content:
    selector: "#body"
    attr: html
    clean:
      remove_selectors: [".ad"]
      min_paragraph_length: 2
"""


def _rule(tmp_path) -> SourceRule:
    path = tmp_path / "rule.yaml"
    path.write_text(textwrap.dedent(RULE_YAML), encoding="utf-8")
    return load_rule_file(path)


def test_parse_chapter_returns_clean_chapter_with_passed_index(tmp_path) -> None:
    rule = _rule(tmp_path)

    chapter = parse_chapter(rule, CHAPTER_HTML, index=4, source_url="https://t.test/book/1/c/5")

    assert chapter.index == 4
    assert chapter.title == "第一章: 黎明"
    assert "广告" not in chapter.content
    assert chapter.content == "第一段。\n\n第二段。"
    assert chapter.source_url == "https://t.test/book/1/c/5"
    assert chapter.word_count > 0


def test_parse_chapter_propagates_empty_content_error(tmp_path) -> None:
    rule = _rule(tmp_path)
    html = CHAPTER_HTML.replace("第一段。", "").replace("第二段。", "")

    with pytest.raises(EmptyContentError):
        parse_chapter(rule, html, index=0, source_url="https://t.test/book/1/c/1")
