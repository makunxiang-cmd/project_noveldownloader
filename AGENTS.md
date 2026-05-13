# AGENTS.md

## Current handoff

Before changing code, read `docs/superpowers/SESSION-STATE.md` first. P0 through P6 are implemented, and P7.1 release-candidate distribution verification is implemented: scaffold, MVP download/convert, library persistence, local Web UI, update scheduling, search, remote rule updates, Web search, rule-selected browser fetching infrastructure, browser rule controls, browser runtime diagnostics, release hardening docs, and repeatable wheel/sdist verification.

The active plan is `docs/superpowers/plans/2026-05-13-ndl-p7-release-candidate.md`. P7.1 (distribution verifier) and P7.2 (release notes draft at `docs/release-notes/v0.1.md`) are implemented; next planned slices are P7.3 install smoke strategy and P7.4 release execution gate. The completed P6 plan remains at `docs/superpowers/plans/2026-05-13-ndl-p6-browser-release.md`. A separate pre-release hardening plan at `docs/superpowers/plans/2026-05-13-ndl-p7-pre-release-hardening.md` records nine implemented P0/P1/P2 fixes that must ship with v0.1: append-only `LibraryRepository.save()`, fault-tolerant `SearchService.search()` returning `SearchOutcome`, capped `JobRegistry`, a per-`update_all()` fetcher pool inside `UpdateService`, the new `fetchers/_common.py` shared helpers, the `_safe_aclose`/`_safe_stop_manager` cleanup helpers in `BrowserFetcher`, event-driven SSE streaming via `asyncio.Event`, the new `ndl rules list` CLI, and concurrent + https-only fetches in `RuleUpdateService`.

The working tree is intentionally dirty at handoff time: it contains the implemented P5.1-P5.4 changes, related Python 3.14/SQLite cleanup, documentation updates, P6.1-P6.4 browser/release work, P7.1 distribution verification work, and the four pre-release hardening fixes above. Do not discard these changes. Start by running:

```bash
git status --short
uv run pytest --cov=ndl --cov-report=term --cov-report=xml
```

Last verified quality gates after the pre-release P0/P1/P2 hardening: `ruff`, `ruff format --check`, `mypy src/ndl`, and `pytest` (184 passed, coverage 88.96%). `pre-commit run --all-files` and `uv lock --check` have not been re-run since the hardening landed. P7.1 previously also verified `uv build --wheel --sdist --out-dir /private/tmp/ndl-p7-dist` plus `scripts/verify_distribution.py` against the built artifacts.

## Agent skills

### Issue tracker

Issues and PRDs live as markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical triage roles, default vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
