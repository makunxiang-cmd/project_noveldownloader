# NDL P2 Library Persistence Plan

> Status: planned. Start here after P1. P2 adds local SQLite persistence and `ndl library` commands while preserving the P1 download/convert behavior.

## Goal

Persist downloaded novels locally and expose a minimum library CLI:

```bash
ndl download <url> -o book.epub --accept-disclaimer
ndl library list
ndl library show <novel-id>
ndl library remove <novel-id>
```

P2 should keep network behavior compliant with the P1 robots/rate-limit/disclaimer constraints.

## Reference

- Design spec: `docs/superpowers/specs/2026-04-20-ndl-design.md` §4.4 and roadmap row P2
- Current handoff: `docs/superpowers/SESSION-STATE.md`

## Proposed Slices

### P2.1 Storage Foundation

Status: pending.

Scope:

- Add storage dependency decision and `pyproject.toml` updates, likely `SQLAlchemy>=2`
- `storage/database.py` for SQLite engine/session setup
- SQLite PRAGMAs: `journal_mode=WAL`, `foreign_keys=ON`
- `storage/models.py` with SQLAlchemy 2.0 Mapped models
- Unit tests for schema creation in `tmp_path`

Exit criteria:

- A temporary SQLite DB can create all P2 tables
- Quality gates remain green

### P2.2 Library Repository

Status: pending.

Scope:

- `storage/repository.py`
- Save/update `Novel` with ordered chapters
- List/get/remove novels
- Map ORM rows back to `Novel`/`Chapter`

Exit criteria:

- Repository round-trips a fixture `Novel`
- Removing a novel removes its chapters

### P2.3 Library Service

Status: pending.

Scope:

- `application/services/library.py`
- Service methods for save/list/get/remove/export
- Decide whether P2 changes `DownloadService` or CLI `download` to auto-save

Exit criteria:

- Service tests cover save/list/show/remove
- P1 download/convert tests still pass

### P2.4 CLI Library Commands

Status: pending.

Scope:

- `ndl library list`
- `ndl library show <id>`
- `ndl library remove <id>`
- Database path configuration via `NDL_HOME` or a small path helper

Exit criteria:

- `typer.testing.CliRunner` tests pass
- Commands operate on a `tmp_path` SQLite DB

## Open Decisions

- Whether `ndl download` should auto-save by default in P2 or require an explicit library option.
- Whether the disclaimer marker should stay as `~/.ndl/disclaimer.accepted` or migrate into a settings table/config file.
- Whether to include `download_jobs` in P2.1 or defer job history until update/retry work.

## Quality Gates

Every slice must pass:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/ndl
uv run pytest --cov=ndl --cov-report=term --cov-report=xml
uv run pre-commit run --all-files
```
