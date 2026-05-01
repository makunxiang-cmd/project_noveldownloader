# Developer Guide

## Current Status

P0 and P1 are implemented. The project now has:

- Core domain models, protocols, progress events, and typed errors
- YAML rule schema, selector DSL, loader, and resolver
- HTTP fetcher with robots.txt, retry, rate-limit, and encoding policy
- HTML index/chapter parsers and TXT reader
- TXT/EPUB writers and writer registry
- Download/convert application services and a lightweight service container
- Typer CLI commands: `download`, `convert`, and `rules validate`

P2 is next: SQLite-backed library persistence and `ndl library {list,show,remove}`.

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

## Architecture Map

- `src/ndl/core/`: domain objects, protocols, progress events, and error hierarchy
- `src/ndl/rules/`: source rule schema, loading, resolution, and selector execution
- `src/ndl/fetchers/`: HTTP fetching infrastructure
- `src/ndl/parsers/`: HTML parsers and TXT reader
- `src/ndl/converters/`: TXT/EPUB writers and writer registry
- `src/ndl/application/`: download/convert services and dependency wiring
- `src/ndl/cli/`: Typer command surface and disclaimer gate
- `tests/unit/`: mirrors source package structure
- `tests/contract/`: bundled rule fixtures and contract tests

## Implementation Style

- Keep modules flat and small; one responsibility per file.
- Prefer pure functions for logic and thin classes for Protocol implementations.
- Keep `from __future__ import annotations` at the top of new Python modules.
- Preserve Python 3.10 compatibility.
- Raise errors from `src/ndl/core/errors.py`; do not invent unrelated exception hierarchies.
- Avoid real network access in tests; use fixtures and `respx`.

## Agent Handoff

Before starting new work, read:

1. `docs/superpowers/SESSION-STATE.md`
2. The active plan named there, currently `docs/superpowers/plans/2026-04-30-ndl-p2-library.md`
3. `AGENTS.md`

The P1 implementation commits are:

- `b8d1c8a feat(p1): add core domain and rule foundation`
- `98eba4e feat(p1): add parsers fetcher and converters`
- `f0f5dbe feat(p1): add services and cli commands`
