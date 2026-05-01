# User Guide

NDL is still pre-release. Use it from a checkout with `uv`.

## Install From Source

```bash
uv sync
uv run ndl --version
```

The package is not published to PyPI yet.

## CLI Commands Available In P1

Validate a source rule:

```bash
uv run ndl rules validate src/ndl/builtin_rules/example_static.yaml
```

Convert a local TXT file:

```bash
uv run ndl convert book.txt -o book.epub
uv run ndl convert book.txt -o book.txt --format txt
```

Download a rule-matched source:

```bash
uv run ndl download https://example-novels.test/book/123 -o book.epub --accept-disclaimer
```

The bundled `example_static` rule is fixture-backed and intended for contract tests. Real site coverage remains deliberately limited until compliant public-domain rules are added.

## Download Disclaimer

`ndl download` requires first-run lawful-use acceptance. Pass `--accept-disclaimer` once, or set `NDL_ACCEPT_DISCLAIMER=1` in test automation. The acceptance marker is written under `~/.ndl/` by default. Tests can redirect this with `NDL_HOME=/tmp/ndl-home`.

## What Is Not Implemented Yet

- Local SQLite library commands: `ndl library list/show/remove`
- Incremental updates: `ndl update --all`
- Web UI: `ndl serve`
- Browser-backed fetching for JS-rendered sources

These are P2+ roadmap items. See `docs/superpowers/SESSION-STATE.md` for the current handoff.
