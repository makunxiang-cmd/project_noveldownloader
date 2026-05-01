"""Storage layer: SQLite engine, sessions, and ORM models."""

from __future__ import annotations

from ndl.storage.database import (
    create_database_engine,
    create_session_factory,
    init_schema,
    session_scope,
)
from ndl.storage.models import (
    Base,
    ChapterRow,
    DownloadJobRow,
    NovelRow,
    SettingRow,
)
from ndl.storage.repository import LibraryRepository, NovelSummary

__all__ = [
    "Base",
    "ChapterRow",
    "DownloadJobRow",
    "LibraryRepository",
    "NovelRow",
    "NovelSummary",
    "SettingRow",
    "create_database_engine",
    "create_session_factory",
    "init_schema",
    "session_scope",
]
