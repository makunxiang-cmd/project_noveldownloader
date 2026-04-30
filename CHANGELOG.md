# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- P1.4 TXT/EPUB converters: `TxtWriter`, `EpubWriter`, `WriterRegistry`, and `TxtReader` for standalone TXT conversion; EPUB generation is backed by `ebooklib`
- P1.3 HTTP fetcher: `HttpFetcher` honors per-host rate limits, retry policy with fixed/exponential backoff, robots.txt enforcement, and rule-driven encoding; backed by `httpx`
- P1.2 HTML parsers: `parse_index` produces `Novel` metadata + `ChapterStub` list, `parse_chapter` produces a cleaned `Chapter`; `HtmlParser` class binds a rule to the `Parser` Protocol
- P1.1 domain foundation: `Chapter`, `Novel`, `ChapterStub`, progress events, protocols, and typed error hierarchy
- P1.1 rule foundation: Pydantic YAML schema, selector DSL helpers, rule loader/resolver, and bundled `example_static` rule
- Contract fixture baseline for bundled rules

### Changed

- Contract test for bundled rules now exercises the parsers end-to-end instead of selector helpers directly
- P0 scaffold complete: project structure, CI, linting/type/test tooling, MkDocs skeleton
- `ndl --version` / `ndl -V` CLI command
- Community files: LICENSE (MIT), DISCLAIMER, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY
- Issue templates (bug / rule / feature) and PR template
- GitHub Actions CI: lint + format + mypy + test matrix (3 OS x 3 Python)

[Unreleased]: https://github.com/makunxiang-cmd/project_noveldownloader/commits/main
