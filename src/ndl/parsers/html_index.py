"""Index page parser turning HTML into Novel metadata and chapter stubs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import cast, get_args

from selectolax.parser import HTMLParser

from ndl.core.errors import SelectorNotFoundError
from ndl.core.models import ChapterStub, Novel, NovelStatus
from ndl.parsers._common import extract_text
from ndl.rules.schema import Selector, SourceRule

_VALID_STATUSES: frozenset[str] = frozenset(get_args(NovelStatus))


def parse_index(rule: SourceRule, html: str, *, source_url: str) -> tuple[Novel, list[ChapterStub]]:
    """Parse an index page into Novel metadata and discovered chapter stubs."""
    root = HTMLParser(html)
    novel_meta = rule.index.novel

    title = extract_text(novel_meta.title, root, base_url=source_url)
    author = extract_text(novel_meta.author, root, base_url=source_url)
    summary = _maybe_text(novel_meta.summary, root, source_url)
    cover_url = _maybe_text(novel_meta.cover, root, source_url)
    status = _coerce_status(_maybe_text(novel_meta.status, root, source_url))

    container_selector = rule.index.chapter_list.container
    container = root.css_first(container_selector)
    if container is None:
        raise SelectorNotFoundError(container_selector)

    stubs: list[ChapterStub] = []
    for index, item in enumerate(container.css(rule.index.chapter_list.items)):
        stub_title = extract_text(rule.index.chapter_list.title, item, base_url=source_url)
        stub_url = extract_text(rule.index.chapter_list.url, item, base_url=source_url)
        stubs.append(ChapterStub(index=index, title=stub_title, url=stub_url))

    novel = Novel(
        title=title,
        author=author,
        source_url=source_url,
        source_rule_id=rule.id,
        summary=summary,
        cover_url=cover_url,
        status=status,
        fetched_at=datetime.now(timezone.utc),
    )
    return novel, stubs


def _maybe_text(selector: Selector | None, root: HTMLParser, source_url: str) -> str | None:
    if selector is None:
        return None
    return extract_text(selector, root, base_url=source_url)


def _coerce_status(value: str | None) -> NovelStatus:
    if value is None:
        return "unknown"
    if value in _VALID_STATUSES:
        return cast(NovelStatus, value)
    return "unknown"
