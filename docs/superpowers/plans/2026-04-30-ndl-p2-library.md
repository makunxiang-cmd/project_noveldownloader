# NDL P2 Library Persistence Plan

> Status: implemented. P2 adds local SQLite persistence and `ndl library` commands while preserving the P1 download/convert behavior.

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

Status: implemented.

Scope:

- Add storage dependency decision and `pyproject.toml` updates, likely `SQLAlchemy>=2`
- `storage/database.py` for SQLite engine/session setup
- SQLite PRAGMAs: `journal_mode=WAL`, `foreign_keys=ON`
- `storage/models.py` with SQLAlchemy 2.0 Mapped models
- Unit tests for schema creation in `tmp_path`

Exit criteria:

- A temporary SQLite DB can create all P2 tables
- Quality gates remain green

Notes:

- Mapped classes are suffixed `Row` (`NovelRow`, `ChapterRow`, `DownloadJobRow`, `SettingRow`) so the ORM layer never collides with the domain models in `ndl.core.models`. Repository round-trip lives in P2.2.
- `download_jobs` is created in P2.1 even though no job rows are written yet, so the schema is stable before P2.2 begins.
- `chapters."index"` is force-quoted via `mapped_column("index", ..., quote=True)` to avoid SQL keyword surprises across dialects.

### P2.2 Library Repository

Status: implemented.

Scope:

- `storage/repository.py`
- Save/update `Novel` with ordered chapters
- List/get/remove novels
- Map ORM rows back to `Novel`/`Chapter`

Exit criteria:

- Repository round-trips a fixture `Novel`
- Removing a novel removes its chapters

Notes:

- `save()` is upsert-by-`(source_rule_id, source_url)`. `source_url is None` (TXT-derived novels) always inserts a fresh row.
- Chapter replacement during upsert deletes existing chapters via `row.chapters.clear() + flush` before inserting the new ones, so the `(novel_id, index)` UNIQUE constraint never sees overlapping rows in a single statement batch.
- `list()` returns `NovelSummary` (id + header fields + `chapter_count`); chapter bodies are not loaded, keeping the call cheap for `ndl library list`.
- `get()` uses `selectinload(NovelRow.chapters)` and re-sorts chapters by index when materializing the domain `Novel`.

### P2.3 Library Service

Status: implemented.

Scope:

- `application/services/library.py`
- Service methods for save/list/get/remove/export
- Decide whether P2 changes `DownloadService` or CLI `download` to auto-save

Exit criteria:

- Service tests cover save/list/show/remove
- P1 download/convert tests still pass

Notes:

- `LibraryService` is a thin pass-through over `LibraryRepository`; the bulk of behavior already lives in P2.2.
- "export" stayed out of P2.4 scope; a future CLI export command can compose `library_service().get(id)` with `convert_service().convert(novel, output_path, target_format=...)` rather than baking export into the service.
- `DownloadService` is unchanged in P2.3. Auto-save is wired in P2.4 at the CLI layer (default on, `--no-save` opt-out).
- New `application/paths.py` owns `ndl_home()` and `library_db_path()`; `cli/disclaimer.py` now imports from there. `ServiceContainer.library_service()` lazily creates the engine on first call (so commands that don't touch the library, e.g. `ndl rules validate`, never create `~/.ndl/`).
- `ServiceContainer` accepts `db_path: Path | None = None` for tests/CLI overrides; default is `library_db_path()`.

### P2.4 CLI Library Commands

Status: implemented.

Scope:

- `ndl library list`
- `ndl library show <id>`
- `ndl library remove <id>`
- Database path configuration via `NDL_HOME` or a small path helper

Exit criteria:

- `typer.testing.CliRunner` tests pass
- Commands operate on a `tmp_path` SQLite DB

Notes:

- `src/ndl/cli/main.py` now registers a `library` Typer sub-app with `list`, `show`, and `remove`.
- `ndl library list` renders `id / title / author / status / chapter_count / fetched_at` summaries from `LibraryService.list()`.
- `ndl library show <id>` renders novel header fields and chapter titles/word counts without printing chapter bodies.
- `ndl library remove <id>` deletes through `LibraryService.remove()` and supports `--yes` / `-y` to skip confirmation.
- `ndl download` saves the downloaded `Novel` to the local library after the output file is written; `--no-save` keeps the old file-only behavior.
- CLI tests use `NDL_HOME=tmp_path/ndl-home` and mocked HTTP routes to verify download auto-save, opt-out, show, and remove.

## Open Decisions

- Whether the disclaimer marker should stay as `~/.ndl/disclaimer.accepted` or migrate into a settings table/config file.

## Quality Gates

Every slice must pass:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/ndl
uv run pytest --cov=ndl --cov-report=term --cov-report=xml
uv run pre-commit run --all-files
```
