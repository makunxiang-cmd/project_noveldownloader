"""Download service that composes fetchers and parsers."""

from __future__ import annotations

import asyncio
import fnmatch
import re
from typing import Protocol, cast, runtime_checkable
from urllib.parse import urljoin, urlparse

from selectolax.parser import HTMLParser

from ndl.application.services._progress import emit_progress
from ndl.core.errors import BrowserError, FetchError, SelectorNotFoundError
from ndl.core.models import Chapter, ChapterStub, Novel
from ndl.core.progress import ProgressCallback
from ndl.core.protocols import Fetcher, Parser
from ndl.rules.schema import ArchiveDownloadRule, PaginationRule, SourceRule
from ndl.rules.selector import extract_selector


@runtime_checkable
class _ByteFetcher(Protocol):
    async def get_bytes(self, url: str) -> bytes:
        """Fetch raw bytes from `url`."""


@runtime_checkable
class _SelectorDownloadFetcher(Protocol):
    async def get_download_bytes(self, url: str, selector: str) -> bytes:
        """Fetch downloaded bytes triggered by clicking `selector` on `url`."""


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
        rule = self._rule
        if rule is not None and rule.download_archive is not None:
            novel, stubs = self._parser.parse_index(index_html, source_url=url)
        else:
            novel, stubs = await self._parse_index_pages(url, index_html)

        await emit_progress(
            self._progress,
            kind="stage",
            stage="fetching_chapters",
            total=len(stubs),
            done=0,
            message="Fetching archive."
            if rule is not None and rule.download_archive
            else "Fetching chapters.",
        )
        if rule is not None and rule.download_archive is not None:
            chapters = await self._fetch_archive_chapters(url, stubs, rule.download_archive)
            for done, chapter in enumerate(chapters, start=1):
                await emit_progress(
                    self._progress,
                    kind="chapter",
                    stage="fetching_chapters",
                    total=len(stubs),
                    done=done,
                    current_title=chapter.title,
                )
        else:
            chapters = await self._fetch_chapters(stubs)

        completed = novel.model_copy(
            update={"chapters": sorted(chapters, key=lambda item: item.index)}
        )
        await emit_progress(
            self._progress,
            kind="done",
            stage="fetching_chapters",
            total=len(stubs),
            done=len(chapters),
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

    async def _fetch_archive_chapters(
        self,
        source_url: str,
        stubs: list[ChapterStub],
        archive: ArchiveDownloadRule,
    ) -> list[Chapter]:
        archive_bytes = await self._fetch_archive_bytes(source_url, archive)
        text = _decode_archive_text(archive_bytes, archive.encodings)
        text = _strip_archive_lines(text, archive.strip_patterns)
        return _split_archive_chapters(text, stubs)

    async def _fetch_archive_bytes(
        self,
        source_url: str,
        archive: ArchiveDownloadRule,
    ) -> bytes:
        match archive.trigger:
            case "url-template":
                archive_url = _format_archive_url(archive, source_url=source_url)
                if not isinstance(self._fetcher, _ByteFetcher):
                    raise FetchError(
                        "Archive URL-template downloads require a byte-capable fetcher.",
                        detail=f"URL: {archive_url}",
                    )
                return await self._fetcher.get_bytes(archive_url)
            case "selector":
                assert archive.selector is not None
                if not isinstance(self._fetcher, _SelectorDownloadFetcher):
                    raise BrowserError(
                        "Archive selector downloads require a browser fetcher.",
                        detail=f"URL: {source_url}\nSelector: {archive.selector}",
                    )
                return await self._fetcher.get_download_bytes(source_url, archive.selector)


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


def _format_archive_url(archive: ArchiveDownloadRule, *, source_url: str) -> str:
    assert archive.url_template is not None
    parsed = urlparse(source_url)
    path_parts = [part for part in parsed.path.split("/") if part]
    source_url_path_id = path_parts[-1] if path_parts else ""
    try:
        archive_url = archive.url_template.format(
            source_url=source_url,
            source_url_path=parsed.path,
            source_url_path_id=source_url_path_id,
        )
    except KeyError as exc:
        raise FetchError(
            "Archive URL template references an unsupported placeholder.",
            detail=f"Placeholder: {exc.args[0]}",
        ) from exc
    return urljoin(source_url, archive_url)


def _decode_archive_text(content: bytes, encodings: list[str]) -> str:
    for encoding in encodings:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode(encodings[-1], errors="replace")


def _strip_archive_lines(text: str, strip_patterns: list[str]) -> str:
    if not strip_patterns:
        return text
    patterns = [re.compile(pattern) for pattern in strip_patterns]
    lines = [
        line
        for line in text.splitlines()
        if not any(pattern.search(line.strip()) for pattern in patterns)
    ]
    return "\n".join(lines)


def _split_archive_chapters(text: str, stubs: list[ChapterStub]) -> list[Chapter]:
    if not stubs:
        return []

    chapters: list[Chapter] = []
    current_stub: ChapterStub | None = None
    current_lines: list[str] = []
    search_start = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        matched_index = _match_stub_title(line, stubs, search_start)
        if matched_index is not None:
            if current_stub is not None:
                chapters.append(_archive_chapter(current_stub, current_lines, len(chapters)))
            current_stub = stubs[matched_index]
            current_lines = []
            search_start = matched_index + 1
            continue
        if current_stub is not None:
            current_lines.append(line)

    if current_stub is not None:
        chapters.append(_archive_chapter(current_stub, current_lines, len(chapters)))
    return chapters


def _match_stub_title(line: str, stubs: list[ChapterStub], start: int) -> int | None:
    normalized = _normalize_title(line)
    lookahead_end = min(len(stubs), start + 8)
    for index in range(start, lookahead_end):
        if normalized == _normalize_title(stubs[index].title):
            return index
    return None


def _archive_chapter(stub: ChapterStub, lines: list[str], index: int) -> Chapter:
    return Chapter(
        index=index,
        title=stub.title,
        content="\n\n".join(lines),
        source_url=stub.url,
    )


def _normalize_title(value: str) -> str:
    return "".join(value.split()).casefold()
