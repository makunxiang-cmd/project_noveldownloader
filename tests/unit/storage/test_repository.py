"""Tests for LibraryRepository round-trip and lifecycle behavior."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from ndl.core.models import Chapter, Novel
from ndl.storage import (
    ChapterRow,
    LibraryRepository,
    NovelRow,
    create_database_engine,
    create_session_factory,
    init_schema,
)


@pytest.fixture
def session_factory(tmp_path: Path) -> Iterator[sessionmaker[Session]]:
    engine = create_database_engine(tmp_path / "library.db")
    init_schema(engine)
    yield create_session_factory(engine)
    engine.dispose()


@pytest.fixture
def repo(session_factory: sessionmaker[Session]) -> LibraryRepository:
    return LibraryRepository(session_factory)


def _make_novel(
    *,
    title: str = "Test Novel",
    author: str = "Author A",
    source_url: str | None = "https://example.com/book/1",
    chapter_count: int = 3,
) -> Novel:
    fetched_at = datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
    chapters = [
        Chapter(index=i, title=f"Chapter {i + 1}", content=f"content of {i + 1}")
        for i in range(chapter_count)
    ]
    return Novel(
        title=title,
        author=author,
        source_url=source_url,
        source_rule_id="example_static",
        summary="A test summary",
        tags=["tag-a", "tag-b"],
        status="ongoing",
        chapters=chapters,
        fetched_at=fetched_at,
    )


def test_save_then_get_round_trips_novel(repo: LibraryRepository) -> None:
    novel = _make_novel()
    novel_id = repo.save(novel)

    loaded = repo.get(novel_id)
    assert loaded is not None
    assert loaded.title == novel.title
    assert loaded.author == novel.author
    assert loaded.source_url == novel.source_url
    assert loaded.source_rule_id == novel.source_rule_id
    assert loaded.summary == novel.summary
    assert loaded.tags == novel.tags
    assert loaded.status == novel.status
    assert [c.index for c in loaded.chapters] == [0, 1, 2]
    assert [c.title for c in loaded.chapters] == ["Chapter 1", "Chapter 2", "Chapter 3"]
    assert [c.content for c in loaded.chapters] == ["content of 1", "content of 2", "content of 3"]


def test_save_is_upsert_on_rule_and_url(
    repo: LibraryRepository, session_factory: sessionmaker[Session]
) -> None:
    first = _make_novel(chapter_count=2)
    first_id = repo.save(first)

    updated = _make_novel(title="Renamed", chapter_count=4)
    second_id = repo.save(updated)

    assert second_id == first_id

    loaded = repo.get(first_id)
    assert loaded is not None
    assert loaded.title == "Renamed"
    assert len(loaded.chapters) == 4

    with session_factory() as session:
        assert session.query(NovelRow).count() == 1
        assert session.query(ChapterRow).count() == 4


def test_save_without_source_url_always_inserts(repo: LibraryRepository) -> None:
    a = _make_novel(source_url=None, title="Local A")
    b = _make_novel(source_url=None, title="Local B")
    a_id = repo.save(a)
    b_id = repo.save(b)
    assert a_id != b_id
    a_loaded = repo.get(a_id)
    b_loaded = repo.get(b_id)
    assert a_loaded is not None
    assert b_loaded is not None
    assert {a_loaded.title, b_loaded.title} == {"Local A", "Local B"}


def test_list_returns_summaries_with_chapter_count(repo: LibraryRepository) -> None:
    repo.save(_make_novel(title="A", source_url="https://example.com/a", chapter_count=2))
    repo.save(_make_novel(title="B", source_url="https://example.com/b", chapter_count=5))

    summaries = repo.list()
    assert [s.title for s in summaries] == ["A", "B"]
    assert [s.chapter_count for s in summaries] == [2, 5]
    assert all(s.id > 0 for s in summaries)


def test_list_includes_novels_without_chapters(repo: LibraryRepository) -> None:
    novel = _make_novel(chapter_count=0)
    repo.save(novel)
    summaries = repo.list()
    assert len(summaries) == 1
    assert summaries[0].chapter_count == 0


def test_append_chapters_updates_status_timestamp_without_new_chapters(
    repo: LibraryRepository,
) -> None:
    novel_id = repo.save(_make_novel())
    updated_at = datetime(2026, 5, 2, 10, 0, tzinfo=timezone.utc)

    inserted = repo.append_chapters(
        novel_id,
        [],
        updated_at=updated_at,
        status="completed",
    )

    loaded = repo.get(novel_id)
    assert inserted == 0
    assert loaded is not None
    assert loaded.status == "completed"
    assert loaded.last_updated == updated_at.replace(tzinfo=None)


def test_get_missing_returns_none(repo: LibraryRepository) -> None:
    assert repo.get(999) is None


def test_remove_deletes_novel_and_chapters(
    repo: LibraryRepository, session_factory: sessionmaker[Session]
) -> None:
    novel_id = repo.save(_make_novel(chapter_count=3))
    assert repo.remove(novel_id) is True
    assert repo.get(novel_id) is None
    with session_factory() as session:
        assert session.query(NovelRow).count() == 0
        assert session.query(ChapterRow).count() == 0


def test_remove_missing_returns_false(repo: LibraryRepository) -> None:
    assert repo.remove(999) is False


def test_chapters_loaded_in_index_order(repo: LibraryRepository) -> None:
    fetched_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    novel = Novel(
        title="Ordered",
        author="A",
        source_url="https://example.com/o",
        source_rule_id="example_static",
        chapters=[
            Chapter(index=0, title="C0", content="x"),
            Chapter(index=1, title="C1", content="y"),
            Chapter(index=2, title="C2", content="z"),
        ],
        fetched_at=fetched_at,
    )
    novel_id = repo.save(novel)
    loaded = repo.get(novel_id)
    assert loaded is not None
    assert [c.index for c in loaded.chapters] == [0, 1, 2]
