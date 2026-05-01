# NDL - NOVELDOWNLOADER

> Rule-driven Chinese novel downloader and format converter

[![CI](https://github.com/makunxiang-cmd/project_noveldownloader/actions/workflows/ci.yml/badge.svg)](https://github.com/makunxiang-cmd/project_noveldownloader/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

[简体中文](README.zh-CN.md)

## Status

Under active development. P0 scaffold, P1 MVP download/convert, P2 library persistence, P3 local Web UI, and P4 library updates are implemented; P5 search and remote rule management are next. First release (v0.1) targets MVP features: download, TXT/EPUB convert, library management, and a local Web UI. See `docs/superpowers/SESSION-STATE.md` for the current handoff snapshot.

## What Works Now

- Validate YAML source rules with `ndl rules validate`
- Download a rule-matched static HTML fixture site to TXT or EPUB
- Convert local TXT files to TXT or EPUB
- Manage the local SQLite library with `ndl library list/show/remove`
- Refresh saved ongoing novels with `ndl update --all`
- Trigger manual and recurring library updates from the local Web UI
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

The package has not been released to PyPI yet.

## Usage

```bash
ndl download <url> -o book.epub --accept-disclaimer
ndl convert book.txt -o book.epub
ndl library list
ndl update --all --accept-disclaimer
ndl serve --accept-disclaimer
ndl rules validate my-rule.yaml
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Rule contributions are especially welcome and do not require Python.

## License

[MIT](LICENSE)
