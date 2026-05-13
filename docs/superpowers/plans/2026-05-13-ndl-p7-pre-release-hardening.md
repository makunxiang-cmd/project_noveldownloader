# NDL P7 Pre-release Reliability Hardening

> Status: implemented. Targeted maintenance fixes landed alongside the active P7 release-candidate work; they are not part of P7.1-P7.4 but must ship before v0.1.
>
> Handoff note, 2026-05-13: every slice in this plan is implemented and verified (P0.1-P0.4 correctness/durability, P1.1-P1.2 fetcher cleanup, P2.1-P2.3 SSE/CLI/RuleUpdate hardening). Treat the active milestone as the P7 release-candidate plan; this document is a record of completed hardening.

## Goal

Close four correctness/durability gaps surfaced by a code review before the v0.1 release candidate is published:

- `ndl download` of the same URL must not destroy already-stored chapters.
- `ndl search` and `/search` must not let a single failing source erase all other sources' results.
- `ndl serve` running for days must not leak download-job memory.
- `ndl update --all` and the Web update flow must not pay a fresh fetcher (Playwright + robots + throttle) cost per saved novel.

Compliance boundaries are unchanged: no real-site test traffic, no new dependencies, mocks only.

## Reference

- Active release plan: `docs/superpowers/plans/2026-05-13-ndl-p7-release-candidate.md`
- Completed: P5 search/remote-rule plan, P6 browser/release plan
- Engineering style memory: zero redundant comments, mypy `--strict`, no broad excepts

## Implemented Slices

### P0.1 LibraryRepository append-only upsert

Status: implemented.

Scope:

- `LibraryRepository.save()` no longer calls `row.chapters.clear()` on an existing match. Metadata is updated in place; chapters are appended only when their `index` is not already stored.
- `row.fetched_at` is preserved as the first-seen timestamp. `row.last_updated` advances on newly appended chapters (or when only `novel.last_updated` is explicitly provided).
- Two regression tests cover: (a) a shrunk redownload does not delete stored chapters, (b) original `fetched_at` survives a second `save()`.

Exit criteria:

- Existing `test_save_is_upsert_on_rule_and_url` still passes (length-based assertion remains correct under append semantics).
- New regression tests in `tests/unit/storage/test_repository.py` pass.

### P0.2 SearchService multi-source fault tolerance

Status: implemented.

Scope:

- `SearchService.search()` now returns `SearchOutcome(results: list[SearchResult], failures: list[SearchFailure])`.
- Per-rule `NDLError` is captured as a `SearchFailure(rule_id, source_name, message)` and logged at warning level; successful sources are still returned.
- CLI prints a secondary "Search failures" Rich table when failures are non-empty. Web search results template renders a `<section class="search-failures">` listing each failure.
- Tests cover: aggregate success path, all-rules-failed path, mixed success+failure path, and the existing keyword/rule-filter/empty paths under the new return type.

Exit criteria:

- Existing search tests adapted to `outcome.results` / `outcome.failures` access.
- New tests for partial failure paths pass.

### P0.3 JobRegistry capped eviction

Status: implemented.

Scope:

- `JobRegistry.__init__` accepts `max_jobs: int = 100`; storage upgraded to `OrderedDict`.
- `create()` evicts the oldest job whose status is in `{succeeded, failed}` when at capacity; running/queued jobs are never evicted (the registry may briefly exceed `max_jobs` when many jobs are active).
- Tests in `tests/unit/web/test_jobs.py` cover both eviction and "no terminal jobs → keep all active" behaviors.

Exit criteria:

- Long-lived `ndl serve` no longer accumulates terminated jobs forever.

### P0.4 UpdateService fetcher pool

Status: implemented.

Scope:

- New private `_FetcherPool` inside `application/services/update.py` caches one fetcher per `rule.id` and exposes `aclose()`.
- `update_all()` opens one pool, walks eligible summaries, and closes the pool once at the end; per-novel `NDLError` is mapped to a failed `UpdateResult` without aborting the batch.
- `update_novel(novel_id)` keeps its one-shot lifecycle by creating and disposing its own pool.
- A new test verifies that two saved novels under the same rule trigger exactly one fetcher build and that the fetcher is closed at end of `update_all`.

Exit criteria:

- Playwright cold-start, robots.txt re-fetch, and throttle reset no longer recur per novel.
- The existing append-only update test still passes.

### P1.1 fetchers private-helper refactor

Status: implemented.

Scope:

- New `src/ndl/fetchers/_common.py` exposes `resolve_headers(rule)` and `backoff_delay(retry, attempt)`.
- `HttpFetcher` and `BrowserFetcher` both import from `_common`; the cross-module import of dunder-private `_backoff_delay` / `_resolve_headers` from `fetchers/http.py` is gone.

Exit criteria:

- No fetcher imports a leading-underscore symbol from a sibling module.

### P1.2 BrowserFetcher startup cleanup

Status: implemented.

Scope:

- `_playwright_session` and `check_browser_runtime` now call new `_safe_aclose(resource)` and `_safe_stop_manager(manager)` helpers, both of which use `contextlib.suppress(Exception)` so secondary failures do not mask the original error.
- `manager.stop()` is invoked unconditionally on the failure path (previously skipped when `manager.start()` itself raised, leaking Playwright subprocesses).
- A unit test exercises `_safe_aclose` / `_safe_stop_manager` against a resource whose close/stop raises.

Exit criteria:

- A failed `manager.start()` no longer leaks a partially-started Playwright process.

### P2.1 SSE event-driven streaming

Status: implemented.

Scope:

- `DownloadJob` gains an `asyncio.Event notify` field.
- `JobRegistry.record / mark_running / mark_succeeded / mark_failed` all call `notify.set()`.
- `JobRegistry.stream` replaces `await asyncio.sleep(0.1)` with `notify.clear()` + `await notify.wait()`; no busy polling, sub-millisecond wake on each new event/state change.
- A new test forces `mark_succeeded` from a separate task and asserts the stream resumes immediately with the terminal `status` event.

Exit criteria:

- No `sleep`-based polling remains in the SSE path.
- The existing download SSE end-to-end test still passes.

### P2.2 `ndl rules list` CLI

Status: implemented.

Scope:

- New `@rules_app.command("list")` that prints a Rich table of `id / name / version / enabled / search / fetcher / patterns` for every loaded rule.
- Closes the documentation contract in `RuleNotFoundError.detail`, which already pointed users at `ndl rules list`.
- CLI test verifies the builtin `example_static` rule shows up.

Exit criteria:

- `ndl rules list` exits 0 and prints at least the bundled rule id.

### P2.3 RuleUpdateService concurrent fetch + https-only whitelist

Status: implemented.

Scope:

- `plan_update` fetches all referenced rule URLs concurrently via `asyncio.gather` (preserves order, validation still all-or-nothing).
- Manifest URL and each resolved rule URL must use `https`; otherwise `InvalidArgumentError` is raised with the offending URL. Environment variable `NDL_RULES_ALLOW_INSECURE=1` allows `http` (for local mirrors or testing only).
- Two new tests cover the http rejection path and the insecure-override path.

Exit criteria:

- Multi-rule manifests no longer pay sequential network round trips.
- A manifest URL using `http://` is rejected by default.

## Non-goals

- Web `/updates` background-task migration — evaluated, deferred. Rationale: P0.4 fetcher pool already cut update latency materially; typical local libraries under 50 novels finish within seconds; introducing `UpdateJobRegistry` + SSE + new templates (~150-200 lines) does not belong in the P7 release-candidate window. Tracked for a future UX batch alongside SSE polling replacement, `rules list` CLI, and `RuleUpdateService` parallelism.
- `Novel.cover_url` validator — evaluated, no change. The current `HttpUrl(value)` side-effect validation is idiomatic in pydantic v2, and the project intentionally preserves the un-normalized cover URL so cache keys downstream remain stable.
- `RuleUpdateService` rule-removal semantics (prune local user-installed rules dropped from manifest) — deferred. Needs a clearer policy decision: which rules are "owned" by the manifest vs. independently installed by the user. Tracked for a future P3 batch.
- `cli/renderers.py` coverage (33%) — deferred. Rich terminal rendering is hard to test without using Rich's recording API; not blocking release.
- `_fetch_chapter` duplication between `download.py` and `update.py` — deferred. Minor; extraction adds risk without functional gain.

## Quality Gates

After all four slices:

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src/ndl
.venv/bin/pytest --cov=ndl --cov-report=term
```

Last verified (after P0.1-P0.4 + P1.1-P1.2 + P2.1-P2.3): ruff ✅ ruff format ✅ mypy ✅ pytest 184 passed ✅ coverage 88.96%.
