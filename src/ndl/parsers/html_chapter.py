"""Chapter page parser turning HTML into a normalized Chapter."""

from __future__ import annotations

from selectolax.parser import HTMLParser

from ndl.core.models import Chapter
from ndl.parsers._common import extract_text
from ndl.rules.schema import SourceRule
from ndl.rules.selector import clean_html_content


def parse_chapter(rule: SourceRule, html: str, *, index: int, source_url: str) -> Chapter:
    """Parse a chapter page into a Chapter with cleaned plain-text body."""
    root = HTMLParser(html)
    title = extract_text(rule.chapter.title, root, base_url=source_url)
    raw_html = extract_text(rule.chapter.content, root, base_url=source_url)
    content = clean_html_content(raw_html, rule.chapter.content.clean)
    return Chapter(index=index, title=title, content=content, source_url=source_url)
