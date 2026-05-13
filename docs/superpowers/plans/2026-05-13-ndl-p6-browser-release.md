# NDL P6 Browser Fetcher and Release Hardening Plan

> Status: implemented. P6 followed completed P5 search/rule-update work and is no longer the active plan.
>
> Handoff note, 2026-05-13: P6.1 through P6.4 are implemented. Keep Playwright optional and avoid real-site traffic in tests.

## Goal

Support rule-selected browser rendering for JavaScript-heavy public-domain pages while preparing the project for a v0.1 release:

```bash
pip install ndl[browser]
ndl download "https://example.test/js-index" -o book.epub
```

P6 must preserve the project boundaries: no commercial platform support, no login/CAPTCHA/paywall bypass, no Cloudflare challenge bypass, no proxy-pool behavior, and no real-site traffic in automated tests.

## Reference

- Design spec: `docs/superpowers/specs/2026-04-20-ndl-design.md` §4.1, §5, §8.2, §11.3
- Current handoff: `docs/superpowers/SESSION-STATE.md`
- Completed base: P1-P5 download, persistence, Web UI, updates, search, and remote rule updates

## Proposed Slices

### P6.1 Optional Browser Fetcher Foundation

Status: implemented.

Scope:

- Add optional `browser` extra with Playwright
- Add `BrowserFetcher` implementing the existing `Fetcher` protocol
- Route `fetcher.type: browser` through `ServiceContainer`
- Fail clearly when Playwright is not installed or browser launch/rendering fails
- Keep tests isolated with fakes/mocks; no browser download and no real network
- Preserve existing robots, per-host rate limit, and retry boundaries on the browser path

Exit criteria:

- Unit tests cover browser fetcher lifecycle, rendered HTML return, missing optional dependency, timeout/error wrapping, and container routing
- Existing HTTP fetcher behavior remains unchanged

### P6.2 Browser Rule Capabilities

Status: implemented.

Scope:

- Extend rule schema only where browser behavior needs declarative controls
- Candidate controls: wait state, selector wait, navigation timeout, extra delay, viewport, JavaScript enabled
- Keep defaults conservative and compatible with existing rules

Exit criteria:

- Rule validation rejects unsafe/unknown browser controls
- Browser fetcher consumes schema settings without affecting HTTP rules

### P6.3 CLI/Web Documentation and Diagnostics

Status: implemented.

Scope:

- Document `ndl[browser]` installation and `playwright install chromium`
- Add user-facing diagnostics for missing browser runtime
- Keep Web UI behavior unchanged except for clearer fetch failures

Exit criteria:

- README, user guide, developer docs, changelog, and session state explain browser support and boundaries

### P6.4 Release Hardening

Status: implemented.

Scope:

- Review package metadata and wheel contents
- Add release checklist and preflight commands
- Document that `0.1.0.dev0` remains until a maintainer explicitly approves the v0.1 release commit/tag/publication

Exit criteria:

- Release checklist is explicit enough for a human maintainer to run
- Quality gates remain green

## Non-goals

- Bundled public browser rules for commercial or protected sites
- CAPTCHA solving, login automation, Cloudflare challenge bypass, proxy pools
- Real website integration tests
- Headful browser UI automation from the local Web app

## Quality Gates

Every slice must pass:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/ndl
uv run pytest --cov=ndl --cov-report=term --cov-report=xml
uv run pre-commit run --all-files
```
