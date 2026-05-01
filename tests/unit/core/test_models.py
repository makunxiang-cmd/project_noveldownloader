"""Tests for core domain models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from ndl.core.models import Chapter, Novel


def test_chapter_fills_word_count_from_content() -> None:
    chapter = Chapter(index=0, title=" 第一章 ", content="第一段\n\n第二段")

    assert chapter.title == "第一章"
    assert chapter.word_count == 6


def test_novel_requires_sorted_unique_chapters() -> None:
    with pytest.raises(ValidationError, match="chapters must be sorted"):
        Novel(
            title="Example",
            author="Author",
            source_url="https://example.test/book/1",
            source_rule_id="example",
            fetched_at=datetime.now(timezone.utc),
            chapters=[
                Chapter(index=1, title="Two", content="two"),
                Chapter(index=0, title="One", content="one"),
            ],
        )


def test_novel_accepts_missing_source_url_for_local_inputs() -> None:
    novel = Novel(
        title="Example",
        author="Author",
        source_rule_id="txt",
        fetched_at=datetime.now(timezone.utc),
    )

    assert novel.source_url is None


def test_novel_rejects_invalid_cover_url() -> None:
    with pytest.raises(ValidationError):
        Novel(
            title="Example",
            author="Author",
            source_url="https://example.test/book/1",
            source_rule_id="example",
            cover_url="not-a-url",
            fetched_at=datetime.now(timezone.utc),
        )
