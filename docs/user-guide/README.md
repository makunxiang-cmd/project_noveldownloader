# User Guide

NDL is still pre-release. Use it from a checkout with `uv`.

## Install From Source

```bash
uv sync
uv run ndl --version
```

The package is not published to PyPI yet.

## CLI Reference

### Validate a source rule

```bash
uv run ndl rules validate src/ndl/builtin_rules/example_static.yaml
```

### Convert a local TXT file

```bash
uv run ndl convert book.txt -o book.epub
uv run ndl convert book.txt -o book.txt --format txt
```

### Download a rule-matched source

```bash
uv run ndl download https://example-novels.test/book/123 -o book.epub --accept-disclaimer
uv run ndl download https://example-novels.test/book/123 -o book.epub --no-save
```

By default a successful download is also persisted into the local SQLite library
(`~/.ndl/library.db`). Pass `--no-save` to keep the file-only behavior of P1.

The bundled `example_static` rule is fixture-backed and intended for contract
tests. Real site coverage remains deliberately limited until compliant
public-domain rules are added.

### Manage the local library

```bash
uv run ndl library list
uv run ndl library show <id>
uv run ndl library remove <id> --yes
```

`list` and `show` use Rich tables. `show` displays chapter titles and word
counts only — chapter bodies are intentionally not printed. `remove` cascades
to chapters and prompts for confirmation unless `--yes` is supplied.

### Run the local Web UI

```bash
uv run ndl serve --accept-disclaimer
# http://127.0.0.1:8000
```

Useful flags:

- `--host` and `--port` choose the bind address and port (defaults
  `127.0.0.1:8000`).
- `--reload` runs uvicorn with autoreload for development.
- `--allow-public-host` is **required** before binding to anything other than
  `127.0.0.1` / `localhost` — `ndl serve` refuses public binds otherwise to
  avoid silently exposing downloads on a network interface.
- `--accept-disclaimer` records first-run disclaimer acceptance, the same way
  `ndl download` does.

The Web UI shares the same SQLite library and disclaimer marker as the CLI:

- The homepage lists saved novels and exposes a download form (URL, format,
  Save toggle).
- Submitting the form runs the existing download/convert services in a
  background task; the page subscribes to a Server-Sent Events stream and
  shows progress and final status without polling.
- Web-triggered downloads write output files to `<NDL_HOME>/downloads`. When
  Save is checked they also persist to the library and become visible on the
  homepage.
- Detail pages (`/library/{id}`) show novel metadata and chapter titles; they
  never render chapter bodies.

The UI is intentionally dependency-light: server-rendered Jinja2 templates,
hand-written CSS, native `EventSource` JavaScript. There is no Node/npm build
step.

## Disclaimer

`ndl download` and `ndl serve` both require first-run lawful-use acceptance.
Pass `--accept-disclaimer` once, or set `NDL_ACCEPT_DISCLAIMER=1` in test
automation. The acceptance marker is written under `<NDL_HOME>/`.

## State Locations

NDL keeps everything in a single home directory. Override the location with the
`NDL_HOME` environment variable; the default is `~/.ndl/`.

| Path                              | Purpose                                          |
| --------------------------------- | ------------------------------------------------ |
| `<NDL_HOME>/library.db`           | SQLite library (novels, chapters, settings).     |
| `<NDL_HOME>/disclaimer.accepted`  | Marker file written after `--accept-disclaimer`. |
| `<NDL_HOME>/downloads/`           | Default output directory for Web UI downloads.   |

Tests redirect this with `NDL_HOME=/tmp/ndl-home` to keep CI hermetic.

## What Is Not Implemented Yet

- Incremental updates: `ndl update --all` (P4 roadmap)
- Browser-backed fetching for JS-rendered sources (P6 roadmap)
- Search across multiple sites: `ndl search` (P5 roadmap)

See `docs/superpowers/SESSION-STATE.md` for the current handoff snapshot.
