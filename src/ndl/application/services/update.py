"""Update service for refreshing saved ongoing novels."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from ndl.application.services._progress import emit_progress
from ndl.application.services.download import DownloadService
from ndl.application.services.library import LibraryService
from ndl.core.errors import NDLError, UserError
from ndl.core.models import Chapter
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
        downloader = DownloadService(
            fetcher=fetcher,
            parser=parser,
            rule=rule,
            progress=self._progress,
        )
        await emit_progress(
            self._progress,
            kind="stage",
            stage="fetching_index",
            total=1,
            done=0,
            message=f"Checking updates: {novel.title}",
        )
        latest, stubs = await downloader.fetch_index_only(novel.source_url)
        stored_urls = _stored_chapter_urls(novel.chapters)
        new_stubs = [stub for stub in stubs if _normalize_url(stub.url) not in stored_urls]
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
        if rule.download_archive is not None:
            candidates = await downloader.fetch_chapters(stubs, source_url=novel.source_url)
            chapters = [
                chapter
                for chapter in candidates
                if chapter.source_url is not None
                and _normalize_url(chapter.source_url) not in stored_urls
            ]
        else:
            chapters = await downloader.fetch_chapters(new_stubs, source_url=novel.source_url)
        chapters = _reindex_for_append(chapters, after=novel.chapters)
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


def _stored_chapter_urls(chapters: list[Chapter]) -> set[str]:
    return {
        _normalize_url(chapter.source_url) for chapter in chapters if chapter.source_url is not None
    }


def _reindex_for_append(chapters: list[Chapter], *, after: list[Chapter]) -> list[Chapter]:
    next_index = max((chapter.index for chapter in after), default=-1) + 1
    return [
        chapter.model_copy(update={"index": next_index + offset})
        for offset, chapter in enumerate(sorted(chapters, key=lambda item: item.index))
    ]


def _normalize_url(url: str) -> str:
    return url.strip()
