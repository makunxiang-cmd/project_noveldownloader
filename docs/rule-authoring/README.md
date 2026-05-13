# Rule Authoring Guide

The rule schema, selector DSL, loader/resolver, bundled `example_static` rule, `ndl rules validate`, rule-defined search, remote rule installation, and P6 optional browser controls are implemented.

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
- Search endpoint selectors and optional pagination shape

Use `src/ndl/builtin_rules/example_static.yaml` as the canonical static HTML example.

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
