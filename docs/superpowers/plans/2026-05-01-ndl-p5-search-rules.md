# NDL P5 Search and Remote Rules Plan

> Status: planned. P5 adds rule-defined search and compliant remote rule updates after P4 library update flows.

## Goal

Let users discover supported public-domain sources and keep declarative YAML rules current:

```bash
ndl search "keyword"
ndl rules update
```

P5 must preserve the existing compliance constraints: no commercial platform support, no login/CAPTCHA/paywall bypass, no real-site test traffic, and user-confirmed remote rule updates.

## Reference

- Design spec: `docs/superpowers/specs/2026-04-20-ndl-design.md` §4.1, §5, §8.2, §11.3
- Current handoff: `docs/superpowers/SESSION-STATE.md`
- Completed base: P1 rule schema/fetch/parse, P2 library, P3 Web UI, P4 update flows

## Proposed Slices

### P5.1 Search Domain + Service

Status: planned.

Scope:

- Add search result domain model
- Extend rules only as needed for declarative search endpoint metadata
- Add `SearchService.search(keyword, rule_ids=None)`
- Keep tests fixture-backed and mocked

Exit criteria:

- Search service returns normalized results from a bundled fixture rule
- No real network access in tests

### P5.2 `ndl search`

Status: planned.

Scope:

- Add CLI command for keyword search
- Render source/title/author/url table
- Validate empty keyword and unsupported rule selection

Exit criteria:

- CliRunner covers mocked search results and empty result state

### P5.3 Remote Rule Update

Status: planned.

Scope:

- Add a rules directory under `NDL_HOME`
- Fetch remote rule manifest declaratively
- Show diff/summary and require confirmation before writing
- Validate all downloaded rules before activation

Exit criteria:

- Tests use local fixtures or mocked HTTP only
- Invalid remote rule bundles never replace current rules

### P5.4 Web Search Surface

Status: planned.

Scope:

- Add local Web search form/results
- Link results to existing download form workflow where practical

Exit criteria:

- TestClient covers search results without real network access

## Non-goals

- Browser-backed search/fetch for JS-heavy sites — P6
- Commercial platforms, Cloudflare bypass, CAPTCHA solving, login, paywall, proxy pools — permanently out of scope

## Quality Gates

Every slice must pass:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/ndl
uv run pytest --cov=ndl --cov-report=term --cov-report=xml
uv run pre-commit run --all-files
```
