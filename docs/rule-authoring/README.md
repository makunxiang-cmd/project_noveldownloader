# Rule Authoring Guide

The rule schema, selector DSL, loader/resolver, `ndl rules validate`, rule-defined search, remote rule installation, and optional browser controls are implemented.

## Validate A Rule

```bash
uv run ndl rules validate path/to/rule.yaml
```

Validation loads the YAML file through the same Pydantic schema used by the application. It catches schema errors before a rule is used by `ndl download`.

## Current Rule Surface

Rules describe:

- URL patterns used by `RuleResolver`
- Fetcher policy: HTTP/browser mode, headers, encoding, retries, robots.txt, and rate limits
- Browser controls for rules using `fetcher.type: browser`
- Index selectors for title, author, summary, cover, status, and chapter list
- Chapter selectors for title and cleaned content
- Search endpoint selectors and browser/form submission controls
- Archive download settings for whole-book TXT endpoints

The production package intentionally ships no demo site rule. `load_builtin_rules()` is the production builtin-rules entry point; in the default install it returns an empty list unless future production rules are added. The test-only static HTML example lives at `tests/fixtures/rules/example_static.yaml`.

## Schema Consumption

This table tracks whether a schema field is only accepted by validation or is actually consumed by upstream services.

| Field | Schema since | Consumed since |
|---|---:|---:|
| `url_patterns` | 0.1 | 0.1 |
| `fetcher.type: "http"` | 0.1 | 0.1 |
| `fetcher.type: "browser"` | 0.1 | 0.1 |
| `fetcher.headers` | 0.1 | 0.1 |
| `fetcher.rate_limit` | 0.1 | 0.1 |
| `fetcher.retry` | 0.1 | 0.1 |
| `fetcher.robots` | 0.1 | 0.1 |
| `fetcher.encoding` | 0.1 | 0.1 |
| `fetcher.browser.navigation_timeout_ms` | 0.1 | 0.1 |
| `fetcher.browser.wait_until` | 0.1 | 0.1 |
| `fetcher.browser.wait_for_selector` | 0.1 | 0.1 |
| `fetcher.browser.extra_wait_ms` | 0.1 | 0.1 |
| `fetcher.browser.viewport` | 0.1 | 0.1 |
| `fetcher.browser.javascript_enabled` | 0.1 | 0.1 |
| `index.url_template` | 0.1 | 0.1 |
| `index.novel.*` | 0.1 | 0.1 |
| `index.chapter_list.container` | 0.1 | 0.1 |
| `index.chapter_list.pick` | 0.2 | 0.2 |
| `index.chapter_list.items` | 0.1 | 0.1 |
| `index.chapter_list.title` | 0.1 | 0.1 |
| `index.chapter_list.url` | 0.1 | 0.1 |
| `index.pagination.type: "none"` | 0.1 | 0.1 |
| `index.pagination.type: "next"` | 0.1 | 0.2 |
| `index.pagination.type: "index-template"` | 0.2 | 0.2 |
| `chapter.title` | 0.1 | 0.1 |
| `chapter.content` | 0.1 | 0.1 |
| `chapter.pagination.type: "none"` | 0.1 | 0.1 |
| `chapter.pagination.type: "next"` | 0.1 | 0.2 |
| `download_archive` | 0.2 | 0.2 |
| `search.method: "GET"` | 0.1 | 0.1 |
| `search.method: "POST"` | 0.2 | 0.2 |
| `search.body` | 0.2 | 0.2 |
| `search.browser` | 0.2 | 0.2 |
| `search.results_container` | 0.1 | 0.1 |
| `search.items` | 0.1 | 0.1 |
| `search.fields.*` | 0.1 | 0.1 |

No accepted 0.2 schema field is intentionally inert. If a future schema field is added before service support lands, document it here and emit a loader warning rather than silently accepting a no-op.

## Browser Fetcher Controls

Browser-backed rules require installing the optional browser extra and Chromium:

```bash
uv sync --extra browser
uv run playwright install chromium
uv run ndl doctor browser
```

Rules opt in explicitly:

```yaml
fetcher:
  type: browser
  browser:
    navigation_timeout_ms: 30000
    wait_until: networkidle
    wait_for_selector: "#chapter-content"
    extra_wait_ms: 0
    viewport:
      width: 1280
      height: 900
    javascript_enabled: true
```

Allowed `wait_until` values are `commit`, `domcontentloaded`, `load`, and
`networkidle`. Browser rules still respect robots.txt, per-host rate limits,
and retry policy. They are only for compliant public-domain JavaScript-rendered
pages, not login, CAPTCHA, paywall, or Cloudflare challenge bypass.

## Selector Behavior

Selectors are implemented in `src/ndl/rules/selector.py` and used by the HTML parsers. P1 supports extracting text, HTML, or attributes and applying cleanup rules such as removing selectors, stripping patterns, normalizing whitespace, and enforcing minimum paragraph length.

## Contract Testing

Bundled rules are tested against fixed fixtures under `tests/contract/fixtures/`. The P1 contract test exercises the full parser path, not just selector helpers.

## Compliance Requirements

- `robots.respect: true` is the default posture.
- If a rule disables robots enforcement, it must provide an `ignore_justification`.
- `rate_limit.min_interval_ms` must stay at or above 500 ms.
- `rate_limit.max_concurrency` must stay at or below 3.
- Do not add rules for commercial platforms, paywalls, CAPTCHA bypass, DRM bypass, login-only content, or Cloudflare bypass.
