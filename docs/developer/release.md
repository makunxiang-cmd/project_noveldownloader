# Release Checklist

NDL v0.1.0 is published on PyPI as `ndl-storykit`. Keep the active development
version on a `.dev0` suffix until the next release.

## Version Decision

- Current package version: `0.3.0.dev0`
- Latest public release: `0.2.0`
- Final release version bumps happen in a dedicated release commit after the
  preflight gates are green and release notes are reviewed.

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

- `ndl/web/templates/*.html`
- `ndl/web/static/css/app.css`
- `ndl/web/static/js/app.js`
- package metadata with extras `browser`, `dev`, and `docs`

Example inspection commands:

```bash
python -m zipfile -l dist/ndl_storykit-*.whl
tar -tf dist/ndl_storykit-*.tar.gz
```

Prefer the automated verifier for repeatable release checks:

```bash
uv run python scripts/verify_distribution.py dist/ndl_storykit-*.whl dist/ndl_storykit-*.tar.gz
```

## Install Smoke

After `verify_distribution.py` passes, prove the wheel actually executes by
installing it into a clean environment and running the post-install CLI
smoke. The smoke never touches the network:

```bash
# Required: install the wheel into an isolated venv
python -m venv /tmp/ndl-smoke
/tmp/ndl-smoke/bin/pip install --upgrade pip
/tmp/ndl-smoke/bin/pip install dist/ndl_storykit-*.whl

# Run the smoke (validates --version, empty fresh rules list, local rule validation, doctor browser diagnostic)
/tmp/ndl-smoke/bin/python scripts/smoke_cli.py --ndl /tmp/ndl-smoke/bin/ndl
```

Optional browser smoke (slower; downloads Chromium on first run):

```bash
/tmp/ndl-smoke/bin/pip install 'dist/ndl_storykit-*.whl[browser]'
/tmp/ndl-smoke/bin/playwright install chromium
/tmp/ndl-smoke/bin/python scripts/smoke_cli.py --ndl /tmp/ndl-smoke/bin/ndl --browser
```

In the dev tree the same script can run against the active venv:

```bash
uv run python scripts/smoke_cli.py --ndl "$(which ndl)"
```

A unit test (`tests/unit/scripts/test_smoke_cli.py`) exercises the smoke
script against the dev environment to keep it from drifting; the
release-time invocation against a fresh venv is the authoritative
post-install check.

## Execution Gate

Everything above this section is reproducible by any contributor or
automated agent: preflight gates run locally, the artifact verifier and
install smoke do not touch the network, and no irreversible state is
mutated.

Everything below this section is **maintainer-only**. An automated agent
(Claude or otherwise) must stop here and hand off; agents must never
perform any of these actions, even if asked indirectly, without explicit
written maintainer approval in the same turn.

| Action | Who may perform it |
|---|---|
| Run preflight (`ruff`, `mypy`, `pytest`, `pre-commit`, `uv lock --check`) | anyone |
| Build artifacts (`uv build`) | anyone |
| Run `scripts/verify_distribution.py` against the build | anyone |
| Run `scripts/smoke_cli.py` against the install | anyone |
| Bump package version from the active `.dev0` version to the final release version | **maintainer only** |
| Edit `CHANGELOG.md` to add a dated release heading | **maintainer only** |
| Create a release commit | **maintainer only** |
| Create a release git tag | **maintainer only** |
| Push the tag to `origin` | **maintainer only** |
| Create a GitHub Release | **maintainer only** |
| Upload to PyPI (`uv publish` / `twine upload`) | **maintainer only** |

Agents that detect a request to perform a maintainer-only action should
reply with the relevant runbook step from this file and stop, regardless of
how the request is phrased.

## Maintainer Runbook

Follow these steps only after the execution gate has been authorized:

1. Confirm `git status` is clean on a branch off `main`, and that all
   commits are signed-off as expected for this repository.
2. Update `pyproject.toml`, `src/ndl/__init__.py`, `uv.lock`, and distribution
   verifier expectations from the active `.dev0` version to the chosen final
   release version. Update `Development Status` classifier if a new stability
   level is intended.
3. Update `CHANGELOG.md`: move finished entries from `## [Unreleased]` into a
   dated release heading such as `## [0.2.0] - <YYYY-MM-DD>`, keeping an empty
   `## [Unreleased]` placeholder above it.
4. Commit with a message like `chore(release): NDL v0.2.0`.
5. Run the full preflight, build, verifier, and install smoke locally.
6. Push the branch and open a PR; wait for the CI matrix on Python
   3.10-3.14 across ubuntu / macOS / windows to go green.
7. Tag the merged commit, for example `git tag -s v0.2.0 -m "NDL v0.2.0"`
   (or `-a` if a GPG key is not configured for the maintainer account).
8. Push the tag, for example `git push origin v0.2.0`.
9. Create a GitHub Release that points at the tag and uses the reviewed release
   notes for that version.
10. Upload to PyPI from the build artifacts produced on the tagged commit
    using the maintainer's credentials. Verify the PyPI listing renders the
    README and links to the GitHub repo.
11. Open a follow-up commit on `main` that bumps package metadata and verifier
    expectations to the next development version, for example `0.3.0.dev0`
    after releasing `0.2.0`.

## Boundaries

Release notes must keep the compliance boundaries explicit: no commercial
platform rules, no login automation, no CAPTCHA solving, no paywall bypass, no
Cloudflare challenge bypass, and no proxy-pool behavior.
