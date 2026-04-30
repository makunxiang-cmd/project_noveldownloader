"""Unit tests for the TXT writer."""

from __future__ import annotations

from datetime import datetime, timezone

from ndl.converters.txt_writer import TxtWriter, render_txt
from ndl.core.models import Chapter, Novel


def _novel() -> Novel:
    return Novel(
        title="测试小说",
        author="某作者",
        source_url="https://example.test/book/1",
        source_rule_id="example_static",
        summary="这是一段简介。",
        fetched_at=datetime.now(timezone.utc),
        chapters=[
            Chapter(index=0, title="第一章 黎明", content="第一段。\n\n第二段。"),
            Chapter(index=1, title="第二章 夜色", content="第三段。"),
        ],
    )


def test_render_txt_includes_metadata_and_chapters() -> None:
    text = render_txt(_novel())

    assert text.startswith("# 测试小说\n作者:某作者\n")
    assert "来源:https://example.test/book/1" in text
    assert "简介:\n这是一段简介。" in text
    assert "## 第一章 黎明\n\n第一段。\n\n第二段。" in text
    assert text.endswith("\n")


def test_txt_writer_writes_utf8_file(tmp_path) -> None:
    output_path = tmp_path / "nested" / "book.txt"

    result = TxtWriter().write(_novel(), output_path)

    assert result == output_path
    assert output_path.read_text(encoding="utf-8").startswith("# 测试小说")
