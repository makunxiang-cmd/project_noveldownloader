# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Post-release housekeeping: development version advanced to `0.2.0.dev0`,
  release notes are no longer marked draft, README/user docs now point at the
  live `pip install ndl-storykit` flow, and handoff docs record the v0.1.0
  GitHub/PyPI publication.
- Public documentation status refreshed after the v0.1.0 release: README,
  MkDocs home, developer guide, release runbook, and public design-spec note
  now describe the published `ndl-storykit` package and the active
  `0.2.0.dev0` development cycle instead of the earlier P7 release-candidate
  state.

### Added

- Rule pagination is now consumed by `DownloadService`: index pages can follow
  `pagination.type: next` links or `pagination.type: index-template` URL
  templates with URL de-duplication and cycle guards, and chapter pages can
  follow same-chapter `next` links to merge split chapter bodies.
- Rules can declare `download_archive` for whole-book TXT archives. URL-template
  archives fetch raw bytes through HTTP, browser selector archives capture a
  Playwright download, and `DownloadService` decodes, strips, and splits the TXT
  against index chapter titles.

### Fixed

- Browser-backed fetches now stop the started Playwright runtime instead of
  calling `stop()` on the `async_playwright()` context manager, fixing shutdown
  crashes and cleanup leaks on normal fetches, startup failures, and
  `ndl doctor browser` runtime checks.

## [0.1.0] - 2026-05-13

### Changed

- PyPI distribution name renamed from `ndl` to **`ndl-storykit`**: the original `ndl` PyPI name has been registered since 2016 by an unrelated abandoned project (`msull/needle`). The Python import path (`from ndl...`) and the CLI entry point (`ndl ...`) are unchanged. After v0.1 ships, users install with `pip install ndl-storykit` and `pip install 'ndl-storykit[browser]'`. All in-repo docs, error messages, release notes, and tests are updated; `uv.lock` regenerated; built wheel/sdist verified end-to-end via `scripts/verify_distribution.py` + a clean-venv `scripts/smoke_cli.py`.
- `RuleUpdateService.plan_update()` now fetches every rule referenced by the manifest concurrently via `asyncio.gather`, replacing the previous sequential loop; ordering and all-or-nothing validation are preserved.
- `SearchService.search()` now returns `SearchOutcome(results, failures)` instead of `list[SearchResult]`; per-rule `NDLError` no longer aborts the whole multi-source search but is captured as a `SearchFailure(rule_id, source_name, message)` entry. CLI renders a secondary "Search failures" table and the Web `/search` result page renders a failures section.
- `UpdateService.update_all()` now reuses one fetcher per rule across all eligible novels via an internal `_FetcherPool`, eliminating per-novel Playwright cold-start, repeated robots.txt fetches, and per-host throttle resets when the library spans many novels under one rule. Standalone `update_novel()` keeps the one-shot lifecycle.
- `ServiceContainer` is now a context manager (`__enter__`/`__exit__` plus an explicit `close()` method) that disposes the lazily-created SQLAlchemy engine; CLI commands and tests that instantiate `ServiceContainer()` directly should use `with ServiceContainer() as container:` (or call `container.close()`) so the underlying SQLite connection pool is released. Web `lifespan` already disposes the container on shutdown.
- CLI commands (`ndl library list/show/remove`, `download`, `convert`, `update --all`) and helper functions in `cli/main.py` now wrap `ServiceContainer()` in `with` blocks; web/cli/storage tests refactored to a `make_container` fixture / `engine` fixture pattern that disposes engines at teardown
- Test suite: `tests/unit/storage/test_database.py` rewritten to use `engine` / `factory` fixtures with explicit `engine.dispose()`; `tests/unit/web/test_app.py` adopts a `make_container` factory fixture; `tests/unit/cli/test_main.py`, `tests/unit/application/test_container.py`, `tests/unit/application/services/test_update.py` refactored to `with ServiceContainer()`
- `pyproject.toml` classifiers extended with Python 3.13 and 3.14; `.github/workflows/ci.yml` test matrix expanded from `[3.10, 3.11, 3.12]` to `[3.10, 3.11, 3.12, 3.13, 3.14]` across ubuntu/windows/macOS
- All `__init__.py` and `__main__.py` modules now include `from __future__ import annotations` for consistency with the project convention
- README.md, README.zh-CN.md, docs/index.md, docs/developer/README.md, AGENTS.md, user/developer docs, plans, ADRs, and session state updated to reflect P0-P6 completion, P7.1 distribution verification, and P7.2 as the next handoff slice
- CI workflow (`.github/workflows/ci.yml`) now skips runs when a push or PR only touches docs/license/editor metadata (`**/*.md`, `docs/**`, `site/**`, `LICENSE`, `.gitignore`, `.editorconfig`); any source/test/dependency change still triggers the full lint + 9-cell test matrix. Note: do **not** mark CI as a required check on `main` branch protection until the skipped runs are accounted for, otherwise doc-only PRs will block on a never-reported status.

### Added

- P7.4 release execution gate documentation: `docs/developer/release.md` gains an explicit "Execution Gate" section with an actions table (anyone vs maintainer-only) and an 11-step Maintainer Runbook for v0.1.0 (version bump, dated CHANGELOG heading, release commit, tag, push, GitHub Release, PyPI upload). The doc states that automated agents must stop at the gate and reply with the relevant runbook step regardless of how a release-mutating request is phrased.
- P7.3 post-install smoke: new `scripts/smoke_cli.py` exercises `ndl --version`, `ndl rules list`, `ndl rules validate <bundled rule>`, and `ndl doctor browser` (with `--browser` to assert the runtime is wired up) against any environment where the `ndl` entry point resolves. No real network calls. `tests/unit/scripts/test_smoke_cli.py` runs the smoke against the dev environment to keep the contract from drifting. `docs/developer/release.md` documents the release-time invocation against a clean venv plus the optional browser smoke command.
- P7.2 release notes page at `docs/release-notes/v0.1.md`, plus a `Release Notes → v0.1` nav entry in `docs/mkdocs.yml`. Single-page user-facing summary of v0.1 with highlights, compliance boundaries, quick start, reliability hardening, what's-not-included, quality snapshot, and the maintainer-only execution gate.
- `ndl rules list` CLI command renders a Rich table of all loaded rules (id / name / version / enabled / search / fetcher type / pattern count). Closes the documentation gap referenced by `RuleNotFoundError`'s "Try `ndl rules list`" hint.
- `RuleUpdateService` now requires `https` for both the manifest URL and every resolved rule URL by default; set `NDL_RULES_ALLOW_INSECURE=1` to allow `http` for local mirrors or testing.

### Fixed

- Web SSE progress streaming no longer polls with `await asyncio.sleep(0.1)`. `DownloadJob` carries an `asyncio.Event` set by `record / mark_running / mark_succeeded / mark_failed`; `JobRegistry.stream` awaits the event, so every progress update reaches the browser as soon as it is recorded and the registry no longer wakes idle every 100 ms.
- `BrowserFetcher` startup error path no longer leaks a partially-started Playwright manager. `_playwright_session` and `check_browser_runtime` now use `_safe_aclose(resource)` and `_safe_stop_manager(manager)` (both `contextlib.suppress(Exception)`); `manager.stop()` is invoked unconditionally so a failure during `manager.start()` itself no longer skips cleanup.
- `fetchers/browser.py` no longer reaches into `fetchers/http.py` for dunder-private helpers. `resolve_headers(rule)` and `backoff_delay(retry, attempt)` now live in the new `fetchers/_common.py` module and both fetchers import from there.
- `LibraryRepository.save()` no longer wipes existing chapters when an upsert resolves the same `(source_rule_id, source_url)`. The save path now updates metadata in place and only appends chapters whose `index` is not yet stored, so a redownload that returns fewer or reordered chapters can no longer destroy library data. `row.fetched_at` is preserved as the first-seen timestamp; `row.last_updated` advances when new chapters are appended.
- `SearchService` no longer fails the entire multi-source search when one rule raises `NDLError`. Successful sources are still returned alongside captured per-rule failures, and CLI/Web surfaces show both.
- `JobRegistry` no longer grows unbounded for the lifetime of `ndl serve`. The registry now has a default 100-job cap with FIFO eviction limited to jobs in terminal states (`succeeded`/`failed`); running/queued jobs are never evicted, so the registry may briefly exceed the cap when many jobs are active.
- `UpdateService.update_all()` previously created a new fetcher per saved novel, which forced a fresh Playwright launch, robots.txt fetch, and host throttle for every entry under the same rule. The internal fetcher pool (see Changed) reuses one fetcher per rule for the full batch and closes them once on completion.
- SQLite `ResourceWarning: unclosed database` (11 → 0) emitted on Python 3.14 during `pytest --cov` runs. Root cause: `ServiceContainer` lazily created SQLAlchemy engines that were never disposed; the CLI and web tests created multiple containers per test, accumulating leaked sqlite3 connection handles which Python 3.14's stricter sqlite3 finalizer surfaced. Fixed via the new `ServiceContainer.close()` context manager (see Changed) and matching test refactors.

### Added

- P7.1 release-candidate verification: new `scripts/verify_distribution.py` performs repeatable stdlib-only wheel/sdist checks for required builtin rule and Web UI resources plus wheel metadata/extras; release checklist now references the verifier, and unit tests cover both success and missing-member failure output
- P6.4 release hardening: new `docs/developer/release.md` checklist documents v0.1 version decision, full preflight gates, optional browser smoke check, artifact build/inspection commands, expected wheel contents, PyPI publication steps, and compliance boundaries; local build verification confirmed wheel/sdist include builtin rules, Web templates/static assets, and the `browser` extra metadata
- P6.3 browser diagnostics: new `ndl doctor browser` command checks the optional Playwright package and Chromium runtime, browser startup failures now include the `ndl[browser]` / `uv sync --extra browser` and `playwright install chromium` guidance, and Web download job failures surface that same diagnostic detail through the existing SSE status event
- P6.2 browser rule controls: rules can now declare `fetcher.browser.navigation_timeout_ms`, `wait_until`, `wait_for_selector`, `extra_wait_ms`, `viewport`, and `javascript_enabled`; `BrowserFetcher` passes those controls into Playwright navigation/context calls while HTTP rules remain compatible
- P6.1 optional browser fetcher foundation: `BrowserFetcher` implements the existing `Fetcher` protocol with Playwright loaded only from the `browser` extra, `ServiceContainer` routes `fetcher.type: browser` rules to it, and tests cover rendered HTML return, lifecycle, retry, robots blocking, HTTP errors, missing optional dependency diagnostics, and default HTTP/browser routing without real browser downloads or real-site traffic
- Optional dependency extra `browser = ["playwright>=1.40"]`; browser rules require installing the extra plus `playwright install chromium`
- P6 browser/release plan (`docs/superpowers/plans/2026-05-13-ndl-p6-browser-release.md`) covering browser fetcher foundation, browser rule controls, diagnostics/docs, and release hardening
- P5.4 Web search surface: homepage search form, `/search` result page, Web result table with source/title/author/url, per-result Download actions wired to the existing Web download flow, and TestClient coverage for results, rule filtering, limits, empty state, and invalid input without real network access
- P5.3 remote rule updates: `<NDL_HOME>/rules` user-installed rule directory, default rule loading with user overrides, `RuleUpdateService` for manifest-driven remote rule downloads with optional SHA-256 checks, all-or-nothing validation before activation, and `ndl rules update --manifest-url ...` with summary table plus confirmation gate
- P5.2 `ndl search` CLI: keyword search over enabled rules with declarative search endpoints, Rich table output (`source/title/author/url`), repeatable `--rule` filtering, `--limit` row truncation, empty-result messaging, and validation for blank keywords or unsupported rule ids; CliRunner coverage uses mocked HTTP only
- P5.1 search domain and service: `SearchResult` domain model in `core/models.py`, `parse_search` HTML parser in `parsers/html_search.py`, and `SearchService.search(keyword, rule_ids=None)` in `application/services/search.py`; `ServiceContainer.search_service()` wires dependencies; `example_static` builtin rule extended with a declarative `search` block; 12 new unit tests across parsers and services cover field extraction, URL encoding, rule filtering, empty results, and missing containers
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
