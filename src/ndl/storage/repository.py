"""LibraryRepository: persist Novels and round-trip them back to the domain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from ndl.core.models import Chapter, Novel, NovelStatus
from ndl.storage.models import ChapterRow, NovelRow


@dataclass(frozen=True)
class NovelSummary:
    """A lightweight library entry used by `list()` without chapter bodies."""

    id: int
    title: str
    author: str
    source_rule_id: str
    source_url: str | None
    status: NovelStatus
    chapter_count: int
    fetched_at: datetime
    last_updated: datetime | None


class LibraryRepository:
    """Persistence-facing role: save/list/get/remove Novels."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def save(self, novel: Novel) -> int:
        """Insert or upsert `novel` (matched on source_rule_id + source_url) and return its id."""
        with self._sessions() as session, session.begin():
            row = self._find_existing(session, novel)
            if row is None:
                row = NovelRow()
                session.add(row)
            else:
                row.chapters.clear()
                session.flush()
            self._apply_novel_to_row(novel, row)
            session.flush()
            return row.id

    def list(self) -> list[NovelSummary]:
        """Return library summaries ordered by id."""
        stmt = (
            select(NovelRow, func.count(ChapterRow.id).label("chapter_count"))
            .outerjoin(ChapterRow, ChapterRow.novel_id == NovelRow.id)
            .group_by(NovelRow.id)
            .order_by(NovelRow.id)
        )
        with self._sessions() as session:
            rows = session.execute(stmt).all()
        return [_row_to_summary(row, count) for row, count in rows]

    def get(self, novel_id: int) -> Novel | None:
        """Load the full Novel (with chapters) by id, or None if missing."""
        stmt = (
            select(NovelRow).where(NovelRow.id == novel_id).options(selectinload(NovelRow.chapters))
        )
        with self._sessions() as session:
            row = session.execute(stmt).scalar_one_or_none()
            if row is None:
                return None
            return _row_to_novel(row)

    def remove(self, novel_id: int) -> bool:
        """Delete the novel and its chapters; return True if a row was removed."""
        with self._sessions() as session, session.begin():
            row = session.get(NovelRow, novel_id)
            if row is None:
                return False
            session.delete(row)
            return True

    @staticmethod
    def _find_existing(session: Session, novel: Novel) -> NovelRow | None:
        if novel.source_url is None:
            return None
        stmt = (
            select(NovelRow)
            .where(
                NovelRow.source_rule_id == novel.source_rule_id,
                NovelRow.source_url == novel.source_url,
            )
            .options(selectinload(NovelRow.chapters))
        )
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def _apply_novel_to_row(novel: Novel, row: NovelRow) -> None:
        row.title = novel.title
        row.author = novel.author
        row.source_url = novel.source_url
        row.source_rule_id = novel.source_rule_id
        row.summary = novel.summary
        row.cover_url = novel.cover_url
        row.cover_blob = novel.cover_data
        row.tags = list(novel.tags)
        row.status = novel.status
        row.fetched_at = novel.fetched_at
        row.last_updated = novel.last_updated
        row.chapters = [_chapter_to_row(chapter, novel.fetched_at) for chapter in novel.chapters]


def _chapter_to_row(chapter: Chapter, fetched_at: datetime) -> ChapterRow:
    return ChapterRow(
        index=chapter.index,
        title=chapter.title,
        content=chapter.content,
        source_url=chapter.source_url,
        word_count=chapter.word_count,
        published_at=chapter.published_at,
        fetched_at=fetched_at,
    )


def _row_to_summary(row: NovelRow, chapter_count: int) -> NovelSummary:
    return NovelSummary(
        id=row.id,
        title=row.title,
        author=row.author,
        source_rule_id=row.source_rule_id,
        source_url=row.source_url,
        status=_coerce_status(row.status),
        chapter_count=chapter_count,
        fetched_at=row.fetched_at,
        last_updated=row.last_updated,
    )


def _row_to_novel(row: NovelRow) -> Novel:
    chapters = [
        Chapter(
            index=chapter.index,
            title=chapter.title,
            content=chapter.content,
            source_url=chapter.source_url,
            word_count=chapter.word_count,
            published_at=chapter.published_at,
        )
        for chapter in sorted(row.chapters, key=lambda c: c.index)
    ]
    return Novel(
        title=row.title,
        author=row.author,
        source_url=row.source_url,
        source_rule_id=row.source_rule_id,
        summary=row.summary,
        cover_url=row.cover_url,
        cover_data=row.cover_blob,
        tags=list(row.tags),
        status=_coerce_status(row.status),
        chapters=chapters,
        fetched_at=row.fetched_at,
        last_updated=row.last_updated,
    )


def _coerce_status(value: str) -> NovelStatus:
    if value in ("ongoing", "completed", "unknown"):
        return value  # type: ignore[return-value]
    return "unknown"
