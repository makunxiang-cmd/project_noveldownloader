"""Unit tests for the service container."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ndl.application.container import ServiceContainer
from ndl.application.services import ConvertService, LibraryService
from ndl.core.models import Chapter, ChapterStub, Novel
from ndl.core.protocols import Fetcher, Parser
from ndl.rules.loader import load_builtin_rules
from ndl.rules.schema import SourceRule

BASE_URL = "https://example-novels.test/book/123"


class DummyFetcher:
    """Fetcher placeholder used to assert container wiring."""

    closed = False

    async def get(self, url: str, *, encoding: str | None = None) -> str:
        return ""

    async def aclose(self) -> None:
        self.closed = True


class DummyParser:
    """Parser placeholder used to assert container wiring."""

    def parse_index(self, html: str, *, source_url: str) -> tuple[Novel, list[ChapterStub]]:
        raise NotImplementedError

    def parse_chapter(self, html: str, *, index: int, source_url: str) -> Chapter:
        raise NotImplementedError


def test_container_resolves_rule_and_builds_dependencies() -> None:
    rules = load_builtin_rules()

    def fetcher_factory(rule: SourceRule) -> Fetcher:
        assert rule.id == "example_static"
        return DummyFetcher()

    def parser_factory(rule: SourceRule) -> Parser:
        assert rule.id == "example_static"
        return DummyParser()

    container = ServiceContainer(
        rules=rules,
        fetcher_factory=fetcher_factory,
        parser_factory=parser_factory,
    )

    rule = container.rule_for(BASE_URL)
    assert rule.id == "example_static"
    assert isinstance(container.fetcher_for(rule), DummyFetcher)
    assert isinstance(container.parser_for(rule), DummyParser)


def test_container_builds_convert_service() -> None:
    assert isinstance(ServiceContainer(rules=[]).convert_service(), ConvertService)


def test_container_library_service_is_singleton(tmp_path: Path) -> None:
    container = ServiceContainer(rules=[], db_path=tmp_path / "lib.db")
    first = container.library_service()
    second = container.library_service()
    assert isinstance(first, LibraryService)
    assert first is second


def test_container_library_service_persists_to_db_path(tmp_path: Path) -> None:
    db_path = tmp_path / "lib.db"
    container = ServiceContainer(rules=[], db_path=db_path)
    library = container.library_service()
    novel = Novel(
        title="T",
        author="A",
        source_url="https://example.com/x",
        source_rule_id="example_static",
        fetched_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        chapters=[Chapter(index=0, title="c", content="x")],
    )
    novel_id = library.save(novel)
    assert db_path.exists()
    assert library.get(novel_id) is not None
