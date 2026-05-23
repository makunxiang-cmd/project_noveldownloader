"""EPUB writer for Novel objects."""

from __future__ import annotations

import contextlib
import mimetypes
import re
from collections.abc import Callable
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, uuid5

import httpx
from ebooklib import epub

from ndl.core.errors import ConvertError
from ndl.core.models import Chapter, Novel

CoverFetcher = Callable[[str], bytes | None]

_EPUB_CSS = """
body {
  color: #1f2328;
  font-family: "Noto Serif CJK SC", "Source Han Serif SC", Georgia, serif;
  line-height: 1.85;
  margin: 0 6%;
}
.title-page {
  margin-top: 18%;
  text-align: center;
}
.title-page h1 {
  font-size: 1.8em;
  font-weight: 700;
  margin-bottom: 0.4em;
}
.title-page .author {
  color: #5c6470;
  font-size: 1em;
  margin-bottom: 2.5em;
}
.title-page .summary {
  margin: 2em auto 0;
  max-width: 36em;
  text-align: left;
}
.chapter-title {
  break-before: page;
  font-size: 1.45em;
  font-weight: 700;
  margin: 18% 0 1.2em;
  text-align: center;
}
.chapter-divider {
  color: #8a6f43;
  margin: 0 auto 2.2em;
  text-align: center;
}
.chapter-body p {
  margin: 0 0 0.85em;
  text-align: justify;
  text-indent: 2em;
}
""".strip()


class EpubWriter:
    """Write a Novel as EPUB 3."""

    def __init__(self, *, cover_fetcher: CoverFetcher | None = None) -> None:
        self._cover_fetcher = cover_fetcher

    def write(self, novel: Novel, output_path: Path) -> Path:
        """Write `novel` to `output_path` and return the path."""
        return write_epub(novel, output_path, cover_fetcher=self._cover_fetcher)


def write_epub(
    novel: Novel,
    output_path: Path,
    *,
    cover_fetcher: CoverFetcher | None = None,
) -> Path:
    """Write a Novel as EPUB 3."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    book = _build_book(novel, cover_fetcher=cover_fetcher)
    try:
        epub.write_epub(str(output_path), book, {"raise_exceptions": True})
    except Exception as exc:
        raise ConvertError(
            "Failed to write EPUB output.",
            detail=f"Path: {output_path}\n{exc}",
        ) from exc
    return output_path


def _build_book(novel: Novel, *, cover_fetcher: CoverFetcher | None) -> Any:
    book = epub.EpubBook()
    book.FOLDER_NAME = "OEBPS"
    seed = novel.source_url or f"ndl:{novel.source_rule_id}:{novel.title}"
    book.set_identifier(f"urn:uuid:{uuid5(NAMESPACE_URL, seed)}")
    book.set_title(novel.title)
    book.set_language("zh-CN")
    book.add_author(novel.author)
    if novel.summary:
        book.add_metadata("DC", "description", novel.summary)
    for tag in novel.tags:
        book.add_metadata("DC", "subject", tag)

    cover_content = _cover_content(novel, cover_fetcher)
    if cover_content:
        book.set_cover(_cover_file_name(novel, cover_content), cover_content)

    stylesheet = _stylesheet_item()
    title_page = _title_page_item(novel, stylesheet)
    chapter_items = [_chapter_item(chapter, stylesheet) for chapter in novel.chapters]
    book.add_item(stylesheet)
    book.add_item(title_page)
    for item in chapter_items:
        book.add_item(item)

    book.toc = (title_page, *chapter_items)
    book.spine = ["nav", title_page, *chapter_items]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    return book


def _stylesheet_item() -> Any:
    return epub.EpubItem(
        uid="ndl_style",
        file_name="Styles/ndl.css",
        media_type="text/css",
        content=_EPUB_CSS.encode("utf-8"),
    )


def _title_page_item(novel: Novel, stylesheet: Any) -> Any:
    item = epub.EpubHtml(
        title=novel.title,
        file_name="Text/title_page.xhtml",
        lang="zh-CN",
    )
    item.add_item(stylesheet)
    item.content = _title_page_content(novel)
    return item


def _chapter_item(chapter: Chapter, stylesheet: Any) -> Any:
    item = epub.EpubHtml(
        title=chapter.title,
        file_name=f"Text/chapter_{chapter.index + 1:04d}.xhtml",
        lang="zh-CN",
    )
    item.add_item(stylesheet)
    item.content = _chapter_content(chapter)
    return item


def _title_page_content(novel: Novel) -> str:
    summary = ""
    if novel.summary:
        paragraphs = "\n".join(_paragraph(block) for block in _paragraph_blocks(novel.summary))
        summary = f'\n<div class="summary">{paragraphs}</div>'
    return (
        '<section class="title-page">'
        f"<h1>{escape(novel.title)}</h1>"
        f'<p class="author">{escape(novel.author)}</p>'
        f"{summary}"
        "</section>"
    )


def _chapter_content(chapter: Chapter) -> str:
    paragraphs = "\n".join(_paragraph(block) for block in _paragraph_blocks(chapter.content))
    if paragraphs:
        return (
            f'<h1 class="chapter-title">{escape(chapter.title)}</h1>'
            '<div class="chapter-divider">***</div>'
            f'<section class="chapter-body">{paragraphs}</section>'
        )
    return f'<h1 class="chapter-title">{escape(chapter.title)}</h1>'


def _paragraph_blocks(content: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", content.strip()) if block.strip()]


def _paragraph(block: str) -> str:
    lines = [escape(line.strip()) for line in block.splitlines() if line.strip()]
    return f"<p>{'<br/>'.join(lines)}</p>"


def _cover_content(novel: Novel, cover_fetcher: CoverFetcher | None) -> bytes | None:
    if novel.cover_data:
        return novel.cover_data
    if not novel.cover_url:
        return None
    fetcher = cover_fetcher or _fetch_cover_bytes
    with contextlib.suppress(Exception):
        return fetcher(novel.cover_url)
    return None


def _fetch_cover_bytes(url: str) -> bytes | None:
    response = httpx.get(url, timeout=10.0, follow_redirects=True)
    if response.status_code >= 400 or not response.content:
        return None
    return response.content


def _cover_file_name(novel: Novel, content: bytes) -> str:
    suffix = _cover_suffix_from_url(novel.cover_url) or _cover_suffix_from_bytes(content)
    return f"Images/cover{suffix}"


def _cover_suffix_from_url(url: str | None) -> str | None:
    if not url:
        return None
    suffix = Path(urlparse(url).path).suffix.lower()
    media_type, _ = mimetypes.guess_type(f"cover{suffix}")
    if media_type is not None and media_type.startswith("image/"):
        return suffix
    return None


def _cover_suffix_from_bytes(content: bytes) -> str:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content.startswith(b"GIF8"):
        return ".gif"
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return ".webp"
    return ".jpg"
