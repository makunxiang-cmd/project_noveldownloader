# NDL - NOVELDOWNLOADER

> Rule-driven Chinese novel downloader and format converter

[![CI](https://github.com/makunxiang-cmd/project_noveldownloader/actions/workflows/ci.yml/badge.svg)](https://github.com/makunxiang-cmd/project_noveldownloader/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

[简体中文](README.zh-CN.md)

## Status

Under active development. P0-P6 are implemented, and P7.1 added repeatable release-candidate distribution verification. First release (v0.1) targets MVP features: download, TXT/EPUB convert, library management, search, rule updates, optional browser rendering for supported rules, local Web UI, and auditable packaging checks. See `docs/superpowers/SESSION-STATE.md` for the current handoff snapshot.

## What Works Now

- Validate YAML source rules with `ndl rules validate`
- Download a rule-matched static HTML fixture site to TXT or EPUB
- Convert local TXT files to TXT or EPUB
- Manage the local SQLite library with `ndl library list/show/remove`
- Refresh saved ongoing novels with `ndl update --all`
- Search rule-defined source indexes with `ndl search`
- Install validated remote YAML rules with `ndl rules update`
- Use optional Playwright-backed rendering when a rule declares `fetcher.type: browser`, including rule-defined wait/viewport controls
- Verify release-candidate wheel/sdist contents with `scripts/verify_distribution.py`
- Search, download, and trigger manual/recurring library updates from the local Web UI
- Enforce robots.txt, per-host rate limits, retries, and a first-run lawful-use disclaimer for downloads

## What It Does (Roadmap)

- Download Chinese web novels from static HTML sites, with Playwright for JS-heavy sites as an optional extra
- Convert between TXT and EPUB formats, standalone or after download
- Manage a local SQLite library and track ongoing novels for updates
- Search across multiple sites via rule-defined search endpoints
- Add new sites by writing YAML rules, not Python code
- Use either CLI or a local Web UI, both sharing the same state

## Non-Goals

NDL does not and will not:

- Support commercial platforms such as Qidian, Fanqie, Jinjiang, or Qimao
- Bypass paywalls, Cloudflare, CAPTCHAs, or DRM
- Include login/account features or proxy pools

See [`DISCLAIMER.md`](DISCLAIMER.md) for the full ethics and legal stance.

## Development Install

```bash
uv sync
uv run ndl --version
```

Optional browser-backed rules require the browser extra and a Playwright browser install:

```bash
uv sync --extra browser
uv run playwright install chromium
uv run ndl doctor browser
```

The package has not been released to PyPI yet. The distribution name will be
`ndl-storykit` (the import path inside the package is still `ndl`, and the
CLI entry point is still `ndl`). When v0.1 ships the install becomes:

```bash
pip install ndl-storykit
pip install 'ndl-storykit[browser]'   # with optional Playwright fetcher
```

## Usage

```bash
ndl download <url> -o book.epub --accept-disclaimer
ndl convert book.txt -o book.epub
ndl library list
ndl update --all --accept-disclaimer
ndl search "keyword"
ndl rules update --manifest-url <manifest-url>
ndl doctor browser
ndl serve --accept-disclaimer
ndl rules validate my-rule.yaml
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Rule contributions are especially welcome and do not require Python.

## License

[MIT](LICENSE)
