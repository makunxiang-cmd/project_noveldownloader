"""Unit tests for the convert service."""

from __future__ import annotations

from datetime import datetime, timezone
from zipfile import ZipFile

import pytest

from ndl.application.services import ConvertService
from ndl.core.errors import ConvertError
from ndl.core.models import Chapter, Novel
from ndl.core.progress import ProgressEvent


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


@pytest.mark.asyncio
async def test_convert_service_writes_novel_to_txt_with_progress(tmp_path) -> None:
    events: list[ProgressEvent] = []

    async def progress(event: ProgressEvent) -> None:
        events.append(event)

    output_path = tmp_path / "book.txt"
    result = await ConvertService(progress=progress).convert(_novel(), output_path)

    assert result == output_path
    assert "## 第一章 黎明" in output_path.read_text(encoding="utf-8")
    assert [event.stage for event in events] == ["converting", "converting", "saving", "saving"]
    assert events[-1].kind == "done"


@pytest.mark.asyncio
async def test_convert_service_reads_txt_and_writes_epub(tmp_path) -> None:
    input_path = tmp_path / "book.txt"
    input_path.write_text(
        "# 测试小说\n作者:某作者\n来源:https://example.test/book/1\n\n## 第一章 黎明\n\n第一段。",
        encoding="utf-8",
    )
    output_path = tmp_path / "book.epub"

    result = await ConvertService().convert(input_path, output_path)

    assert result == output_path
    with ZipFile(output_path) as archive:
        assert "OEBPS/content.opf" in archive.namelist()
        assert "OEBPS/Text/chapter_0001.xhtml" in archive.namelist()
        assert "测试小说" in archive.read("OEBPS/content.opf").decode("utf-8")


@pytest.mark.asyncio
async def test_convert_service_rejects_unsupported_input_format(tmp_path) -> None:
    with pytest.raises(ConvertError, match="Unsupported input format"):
        await ConvertService().convert(tmp_path / "book.md", tmp_path / "book.txt")
