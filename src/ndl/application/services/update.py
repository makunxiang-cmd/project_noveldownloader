"""Update service for refreshing saved ongoing novels."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from ndl.application.services._progress import emit_progress
from ndl.application.services.library import LibraryService
from ndl.core.errors import NDLError, UserError
from ndl.core.models import Chapter, ChapterStub
from ndl.core.progress import ProgressCallback
from ndl.core.protocols import Fetcher, Parser
from ndl.rules import SourceRule
from ndl.storage import NovelSummary

RuleResolver = Callable[[str], SourceRule]
FetcherFactory = Callable[[SourceRule], Fetcher]
ParserFactory = Callable[[SourceRule], Parser]
UpdateStatus = Literal["updated", "skipped", "failed"]


class _FetcherPool:
    """Borrow-and-share Fetcher per rule.id, closed all at once on aclose()."""

    def __init__(self, factory: FetcherFactory) -> None:
        self._factory = factory
        self._cache: dict[str, Fetcher] = {}

    def for_rule(self, rule: SourceRule) -> Fetcher:
        if rule.id not in self._cache:
            self._cache[rule.id] = self._factory(rule)
        return self._cache[rule.id]

    async def aclose(self) -> None:
        for fetcher in self._cache.values():
            await fetcher.aclose()
        self._cache.clear()


@dataclass(frozen=True)
class UpdateResult:
    """Outcome for one library update attempt."""

    novel_id: int
    title: str
    status: UpdateStatus
    new_chapter_count: int
    total_chapter_count: int
    message: str | None = None


class UpdateService:
    """Find and append newly published chapters for saved novels."""

    def __init__(
        self,
        *,
        library: LibraryService,
        rule_for: RuleResolver,
        fetcher_factory: FetcherFactory,
        parser_factory: ParserFactory,
        progress: ProgressCallback | None = None,
    ) -> None:
        self._library = library
        self._rule_for = rule_for
        self._fetcher_factory = fetcher_factory
        self._parser_factory = parser_factory
        self._progress = progress

    async def update_all(self) -> list[UpdateResult]:
        """Update every saved novel that can be refreshed."""
        results: list[UpdateResult] = []
        pool = _FetcherPool(self._fetcher_factory)
        try:
            for summary in self._library.list():
                if summary.status == "completed" or summary.source_url is None:
                    continue
                results.append(await self._update_summary(summary, pool))
        finally:
            await pool.aclose()
        return results

    async def _update_summary(self, summary: NovelSummary, pool: _FetcherPool) -> UpdateResult:
        try:
            return await self._update_novel_with_pool(summary.id, pool)
        except NDLError as exc:
            return UpdateResult(
                novel_id=summary.id,
                title=summary.title,
                status="failed",
                new_chapter_count=0,
                total_chapter_count=summary.chapter_count,
                message=exc.user_message(),
            )

    async def update_novel(self, novel_id: int) -> UpdateResult:
        """Refresh one saved novel by id."""
        pool = _FetcherPool(self._fetcher_factory)
        try:
            return await self._update_novel_with_pool(novel_id, pool)
        finally:
            await pool.aclose()

    async def _update_novel_with_pool(self, novel_id: int, pool: _FetcherPool) -> UpdateResult:
        novel = self._library.get(novel_id)
        if novel is None:
            raise UserError("Library entry not found.", detail=f"ID: {novel_id}")
        if novel.source_url is None:
            return UpdateResult(
                novel_id=novel_id,
                title=novel.title,
                status="skipped",
                new_chapter_count=0,
                total_chapter_count=len(novel.chapters),
                message="No source URL.",
            )
        if novel.status == "completed":
            return UpdateResult(
                novel_id=novel_id,
                title=novel.title,
                status="skipped",
                new_chapter_count=0,
                total_chapter_count=len(novel.chapters),
                message="Novel is completed.",
            )

        rule = self._rule_for(novel.source_url)
        fetcher = pool.for_rule(rule)
        parser = self._parser_factory(rule)
        await emit_progress(
            self._progress,
            kind="stage",
            stage="fetching_index",
            total=1,
            done=0,
            message=f"Checking updates: {novel.title}",
        )
        index_html = await fetcher.get(novel.source_url)
        latest, stubs = parser.parse_index(index_html, source_url=novel.source_url)
        stored_indices = {chapter.index for chapter in novel.chapters}
        new_stubs = [stub for stub in stubs if stub.index not in stored_indices]
        if not new_stubs:
            if latest.status != novel.status:
                self._library.append_chapters(
                    novel_id,
                    [],
                    updated_at=datetime.now(timezone.utc),
                    status=latest.status,
                )
            await emit_progress(
                self._progress,
                kind="done",
                stage="fetching_index",
                total=1,
                done=1,
                message=f"No new chapters: {novel.title}",
            )
            return UpdateResult(
                novel_id=novel_id,
                title=novel.title,
                status="skipped",
                new_chapter_count=0,
                total_chapter_count=len(novel.chapters),
                message="No new chapters.",
            )

        await emit_progress(
            self._progress,
            kind="stage",
            stage="fetching_chapters",
            total=len(new_stubs),
            done=0,
            message=f"Fetching {len(new_stubs)} new chapter(s).",
        )
        chapters = await self._fetch_chapters(fetcher, parser, new_stubs)
        await emit_progress(
            self._progress,
            kind="stage",
            stage="saving",
            total=len(chapters),
            done=0,
            message=f"Saving updates: {novel.title}",
        )
        appended = self._library.append_chapters(
            novel_id,
            sorted(chapters, key=lambda chapter: chapter.index),
            updated_at=datetime.now(timezone.utc),
            status=latest.status,
        )
        await emit_progress(
            self._progress,
            kind="done",
            stage="saving",
            total=len(chapters),
            done=appended,
            message=f"Update complete: {novel.title}",
        )

        return UpdateResult(
            novel_id=novel_id,
            title=novel.title,
            status="updated" if appended else "skipped",
            new_chapter_count=appended,
            total_chapter_count=len(novel.chapters) + appended,
            message=None if appended else "No new chapters.",
        )

    async def _fetch_chapters(
        self,
        fetcher: Fetcher,
        parser: Parser,
        stubs: list[ChapterStub],
    ) -> list[Chapter]:
        tasks = [asyncio.create_task(_fetch_chapter(fetcher, parser, stub)) for stub in stubs]
        chapters: list[Chapter] = []
        try:
            for coro in asyncio.as_completed(tasks):
                chapter = await coro
                chapters.append(chapter)
                await emit_progress(
                    self._progress,
                    kind="chapter",
                    stage="fetching_chapters",
                    total=len(stubs),
                    done=len(chapters),
                    current_title=chapter.title,
                )
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        return chapters


async def _fetch_chapter(fetcher: Fetcher, parser: Parser, stub: ChapterStub) -> Chapter:
    chapter_html = await fetcher.get(stub.url)
    return parser.parse_chapter(chapter_html, index=stub.index, source_url=stub.url)
