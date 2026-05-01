# Rule Authoring Guide

P1 includes the rule schema, selector DSL, loader/resolver, bundled `example_static` rule, and `ndl rules validate`.

## Validate A Rule

```bash
uv run ndl rules validate path/to/rule.yaml
```

Validation loads the YAML file through the same Pydantic schema used by the application. It catches schema errors before a rule is used by `ndl download`.

## Current Rule Surface

Rules describe:

- URL patterns used by `RuleResolver`
- Fetcher policy: headers, encoding, retries, robots.txt, and rate limits
- Index selectors for title, author, summary, cover, status, and chapter list
- Chapter selectors for title and cleaned content
- Optional pagination shape, currently fixture-backed in P1

Use `src/ndl/builtin_rules/example_static.yaml` as the canonical P1 example.

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
