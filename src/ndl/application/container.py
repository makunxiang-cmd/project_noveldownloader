"""Lightweight factories for application services."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from types import TracebackType

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from ndl.application.paths import library_db_path, rules_dir
from ndl.application.services import (
    ConvertService,
    DownloadService,
    LibraryService,
    RuleUpdateService,
    SearchService,
    UpdateService,
)
from ndl.converters import WriterRegistry, default_writer_registry
from ndl.core.models import Novel
from ndl.core.progress import ProgressCallback
from ndl.core.protocols import Fetcher, Parser, Reader
from ndl.fetchers import BrowserFetcher, HttpFetcher
from ndl.parsers import HtmlParser, TxtReader
from ndl.rules import RuleResolver, SourceRule, load_default_rules
from ndl.storage import (
    LibraryRepository,
    create_database_engine,
    create_session_factory,
    init_schema,
)

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
        db_path: Path | None = None,
    ) -> None:
        self._resolver = RuleResolver(
            rules if rules is not None else load_default_rules(user_rules_path=rules_dir())
        )
        self._fetcher_factory = fetcher_factory or _default_fetcher
        self._parser_factory = parser_factory or _default_parser
        self._readers = readers or {"txt": TxtReader()}
        self._writer_registry = writer_registry or default_writer_registry()
        self._db_path = db_path
        self._engine: Engine | None = None
        self._sessions: sessionmaker[Session] | None = None
        self._library: LibraryService | None = None

    def rule_for(self, url: str) -> SourceRule:
        """Resolve the SourceRule for `url`."""
        return self._resolver.resolve(url)

    def list_rules(self) -> list[SourceRule]:
        """Return loaded rules in resolution order."""
        return self._resolver.list_rules()

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
                rule=rule,
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

    def library_service(self) -> LibraryService:
        """Return a singleton LibraryService backed by a SQLite database."""
        if self._library is None:
            self._library = LibraryService(LibraryRepository(self._ensure_sessions()))
        return self._library

    def search_service(self) -> SearchService:
        """Build a SearchService over all loaded rules that declare a search endpoint."""
        return SearchService(
            rules=self._resolver.list_rules(),
            fetcher_factory=self.fetcher_for,
        )

    def rule_update_service(self) -> RuleUpdateService:
        """Build a RuleUpdateService for the user-installed rules directory."""
        return RuleUpdateService(rules_dir=rules_dir())

    def update_service(self, *, progress: ProgressCallback | None = None) -> UpdateService:
        """Build an UpdateService with configured rules and fetcher/parser factories."""
        return UpdateService(
            library=self.library_service(),
            rule_for=self.rule_for,
            fetcher_factory=self.fetcher_for,
            parser_factory=self.parser_for,
            progress=progress,
        )

    def close(self) -> None:
        """Dispose any database engine this container created."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._sessions = None
            self._library = None

    def __enter__(self) -> ServiceContainer:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _ensure_sessions(self) -> sessionmaker[Session]:
        if self._sessions is None:
            engine = self._ensure_engine()
            self._sessions = create_session_factory(engine)
        return self._sessions

    def _ensure_engine(self) -> Engine:
        if self._engine is None:
            path = self._db_path or library_db_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            self._engine = create_database_engine(path)
            init_schema(self._engine)
        return self._engine


def _default_fetcher(rule: SourceRule) -> Fetcher:
    if rule.fetcher.type == "browser":
        return BrowserFetcher(rule)
    return HttpFetcher(rule)


def _default_parser(rule: SourceRule) -> Parser:
    return HtmlParser(rule)
