"""EPUB writer for Novel objects."""

from __future__ import annotations

import re
from html import escape
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from ebooklib import epub

from ndl.core.errors import ConvertError
from ndl.core.models import Chapter, Novel


class EpubWriter:
    """Write a Novel as EPUB 3."""

    def write(self, novel: Novel, output_path: Path) -> Path:
        """Write `novel` to `output_path` and return the path."""
        return write_epub(novel, output_path)


def write_epub(novel: Novel, output_path: Path) -> Path:
    """Write a Novel as EPUB 3."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    book = _build_book(novel)
    try:
        epub.write_epub(str(output_path), book, {"raise_exceptions": True})
    except Exception as exc:
        raise ConvertError(
            "Failed to write EPUB output.",
            detail=f"Path: {output_path}\n{exc}",
        ) from exc
    return output_path


def _build_book(novel: Novel) -> Any:
    book = epub.EpubBook()
    book.FOLDER_NAME = "OEBPS"
    seed = novel.source_url or f"ndl:{novel.source_rule_id}:{novel.title}"
    book.set_identifier(f"urn:uuid:{uuid5(NAMESPACE_URL, seed)}")
    book.set_title(novel.title)
    book.set_language("zh-CN")
    book.add_author(novel.author)

    chapter_items = [_chapter_item(chapter) for chapter in novel.chapters]
    for item in chapter_items:
        book.add_item(item)

    book.toc = tuple(chapter_items)
    book.spine = ["nav", *chapter_items]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    return book


def _chapter_item(chapter: Chapter) -> Any:
    item = epub.EpubHtml(
        title=chapter.title,
        file_name=f"Text/chapter_{chapter.index + 1:04d}.xhtml",
        lang="zh-CN",
    )
    item.content = _chapter_content(chapter)
    return item


def _chapter_content(chapter: Chapter) -> str:
    paragraphs = "\n".join(_paragraph(block) for block in _paragraph_blocks(chapter.content))
    if paragraphs:
        return f"<h1>{escape(chapter.title)}</h1>\n{paragraphs}"
    return f"<h1>{escape(chapter.title)}</h1>"


def _paragraph_blocks(content: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", content.strip()) if block.strip()]


def _paragraph(block: str) -> str:
    lines = [escape(line.strip()) for line in block.splitlines() if line.strip()]
    return f"<p>{'<br/>'.join(lines)}</p>"
