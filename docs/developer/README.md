# Developer Guide

## Current Status

P0 through P6 are implemented, and P7.1 release-candidate distribution verification is implemented. The project now has:

- Core domain models, protocols, progress events, and typed errors
- YAML rule schema, selector DSL, loader, and resolver
- HTTP fetcher with robots.txt, retry, rate-limit, and encoding policy
- Optional Playwright-backed browser fetcher selected by `fetcher.type: browser`, with declarative wait/viewport controls under `fetcher.browser`
- HTML index/chapter parsers and TXT reader
- TXT/EPUB writers and writer registry
- SQLite-backed library persistence (`src/ndl/storage/`), with `LibraryRepository`
  and a `LibraryService` exposed through `ServiceContainer.library_service()`
- Download/convert/library/update application services and a lightweight service container
- Typer CLI commands: `download`, `convert`, `rules validate`, `rules update`,
  `library list/show/remove`, `update --all`, `search`, `serve`, and `doctor browser`
- Local FastAPI/Jinja2 Web UI under `src/ndl/web/`: homepage library list,
  detail pages, search form/results, download form, update-all controls, and an SSE progress channel
- APScheduler-backed recurring update runs while `ndl serve` is active
- `SearchResult` domain model, `parse_search` HTML parser, and `SearchService.search(keyword, rule_ids=None) -> SearchOutcome` wired through `ServiceContainer.search_service()`. `SearchOutcome` exposes `results: list[SearchResult]` and `failures: list[SearchFailure]`; a single rule raising `NDLError` is captured as a failure and no longer aborts the multi-source search
- `ndl search` CLI rendering source/title/author/url tables, with optional `--rule` filters and `--limit`
- `RuleUpdateService` and `ndl rules update` for manifest-driven remote rule installation under `<NDL_HOME>/rules`, with full validation before activation
- `scripts/verify_distribution.py` for repeatable wheel/sdist resource and metadata checks before release-candidate review

P6 is complete and P7 is active. P6.1 added the optional browser fetcher foundation, P6.2 added browser-specific rule controls, P6.3 added browser runtime diagnostics, P6.4 added release hardening docs plus artifact verification, and P7.1 added a repeatable distribution verifier script. A separate pre-release hardening pass (`docs/superpowers/plans/2026-05-13-ndl-p7-pre-release-hardening.md`) landed alongside P7.1 with four P0 fixes:

- `LibraryRepository.save()` is now append-only on chapters: it merges metadata in place and only appends chapters whose `index` is not already stored, so a re-download that returns fewer chapters can no longer destroy library data; the row's `fetched_at` stays at first-seen time and `last_updated` advances only on real changes.
- `SearchService.search()` returns `SearchOutcome(results, failures)`; per-rule `NDLError` is captured as a `SearchFailure` instead of aborting the whole search. CLI prints a "Search failures" table and the Web `/search` page renders a failures section.
- `JobRegistry` has a default 100-job cap with FIFO eviction limited to terminal-status jobs; running/queued jobs are never evicted, so long-running `ndl serve` no longer leaks memory.
- `UpdateService.update_all()` opens an internal per-`rule.id` fetcher pool once, walks the eligible novels, and closes the pool at the end. Playwright cold-start, robots.txt re-fetch, and per-host throttle reset no longer recur for every saved novel under the same rule. `update_novel()` keeps its one-shot lifecycle.
- New `src/ndl/fetchers/_common.py` exposes `resolve_headers(rule)` and `backoff_delay(retry, attempt)`; `HttpFetcher` and `BrowserFetcher` both import from there instead of reaching across modules for dunder-private helpers.
- `BrowserFetcher` startup uses `_safe_aclose(resource)` / `_safe_stop_manager(manager)` (both `contextlib.suppress(Exception)`), so a failure during `async_playwright().start()` no longer skips `manager.stop()` and leak a partially-started subprocess.
- Web SSE streaming is event-driven: `DownloadJob` carries an `asyncio.Event`, `JobRegistry.record / mark_*` call `notify.set()`, and `JobRegistry.stream` awaits the event instead of polling — every progress update reaches the browser as soon as it is recorded.
- New `ndl rules list` CLI command prints the full id/name/version/enabled/search/fetcher/patterns table for all loaded rules.
- `RuleUpdateService.plan_update()` fetches each referenced rule concurrently and refuses non-https URLs by default; `NDL_RULES_ALLOW_INSECURE=1` allows `http` for local mirrors or testing only.

## Development Workflow

Use `uv` for dependency management and command execution:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy src/ndl
uv run pytest --cov=ndl --cov-report=term --cov-report=xml
uv run pre-commit run --all-files
```

All slices should keep these gates green.

For release-specific preflight, artifact inspection, and publication steps, see
[`release.md`](release.md).

### CI behavior

`.github/workflows/ci.yml` runs lint + a 3-OS × 3-Python test matrix on every push/PR to `main`, **except** when the change touches only docs or metadata. The `paths-ignore` list covers `**/*.md`, `docs/**`, `site/**`, `LICENSE`, `.gitignore`, and `.editorconfig`. Any other path (including `pyproject.toml`, `uv.lock`, the workflow file itself, or anything under `src/` or `tests/`) re-enables the full run.

If you later add CI as a required check under `main` branch protection, switch the doc-only paths to a skip job (a no-op job with the same name as the required check) instead of `paths-ignore` — otherwise doc-only PRs will block on a check that never reports.

## Architecture Map

- `src/ndl/core/`: domain objects, protocols, progress events, and error hierarchy
- `src/ndl/rules/`: source rule schema, loading, resolution, and selector execution
- `src/ndl/fetchers/`: HTTP and optional browser fetching infrastructure
- `src/ndl/parsers/`: HTML parsers and TXT reader
- `src/ndl/converters/`: TXT/EPUB writers and writer registry
- `src/ndl/storage/`: SQLAlchemy 2.0 models, engine factory, sessionmaker, and `LibraryRepository`
- `src/ndl/application/`: download/convert/library/update services and dependency wiring
- `src/ndl/scheduler/`: APScheduler wrapper for recurring update jobs
- `src/ndl/cli/`: Typer command surface and disclaimer gate
- `src/ndl/web/`: FastAPI app factory, Jinja2 templates, hand-written CSS, native EventSource JS, and the in-memory job registry
- `tests/unit/`: mirrors source package structure
- `tests/contract/`: bundled rule fixtures and contract tests

## Implementation Style

- Keep modules flat and small; one responsibility per file.
- Prefer pure functions for logic and thin classes for Protocol implementations.
- Keep `from __future__ import annotations` at the top of every Python module (including `__init__.py` / `__main__.py`).
- Preserve Python 3.10 compatibility (mypy `python_version = "3.10"`); do not use `Self` or other 3.11+ syntax. The CI matrix runs Python 3.10 through 3.14 across ubuntu / windows / macOS.
- Raise errors from `src/ndl/core/errors.py`; do not invent unrelated exception hierarchies.
- Avoid real network access in tests; use fixtures and `respx`.

### `ServiceContainer` lifecycle

`ServiceContainer` lazily creates a SQLAlchemy engine the first time `library_service()` (or anything that depends on it) is called. The engine must be disposed when the container goes out of scope, otherwise SQLite connections leak — Python 3.14's sqlite3 finalizer turns this into `ResourceWarning: unclosed database` during tests.

The container exposes `close()` plus the context-manager protocol. Use one of the following patterns:

```python
# CLI / scripts: prefer `with`
with ServiceContainer() as container:
    summaries = container.library_service().list()

# Tests with multiple containers: factory fixture that disposes at teardown
@pytest.fixture
def make_container() -> Iterator[Callable[..., ServiceContainer]]:
    created: list[ServiceContainer] = []
    def factory(**kwargs: Any) -> ServiceContainer:
        c = ServiceContainer(**kwargs)
        created.append(c)
        return c
    yield factory
    for c in created:
        c.close()

# Web app factory: lifespan handles disposal automatically
# (see src/ndl/web/app.py — `service_container.close()` runs in lifespan finally)
```

`close()` is idempotent and a no-op when no engine has been created (e.g. `rules validate`, `search` without a database hit).

## Agent Handoff

Before starting new work, read:

1. `docs/superpowers/SESSION-STATE.md`
2. The active P7 plan (`docs/superpowers/plans/2026-05-13-ndl-p7-release-candidate.md`)
3. The completed P6 plan (`docs/superpowers/plans/2026-05-13-ndl-p6-browser-release.md`)
4. The completed P5 plan (`docs/superpowers/plans/2026-05-01-ndl-p5-search-rules.md`)
5. `AGENTS.md`

`git log --oneline` is the authoritative record of committed work. At the current handoff, the working tree is expected to contain uncommitted P5.1-P5.4 implementation, Python 3.14 cleanup, documentation updates, P6.1-P6.4 browser/release work, P7.1 distribution verification work, and the four pre-release P0 hardening fixes (`docs/superpowers/plans/2026-05-13-ndl-p7-pre-release-hardening.md`); inspect with `git status --short` before editing and do not discard them.

P7 is the active milestone. Do not bump versions, tag, publish to GitHub Releases, or upload to PyPI without explicit maintainer approval.
