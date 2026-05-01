# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- P4.3 Web update controls: homepage `Update all` action, `/updates` result page, and Web tests covering append-only update results plus empty-library status
- P4.2 scheduled update runs under `ndl serve`: APScheduler-backed `UpdateScheduler`, FastAPI lifespan startup/shutdown wiring, and `--scheduler/--no-scheduler` plus `--update-interval-hours` serve options
- P4.1 manual update flow: `UpdateService.update_all()`, repository append support for newly discovered chapters, and `ndl update --all` for refreshing saved non-completed novels without refetching stored chapter bodies
- P4 update scheduling plan (`docs/superpowers/plans/2026-05-01-ndl-p4-update-scheduling.md`) splitting manual update logic, APScheduler integration, and Web-triggered update status
- P3.5 Web UI polish: empty-state hint pointing at the download form, and a result block on the download job page that renders the final output path and a link back to the saved library entry once the SSE stream emits the terminal status event
- P3.5 documentation pass: `docs/user-guide/README.md` now documents the library and serve commands, web download flow, disclaimer marker, and the `<NDL_HOME>/{library.db,disclaimer.accepted,downloads/}` state layout; `docs/index.md` and `README.zh-CN.md` reflect P2/P3 progress
- P3.4 `ndl serve` CLI with `--host`, `--port`, `--reload`, `--accept-disclaimer`, and `--allow-public-host`; defaults to localhost and refuses public binds unless explicitly allowed
- P3.4 CLI tests covering the serve disclaimer gate, uvicorn wrapper arguments, and public-host validation without starting a real server
- P3.3 Web download flow: homepage download form, URL-encoded form handling without `python-multipart`, in-memory download job registry, native EventSource progress rendering, and `/downloads/{job_id}/events` SSE endpoint
- P3.3 Web download tests: mocked HTTP web-triggered download persists to the temp library, no-save skips persistence, SSE emits progress/status events, and missing URL validation returns a user-visible error
- P3.2 read-only Web library views: list rows link to `/library/{id}`, detail pages render novel metadata and chapter titles/word counts without bodies, and missing IDs render a 404 error template
- P3.1 Web UI skeleton: `src/ndl/web/` FastAPI app factory, Jinja2 templates, static CSS, and TestClient coverage for the local library homepage
- P3 runtime dependencies: `fastapi>=0.110`, `uvicorn[standard]>=0.27`, `jinja2>=3.1`, and `sse-starlette>=2.0`
- P3 Web UI implementation plan (`docs/superpowers/plans/2026-05-01-ndl-p3-web-ui.md`) with approved dependency decisions and slices for app skeleton, read-only library views, download progress, `ndl serve`, and docs polish
- P2.4 library CLI: `ndl library list`, `ndl library show <id>`, and `ndl library remove <id> --yes`; list/show render Rich tables and `show` omits chapter bodies
- P2.4 CLI persistence coverage: `CliRunner` tests now isolate `library.db` with `NDL_HOME`, verify download auto-save, verify `--no-save`, and cover show/remove lifecycle
- P2.3 `LibraryService` (`src/ndl/application/services/library.py`): thin domain-facing wrapper over `LibraryRepository` with `save`/`list`/`get`/`remove`; `ServiceContainer` exposes a singleton `library_service()` that lazily provisions a SQLite engine + sessionmaker on first use
- P2.3 shared path helpers (`src/ndl/application/paths.py`): `ndl_home()` (respects `NDL_HOME`) and `library_db_path()` (`<NDL_HOME>/library.db`); `cli/disclaimer.py` now reuses them instead of re-implementing the resolution
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

- README status and usage now reflect that P2 library persistence is implemented and P3 Web UI is next
- `ndl download` now saves successful downloads into the local SQLite library after writing the requested output file; pass `--no-save` to preserve the old file-only behavior
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
