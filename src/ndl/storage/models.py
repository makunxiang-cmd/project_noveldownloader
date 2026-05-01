"""SQLAlchemy 2.0 ORM mappings for the NDL local library."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NOVEL_STATUSES = ("ongoing", "completed", "unknown")
JOB_STATUSES = ("running", "succeeded", "incomplete", "failed")


class Base(DeclarativeBase):
    """Base class for NDL ORM models."""


class NovelRow(Base):
    """A persisted Novel header row."""

    __tablename__ = "novels"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ongoing', 'completed', 'unknown')",
            name="ck_novels_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    author: Mapped[str] = mapped_column(String(256), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    cover_blob: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    chapters: Mapped[list[ChapterRow]] = relationship(
        back_populates="novel",
        cascade="all, delete-orphan",
        order_by="ChapterRow.index",
    )
    jobs: Mapped[list[DownloadJobRow]] = relationship(
        back_populates="novel",
        cascade="all, delete-orphan",
    )


class ChapterRow(Base):
    """A persisted Chapter row, ordered within its parent novel."""

    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("novel_id", "index", name="uq_chapters_novel_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    novel_id: Mapped[int] = mapped_column(
        ForeignKey("novels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    index: Mapped[int] = mapped_column("index", Integer, nullable=False, quote=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    novel: Mapped[NovelRow] = relationship(back_populates="chapters")


class DownloadJobRow(Base):
    """A persisted download job for retry/resume bookkeeping."""

    __tablename__ = "download_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'incomplete', 'failed')",
            name="ck_download_jobs_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    novel_id: Mapped[int | None] = mapped_column(
        ForeignKey("novels.id", ondelete="CASCADE"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    novel: Mapped[NovelRow | None] = relationship(back_populates="jobs")


class SettingRow(Base):
    """A generic key/value settings row stored as JSON."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
