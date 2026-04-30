"""Unit tests for the download service."""

from __future__ import annotations

from pathlib import Path

import pytest

from ndl.application.services import DownloadService
from ndl.core.progress import ProgressEvent
from ndl.parsers import HtmlParser
from ndl.rules.loader import load_builtin_rules

BASE_URL = "https://example-novels.test/book/123"
FIXTURE_DIR = Path(__file__).parents[3] / "contract" / "fixtures" / "example_static"


class FakeFetcher:
    """Map URLs to fixture bodies for service tests."""

    def __init__(self, bodies: dict[str, str]) -> None:
        self.requests: list[str] = []
        self._bodies = bodies

    async def get(self, url: str, *, encoding: str | None = None) -> str:
        self.requests.append(url)
        return self._bodies[url]


@pytest.mark.asyncio
async def test_download_service_fetches_index_and_chapters_with_progress() -> None:
    rule = next(rule for rule in load_builtin_rules() if rule.id == "example_static")
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

    assert fetcher.requests == [BASE_URL, f"{BASE_URL}/chapter/1", f"{BASE_URL}/chapter/2"]
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
