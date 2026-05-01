# NDL - NOVELDOWNLOADER

Welcome to the NDL documentation.

**Status:** Under active development. P0 scaffold, P1 MVP download/convert, P2 library persistence, and the P3 local Web UI core flow are implemented; P3.5 docs polish is in progress. Agent handoff state is tracked in `superpowers/SESSION-STATE.md`.

## Current Capabilities

- `ndl rules validate <rule.yaml>` validates YAML source rules.
- `ndl convert book.txt -o book.epub` converts local TXT input to TXT or EPUB.
- `ndl download <url> -o book.epub --accept-disclaimer` downloads a rule-matched static HTML source, writes TXT or EPUB, and saves to the local SQLite library by default (`--no-save` to skip).
- `ndl library list/show/remove` inspects and prunes the local SQLite library.
- `ndl serve --accept-disclaimer` starts the local FastAPI/Jinja2 Web UI on `127.0.0.1`.
- Downloads honor the bundled rule's robots.txt, rate-limit, retry, and encoding policies.

## Next Milestone

P3.5 finishes Web UI polish and documentation; P4 adds the update scheduler (`ndl update --all`). See the active plan under `superpowers/plans/2026-05-01-ndl-p3-web-ui.md` and the handoff snapshot under `superpowers/SESSION-STATE.md`.

## Sections

- [User Guide](user-guide/README.md) - installation, CLI reference, Web UI walkthrough, configuration
- [Rule Authoring](rule-authoring/README.md) - writing YAML rules to support new sites
- [Developer](developer/README.md) - architecture, contribution workflow, rule contract tests

## See Also

- [Design Specification](superpowers/specs/2026-04-20-ndl-design.md) - the complete design document

## License

NDL is released under the [MIT License](https://github.com/makunxiang-cmd/project_noveldownloader/blob/main/LICENSE). See also the [Disclaimer](https://github.com/makunxiang-cmd/project_noveldownloader/blob/main/DISCLAIMER.md) for legal and ethical stance.
