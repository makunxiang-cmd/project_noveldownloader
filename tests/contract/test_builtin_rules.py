"""Contract tests for bundled rules against fixed HTML fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from selectolax.parser import HTMLParser

from ndl.rules.loader import load_builtin_rules
from ndl.rules.schema import ContentSelector, Selector
from ndl.rules.selector import clean_html_content, extract_selector

FIXTURE_ROOT = Path(__file__).parent / "fixtures"
BASE_URL = "https://example-novels.test/book/123"


def test_example_static_rule_contract() -> None:
    rule = next(rule for rule in load_builtin_rules() if rule.id == "example_static")
    fixture_dir = FIXTURE_ROOT / rule.id
    expected = json.loads((fixture_dir / "expected.json").read_text(encoding="utf-8"))

    index = HTMLParser((fixture_dir / "index.html").read_text(encoding="utf-8"))
    chapter = HTMLParser((fixture_dir / "chapter.html").read_text(encoding="utf-8"))

    assert extract_selector(rule.index.novel.title, index) == expected["title"]
    assert extract_selector(rule.index.novel.author, index) == expected["author"]
    assert _extract_optional(rule.index.novel.summary, index) == expected["summary"]
    assert (
        _extract_optional(rule.index.novel.cover, index, base_url=BASE_URL) == expected["cover_url"]
    )
    assert _extract_optional(rule.index.novel.status, index) == expected["status"]

    container = index.css_first(rule.index.chapter_list.container)
    assert container is not None
    chapter_items = container.css(rule.index.chapter_list.items)
    chapters = [
        {
            "title": extract_selector(rule.index.chapter_list.title, item),
            "url": extract_selector(rule.index.chapter_list.url, item, base_url=BASE_URL),
        }
        for item in chapter_items
    ]
    assert chapters == expected["chapters"]

    chapter_title = extract_selector(rule.chapter.title, chapter)
    chapter_html = extract_selector(rule.chapter.content, chapter)
    assert isinstance(chapter_html, str)
    chapter_content = clean_html_content(chapter_html, rule.chapter.content.clean)

    assert chapter_title == expected["chapter"]["title"]
    assert chapter_content == expected["chapter"]["content"]


def _extract_optional(
    selector: Selector | ContentSelector | None,
    root: HTMLParser,
    *,
    base_url: str | None = None,
) -> str | list[str] | None:
    if selector is None:
        return None
    return extract_selector(selector, root, base_url=base_url)
