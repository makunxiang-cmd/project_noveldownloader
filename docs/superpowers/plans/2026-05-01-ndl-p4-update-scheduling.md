# NDL P4 Update Scheduling Plan

> Status: implemented. P4 adds reusable update logic first, then wires scheduled background runs and manual update controls into the local Web server.

## Goal

Let users refresh saved ongoing novels without redownloading every chapter:

```bash
ndl update --all --accept-disclaimer
```

P4 must preserve the existing P1-P3 constraints: first-run disclaimer, robots.txt enforcement, per-host rate limits, no real-site test traffic, and no bypass features.

## Reference

- Design spec: `docs/superpowers/specs/2026-04-20-ndl-design.md` §4.1, §4.3.2, §4.4
- Current handoff: `docs/superpowers/SESSION-STATE.md`
- Completed dependency base: P2 library persistence and P3 Web UI

## Dependency Decision

P4.1 does not need new dependencies. It adds the manual update service and CLI path.

APScheduler remains approved for P4.2:

- `apscheduler>=3.10` — recurring update trigger shared with `ndl serve`

Do not introduce APScheduler until the update service has a covered manual path.

## Proposed Slices

### P4.1 Manual Update Service + CLI

Status: implemented.

Scope:

- Add `UpdateService.update_novel()` and `UpdateService.update_all()`
- Compare latest index stubs against stored chapter indices
- Fetch only newly discovered chapters
- Append new chapters through `LibraryRepository`
- Add `ndl update --all`

Exit criteria:

- Unit tests cover appending only missing chapters
- CLI tests use mocked HTTP only
- Quality gates remain green

Notes:

- `update_all()` skips completed novels and library rows without `source_url`.
- Individual failures should be represented in results so one bad novel does not abort the whole `--all` run.
- Implemented with `UpdateService`, `LibraryRepository.append_chapters()`, `ServiceContainer.update_service()`, and `ndl update --all`.
- Tests cover service-level append-only behavior, skipped completed/sourceless rows, and CLI update with mocked HTTP.

### P4.2 Scheduled Runs Under `ndl serve`

Status: implemented.

Scope:

- Add APScheduler dependency
- Start an AsyncIOScheduler from the Web app lifespan
- Default interval: 6 hours
- Provide a local-only configuration switch or setting for interval/disabled state

Exit criteria:

- Scheduler does not start in tests unless explicitly enabled
- Manual CLI and scheduled Web path call the same `UpdateService.update_all()`

Notes:

- Implemented with `src/ndl/scheduler/update_job.py`, an APScheduler-backed wrapper around a single `update_all` coroutine.
- `create_app()` keeps scheduling disabled by default for tests and direct app-factory use.
- `ndl serve` targets `create_serve_app()` and enables scheduling by default after the existing disclaimer gate; users can pass `--no-scheduler` or adjust `--update-interval-hours`.

### P4.3 Web Update Trigger + Status

Status: implemented.

Scope:

- Add a Web button for manual update-all
- Surface update results in the same dense local UI style
- Reuse existing SSE/progress patterns where practical

Exit criteria:

- TestClient covers Web-triggered update with mocked fetcher/parser
- Failed rows show user-safe errors, not tracebacks

Notes:

- Implemented with a homepage `Update all` form posting to `/updates`.
- `/updates` calls `service_container.update_service().update_all()` and renders a per-novel result table with status, new count, total count, and message.
- TestClient coverage verifies append-only update behavior and empty-library status with mocked HTTP only.

## Non-goals

- Search UI (`ndl search`) — P5
- Remote rule updates — P5
- Browser fetcher / Playwright — P6
- Cloudflare, CAPTCHA, login, paywall, or proxy support — permanently out of scope

## Quality Gates

Every slice must pass:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/ndl
uv run pytest --cov=ndl --cov-report=term --cov-report=xml
uv run pre-commit run --all-files
```
