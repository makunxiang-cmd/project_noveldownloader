"""Unit tests for LibraryService."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ndl.application.services import LibraryService
from ndl.core.models import Chapter, Novel
from ndl.storage import (
    LibraryRepository,
    create_database_engine,
    create_session_factory,
    init_schema,
)


@pytest.fixture
def service(tmp_path: Path) -> Iterator[LibraryService]:
    engine = create_database_engine(tmp_path / "library.db")
    init_schema(engine)
    factory = create_session_factory(engine)
    yield LibraryService(LibraryRepository(factory))
    engine.dispose()


def _novel(*, source_url: str | None = "https://example.com/book/1") -> Novel:
    fetched_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    return Novel(
        title="A Library Book",
        author="Author",
        source_url=source_url,
        source_rule_id="example_static",
        chapters=[
            Chapter(index=0, title="C0", content="hello"),
            Chapter(index=1, title="C1", content="world"),
        ],
        fetched_at=fetched_at,
    )


def test_save_then_get(service: LibraryService) -> None:
    novel_id = service.save(_novel())
    loaded = service.get(novel_id)
    assert loaded is not None
    assert loaded.title == "A Library Book"
    assert [c.index for c in loaded.chapters] == [0, 1]


def test_list_returns_summaries(service: LibraryService) -> None:
    service.save(_novel(source_url="https://example.com/a"))
    service.save(_novel(source_url="https://example.com/b"))
    summaries = service.list()
    assert [s.chapter_count for s in summaries] == [2, 2]
    assert {s.source_url for s in summaries} == {
        "https://example.com/a",
        "https://example.com/b",
    }


def test_remove_clears_novel(service: LibraryService) -> None:
    novel_id = service.save(_novel())
    assert service.remove(novel_id) is True
    assert service.get(novel_id) is None
    assert service.list() == []


def test_remove_missing_returns_false(service: LibraryService) -> None:
    assert service.remove(42) is False


def test_save_is_upsert(service: LibraryService) -> None:
    first_id = service.save(_novel())
    again = _novel()
    again_id = service.save(again)
    assert again_id == first_id
    assert len(service.list()) == 1
