"""Parsers that produce Novel/Chapter domain objects."""

from __future__ import annotations

from ndl.core.models import Chapter, ChapterStub, Novel
from ndl.parsers.html_chapter import parse_chapter
from ndl.parsers.html_index import parse_index
from ndl.parsers.txt_reader import TxtReader, parse_txt, read_txt
from ndl.rules.schema import SourceRule


class HtmlParser:
    """Bind a SourceRule to the Parser Protocol so callers stay rule-agnostic."""

    def __init__(self, rule: SourceRule) -> None:
        self._rule = rule

    def parse_index(self, html: str, *, source_url: str) -> tuple[Novel, list[ChapterStub]]:
        return parse_index(self._rule, html, source_url=source_url)

    def parse_chapter(self, html: str, *, index: int, source_url: str) -> Chapter:
        return parse_chapter(self._rule, html, index=index, source_url=source_url)


__all__ = ["HtmlParser", "TxtReader", "parse_chapter", "parse_index", "parse_txt", "read_txt"]
