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
        summary="这是一段简介。\n\n第二段简介。",
        tags=["fixture"],
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
        assert "OEBPS/Styles/ndl.css" in names
        assert "OEBPS/Text/title_page.xhtml" in names
        assert "OEBPS/Text/chapter_0001.xhtml" in names
        assert "OEBPS/Text/chapter_0002.xhtml" in names

        opf = archive.read("OEBPS/content.opf").decode("utf-8")
        css = archive.read("OEBPS/Styles/ndl.css").decode("utf-8")
        title_page = archive.read("OEBPS/Text/title_page.xhtml").decode("utf-8")
        first_chapter = archive.read("OEBPS/Text/chapter_0001.xhtml").decode("utf-8")

    assert "测试小说" in opf
    assert "某作者" in opf
    assert "这是一段简介。" in opf
    assert "fixture" in opf
    assert "text-indent: 2em" in css
    assert "title-page" in title_page
    assert "这是一段简介。" in title_page
    assert "第一章 黎明" in first_chapter
    assert "chapter-title" in first_chapter
    assert "chapter-body" in first_chapter
    assert "第一段。" in first_chapter


def test_epub_writer_embeds_cover_data(tmp_path) -> None:
    output_path = tmp_path / "book.epub"
    cover = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    novel = _novel().model_copy(
        update={
            "cover_url": "https://example.test/cover.png",
            "cover_data": cover,
        }
    )

    EpubWriter().write(novel, output_path)

    with ZipFile(output_path) as archive:
        names = archive.namelist()
        opf = archive.read("OEBPS/content.opf").decode("utf-8")

    assert "OEBPS/Images/cover.png" in names
    assert "Images/cover.png" in opf


def test_epub_writer_fetches_cover_url_when_data_missing(tmp_path) -> None:
    output_path = tmp_path / "book.epub"
    calls: list[str] = []

    def fetch_cover(url: str) -> bytes:
        calls.append(url)
        return b"\xff\xd8\xffcover"

    novel = _novel().model_copy(update={"cover_url": "https://example.test/cover.jpg"})

    EpubWriter(cover_fetcher=fetch_cover).write(novel, output_path)

    with ZipFile(output_path) as archive:
        names = archive.namelist()

    assert calls == ["https://example.test/cover.jpg"]
    assert "OEBPS/Images/cover.jpg" in names
