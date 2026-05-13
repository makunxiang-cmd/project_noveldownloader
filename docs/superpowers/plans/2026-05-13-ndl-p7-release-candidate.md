# NDL P7 Release Candidate Verification Plan

> Status: active. P7 starts after completed P6 browser/release-hardening work.
>
> Handoff note, 2026-05-13: P7.1 is implemented. Do not publish, tag, or bump the package version without explicit maintainer approval.

## Goal

Make v0.1 release preparation repeatable and auditable without performing the actual publication:

```bash
uv build --wheel --sdist --out-dir dist
uv run python scripts/verify_distribution.py dist/ndl-*.whl dist/ndl-*.tar.gz
```

P7 must preserve the project boundaries: no PyPI upload, no git tag, no commercial platform rules, no login/CAPTCHA/paywall bypass, no Cloudflare challenge bypass, and no real-site traffic in automated tests.

## Reference

- Completed P6 plan: `docs/superpowers/plans/2026-05-13-ndl-p6-browser-release.md`
- Release checklist: `docs/developer/release.md`
- Current handoff: `docs/superpowers/SESSION-STATE.md`

## Proposed Slices

### P7.1 Distribution Verification Script

Status: implemented.

Scope:

- Add a small stdlib-only script that validates wheel/sdist contents and package metadata
- Check required runtime resources: builtin rule, Web templates, Web static assets
- Check wheel metadata: version and optional extras, including `browser`
- Document the script in the release checklist

Exit criteria:

- Script succeeds against a freshly built local wheel/sdist
- Script fails with clear messages when an expected artifact member is missing

### P7.2 Release Notes Draft

Status: implemented.

Scope:

- Convert the large Unreleased changelog into a concise v0.1 release-note draft
- Keep detailed implementation bullets available but put user-facing highlights first
- Keep compliance boundaries explicit

Output:

- `docs/release-notes/v0.1.md` — draft, marked "pending maintainer approval".
  Leads with highlights and compliance boundaries, then quick-start commands,
  pre-release hardening summary, what's-not-included, quality snapshot, and
  the maintainer-only execution gate.
- Linked into the MkDocs nav under `Release Notes → v0.1 (Draft)`.

Exit criteria:

- ✅ Maintainer can review release notes without reading the entire handoff
  state (one page, ~10 sections).
- ✅ Compliance boundaries appear before any feature bullet.

### P7.3 Install Smoke Strategy

Status: planned.

Scope:

- Define a practical install smoke that does not require network during CI
- Prefer wheel metadata/content validation plus CLI smoke in an environment with dependencies already synced
- Document when optional browser smoke is expected

Exit criteria:

- Release checklist has an unambiguous local smoke path

### P7.4 Release Execution Gate

Status: planned.

Scope:

- Document explicit maintainer approval required for version bump, tag, GitHub release, and PyPI upload
- Leave publication credentials and upload outside automated agent work

Exit criteria:

- No release-mutating action is implied by the verification workflow

## Quality Gates

Every implemented slice must pass:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/ndl
uv run pytest --cov=ndl --cov-report=term --cov-report=xml
uv run pre-commit run --all-files
```
