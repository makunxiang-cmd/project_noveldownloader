"""Lightweight factories for application services."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping

from ndl.application.services import ConvertService, DownloadService
from ndl.converters import WriterRegistry, default_writer_registry
from ndl.core.models import Novel
from ndl.core.progress import ProgressCallback
from ndl.core.protocols import Fetcher, Parser, Reader
from ndl.fetchers import HttpFetcher
from ndl.parsers import HtmlParser, TxtReader
from ndl.rules import RuleResolver, SourceRule, load_builtin_rules

FetcherFactory = Callable[[SourceRule], Fetcher]
ParserFactory = Callable[[SourceRule], Parser]


class ServiceContainer:
    """Resolve rules and build service instances with default dependencies."""

    def __init__(
        self,
        *,
        rules: Iterable[SourceRule] | None = None,
        fetcher_factory: FetcherFactory | None = None,
        parser_factory: ParserFactory | None = None,
        readers: Mapping[str, Reader] | None = None,
        writer_registry: WriterRegistry | None = None,
    ) -> None:
        self._resolver = RuleResolver(rules if rules is not None else load_builtin_rules())
        self._fetcher_factory = fetcher_factory or _default_fetcher
        self._parser_factory = parser_factory or _default_parser
        self._readers = readers or {"txt": TxtReader()}
        self._writer_registry = writer_registry or default_writer_registry()

    def rule_for(self, url: str) -> SourceRule:
        """Resolve the SourceRule for `url`."""
        return self._resolver.resolve(url)

    def fetcher_for(self, rule: SourceRule) -> Fetcher:
        """Build a Fetcher for `rule` using the configured factory."""
        return self._fetcher_factory(rule)

    def parser_for(self, rule: SourceRule) -> Parser:
        """Build a Parser for `rule` using the configured factory."""
        return self._parser_factory(rule)

    async def download(
        self,
        url: str,
        *,
        progress: ProgressCallback | None = None,
    ) -> Novel:
        """Resolve the rule, build dependencies, and download `url` end-to-end."""
        rule = self.rule_for(url)
        fetcher = self.fetcher_for(rule)
        try:
            service = DownloadService(
                fetcher=fetcher,
                parser=self.parser_for(rule),
                progress=progress,
            )
            return await service.download(url)
        finally:
            await fetcher.aclose()

    def convert_service(self, *, progress: ProgressCallback | None = None) -> ConvertService:
        """Build a ConvertService with configured readers and writers."""
        return ConvertService(
            readers=self._readers,
            writer_registry=self._writer_registry,
            progress=progress,
        )


def _default_fetcher(rule: SourceRule) -> Fetcher:
    return HttpFetcher(rule)


def _default_parser(rule: SourceRule) -> Parser:
    return HtmlParser(rule)
