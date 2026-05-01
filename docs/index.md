# NDL - NOVELDOWNLOADER

Welcome to the NDL documentation.

**Status:** Under active development. P0 scaffold, P1 MVP download/convert, P2 library persistence, P3 local Web UI, and P4 library updates are implemented; P5 search and remote rule management are next. Agent handoff state is tracked in `superpowers/SESSION-STATE.md`.

## Current Capabilities

- `ndl rules validate <rule.yaml>` validates YAML source rules.
- `ndl convert book.txt -o book.epub` converts local TXT input to TXT or EPUB.
- `ndl download <url> -o book.epub --accept-disclaimer` downloads a rule-matched static HTML source, writes TXT or EPUB, and saves to the local SQLite library by default (`--no-save` to skip).
- `ndl library list/show/remove` inspects and prunes the local SQLite library.
- `ndl update --all --accept-disclaimer` refreshes saved non-completed novels and appends newly discovered chapters.
- `ndl serve --accept-disclaimer` starts the local FastAPI/Jinja2 Web UI on `127.0.0.1`, supports manual update-all, and runs recurring updates by default.
- Downloads honor the bundled rule's robots.txt, rate-limit, retry, and encoding policies.

## Next Milestone

P5 adds search and remote rule management. See the handoff snapshot under `superpowers/SESSION-STATE.md`.

## Sections

- [User Guide](user-guide/README.md) - installation, CLI reference, Web UI walkthrough, configuration
- [Rule Authoring](rule-authoring/README.md) - writing YAML rules to support new sites
- [Developer](developer/README.md) - architecture, contribution workflow, rule contract tests

## See Also

- [Design Specification](superpowers/specs/2026-04-20-ndl-design.md) - the complete design document

## License

NDL is released under the [MIT License](https://github.com/makunxiang-cmd/project_noveldownloader/blob/main/LICENSE). See also the [Disclaimer](https://github.com/makunxiang-cmd/project_noveldownloader/blob/main/DISCLAIMER.md) for legal and ethical stance.
