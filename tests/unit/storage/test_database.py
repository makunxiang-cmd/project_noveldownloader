"""Tests for the SQLite engine factory and PRAGMA defaults."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from ndl.storage import (
    ChapterRow,
    DownloadJobRow,
    NovelRow,
    SettingRow,
    create_database_engine,
    create_session_factory,
    init_schema,
    session_scope,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "library.db"


def test_init_schema_creates_all_tables(db_path: Path) -> None:
    engine = create_database_engine(db_path)
    init_schema(engine)

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {"novels", "chapters", "download_jobs", "settings"} <= tables


def test_pragmas_applied_on_file_engine(db_path: Path) -> None:
    engine = create_database_engine(db_path)
    init_schema(engine)
    with engine.connect() as conn:
        journal_mode = conn.execute(text("PRAGMA journal_mode")).scalar_one()
        foreign_keys = conn.execute(text("PRAGMA foreign_keys")).scalar_one()
    assert str(journal_mode).lower() == "wal"
    assert int(foreign_keys) == 1


def test_in_memory_engine_applies_pragmas() -> None:
    engine = create_database_engine()
    init_schema(engine)
    with engine.connect() as conn:
        foreign_keys = conn.execute(text("PRAGMA foreign_keys")).scalar_one()
    assert int(foreign_keys) == 1


def test_session_scope_persists_novel_and_chapter(db_path: Path) -> None:
    engine = create_database_engine(db_path)
    init_schema(engine)
    factory = create_session_factory(engine)

    fetched_at = datetime.now(timezone.utc)
    with session_scope(factory) as session:
        novel = NovelRow(
            title="Test Novel",
            author="Author",
            source_url="https://example.com/book",
            source_rule_id="example_static",
            tags=["a", "b"],
            status="ongoing",
            fetched_at=fetched_at,
            chapters=[
                ChapterRow(
                    index=0,
                    title="Ch 1",
                    content="hello",
                    word_count=1,
                    fetched_at=fetched_at,
                ),
                ChapterRow(
                    index=1,
                    title="Ch 2",
                    content="world",
                    word_count=1,
                    fetched_at=fetched_at,
                ),
            ],
        )
        session.add(novel)

    with session_scope(factory) as session:
        loaded = session.query(NovelRow).one()
        assert loaded.title == "Test Novel"
        assert [c.index for c in loaded.chapters] == [0, 1]
        assert loaded.tags == ["a", "b"]


def test_chapter_unique_per_novel_index(db_path: Path) -> None:
    engine = create_database_engine(db_path)
    init_schema(engine)
    factory = create_session_factory(engine)

    fetched_at = datetime.now(timezone.utc)
    session = factory()
    try:
        session.add(
            NovelRow(
                title="N",
                author="A",
                source_rule_id="example_static",
                fetched_at=fetched_at,
                chapters=[
                    ChapterRow(index=0, title="t", content="c", fetched_at=fetched_at),
                    ChapterRow(index=0, title="t2", content="c2", fetched_at=fetched_at),
                ],
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
    finally:
        session.rollback()
        session.close()


def test_chapter_cascade_delete(db_path: Path) -> None:
    engine = create_database_engine(db_path)
    init_schema(engine)
    factory = create_session_factory(engine)

    fetched_at = datetime.now(timezone.utc)
    with session_scope(factory) as session:
        session.add(
            NovelRow(
                title="N",
                author="A",
                source_rule_id="example_static",
                fetched_at=fetched_at,
                chapters=[
                    ChapterRow(index=0, title="t", content="c", fetched_at=fetched_at),
                ],
            )
        )

    with session_scope(factory) as session:
        novel = session.query(NovelRow).one()
        session.delete(novel)

    with session_scope(factory) as session:
        assert session.query(ChapterRow).count() == 0


def test_settings_kv_round_trip(db_path: Path) -> None:
    engine = create_database_engine(db_path)
    init_schema(engine)
    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        session.add(SettingRow(key="library.path", value={"path": "/tmp/x"}))

    with session_scope(factory) as session:
        row = session.get(SettingRow, "library.path")
        assert row is not None
        assert row.value == {"path": "/tmp/x"}


def test_download_job_status_check_constraint(db_path: Path) -> None:
    engine = create_database_engine(db_path)
    init_schema(engine)
    factory = create_session_factory(engine)

    started_at = datetime.now(timezone.utc)
    with session_scope(factory) as session:
        session.add(DownloadJobRow(status="running", started_at=started_at, progress={}))

    session = factory()
    try:
        session.add(DownloadJobRow(status="bogus", started_at=started_at, progress={}))
        with pytest.raises(IntegrityError):
            session.flush()
    finally:
        session.rollback()
        session.close()
