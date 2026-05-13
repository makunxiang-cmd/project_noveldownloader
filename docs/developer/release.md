# Release Checklist

NDL is still pre-release. Keep `0.1.0.dev0` until a maintainer explicitly chooses
the v0.1 tag and PyPI publication date.

## Version Decision

- Current package version: `0.1.0.dev0`
- First public release target: `0.1.0`
- Version bump should happen in a dedicated release commit after P7 release-candidate
  gates are green and release notes are reviewed.

## Preflight

Run from the repository root:

```bash
uv lock --check
uv run ruff check .
uv run ruff format --check .
uv run mypy src/ndl
uv run pytest --cov=ndl --cov-report=term --cov-report=xml
uv run pre-commit run --all-files
```

Optional browser runtime smoke check:

```bash
uv sync --extra browser
uv run playwright install chromium
uv run ndl doctor browser
```

## Build Artifacts

Build into a clean output directory:

```bash
uv build --wheel --sdist --out-dir dist
```

Inspect the wheel before upload. It must include:

- `ndl/builtin_rules/example_static.yaml`
- `ndl/web/templates/*.html`
- `ndl/web/static/css/app.css`
- `ndl/web/static/js/app.js`
- package metadata with extras `browser`, `dev`, and `docs`

Example inspection commands:

```bash
python -m zipfile -l dist/ndl-*.whl
tar -tf dist/ndl-*.tar.gz
```

Prefer the automated verifier for repeatable release-candidate checks:

```bash
uv run python scripts/verify_distribution.py dist/ndl-*.whl dist/ndl-*.tar.gz
```

## Publication

Do not publish from an uncommitted working tree. For the v0.1 release:

1. Update `pyproject.toml` from `0.1.0.dev0` to `0.1.0`.
2. Ensure `CHANGELOG.md` has a concise v0.1 summary under a dated heading.
3. Run the preflight and build commands above.
4. Tag the release after CI passes on the release commit.
5. Upload artifacts with the maintainer's PyPI credentials.

## Boundaries

Release notes must keep the compliance boundaries explicit: no commercial
platform rules, no login automation, no CAPTCHA solving, no paywall bypass, no
Cloudflare challenge bypass, and no proxy-pool behavior.
