# AGENTS.md

## 0.2 release — downstream requirements (added 2026-05-23)

Before planning any 0.2 work, read **`docs/agents/downstream-feedback/2026-05-23-ndl-desktop.md`**. It is a 1,100-line, item-by-item improvement-requirements document authored by the downstream consumer `ndl-desktop`, derived from every workaround that downstream had to ship because this repo couldn't do something. It is organised into 9 parallel-safe tracks (A–I) with severity / effort tags, current behaviour (with file:line citations into this repo), proposed fixes with code sketches, acceptance criteria, and dependencies between items. Landing tracks A–E unblocks deleting ~1,200 lines of downstream adapter code.

Pick a track, follow it as the spec.

## Current handoff

Before changing code, read `docs/superpowers/SESSION-STATE.md` first. P0
through P7 are implemented, and v0.1.0 has been published as the PyPI
distribution `ndl-storykit`. The Python import path remains `ndl`, and the CLI
entry point remains `ndl`.

All P7 slices are implemented. `docs/superpowers/plans/2026-05-13-ndl-p7-release-candidate.md` records P7.1 distribution verifier, P7.2 release notes draft (`docs/release-notes/v0.1.md`), P7.3 install smoke strategy (`scripts/smoke_cli.py` + `docs/developer/release.md` + `tests/unit/scripts/test_smoke_cli.py`), and P7.4 release execution gate (`docs/developer/release.md` "Execution Gate" section + 11-step Maintainer Runbook). The completed P6 plan remains at `docs/superpowers/plans/2026-05-13-ndl-p6-browser-release.md`.

The current active plan is **`docs/superpowers/plans/2026-05-13-ndl-release-prep.md`**
(Phases A-E from release candidate to published v0.1.0). v0.1.0 and v0.2.0 have both shipped on PyPI; the 0.2.0 release rolled up the
11 downstream-driven tracks tracked in
`docs/agents/downstream-feedback/2026-05-23-ndl-desktop.md`. Current source
checkouts are back on the next development version, `0.3.0.dev0`.

For future releases, the execution gate remains hard: agents must not bump a
release version, insert a dated CHANGELOG heading, create a release commit,
create or push a tag, create a GitHub Release, or upload to PyPI. If the user
requests those actions, reply with the relevant step from
`docs/developer/release.md` and stop.

## Branch protection (since 2026-05-13)

`main` is protected. Direct pushes are rejected even for `makunxiang-cmd`'s account. Standard agent workflow for any code/doc change:

```bash
git checkout -b <topic-branch>
# edit, commit (pre-commit hook still runs ruff / mypy locally)
git push -u origin <topic-branch>
gh pr create --fill                # or --title / --body for tailored PR copy
gh pr merge --squash --auto        # 0 approvals required; CI is not a hard gate yet
```

Force-push to `main` and deletion of `main` are blocked. `enforce_admins = false` lets the maintainer override in true emergencies via the GitHub web UI; agents must not exploit this.

`gh` CLI is installed locally and authenticated as `makunxiang-cmd` (`gh auth status` to verify). A separate pre-release hardening plan at `docs/superpowers/plans/2026-05-13-ndl-p7-pre-release-hardening.md` records nine implemented P0/P1/P2 fixes that must ship with v0.1: append-only `LibraryRepository.save()`, fault-tolerant `SearchService.search()` returning `SearchOutcome`, capped `JobRegistry`, a per-`update_all()` fetcher pool inside `UpdateService`, the new `fetchers/_common.py` shared helpers, the `_safe_aclose`/`_safe_stop_manager` cleanup helpers in `BrowserFetcher`, event-driven SSE streaming via `asyncio.Event`, the new `ndl rules list` CLI, and concurrent + https-only fetches in `RuleUpdateService`.

Start by running:

```bash
git status --short
uv run pytest --cov=ndl --cov-report=term --cov-report=xml
```

Last verified release gates for v0.1.0: `uv lock --check`, `ruff`,
`ruff format --check`, `mypy src/ndl`, `pytest` (185 passed, coverage
88.96%), `pre-commit run --all-files`, `uv build --wheel --sdist`,
`scripts/verify_distribution.py`, and a clean PyPI install smoke for
`ndl-storykit==0.1.0`.

## Agent skills

### Issue tracker

Issues and PRDs live as markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical triage roles, default vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
