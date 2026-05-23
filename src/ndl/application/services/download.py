"""Download service that composes fetchers and parsers."""

from __future__ import annotations

import asyncio
import fnmatch
from typing import cast
from urllib.parse import urljoin, urlparse

from selectolax.parser import HTMLParser

from ndl.application.services._progress import emit_progress
from ndl.core.errors import SelectorNotFoundError
from ndl.core.models import Chapter, ChapterStub, Novel
from ndl.core.progress import ProgressCallback
from ndl.core.protocols import Fetcher, Parser
from ndl.rules.schema import PaginationRule, SourceRule
from ndl.rules.selector import extract_selector


class DownloadService:
    """Download a novel through injected fetcher and parser implementations."""

    def __init__(
        self,
        *,
        fetcher: Fetcher,
        parser: Parser,
        rule: SourceRule | None = None,
        progress: ProgressCallback | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._parser = parser
        self._rule = rule or cast(SourceRule | None, getattr(parser, "rule", None))
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
        novel, stubs = await self._parse_index_pages(url, index_html)

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

    async def _parse_index_pages(
        self, url: str, first_html: str
    ) -> tuple[Novel, list[ChapterStub]]:
        novel, first_stubs = self._parser.parse_index(first_html, source_url=url)
        rule = self._rule
        if rule is None or rule.index.pagination.type == "none":
            return novel, first_stubs

        pagination = rule.index.pagination
        stubs: list[ChapterStub] = []
        seen_urls: set[str] = set()
        _extend_unique_stubs(stubs, seen_urls, first_stubs)

        if _page_has_terminator(first_html, pagination.terminator):
            return novel, stubs

        match pagination.type:
            case "next":
                await self._append_next_index_pages(
                    stubs=stubs,
                    seen_urls=seen_urls,
                    pagination=pagination,
                    first_html=first_html,
                    first_url=url,
                )
            case "index-template":
                await self._append_template_index_pages(
                    stubs=stubs,
                    seen_urls=seen_urls,
                    pagination=pagination,
                    first_url=url,
                )
            case "none":
                pass

        return novel, stubs

    async def _append_next_index_pages(
        self,
        *,
        stubs: list[ChapterStub],
        seen_urls: set[str],
        pagination: PaginationRule,
        first_html: str,
        first_url: str,
    ) -> None:
        current_html = first_html
        current_url = first_url
        visited = {first_url}
        page_count = 1
        while page_count < pagination.max_pages:
            next_url = _extract_next_url(pagination, current_html, current_url)
            if (
                next_url is None
                or next_url in visited
                or _url_matches_terminator(next_url, pagination.terminator)
            ):
                return

            visited.add(next_url)
            page_count += 1
            current_html = await self._fetcher.get(next_url)
            _, page_stubs = self._parser.parse_index(current_html, source_url=next_url)
            if not _extend_unique_stubs(stubs, seen_urls, page_stubs):
                return
            if _page_has_terminator(current_html, pagination.terminator):
                return
            current_url = next_url

    async def _append_template_index_pages(
        self,
        *,
        stubs: list[ChapterStub],
        seen_urls: set[str],
        pagination: PaginationRule,
        first_url: str,
    ) -> None:
        visited = {first_url}
        page = pagination.start
        page_count = 1
        while page_count < pagination.max_pages:
            next_url = _format_pagination_template(pagination, source_url=first_url, page=page)
            next_url = urljoin(first_url, next_url)
            if next_url in visited or _url_matches_terminator(next_url, pagination.terminator):
                return

            visited.add(next_url)
            page_count += 1
            page_html = await self._fetcher.get(next_url)
            _, page_stubs = self._parser.parse_index(page_html, source_url=next_url)
            if not _extend_unique_stubs(stubs, seen_urls, page_stubs):
                return
            if _page_has_terminator(page_html, pagination.terminator):
                return
            page += 1

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
        first = self._parser.parse_chapter(
            chapter_html,
            index=stub.index,
            source_url=stub.url,
        )
        pagination = None if self._rule is None else self._rule.chapter.pagination
        if pagination is None or pagination.type != "next":
            return first

        parts = [first.content]
        first_stem = _url_stem(stub.url)
        current_html = chapter_html
        current_url = stub.url
        visited = {stub.url}
        page_count = 1
        while page_count < pagination.max_pages:
            next_url = _extract_next_url(pagination, current_html, current_url)
            if (
                next_url is None
                or next_url in visited
                or not _same_chapter_stem(first_stem, next_url)
            ):
                break

            visited.add(next_url)
            page_count += 1
            current_html = await self._fetcher.get(next_url)
            page = self._parser.parse_chapter(
                current_html,
                index=stub.index,
                source_url=next_url,
            )
            parts.append(page.content)
            current_url = next_url

        return Chapter(
            index=stub.index,
            title=first.title,
            content="\n\n".join(parts),
            source_url=stub.url,
            published_at=first.published_at,
        )


def _extend_unique_stubs(
    target: list[ChapterStub],
    seen_urls: set[str],
    stubs: list[ChapterStub],
) -> bool:
    added = False
    for stub in stubs:
        key = _normalize_url(stub.url)
        if key in seen_urls:
            continue
        seen_urls.add(key)
        target.append(stub.model_copy(update={"index": len(target)}))
        added = True
    return added


def _extract_next_url(pagination: PaginationRule, html: str, base_url: str) -> str | None:
    if pagination.next is None:
        return None
    try:
        value = extract_selector(pagination.next, HTMLParser(html), base_url=base_url)
    except SelectorNotFoundError:
        return None
    if isinstance(value, list):
        value = value[0] if value else ""
    if not value:
        return None
    return urljoin(base_url, value)


def _format_pagination_template(pagination: PaginationRule, *, source_url: str, page: int) -> str:
    assert pagination.template is not None
    return pagination.template.format(source_url=source_url, page=page)


def _page_has_terminator(html: str, terminator: str | None) -> bool:
    if terminator is None:
        return False
    try:
        return HTMLParser(html).css_first(terminator) is not None
    except ValueError:
        return False


def _url_matches_terminator(url: str, terminator: str | None) -> bool:
    return terminator is not None and fnmatch.fnmatch(url, terminator)


def _same_chapter_stem(first_stem: str, next_url: str) -> bool:
    next_stem = _url_stem(next_url)
    return next_stem == first_stem or _strip_page_suffix(next_stem) == first_stem


def _url_stem(url: str) -> str:
    name = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[0]


def _strip_page_suffix(stem: str) -> str:
    prefix, separator, suffix = stem.rpartition("_")
    if separator and suffix.isdigit():
        return prefix
    return stem


def _normalize_url(url: str) -> str:
    return url.strip()
