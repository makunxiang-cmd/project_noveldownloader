# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- P2.2 `LibraryRepository` (`src/ndl/storage/repository.py`): upsert-on-`(source_rule_id, source_url)` `save`, `list` with chapter counts, full-novel `get`, and cascade-deleting `remove`; introduces lightweight `NovelSummary` dataclass for list views
- P2.1 storage foundation: `src/ndl/storage/` with SQLAlchemy 2.0 Mapped models (`NovelRow`, `ChapterRow`, `DownloadJobRow`, `SettingRow`), engine factory with `journal_mode=WAL` + `foreign_keys=ON` PRAGMAs, sessionmaker, and a `session_scope` helper; new dependency `sqlalchemy>=2.0`
- P1.6 CLI commands: `ndl download`, `ndl convert`, and `ndl rules validate`; `download` is guarded by a first-run lawful-use disclaimer acceptance gate
- P1.5 application services: `DownloadService`, `ConvertService`, and `ServiceContainer` compose fetchers, parsers, readers, writers, and progress callbacks
- P1.4 TXT/EPUB converters: `TxtWriter`, `EpubWriter`, `WriterRegistry`, and `TxtReader` for standalone TXT conversion; EPUB generation is backed by `ebooklib`
- P1.3 HTTP fetcher: `HttpFetcher` honors per-host rate limits, retry policy with fixed/exponential backoff, robots.txt enforcement, and rule-driven encoding; backed by `httpx`
- P1.2 HTML parsers: `parse_index` produces `Novel` metadata + `ChapterStub` list, `parse_chapter` produces a cleaned `Chapter`; `HtmlParser` class binds a rule to the `Parser` Protocol
- P1.1 domain foundation: `Chapter`, `Novel`, `ChapterStub`, progress events, protocols, and typed error hierarchy
- P1.1 rule foundation: Pydantic YAML schema, selector DSL helpers, rule loader/resolver, and bundled `example_static` rule
- Contract fixture baseline for bundled rules
- Concurrent chapter fetching in `DownloadService`, capped by the rule's `rate_limit.max_concurrency` via the per-host throttle
- Rich-backed CLI progress renderer (`ndl.cli.renderers.cli_progress`) wired into `download` and `convert`; non-interactive runs degrade silently
- `ServiceContainer.download(url, progress=...)` end-to-end helper that owns Fetcher lifecycle and the new `fetcher_for` / `parser_for` accessors
- HTTP 429 retries now honor the `Retry-After` header (delta-seconds or HTTP-date), capped at 60s
- `Fetcher` Protocol now declares `aclose()` so service containers and tests can rely on a single shutdown contract
- Repository domain conventions: `CONTEXT.md` glossary, first ADR (`docs/adr/0001-architecture-and-deps.md`), and `.scratch/` issue tracker root

### Changed

- P0 scaffold (project structure, CI, lint/type/test tooling, MkDocs skeleton, `ndl --version`, community files, issue/PR templates, GitHub Actions CI matrix) is now complete; previously listed under "Changed" by mistake
- Documentation reflects P1 completion, current CLI capabilities, and the P2 library persistence handoff plan
- Contract test for bundled rules now exercises the parsers end-to-end instead of selector helpers directly
- CLI `download` / `convert` route through `ServiceContainer` instead of instantiating fetchers and parsers ad hoc
- `Novel.source_url` is now optional (`str | None`); HTTP-URL validation moved off the field so TXT-derived novels no longer need a synthetic placeholder
- `Chapter.word_count` is filled by a `model_validator(mode="before")` instead of bypassing the frozen model with `object.__setattr__`
- `HttpFetcher` now resolves a single set of request headers (with a guaranteed `User-Agent`) so robots checks and real requests use the same identity
- `NDLError.user_message()` no longer takes an unused `lang` parameter; i18n will reintroduce a structured API in P5
- `pyproject.toml` collapses dev dependencies into a single `[project.optional-dependencies].dev` group (was split across `[dependency-groups]`)

### Fixed

- `core.errors.HTTPError` no longer reads `HTTPStatus._value2member_map_`; it falls back to "HTTP error" via `HTTPStatus(code)` / `ValueError`

[Unreleased]: https://github.com/makunxiang-cmd/project_noveldownloader/commits/main
