"""Download service that composes fetchers and parsers."""

from __future__ import annotations

import asyncio

from ndl.application.services._progress import emit_progress
from ndl.core.models import Chapter, ChapterStub, Novel
from ndl.core.progress import ProgressCallback
from ndl.core.protocols import Fetcher, Parser


class DownloadService:
    """Download a novel through injected fetcher and parser implementations."""

    def __init__(
        self,
        *,
        fetcher: Fetcher,
        parser: Parser,
        progress: ProgressCallback | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._parser = parser
        self._progress = progress

    async def download(self, url: str) -> Novel:
        """Fetch an index URL and all discovered chapters into a Novel."""
        await emit_progress(
            self._progress,
            kind="stage",
            stage="fetching_index",
            total=1,
            done=0,
            message=f"Fetching index: {url}",
        )
        index_html = await self._fetcher.get(url)
        await emit_progress(
            self._progress,
            kind="stage",
            stage="fetching_index",
            total=1,
            done=1,
            message="Parsing index.",
        )
        novel, stubs = self._parser.parse_index(index_html, source_url=url)

        await emit_progress(
            self._progress,
            kind="stage",
            stage="fetching_chapters",
            total=len(stubs),
            done=0,
            message="Fetching chapters.",
        )
        chapters = await self._fetch_chapters(stubs)

        completed = novel.model_copy(
            update={"chapters": sorted(chapters, key=lambda item: item.index)}
        )
        await emit_progress(
            self._progress,
            kind="done",
            stage="fetching_chapters",
            total=len(stubs),
            done=len(stubs),
            message="Download complete.",
        )
        return completed

    async def _fetch_chapters(self, stubs: list[ChapterStub]) -> list[Chapter]:
        """Fetch chapters concurrently. Per-host concurrency cap is enforced by the fetcher."""
        if not stubs:
            return []
        tasks = [asyncio.create_task(self._fetch_chapter(stub)) for stub in stubs]
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

    async def _fetch_chapter(self, stub: ChapterStub) -> Chapter:
        chapter_html = await self._fetcher.get(stub.url)
        return self._parser.parse_chapter(
            chapter_html,
            index=stub.index,
            source_url=stub.url,
        )
