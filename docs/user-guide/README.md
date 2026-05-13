# User Guide

NDL is still pre-release. Use it from a checkout with `uv`.

## Install From Source

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

Rules can opt into browser-backed rendering with `fetcher.type: browser`.
This path uses Playwright only when the optional `browser` extra is installed;
it still applies robots.txt checks, per-host rate limits, and retry policy.
Browser rules can also declare `fetcher.browser` controls for navigation
timeout, wait state, wait selector, extra wait, viewport, and JavaScript
enablement. It is for compliant JavaScript-rendered public-domain pages, not
login, CAPTCHA, paywall, or Cloudflare-challenge bypass.

### Diagnose browser support

```bash
uv run ndl doctor browser
```

This checks whether the optional Playwright package is installed and whether
Chromium can launch. A failed check prints the install commands needed for
browser-backed rules.

### Manage the local library

```bash
uv run ndl library list
uv run ndl library show <id>
uv run ndl library remove <id> --yes
```

`list` and `show` use Rich tables. `show` displays chapter titles and word
counts only — chapter bodies are intentionally not printed. `remove` cascades
to chapters and prompts for confirmation unless `--yes` is supplied.

### Update saved ongoing novels

```bash
uv run ndl update --all --accept-disclaimer
```

`update --all` checks every saved non-completed library entry that has a source
URL, reloads the index page, fetches only chapters whose indices are not already
stored, and appends them to the SQLite library. Completed novels and local-only
entries are skipped.

### Search rule-defined sources

```bash
uv run ndl search "keyword"
uv run ndl search "keyword" --rule example_static --limit 10
```

`search` queries every enabled rule that declares a search endpoint and prints
source, title, author, and URL. Use `--rule` to restrict the query to a
specific rule id; repeat it to search multiple selected rules. `--limit`
truncates the rendered rows after results are collected. If one rule fails
(network error, blocked by robots.txt, etc.), the other sources' results are
still printed, and a second "Search failures" table lists the failing rule id
and message.

### List loaded rules

```bash
uv run ndl rules list
```

Prints a table of every bundled and user-installed rule with id, name, version, enabled flag, whether it declares a search endpoint, fetcher type, and URL pattern count.

### Update remote source rules

```bash
uv run ndl rules update --manifest-url https://example.test/ndl-rules.yaml
NDL_RULES_MANIFEST_URL=https://example.test/ndl-rules.yaml uv run ndl rules update --yes
```

The manifest is YAML/JSON-compatible and contains `version: 1` plus a `rules`
list of `{id, url, sha256?}` entries. NDL downloads every referenced YAML rule,
checks optional SHA-256 digests, validates the full rule bundle, and prints a
summary before writing anything. Invalid bundles never replace existing files.

Installed rules are written to `<NDL_HOME>/rules/<rule-id>.yaml` and override
bundled rules with the same id. There is no bundled default remote feed yet, so
pass `--manifest-url` or set `NDL_RULES_MANIFEST_URL`.

Both the manifest URL and every resolved rule URL must use `https`. Set
`NDL_RULES_ALLOW_INSECURE=1` only for local mirrors or testing if you need to
pull rules over plain `http`.

### Run the local Web UI

```bash
uv run ndl serve --accept-disclaimer
# http://127.0.0.1:8000
```

Useful flags:

- `--host` and `--port` choose the bind address and port (defaults
  `127.0.0.1:8000`).
- `--reload` runs uvicorn with autoreload for development.
- `--scheduler/--no-scheduler` controls recurring library updates while the
  Web UI is active. The scheduler is on by default for `ndl serve`.
- `--update-interval-hours` sets the recurring update interval (default 6).
- `--allow-public-host` is **required** before binding to anything other than
  `127.0.0.1` / `localhost` — `ndl serve` refuses public binds otherwise to
  avoid silently exposing downloads on a network interface.
- `--accept-disclaimer` records first-run disclaimer acceptance, the same way
  `ndl download` does.

The Web UI shares the same SQLite library and disclaimer marker as the CLI:

- The homepage lists saved novels and exposes a download form (URL, format,
  Save toggle).
- The homepage exposes a search form. Results show source, title, author, URL,
  and a Download action that uses the existing Web download flow. If one source
  fails, a separate "Search failures" section lists the failing rule and message
  while other sources' results are still rendered.
- The homepage also exposes `Update all`, which checks saved ongoing novels and
  renders a per-novel result table.
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
| `<NDL_HOME>/rules/`               | User-installed YAML rules from remote updates.   |

Tests redirect this with `NDL_HOME=/tmp/ndl-home` to keep CI hermetic.

## Current Release-Candidate Work

P6 release hardening is complete and P7 is active. P7.1 added repeatable
wheel/sdist verification through `scripts/verify_distribution.py`. Next planned
work is P7.2 release notes, P7.3 install smoke strategy, and P7.4 release
execution gate.

Do not treat the current checkout as a published package: there is no PyPI
release yet, and version bumping, git tags, GitHub Releases, or PyPI upload
require explicit maintainer approval.

See `docs/superpowers/SESSION-STATE.md` for the current handoff snapshot.
