# NDL - NOVELDOWNLOADER

Welcome to the NDL documentation.

**Status:** Under active development. P0-P6 are implemented, covering scaffold, MVP download/convert, library persistence, local Web UI, updates, search, remote rule updates, optional browser rendering, diagnostics, and release hardening. P7.1 added repeatable release-candidate wheel/sdist verification. Agent handoff state is tracked in `superpowers/SESSION-STATE.md`.

## Current Capabilities

- `ndl rules validate <rule.yaml>` validates YAML source rules.
- `ndl convert book.txt -o book.epub` converts local TXT input to TXT or EPUB.
- `ndl download <url> -o book.epub --accept-disclaimer` downloads a rule-matched static HTML source, writes TXT or EPUB, and saves to the local SQLite library by default (`--no-save` to skip).
- `ndl library list/show/remove` inspects and prunes the local SQLite library.
- `ndl update --all --accept-disclaimer` refreshes saved non-completed novels and appends newly discovered chapters.
- `ndl search <keyword>` queries rule-defined search endpoints and prints source/title/author/url results.
- `ndl rules update --manifest-url <url>` fetches a remote manifest, validates every downloaded YAML rule, shows a summary, and writes to `<NDL_HOME>/rules` only after confirmation.
- `ndl doctor browser` checks the optional Playwright/Chromium runtime for browser-backed rules.
- `ndl serve --accept-disclaimer` starts the local FastAPI/Jinja2 Web UI on `127.0.0.1`, supports search, Web-triggered downloads, manual update-all, and recurring updates by default.
- Downloads honor the bundled rule's robots.txt, rate-limit, retry, and encoding policies.
- Rules may opt into optional Playwright rendering with `fetcher.type: browser` when installed with `ndl[browser]`, including declarative wait/viewport controls.

## Next Milestone

P6 is complete and P7 is active. P7.1 added repeatable wheel/sdist verification for release-candidate artifacts. See the handoff snapshot under `superpowers/SESSION-STATE.md`.

## Sections

- [User Guide](user-guide/README.md) - installation, CLI reference, Web UI walkthrough, configuration
- [Rule Authoring](rule-authoring/README.md) - writing YAML rules to support new sites
- [Developer](developer/README.md) - architecture, contribution workflow, rule contract tests
- [Release Checklist](developer/release.md) - v0.1 preflight, artifact inspection, and publication steps

## See Also

- [Design Specification](superpowers/specs/2026-04-20-ndl-design.md) - the complete design document

## License

NDL is released under the [MIT License](https://github.com/makunxiang-cmd/project_noveldownloader/blob/main/LICENSE). See also the [Disclaimer](https://github.com/makunxiang-cmd/project_noveldownloader/blob/main/DISCLAIMER.md) for legal and ethical stance.
