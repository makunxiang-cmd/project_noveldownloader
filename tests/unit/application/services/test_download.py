"""Unit tests for the download service."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ndl.application.services import DownloadService
from ndl.core.progress import ProgressEvent
from ndl.parsers import HtmlParser
from ndl.rules.schema import ArchiveDownloadRule, PaginationRule, Selector, SourceRule
from tests.rule_fixtures import load_example_static_rule

BASE_URL = "https://example-novels.test/book/123"
FIXTURE_DIR = Path(__file__).parents[3] / "contract" / "fixtures" / "example_static"


class FakeFetcher:
    """Map URLs to fixture bodies for service tests."""

    def __init__(
        self,
        bodies: dict[str, str],
        *,
        bytes_bodies: dict[str, bytes] | None = None,
        download_bodies: dict[tuple[str, str], bytes] | None = None,
        delay: float = 0.0,
    ) -> None:
        self.requests: list[str] = []
        self.bytes_requests: list[str] = []
        self.download_requests: list[tuple[str, str]] = []
        self._bodies = bodies
        self._bytes_bodies = bytes_bodies or {}
        self._download_bodies = download_bodies or {}
        self._delay = delay
        self.in_flight = 0
        self.peak_in_flight = 0

    async def get(self, url: str, *, encoding: str | None = None) -> str:
        self.in_flight += 1
        self.peak_in_flight = max(self.peak_in_flight, self.in_flight)
        try:
            if self._delay:
                await asyncio.sleep(self._delay)
            self.requests.append(url)
            return self._bodies[url]
        finally:
            self.in_flight -= 1

    async def get_bytes(self, url: str) -> bytes:
        self.bytes_requests.append(url)
        return self._bytes_bodies[url]

    async def get_download_bytes(self, url: str, selector: str) -> bytes:
        self.download_requests.append((url, selector))
        return self._download_bodies[(url, selector)]

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_download_service_fetches_index_and_chapters_with_progress() -> None:
    rule = load_example_static_rule()
    chapter_one = (FIXTURE_DIR / "chapter.html").read_text(encoding="utf-8")
    chapter_two = chapter_one.replace("Chapter 1: Dawn", "Chapter 2: Noon").replace(
        "Morning arrived over the quiet archive.",
        "Noon light filled the reading room.",
    )
    fetcher = FakeFetcher(
        {
            BASE_URL: (FIXTURE_DIR / "index.html").read_text(encoding="utf-8"),
            f"{BASE_URL}/chapter/1": chapter_one,
            f"{BASE_URL}/chapter/2": chapter_two,
        }
    )
    events: list[ProgressEvent] = []

    async def progress(event: ProgressEvent) -> None:
        events.append(event)

    service = DownloadService(fetcher=fetcher, parser=HtmlParser(rule), progress=progress)

    novel = await service.download(BASE_URL)

    assert fetcher.requests[0] == BASE_URL
    assert set(fetcher.requests[1:]) == {f"{BASE_URL}/chapter/1", f"{BASE_URL}/chapter/2"}
    assert novel.title == "Example Public Domain Novel"
    assert [chapter.index for chapter in novel.chapters] == [0, 1]
    assert [chapter.title for chapter in novel.chapters] == ["Chapter 1: Dawn", "Chapter 2: Noon"]
    assert "Advertisement" not in novel.chapters[0].content
    assert [event.kind for event in events] == [
        "stage",
        "stage",
        "stage",
        "chapter",
        "chapter",
        "done",
    ]
    assert events[0].stage == "fetching_index"
    assert events[-1].done == 2


@pytest.mark.asyncio
async def test_download_service_fetches_chapters_concurrently() -> None:
    rule = load_example_static_rule()
    chapter_one = (FIXTURE_DIR / "chapter.html").read_text(encoding="utf-8")
    chapter_two = chapter_one.replace("Chapter 1: Dawn", "Chapter 2: Noon").replace(
        "Morning arrived over the quiet archive.",
        "Noon light filled the reading room.",
    )
    fetcher = FakeFetcher(
        {
            BASE_URL: (FIXTURE_DIR / "index.html").read_text(encoding="utf-8"),
            f"{BASE_URL}/chapter/1": chapter_one,
            f"{BASE_URL}/chapter/2": chapter_two,
        },
        delay=0.05,
    )
    service = DownloadService(fetcher=fetcher, parser=HtmlParser(rule))

    await service.download(BASE_URL)

    assert fetcher.peak_in_flight >= 2


@pytest.mark.asyncio
async def test_download_service_combines_next_paginated_index() -> None:
    rule = _example_rule(
        index_pagination=PaginationRule(
            type="next",
            next=Selector(selector="a.next-index", attr="href", resolve="relative"),
        )
    )
    chapter_one_url = f"{BASE_URL}/chapter/1"
    chapter_two_url = f"{BASE_URL}/chapter/2"
    chapter_three_url = f"{BASE_URL}/chapter/3"
    fetcher = FakeFetcher(
        {
            BASE_URL: _index_html(
                [
                    ("Chapter 1: Dawn", chapter_one_url),
                    ("Chapter 2: Noon", chapter_two_url),
                ],
                next_href="/book/123/index-2",
            ),
            f"{BASE_URL}/index-2": _index_html(
                [
                    ("Chapter 2: Noon", chapter_two_url),
                    ("Chapter 3: Dusk", chapter_three_url),
                ]
            ),
            chapter_one_url: _chapter_html("Chapter 1: Dawn", ["Morning arrived."]),
            chapter_two_url: _chapter_html("Chapter 2: Noon", ["Noon light filled the room."]),
            chapter_three_url: _chapter_html("Chapter 3: Dusk", ["Dusk settled."]),
        }
    )
    service = DownloadService(fetcher=fetcher, parser=HtmlParser(rule), rule=rule)

    novel = await service.download(BASE_URL)

    assert fetcher.requests[:2] == [BASE_URL, f"{BASE_URL}/index-2"]
    assert [chapter.index for chapter in novel.chapters] == [0, 1, 2]
    assert [chapter.title for chapter in novel.chapters] == [
        "Chapter 1: Dawn",
        "Chapter 2: Noon",
        "Chapter 3: Dusk",
    ]


@pytest.mark.asyncio
async def test_download_service_combines_index_template_until_empty_page() -> None:
    rule = _example_rule(
        index_pagination=PaginationRule(
            type="index-template",
            template="{source_url}/index-{page}",
            start=2,
            max_pages=5,
        )
    )
    chapter_one_url = f"{BASE_URL}/chapter/1"
    chapter_two_url = f"{BASE_URL}/chapter/2"
    fetcher = FakeFetcher(
        {
            BASE_URL: _index_html([("Chapter 1: Dawn", chapter_one_url)]),
            f"{BASE_URL}/index-2": _index_html(
                [
                    ("Chapter 1: Dawn", chapter_one_url),
                    ("Chapter 2: Noon", chapter_two_url),
                ]
            ),
            f"{BASE_URL}/index-3": _index_html([]),
            chapter_one_url: _chapter_html("Chapter 1: Dawn", ["Morning arrived."]),
            chapter_two_url: _chapter_html("Chapter 2: Noon", ["Noon light filled the room."]),
        }
    )
    service = DownloadService(fetcher=fetcher, parser=HtmlParser(rule), rule=rule)

    novel = await service.download(BASE_URL)

    assert fetcher.requests[:3] == [BASE_URL, f"{BASE_URL}/index-2", f"{BASE_URL}/index-3"]
    assert f"{BASE_URL}/index-4" not in fetcher.requests
    assert [chapter.title for chapter in novel.chapters] == ["Chapter 1: Dawn", "Chapter 2: Noon"]


@pytest.mark.asyncio
async def test_download_service_stops_next_paginated_index_on_cycle() -> None:
    rule = _example_rule(
        index_pagination=PaginationRule(
            type="next",
            next=Selector(selector="a.next-index", attr="href", resolve="relative"),
        )
    )
    chapter_one_url = f"{BASE_URL}/chapter/1"
    fetcher = FakeFetcher(
        {
            BASE_URL: _index_html(
                [("Chapter 1: Dawn", chapter_one_url)],
                next_href=BASE_URL,
            ),
            chapter_one_url: _chapter_html("Chapter 1: Dawn", ["Morning arrived."]),
        }
    )
    service = DownloadService(fetcher=fetcher, parser=HtmlParser(rule), rule=rule)

    novel = await service.download(BASE_URL)

    assert fetcher.requests.count(BASE_URL) == 1
    assert [chapter.title for chapter in novel.chapters] == ["Chapter 1: Dawn"]


@pytest.mark.asyncio
async def test_download_service_combines_next_paginated_chapter_pages() -> None:
    rule = _example_rule(
        chapter_pagination=PaginationRule(
            type="next",
            next=Selector(selector="a.next-page", attr="href", resolve="relative"),
        )
    )
    chapter_one_url = f"{BASE_URL}/chapter_001.html"
    chapter_one_page_two_url = f"{BASE_URL}/chapter_001_2.html"
    next_chapter_url = f"{BASE_URL}/chapter_002.html"
    fetcher = FakeFetcher(
        {
            BASE_URL: _index_html([("Chapter 1: Dawn", chapter_one_url)]),
            chapter_one_url: _chapter_html(
                "Chapter 1: Dawn",
                ["Part one."],
                next_href="chapter_001_2.html",
            ),
            chapter_one_page_two_url: _chapter_html(
                "Chapter 1: Dawn",
                ["Part two."],
                next_href="/book/123/chapter_002.html",
            ),
        }
    )
    service = DownloadService(fetcher=fetcher, parser=HtmlParser(rule), rule=rule)

    novel = await service.download(BASE_URL)

    assert fetcher.requests == [BASE_URL, chapter_one_url, chapter_one_page_two_url]
    assert next_chapter_url not in fetcher.requests
    assert novel.chapters[0].content == "Part one.\n\nPart two."


@pytest.mark.asyncio
async def test_download_service_next_paginated_chapter_without_next_link_is_noop() -> None:
    rule = _example_rule(
        chapter_pagination=PaginationRule(
            type="next",
            next=Selector(selector="a.next-page", attr="href", resolve="relative"),
        )
    )
    chapter_one_url = f"{BASE_URL}/chapter_001.html"
    fetcher = FakeFetcher(
        {
            BASE_URL: _index_html([("Chapter 1: Dawn", chapter_one_url)]),
            chapter_one_url: _chapter_html("Chapter 1: Dawn", ["Only page."]),
        }
    )
    service = DownloadService(fetcher=fetcher, parser=HtmlParser(rule), rule=rule)

    novel = await service.download(BASE_URL)

    assert fetcher.requests == [BASE_URL, chapter_one_url]
    assert novel.chapters[0].content == "Only page."


@pytest.mark.asyncio
async def test_download_service_uses_url_template_archive_and_splits_txt() -> None:
    archive_url = f"{BASE_URL}/download.txt"
    archive = ArchiveDownloadRule(
        trigger="url-template",
        url_template="{source_url}/download.txt",
        encodings=["utf-8-sig", "gb18030"],
        strip_patterns=[r"^AD.*$"],
    )
    rule = _example_rule(archive=archive)
    chapter_one_url = f"{BASE_URL}/chapter/1"
    chapter_two_url = f"{BASE_URL}/chapter/2"
    archive_text = "\n".join(
        [
            "AD should be removed",
            "Chapter 1: Dawn",
            "Morning arrived.",
            "The catalog opened.",
            "Chapter 2: Noon",
            "Noon light filled the room.",
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
        bytes_bodies={archive_url: archive_text.encode("gb18030")},
    )
    service = DownloadService(fetcher=fetcher, parser=HtmlParser(rule), rule=rule)

    novel = await service.download(BASE_URL)

    assert fetcher.requests == [BASE_URL]
    assert fetcher.bytes_requests == [archive_url]
    assert [chapter.title for chapter in novel.chapters] == ["Chapter 1: Dawn", "Chapter 2: Noon"]
    assert novel.chapters[0].content == "Morning arrived.\n\nThe catalog opened."
    assert novel.chapters[1].content == "Noon light filled the room."
    assert all("AD" not in chapter.content for chapter in novel.chapters)


@pytest.mark.asyncio
async def test_download_service_uses_browser_selector_archive() -> None:
    archive = ArchiveDownloadRule(
        trigger="selector",
        selector="a.download",
        encodings=["utf-8"],
    )
    rule = _example_rule(archive=archive, fetcher_type="browser")
    chapter_one_url = f"{BASE_URL}/chapter/1"
    fetcher = FakeFetcher(
        {BASE_URL: _index_html([("Chapter 1: Dawn", chapter_one_url)])},
        download_bodies={(BASE_URL, "a.download"): b"Chapter 1: Dawn\nDownloaded chapter body."},
    )
    service = DownloadService(fetcher=fetcher, parser=HtmlParser(rule), rule=rule)

    novel = await service.download(BASE_URL)

    assert fetcher.requests == [BASE_URL]
    assert fetcher.download_requests == [(BASE_URL, "a.download")]
    assert novel.chapters[0].content == "Downloaded chapter body."


def _example_rule(
    *,
    index_pagination: PaginationRule | None = None,
    chapter_pagination: PaginationRule | None = None,
    archive: ArchiveDownloadRule | None = None,
    fetcher_type: str | None = None,
) -> SourceRule:
    rule = load_example_static_rule()
    index = rule.index
    chapter = rule.chapter
    fetcher = rule.fetcher
    if index_pagination is not None:
        index = index.model_copy(update={"pagination": index_pagination})
    if chapter_pagination is not None:
        chapter = chapter.model_copy(update={"pagination": chapter_pagination})
    if fetcher_type is not None:
        fetcher = fetcher.model_copy(update={"type": fetcher_type})
    return rule.model_copy(
        update={
            "index": index,
            "chapter": chapter,
            "download_archive": archive,
            "fetcher": fetcher,
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
