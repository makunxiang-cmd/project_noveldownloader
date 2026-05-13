# NDL Release Preparation Plan (Phases A–E)

> Status: active. P7 verification is complete; this plan tracks the
> end-to-end path from release-candidate state to a published v0.1.0 plus
> the day-after operating routine. Phase A is the current focus.
>
> Owners: maintainer (`makunxiang-cmd`) for account / web-UI / publication
> actions; agents (Claude or otherwise) for code/doc/tooling work routed
> through pull requests against `main`.

## Why this plan exists

By the end of the active P7 plan
(`2026-05-13-ndl-p7-release-candidate.md`) the repo is at a verified
release-candidate state: all P0–P7 implemented, nine pre-release hardening
slices in `2026-05-13-ndl-p7-pre-release-hardening.md`, distribution
verifier + install smoke + execution gate documented. What remains is not
"more features" — it's the **maintainer-only release execution** plus a
short list of one-time account / repository preparations that no agent can
do on the maintainer's behalf.

This plan enumerates those steps so a new agent or a returning maintainer
can pick up without re-deriving the roadmap.

## Phase A — Pre-release setup (one-time per project)

### A0 — Decide PyPI distribution name ✅ implemented (2026-05-13)

- The bare `ndl` name on PyPI has been registered since 2016 by an
  unrelated abandoned project (`msull/needle`, last release 0.2). PEP 541
  reclaim would be slow and uncertain.
- Decision: ship as `noveldownloader`. Python import path stays
  `from ndl ...`; CLI entry point stays `ndl`. Only the *distribution*
  (wheel/sdist artifact name + `pip install` argument) changes.
- Done in commit `0b412af`. Verified end-to-end: `uv build` produces
  `noveldownloader-0.1.0.dev0-py3-none-any.whl` + `.tar.gz`,
  `scripts/verify_distribution.py` accepts both, a fresh
  `python -m venv` + `pip install <wheel>` + `scripts/smoke_cli.py`
  reports `Smoke OK.`.

### A1 — PyPI account + 2FA ⏳ maintainer-only

- https://pypi.org/account/register/ — real-name email registration.
- Verify email.
- Account Settings → 2FA → enroll either TOTP (Authy / Google
  Authenticator / 1Password) or a WebAuthn hardware key.
- Save the eight recovery codes into a password manager or paper safe.
- (Recommended) Repeat against https://test.pypi.org/ so that B14 can be
  rehearsed against TestPyPI first.

Agent cannot create the account, set 2FA, or store recovery codes.

### A2 — PyPI API token ⏳ maintainer-only (depends on A1)

- After A1, https://pypi.org/manage/account/token/ → "Add API token".
- Token name: e.g. `noveldownloader-release-1`.
- Scope: **must be "Entire account" for the first release** (the
  `noveldownloader` project does not exist on PyPI yet, so a
  project-scoped token can't be issued). After B15 succeeds, generate a
  project-scoped token and replace the account-wide one.
- Copy the `pypi-...` token immediately (only shown once).
- Store via one of:
  - `~/.pypirc` (template below), or
  - `UV_PUBLISH_TOKEN` environment variable for `uv publish`, or
  - `TWINE_PASSWORD=...` for `twine upload`.

`~/.pypirc` template (already excluded from the repo by living in
`$HOME`):

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-<paste-token>

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-<paste-testpypi-token>
```

Agent cannot log in to PyPI, see / generate the token, or write it to
`~/.pypirc`.

### A3 — `main` branch protection (lightweight) ✅ enabled (2026-05-13)

- Applied via `gh api -X PUT
  /repos/makunxiang-cmd/project_noveldownloader/branches/main/protection`.
- Active settings:
  - `required_pull_request_reviews.required_approving_review_count = 0`
    → PR is required to merge to `main`, but no approving review is
    required (solo-maintainer friendly).
  - `allow_force_pushes = false`, `allow_deletions = false`.
  - `enforce_admins = false` → admin can override in emergencies, but the
    default workflow goes through PR.
  - `required_status_checks = null` → CI is **not** required to be green
    for merge. The maintainer should still visually confirm CI passes on
    the PR page before merging.
- Why no required status checks yet: `.github/workflows/ci.yml` uses
  `paths-ignore` to skip CI on doc-only changes. If a status check is
  marked required and the run is skipped, the PR would block forever. To
  promote CI to "required", first refactor the workflow to use a
  no-op-pass job (the pattern is already noted in
  `docs/developer/README.md` → "CI behavior" section).

### A4 — MkDocs → GitHub Pages workflow ✅ partial (workflow shipped, Pages source pending)

- `.github/workflows/docs.yml` shipped in commit `aea9978`. On push to
  `main` (when `docs/**`, `mkdocs.yml`, `CHANGELOG.md`, or top-level
  community docs change) and on `workflow_dispatch`, the workflow builds
  the MkDocs site with `--strict` and deploys via
  `actions/deploy-pages@v4`.
- Local `uv run mkdocs build --strict --config-file docs/mkdocs.yml`
  produces zero warnings.
- **Maintainer action still required (one-time, web UI only):**
  - https://github.com/makunxiang-cmd/project_noveldownloader/settings/pages
  - Build and deployment → Source → change from "Deploy from a branch"
    to **"GitHub Actions"** → Save.
- Until that toggle is set, the `Deploy to GitHub Pages` job in the Docs
  workflow fails with HTTP 404 (the Build step still passes). The first
  push after the toggle will succeed and publish to
  https://makunxiang-cmd.github.io/project_noveldownloader/.

### A5 — Tag signing key (GPG / SSH) ⏳ optional, maintainer-only

- Only needed if the maintainer wants to use `git tag -s` in B13. The
  release runbook fallback is `git tag -a v0.1.0 -m "..."`, which is
  acceptable.
- If signing is desired:
  ```bash
  gpg --full-generate-key            # generate locally; private key never leaves
  gpg --list-secret-keys --keyid-format=long
  git config --global user.signingkey <KEY-ID>
  git config --global commit.gpgsign true
  gpg --armor --export <KEY-ID> | pbcopy   # paste into GitHub → Settings → SSH and GPG keys
  ```
- Alternative: SSH-based signing
  ```bash
  git config --global gpg.format ssh
  git config --global user.signingkey "$(cat ~/.ssh/id_ed25519.pub)"
  ```

Agent cannot generate keys (private key material) or upload public keys
to GitHub.

### A6 — Issue / PR templates ✅ implemented (P0 era, verified 2026-05-13)

- `.github/ISSUE_TEMPLATE/bug_report.md`,
  `.github/ISSUE_TEMPLATE/feature_request.md`,
  `.github/ISSUE_TEMPLATE/rule_request.md`, and
  `.github/pull_request_template.md` exist with reasonable content.
- The rule_request template already enforces the ethics check (no
  commercial platforms, no paywalls).

## Phase B — Release execution ⛔ MAINTAINER-ONLY

See `docs/developer/release.md` "Execution Gate" + "Maintainer Runbook".
The 11-step runbook covers: version bump (`0.1.0.dev0` → `0.1.0`), dated
CHANGELOG heading, release commit, PR + CI green, tag, push tag, GitHub
Release, PyPI upload (`uv publish` or `twine upload`), verify PyPI
listing, and the post-release `0.2.0.dev0` bump.

Agent boundary: **never** bump the version, edit CHANGELOG to insert a
dated `[0.1.0]` heading, create a release commit, create / push a tag,
create a GitHub Release, or upload to PyPI. If asked, reply with the
relevant runbook step and stop.

## Phase C — Post-release housekeeping (after B succeeds)

- Strip "Status: draft" notice from `docs/release-notes/v0.1.md` header.
- Update README install snippet from "after v0.1 reaches PyPI" to the
  live `pip install noveldownloader` command (already pointing at the
  new name; just drop the conditional wording).
- If Pages is enabled (A4 toggle), confirm
  https://makunxiang-cmd.github.io/project_noveldownloader/ shows the
  release notes nav entry.
- Add a release log entry to
  `docs/superpowers/plans/2026-05-13-ndl-p7-release-candidate.md`
  recording the release commit hash, tag, and PyPI publish timestamp.
- Generate a new project-scoped PyPI API token; revoke the account-wide
  token from A2.

## Phase D — User installation flow (anyone)

After v0.1.0 lands on PyPI:

```bash
pip install noveldownloader                  # base install
pip install 'noveldownloader[browser]'       # optional Playwright fetcher
playwright install chromium                  # only with browser extra
ndl doctor browser                           # confirm browser runtime
ndl rules list                               # see builtin example_static
ndl download <url> -o book.epub --accept-disclaimer
ndl library list
ndl update --all --accept-disclaimer
ndl serve --accept-disclaimer                # http://127.0.0.1:8000
```

Authoritative user docs: `docs/user-guide/README.md`, optionally on the
hosted Pages site once A4 is finished.

## Phase E — Ongoing maintenance

- Triage issues filed via the templates from A6.
- Monitor CI runs for the known annotation noise (Actions cache HTTP
  400, Node.js 20 deprecation by 2026-06-02).
- Bug-fix patch releases follow the same B-runbook with `0.1.x`
  version bumps.
- Deferred candidates (see
  `docs/superpowers/plans/2026-05-13-ndl-p7-pre-release-hardening.md`
  "Non-goals"): `/updates` async migration, RuleUpdateService rule
  removal semantics, `cli/renderers.py` test coverage,
  `_fetch_chapter` extraction. Pick into a future P8 plan when
  scheduled.

## Workflow constraints (new since 2026-05-13)

- `main` is protected. Direct pushes by anyone (including the agent
  account) are rejected. Workflow:
  ```bash
  git checkout -b <topic>
  # edits, commits
  git push -u origin <topic>
  gh pr create --fill   # or with custom title/body
  gh pr merge --squash --auto   # or --merge, --rebase
  ```
- Force-push to `main` is blocked; deletion of `main` is blocked.
- `gh` CLI is installed and authenticated as `makunxiang-cmd` in this
  environment (`gh auth status` to verify).
- The pre-commit hook (ruff + mypy) still runs on every commit; the
  full quality gate (`ruff` / `ruff format` / `mypy` / `pytest --cov`)
  must be green before a PR is opened.

## Authoritative pointers (start here next session)

| When you need… | Read |
|---|---|
| Current handoff state | `docs/superpowers/SESSION-STATE.md` |
| This plan | this file |
| Release runbook (Phase B detail) | `docs/developer/release.md` |
| Reliability hardening record | `docs/superpowers/plans/2026-05-13-ndl-p7-pre-release-hardening.md` |
| Active P7 plan (now closed) | `docs/superpowers/plans/2026-05-13-ndl-p7-release-candidate.md` |
| User-facing release notes draft | `docs/release-notes/v0.1.md` |
| Agent / maintainer responsibilities | `AGENTS.md` |
| Engineering style + glossary | `CONTEXT.md`, `docs/developer/README.md` |
