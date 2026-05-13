"""Tests for the Web UI app factory."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from ndl.application.container import ServiceContainer
from ndl.core.errors import BrowserError
from ndl.core.models import Chapter, Novel
from ndl.web import create_app

BASE_URL = "https://example-novels.test/book/123"
REPO_ROOT = Path(__file__).parents[3]
FIXTURE_DIR = REPO_ROOT / "tests" / "contract" / "fixtures" / "example_static"
SEARCH_HTML = """
<html><body>
<div id="search-results">
  <div class="result-item">
    <span class="result-title">Journey to the West</span>
    <span class="result-author">Wu Cheng'en</span>
    <a class="result-link" href="/book/1">View</a>
  </div>
  <div class="result-item">
    <span class="result-title">Dream of the Red Chamber</span>
    <span class="result-author">Cao Xueqin</span>
    <a class="result-link" href="/book/2">View</a>
  </div>
</div>
</body></html>
"""
EMPTY_SEARCH_HTML = """
<html><body>
<div id="search-results"></div>
</body></html>
"""

ContainerFactory = Callable[..., ServiceContainer]


@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip real sleeping in Web download tests."""

    async def _instant(_seconds: float) -> None:
        return None

    monkeypatch.setattr("ndl.fetchers._throttle.asyncio.sleep", _instant)
    monkeypatch.setattr("ndl.fetchers.http.asyncio.sleep", _instant)


@pytest.fixture
def make_container() -> Iterator[ContainerFactory]:
    """Create ServiceContainers and dispose their engines at teardown."""
    created: list[ServiceContainer] = []

    def factory(**kwargs: Any) -> ServiceContainer:
        container = ServiceContainer(**kwargs)
        created.append(container)
        return container

    yield factory
    for container in created:
        container.close()


def test_index_renders_empty_library_shell(
    tmp_path: Path, make_container: ContainerFactory
) -> None:
    container = make_container(rules=[], db_path=tmp_path / "library.db")
    client = TestClient(create_app(container=container))

    response = client.get("/")

    assert response.status_code == 200
    assert "NDL Library" in response.text
    assert "No saved novels" in response.text
    assert 'action="/updates"' in response.text
    assert 'action="/search"' in response.text


def test_scheduler_is_disabled_by_default(tmp_path: Path, make_container: ContainerFactory) -> None:
    container = make_container(rules=[], db_path=tmp_path / "library.db")
    app = create_app(container=container)

    assert app.state.update_scheduler is None


def test_scheduler_runs_during_lifespan_when_enabled(
    tmp_path: Path, make_container: ContainerFactory
) -> None:
    container = make_container(rules=[], db_path=tmp_path / "library.db")
    app = create_app(container=container, enable_scheduler=True, scheduler_interval_hours=1)

    scheduler = app.state.update_scheduler
    assert scheduler is not None
    assert scheduler.state.running is False

    with TestClient(app):
        assert scheduler.state.running is True

    assert scheduler.state.running is False


def test_index_lists_library_summaries(tmp_path: Path, make_container: ContainerFactory) -> None:
    container = make_container(rules=[], db_path=tmp_path / "library.db")
    novel_id = container.library_service().save(_novel())
    client = TestClient(create_app(container=container))

    response = client.get("/")

    assert response.status_code == 200
    assert "Seed Novel" in response.text
    assert "Seed Author" in response.text
    assert f"/library/{novel_id}" in response.text
    assert "First Chapter" not in response.text


def test_library_detail_lists_chapters_without_bodies(
    tmp_path: Path, make_container: ContainerFactory
) -> None:
    container = make_container(rules=[], db_path=tmp_path / "library.db")
    novel_id = container.library_service().save(_novel())
    client = TestClient(create_app(container=container))

    response = client.get(f"/library/{novel_id}")

    assert response.status_code == 200
    assert "Seed Novel" in response.text
    assert "Seed Author" in response.text
    assert "https://example.com/seed" in response.text
    assert "First Chapter" in response.text
    assert "Second Chapter" in response.text
    assert "secret body" not in response.text


def test_library_detail_missing_id_renders_404(
    tmp_path: Path, make_container: ContainerFactory
) -> None:
    container = make_container(rules=[], db_path=tmp_path / "library.db")
    client = TestClient(create_app(container=container))

    response = client.get("/library/404")

    assert response.status_code == 404
    assert "Library entry not found" in response.text
    assert "ID: 404" in response.text


@respx.mock
def test_update_all_appends_new_chapters_and_renders_results(
    tmp_path: Path, make_container: ContainerFactory
) -> None:
    container = make_container(db_path=tmp_path / "library.db")
    novel_id = container.library_service().save(_updatable_novel())
    client = TestClient(create_app(container=container))
    _mock_example_update()

    response = client.post("/updates")

    assert response.status_code == 200
    assert "Update Results" in response.text
    assert "Example Public Domain Novel" in response.text
    assert "updated" in response.text
    assert "1 new chapter" in response.text
    assert f"/library/{novel_id}" in response.text

    stored = container.library_service().get(novel_id)
    assert stored is not None
    assert [chapter.title for chapter in stored.chapters] == [
        "Chapter 1: Dawn",
        "Chapter 2: Noon",
    ]


def test_update_all_empty_library_renders_empty_results(
    tmp_path: Path, make_container: ContainerFactory
) -> None:
    container = make_container(rules=[], db_path=tmp_path / "library.db")
    client = TestClient(create_app(container=container))

    response = client.post("/updates")

    assert response.status_code == 200
    assert "No updatable library entries" in response.text


@respx.mock
def test_search_page_renders_results_with_download_actions(
    tmp_path: Path, make_container: ContainerFactory
) -> None:
    container = make_container(db_path=tmp_path / "library.db")
    client = TestClient(create_app(container=container))
    _mock_example_search("west", SEARCH_HTML)

    response = client.get("/search", params={"keyword": "west", "limit": "10"})

    assert response.status_code == 200
    assert "Search Results" in response.text
    assert "Journey to the West" in response.text
    assert "Wu Cheng&#39;en" in response.text
    assert "https://example-novels.test/book/1" in response.text
    assert 'action="/downloads"' in response.text


@respx.mock
def test_search_page_supports_rule_filter_and_limit(
    tmp_path: Path, make_container: ContainerFactory
) -> None:
    container = make_container(db_path=tmp_path / "library.db")
    client = TestClient(create_app(container=container))
    _mock_example_search("west", SEARCH_HTML)

    response = client.get(
        "/search",
        params={"keyword": "west", "rule_id": "example_static", "limit": "1"},
    )

    assert response.status_code == 200
    assert "Journey to the West" in response.text
    assert "Dream of the Red Chamber" not in response.text


@respx.mock
def test_search_page_renders_empty_state(tmp_path: Path, make_container: ContainerFactory) -> None:
    container = make_container(db_path=tmp_path / "library.db")
    client = TestClient(create_app(container=container))
    _mock_example_search("nothing", EMPTY_SEARCH_HTML)

    response = client.get("/search", params={"keyword": "nothing"})

    assert response.status_code == 200
    assert "No search results" in response.text


def test_search_page_rejects_missing_keyword(
    tmp_path: Path, make_container: ContainerFactory
) -> None:
    container = make_container(rules=[], db_path=tmp_path / "library.db")
    client = TestClient(create_app(container=container))

    response = client.get("/search", params={"keyword": "  "})

    assert response.status_code == 400
    assert "Search keyword is required." in response.text


def test_search_page_rejects_unsupported_rule(
    tmp_path: Path, make_container: ContainerFactory
) -> None:
    container = make_container(db_path=tmp_path / "library.db")
    client = TestClient(create_app(container=container))

    response = client.get("/search", params={"keyword": "west", "rule_id": "missing"})

    assert response.status_code == 400
    assert "Unsupported search rule selection." in response.text
    assert "example_static" in response.text


@respx.mock
def test_download_form_persists_novel_and_records_progress(
    tmp_path: Path, make_container: ContainerFactory
) -> None:
    container = make_container(db_path=tmp_path / "library.db")
    app = create_app(container=container, output_dir=tmp_path / "downloads")
    _mock_example_download()

    with TestClient(app) as client:
        response = client.post(
            "/downloads",
            data={"url": BASE_URL, "format": "epub", "save": "on"},
        )

        assert response.status_code == 202, response.text
        assert "Download Job" in response.text

        jobs = app.state.job_registry.list()
        assert len(jobs) == 1
        job = jobs[0]
        assert job.status == "succeeded"
        assert job.output_path is not None
        assert job.output_path.exists()
        with ZipFile(job.output_path) as archive:
            assert "OEBPS/content.opf" in archive.namelist()

        summaries = container.library_service().list()
        assert [summary.title for summary in summaries] == ["Example Public Domain Novel"]

        events_response = client.get(f"/downloads/{job.id}/events")
        assert events_response.status_code == 200
        assert "event: progress" in events_response.text
        assert "fetching_index" in events_response.text
        assert "event: status" in events_response.text
        assert '"status": "succeeded"' in events_response.text


@respx.mock
def test_download_form_no_save_skips_library(
    tmp_path: Path, make_container: ContainerFactory
) -> None:
    container = make_container(db_path=tmp_path / "library.db")
    app = create_app(container=container, output_dir=tmp_path / "downloads")
    _mock_example_download()

    with TestClient(app) as client:
        response = client.post(
            "/downloads",
            data={"url": BASE_URL, "format": "txt"},
        )

    assert response.status_code == 202, response.text
    job = app.state.job_registry.list()[0]
    assert job.status == "succeeded"
    assert job.output_path is not None
    assert job.output_path.suffix == ".txt"
    assert container.library_service().list() == []


def test_download_form_rejects_missing_url(
    tmp_path: Path, make_container: ContainerFactory
) -> None:
    container = make_container(rules=[], db_path=tmp_path / "library.db")
    client = TestClient(create_app(container=container, output_dir=tmp_path / "downloads"))

    response = client.post("/downloads", data={"url": "", "format": "epub"})

    assert response.status_code == 400
    assert "Download URL is required." in response.text


def test_download_form_records_browser_runtime_failure(
    tmp_path: Path,
    make_container: ContainerFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_download(
        self: ServiceContainer,
        url: str,
        *,
        progress: object | None = None,
    ) -> Novel:
        raise BrowserError(
            "Browser runtime failed to start.",
            detail="Run `playwright install chromium`.",
        )

    monkeypatch.setattr(ServiceContainer, "download", fail_download)
    container = make_container(rules=[], db_path=tmp_path / "library.db")
    app = create_app(container=container, output_dir=tmp_path / "downloads")

    with TestClient(app) as client:
        response = client.post(
            "/downloads",
            data={"url": "https://browser.test/book/1", "format": "epub"},
        )

        assert response.status_code == 202, response.text
        job = app.state.job_registry.list()[0]
        assert job.status == "failed"
        assert job.error_message is not None
        assert "Browser runtime failed to start." in job.error_message
        assert "playwright install chromium" in job.error_message

        events_response = client.get(f"/downloads/{job.id}/events")
        assert events_response.status_code == 200
        assert "event: status" in events_response.text
        assert '"status": "failed"' in events_response.text
        assert "playwright install chromium" in events_response.text


def _novel() -> Novel:
    return Novel(
        title="Seed Novel",
        author="Seed Author",
        source_url="https://example.com/seed",
        source_rule_id="example_static",
        chapters=[
            Chapter(index=0, title="First Chapter", content="secret body"),
            Chapter(index=1, title="Second Chapter", content="more secret body"),
        ],
        fetched_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
    )


def _updatable_novel() -> Novel:
    return Novel(
        title="Example Public Domain Novel",
        author="Example Author",
        source_url=BASE_URL,
        source_rule_id="example_static",
        status="ongoing",
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


def _mock_example_download() -> None:
    chapter_one = (FIXTURE_DIR / "chapter.html").read_text(encoding="utf-8")
    chapter_two = chapter_one.replace("Chapter 1: Dawn", "Chapter 2: Noon").replace(
        "Morning arrived over the quiet archive.",
        "Noon light filled the reading room.",
    )
    respx.get("https://example-novels.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /\n")
    )
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(
            200,
            text=(FIXTURE_DIR / "index.html").read_text(encoding="utf-8"),
        )
    )
    respx.get(f"{BASE_URL}/chapter/1").mock(return_value=httpx.Response(200, text=chapter_one))
    respx.get(f"{BASE_URL}/chapter/2").mock(return_value=httpx.Response(200, text=chapter_two))


def _mock_example_update() -> None:
    chapter_two = (
        (FIXTURE_DIR / "chapter.html")
        .read_text(encoding="utf-8")
        .replace(
            "Chapter 1: Dawn",
            "Chapter 2: Noon",
        )
    )
    respx.get("https://example-novels.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /\n")
    )
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(
            200,
            text=(FIXTURE_DIR / "index.html").read_text(encoding="utf-8"),
        )
    )
    respx.get(f"{BASE_URL}/chapter/2").mock(return_value=httpx.Response(200, text=chapter_two))


def _mock_example_search(keyword: str, html: str) -> None:
    encoded_keyword = keyword.replace(" ", "+")
    respx.get("https://example-novels.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nAllow: /\n")
    )
    respx.get(f"https://example-novels.test/search?q={encoded_keyword}").mock(
        return_value=httpx.Response(200, text=html)
    )
