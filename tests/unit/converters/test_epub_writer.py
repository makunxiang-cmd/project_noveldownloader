"""Unit tests for the EPUB writer."""

from __future__ import annotations

from datetime import datetime, timezone
from zipfile import ZipFile

from ndl.converters.epub_writer import EpubWriter
from ndl.core.models import Chapter, Novel


def _novel() -> Novel:
    return Novel(
        title="测试小说",
        author="某作者",
        source_url="https://example.test/book/1",
        source_rule_id="example_static",
        fetched_at=datetime.now(timezone.utc),
        chapters=[
            Chapter(index=0, title="第一章 黎明", content="第一段。\n\n第二段。"),
            Chapter(index=1, title="第二章 夜色", content="第三段。"),
        ],
    )


def test_epub_writer_creates_expected_package_files(tmp_path) -> None:
    output_path = tmp_path / "book.epub"

    result = EpubWriter().write(_novel(), output_path)

    assert result == output_path
    with ZipFile(output_path) as archive:
        names = archive.namelist()
        assert "mimetype" in names
        assert "OEBPS/content.opf" in names
        assert "OEBPS/Text/chapter_0001.xhtml" in names
        assert "OEBPS/Text/chapter_0002.xhtml" in names

        opf = archive.read("OEBPS/content.opf").decode("utf-8")
        first_chapter = archive.read("OEBPS/Text/chapter_0001.xhtml").decode("utf-8")

    assert "测试小说" in opf
    assert "某作者" in opf
    assert "第一章 黎明" in first_chapter
    assert "第一段。" in first_chapter
