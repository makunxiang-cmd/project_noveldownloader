# NDL - NOVELDOWNLOADER

Welcome to the NDL documentation.

**Status:** Under active development. P0 scaffold and the P1 MVP download/convert path are implemented; P2 library persistence is next. Agent handoff state is tracked in `superpowers/SESSION-STATE.md`.

## Current Capabilities

- `ndl rules validate <rule.yaml>` validates YAML source rules.
- `ndl convert book.txt -o book.epub` converts local TXT input to TXT or EPUB.
- `ndl download <url> -o book.epub --accept-disclaimer` downloads a rule-matched static HTML source and writes TXT or EPUB.
- Downloads honor the bundled rule's robots.txt, rate-limit, retry, and encoding policies.

## Next Milestone

P2 adds local SQLite library persistence and `ndl library {list,show,remove}`. See the implementation handoff notes under `superpowers/SESSION-STATE.md` and the P2 plan under `superpowers/plans/2026-04-30-ndl-p2-library.md`.

## Sections

- [User Guide](user-guide/README.md) - installation, CLI reference, Web UI walkthrough, configuration
- [Rule Authoring](rule-authoring/README.md) - writing YAML rules to support new sites
- [Developer](developer/README.md) - architecture, contribution workflow, rule contract tests

## See Also

- [Design Specification](superpowers/specs/2026-04-20-ndl-design.md) - the complete design document

## License

NDL is released under the [MIT License](https://github.com/makunxiang-cmd/project_noveldownloader/blob/main/LICENSE). See also the [Disclaimer](https://github.com/makunxiang-cmd/project_noveldownloader/blob/main/DISCLAIMER.md) for legal and ethical stance.
