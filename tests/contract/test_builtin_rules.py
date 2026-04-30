"""Contract tests for bundled rules against fixed HTML fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from ndl.parsers import HtmlParser
from ndl.rules.loader import load_builtin_rules

FIXTURE_ROOT = Path(__file__).parent / "fixtures"
BASE_URL = "https://example-novels.test/book/123"


def test_example_static_rule_contract() -> None:
    rule = next(rule for rule in load_builtin_rules() if rule.id == "example_static")
    fixture_dir = FIXTURE_ROOT / rule.id
    expected = json.loads((fixture_dir / "expected.json").read_text(encoding="utf-8"))
    parser = HtmlParser(rule)

    novel, stubs = parser.parse_index(
        (fixture_dir / "index.html").read_text(encoding="utf-8"), source_url=BASE_URL
    )

    assert novel.title == expected["title"]
    assert novel.author == expected["author"]
    assert novel.summary == expected["summary"]
    assert novel.cover_url == expected["cover_url"]
    assert novel.status == expected["status"]
    assert novel.source_rule_id == rule.id
    assert [{"title": stub.title, "url": stub.url} for stub in stubs] == expected["chapters"]
    assert [stub.index for stub in stubs] == list(range(len(stubs)))

    chapter = parser.parse_chapter(
        (fixture_dir / "chapter.html").read_text(encoding="utf-8"),
        index=0,
        source_url=stubs[0].url,
    )

    assert chapter.title == expected["chapter"]["title"]
    assert chapter.content == expected["chapter"]["content"]
    assert chapter.index == 0
    assert chapter.source_url == stubs[0].url
