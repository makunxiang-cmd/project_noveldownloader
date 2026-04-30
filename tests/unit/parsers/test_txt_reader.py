"""Unit tests for the TXT reader."""

from __future__ import annotations

import textwrap

import pytest

from ndl.core.errors import ConvertError
from ndl.parsers.txt_reader import TxtReader, parse_txt


def test_txt_reader_parses_ndl_metadata_and_markdown_chapters(tmp_path) -> None:
    path = tmp_path / "book.txt"
    path.write_text(
        textwrap.dedent(
            """
            # 测试小说
            作者:某作者
            来源:https://example.test/book/1
            规则:example_static
            状态:completed

            简介:
            这是一段简介。

            正文

            ## 第一章 黎明

            第一段。

            第二段。

            ## 第二章 夜色

            第三段。
            """
        ).strip(),
        encoding="utf-8",
    )

    novel = TxtReader().read(path)

    assert novel.title == "测试小说"
    assert novel.author == "某作者"
    assert novel.source_url == "https://example.test/book/1"
    assert novel.source_rule_id == "example_static"
    assert novel.summary == "这是一段简介。"
    assert [chapter.title for chapter in novel.chapters] == ["第一章 黎明", "第二章 夜色"]
    assert novel.chapters[0].content == "第一段。\n\n第二段。"


def test_parse_txt_recognizes_common_chapter_heading_variants(tmp_path) -> None:
    text = textwrap.dedent(
        """
        测试小说

        序章

        开头。

        第十二章 风起

        正文。

        Chapter 3 Return

        English body.
        """
    )

    novel = parse_txt(text, source_path=tmp_path / "book.txt")

    assert novel.title == "测试小说"
    assert [chapter.title for chapter in novel.chapters] == [
        "序章",
        "第十二章 风起",
        "Chapter 3 Return",
    ]
    assert novel.source_url == "https://local.ndl.invalid/txt/book.txt"


def test_parse_txt_falls_back_to_single_chapter_without_headings(tmp_path) -> None:
    novel = parse_txt("无标题文本\n\n第一段。\n第二段。", source_path=tmp_path / "loose.txt")

    assert novel.title == "无标题文本"
    assert len(novel.chapters) == 1
    assert novel.chapters[0].title == "无标题文本"
    assert novel.chapters[0].content == "第一段。\n第二段。"


def test_parse_txt_rejects_empty_input(tmp_path) -> None:
    with pytest.raises(ConvertError, match="TXT input is empty"):
        parse_txt(" \n\n ", source_path=tmp_path / "empty.txt")
