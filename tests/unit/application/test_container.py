"""Unit tests for the service container."""

from __future__ import annotations

from ndl.application.container import ServiceContainer
from ndl.application.services import ConvertService
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
