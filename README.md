# NDL - NOVELDOWNLOADER

> Rule-driven Chinese novel downloader and format converter

[![CI](https://github.com/makunxiang-cmd/project_noveldownloader/actions/workflows/ci.yml/badge.svg)](https://github.com/makunxiang-cmd/project_noveldownloader/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

[简体中文](README.zh-CN.md)

## Status

Under active development. The project is currently in P0 scaffold stage. First release (v0.1) targets MVP features: download, TXT/EPUB convert, and library management.

## What It Does (Planned)

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

## Install (Coming Soon)

```bash
pip install ndl
pip install ndl[browser]
```

## Usage Preview (Coming Soon)

```bash
ndl download <url> -o book.epub
ndl convert book.txt -o book.epub
ndl library list
ndl update --all
ndl serve
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Rule contributions are especially welcome and do not require Python.

## License

[MIT](LICENSE)
