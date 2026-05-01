"""Unit tests for the update service."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ndl.application.container import ServiceContainer
from ndl.core.models import Chapter, Novel
from ndl.core.progress import ProgressEvent
from ndl.rules.loader import load_builtin_rules

BASE_URL = "https://example-novels.test/book/123"
FIXTURE_DIR = Path(__file__).parents[3] / "contract" / "fixtures" / "example_static"


class FakeFetcher:
    """Map URLs to fixture bodies for update tests."""

    def __init__(self, bodies: dict[str, str]) -> None:
        self.requests: list[str] = []
        self.closed = False
        self._bodies = bodies

    async def get(self, url: str, *, encoding: str | None = None) -> str:
        await asyncio.sleep(0)
        self.requests.append(url)
        return self._bodies[url]

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_update_all_appends_only_missing_chapters(tmp_path: Path) -> None:
    rule = next(rule for rule in load_builtin_rules() if rule.id == "example_static")
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
    container = ServiceContainer(
        rules=[rule],
        fetcher_factory=lambda _rule: fetcher,
        db_path=tmp_path / "library.db",
    )
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
async def test_update_all_skips_completed_and_sourceless_entries(tmp_path: Path) -> None:
    rule = next(rule for rule in load_builtin_rules() if rule.id == "example_static")
    fetcher = FakeFetcher({})
    container = ServiceContainer(
        rules=[rule],
        fetcher_factory=lambda _rule: fetcher,
        db_path=tmp_path / "library.db",
    )
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
