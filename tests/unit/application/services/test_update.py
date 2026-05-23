"""Unit tests for the update service."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ndl.application.container import ServiceContainer
from ndl.core.models import Chapter, Novel
from ndl.core.progress import ProgressEvent
from ndl.rules.schema import ArchiveDownloadRule, PaginationRule, Selector, SourceRule
from tests.rule_fixtures import load_example_static_rule

BASE_URL = "https://example-novels.test/book/123"
FIXTURE_DIR = Path(__file__).parents[3] / "contract" / "fixtures" / "example_static"


class FakeFetcher:
    """Map URLs to fixture bodies for update tests."""

    def __init__(
        self,
        bodies: dict[str, str],
        *,
        bytes_bodies: dict[str, bytes] | None = None,
    ) -> None:
        self.requests: list[str] = []
        self.bytes_requests: list[str] = []
        self.closed = False
        self._bodies = bodies
        self._bytes_bodies = bytes_bodies or {}

    async def get(self, url: str, *, encoding: str | None = None) -> str:
        await asyncio.sleep(0)
        self.requests.append(url)
        return self._bodies[url]

    async def get_bytes(self, url: str) -> bytes:
        self.bytes_requests.append(url)
        return self._bytes_bodies[url]

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_update_all_appends_only_missing_chapters(tmp_path: Path) -> None:
    rule = load_example_static_rule()
    chapter_two = (
        (FIXTURE_DIR / "chapter.html")
        .read_text(encoding="utf-8")
        .replace(
            "Chapter 1: Dawn",
            "Chapter 2: Noon",
        )
    )
    fetcher = FakeFetcher(
        {
            BASE_URL: (FIXTURE_DIR / "index.html").read_text(encoding="utf-8"),
            f"{BASE_URL}/chapter/2": chapter_two,
        }
    )
    with ServiceContainer(
        rules=[rule],
        fetcher_factory=lambda _rule: fetcher,
        db_path=tmp_path / "library.db",
    ) as container:
        library = container.library_service()
        novel_id = library.save(_stored_novel())
        events: list[ProgressEvent] = []

        async def progress(event: ProgressEvent) -> None:
            events.append(event)

        results = await container.update_service(progress=progress).update_all()

        assert len(results) == 1
        assert results[0].status == "updated"
        assert results[0].new_chapter_count == 1
        assert results[0].total_chapter_count == 2
        assert fetcher.requests == [BASE_URL, f"{BASE_URL}/chapter/2"]
        assert fetcher.closed is True

        stored = library.get(novel_id)
        assert stored is not None
        assert [chapter.title for chapter in stored.chapters] == [
            "Chapter 1: Dawn",
            "Chapter 2: Noon",
        ]
        assert stored.last_updated is not None
        assert [event.kind for event in events] == ["stage", "stage", "chapter", "stage", "done"]


@pytest.mark.asyncio
async def test_update_all_reuses_fetcher_across_novels_with_same_rule(tmp_path: Path) -> None:
    rule = load_example_static_rule()
    index_html = (FIXTURE_DIR / "index.html").read_text(encoding="utf-8")
    chapter_two = (
        (FIXTURE_DIR / "chapter.html")
        .read_text(encoding="utf-8")
        .replace("Chapter 1: Dawn", "Chapter 2: Noon")
    )
    fetcher = FakeFetcher(
        {
            BASE_URL: index_html,
            BASE_URL + "?b=1": index_html,
            f"{BASE_URL}/chapter/2": chapter_two,
        }
    )
    built_count = 0

    def factory(_rule: object) -> FakeFetcher:
        nonlocal built_count
        built_count += 1
        return fetcher

    with ServiceContainer(
        rules=[rule],
        fetcher_factory=factory,
        db_path=tmp_path / "library.db",
    ) as container:
        library = container.library_service()
        novel_a = Novel(
            title="A",
            author="A",
            source_url=BASE_URL,
            source_rule_id="example_static",
            status="ongoing",
            chapters=[
                Chapter(
                    index=0,
                    title="Chapter 1: Dawn",
                    content="x",
                    source_url=f"{BASE_URL}/chapter/1",
                )
            ],
            fetched_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        )
        library.save(novel_a)
        novel_b = Novel(
            title="B",
            author="A",
            source_url=BASE_URL + "?b=1",
            source_rule_id="example_static",
            status="ongoing",
            chapters=[
                Chapter(
                    index=0,
                    title="Chapter 1: Dawn",
                    content="x",
                    source_url=f"{BASE_URL}/chapter/1",
                )
            ],
            fetched_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        )
        library.save(novel_b)

        await container.update_service().update_all()

    assert built_count == 1
    assert fetcher.closed is True


@pytest.mark.asyncio
async def test_update_uses_url_diff_when_remote_indices_shift(tmp_path: Path) -> None:
    rule = load_example_static_rule()
    chapter_zero_url = f"{BASE_URL}/chapter/0"
    chapter_one_url = f"{BASE_URL}/chapter/1"
    fetcher = FakeFetcher(
        {
            BASE_URL: _index_html(
                [
                    ("Chapter 0: Prologue", chapter_zero_url),
                    ("Chapter 1: Dawn", chapter_one_url),
                ]
            ),
            chapter_zero_url: _chapter_html("Chapter 0: Prologue", ["Before dawn."]),
        }
    )
    with ServiceContainer(
        rules=[rule],
        fetcher_factory=lambda _rule: fetcher,
        db_path=tmp_path / "library.db",
    ) as container:
        library = container.library_service()
        novel_id = library.save(_stored_novel())

        result = await container.update_service().update_novel(novel_id)

        assert result.status == "updated"
        assert result.new_chapter_count == 1
        assert fetcher.requests == [BASE_URL, chapter_zero_url]

        stored = library.get(novel_id)
        assert stored is not None
        assert [chapter.title for chapter in stored.chapters] == [
            "Chapter 1: Dawn",
            "Chapter 0: Prologue",
        ]
        assert [chapter.index for chapter in stored.chapters] == [0, 1]


@pytest.mark.asyncio
async def test_update_uses_paginated_index_pipeline(tmp_path: Path) -> None:
    rule = _example_rule(
        index_pagination=PaginationRule(
            type="next",
            next=Selector(selector="a.next-index", attr="href", resolve="relative"),
        )
    )
    chapter_one_url = f"{BASE_URL}/chapter/1"
    chapter_two_url = f"{BASE_URL}/chapter/2"
    fetcher = FakeFetcher(
        {
            BASE_URL: _index_html(
                [("Chapter 1: Dawn", chapter_one_url)],
                next_href="/book/123/index-2",
            ),
            f"{BASE_URL}/index-2": _index_html([("Chapter 2: Noon", chapter_two_url)]),
            chapter_two_url: _chapter_html("Chapter 2: Noon", ["Noon arrived."]),
        }
    )
    with ServiceContainer(
        rules=[rule],
        fetcher_factory=lambda _rule: fetcher,
        db_path=tmp_path / "library.db",
    ) as container:
        library = container.library_service()
        novel_id = library.save(_stored_novel())

        result = await container.update_service().update_novel(novel_id)

        assert result.status == "updated"
        assert result.new_chapter_count == 1
        assert fetcher.requests == [BASE_URL, f"{BASE_URL}/index-2", chapter_two_url]


@pytest.mark.asyncio
async def test_update_uses_chapter_pagination_pipeline(tmp_path: Path) -> None:
    rule = _example_rule(
        chapter_pagination=PaginationRule(
            type="next",
            next=Selector(selector="a.next-page", attr="href", resolve="relative"),
        )
    )
    chapter_one_url = f"{BASE_URL}/chapter/1"
    chapter_two_url = f"{BASE_URL}/chapter_002.html"
    chapter_two_page_two_url = f"{BASE_URL}/chapter_002_2.html"
    fetcher = FakeFetcher(
        {
            BASE_URL: _index_html(
                [
                    ("Chapter 1: Dawn", chapter_one_url),
                    ("Chapter 2: Noon", chapter_two_url),
                ]
            ),
            chapter_two_url: _chapter_html(
                "Chapter 2: Noon",
                ["Part one."],
                next_href="chapter_002_2.html",
            ),
            chapter_two_page_two_url: _chapter_html(
                "Chapter 2: Noon",
                ["Part two."],
                next_href="/book/123/chapter_003.html",
            ),
        }
    )
    with ServiceContainer(
        rules=[rule],
        fetcher_factory=lambda _rule: fetcher,
        db_path=tmp_path / "library.db",
    ) as container:
        library = container.library_service()
        novel_id = library.save(_stored_novel())

        await container.update_service().update_novel(novel_id)

        stored = library.get(novel_id)
        assert stored is not None
        assert fetcher.requests == [BASE_URL, chapter_two_url, chapter_two_page_two_url]
        assert stored.chapters[1].content == "Part one.\n\nPart two."


@pytest.mark.asyncio
async def test_update_uses_archive_pipeline_and_appends_only_new_tail(tmp_path: Path) -> None:
    archive_url = f"{BASE_URL}/download.txt"
    archive = ArchiveDownloadRule(
        trigger="url-template",
        url_template="{source_url}/download.txt",
        encodings=["utf-8"],
    )
    rule = _example_rule(archive=archive)
    chapter_one_url = f"{BASE_URL}/chapter/1"
    chapter_two_url = f"{BASE_URL}/chapter/2"
    archive_text = "\n".join(
        [
            "Chapter 1: Dawn",
            "Old body from archive.",
            "Chapter 2: Noon",
            "Noon arrived from archive.",
        ]
    )
    fetcher = FakeFetcher(
        {
            BASE_URL: _index_html(
                [
                    ("Chapter 1: Dawn", chapter_one_url),
                    ("Chapter 2: Noon", chapter_two_url),
                ]
            )
        },
        bytes_bodies={archive_url: archive_text.encode("utf-8")},
    )
    with ServiceContainer(
        rules=[rule],
        fetcher_factory=lambda _rule: fetcher,
        db_path=tmp_path / "library.db",
    ) as container:
        library = container.library_service()
        novel_id = library.save(_stored_novel())

        result = await container.update_service().update_novel(novel_id)

        assert result.status == "updated"
        assert result.new_chapter_count == 1
        assert fetcher.requests == [BASE_URL]
        assert fetcher.bytes_requests == [archive_url]

        stored = library.get(novel_id)
        assert stored is not None
        assert [chapter.title for chapter in stored.chapters] == [
            "Chapter 1: Dawn",
            "Chapter 2: Noon",
        ]
        assert stored.chapters[1].content == "Noon arrived from archive."


@pytest.mark.asyncio
async def test_update_all_skips_completed_and_sourceless_entries(tmp_path: Path) -> None:
    rule = load_example_static_rule()
    fetcher = FakeFetcher({})
    with ServiceContainer(
        rules=[rule],
        fetcher_factory=lambda _rule: fetcher,
        db_path=tmp_path / "library.db",
    ) as container:
        library = container.library_service()
        library.save(_stored_novel(status="completed"))
        library.save(_stored_novel(source_url=None))

        results = await container.update_service().update_all()

        assert results == []
        assert fetcher.requests == []
        assert fetcher.closed is False


def _stored_novel(
    *,
    status: str = "ongoing",
    source_url: str | None = BASE_URL,
) -> Novel:
    return Novel(
        title="Example Public Domain Novel",
        author="Example Author",
        source_url=source_url,
        source_rule_id="example_static",
        status=status,
        chapters=[
            Chapter(
                index=0,
                title="Chapter 1: Dawn",
                content="Morning arrived over the quiet archive.",
                source_url=f"{BASE_URL}/chapter/1",
            )
        ],
        fetched_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
    )


def _example_rule(
    *,
    index_pagination: PaginationRule | None = None,
    chapter_pagination: PaginationRule | None = None,
    archive: ArchiveDownloadRule | None = None,
) -> SourceRule:
    rule = load_example_static_rule()
    index = rule.index
    chapter = rule.chapter
    if index_pagination is not None:
        index = index.model_copy(update={"pagination": index_pagination})
    if chapter_pagination is not None:
        chapter = chapter.model_copy(update={"pagination": chapter_pagination})
    return rule.model_copy(
        update={
            "index": index,
            "chapter": chapter,
            "download_archive": archive,
        }
    )


def _index_html(
    chapters: list[tuple[str, str]],
    *,
    next_href: str | None = None,
) -> str:
    items = "\n".join(f'<li><a href="{url}">{title}</a></li>' for title, url in chapters)
    next_link = "" if next_href is None else f'<a class="next-index" href="{next_href}">More</a>'
    return f"""
<!doctype html>
<html lang="en">
  <body>
    <main>
      <h1 class="book-title">Example Public Domain Novel</h1>
      <div class="book-meta">
        <span class="author">Example Author</span>
        <span class="status">Completed</span>
      </div>
      <p class="book-intro">A fixture novel used to validate the example rule.</p>
      <div class="book-cover"><img src="/covers/example.jpg" alt="cover"></div>
      <ol id="chapter-list">{items}</ol>
      {next_link}
    </main>
  </body>
</html>
"""


def _chapter_html(
    title: str,
    paragraphs: list[str],
    *,
    next_href: str | None = None,
) -> str:
    body = "\n".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)
    next_link = "" if next_href is None else f'<a class="next-page" href="{next_href}">Next</a>'
    return f"""
<!doctype html>
<html lang="en">
  <body>
    <main>
      <h1 class="chapter-title">{title}</h1>
      <div id="chapter-content">{body}</div>
      {next_link}
    </main>
  </body>
</html>
"""
