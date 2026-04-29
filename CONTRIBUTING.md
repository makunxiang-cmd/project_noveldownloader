# Contributing to NDL

Thank you for your interest in contributing.

## Quick Start

```bash
git clone https://github.com/makunxiang-cmd/project_noveldownloader.git
cd project_noveldownloader

uv sync --all-extras

uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy src/ndl
uv run pre-commit install
```

## What to Contribute

### 1. New Site Rules

NDL is rule-driven. Adding support for a new site does not require writing Python.

1. Fork the repo
2. Create a YAML rule under `src/ndl/builtin_rules/<your_site>.yaml` for PRs, or `~/.ndl/rules/custom/` for personal use
3. Add a contract test fixture under `tests/contract/fixtures/<rule_id>/` containing `index.html`, `chapter.html`, `expected.json`
4. Run `uv run pytest tests/contract/ -k <rule_id>`
5. Submit a PR

Rules violating `DISCLAIMER.md` will be declined.

### 2. Bug Reports

Use the bug report template. Include:

- NDL version (`ndl --version`)
- OS and Python version
- Minimal URL, YAML, or command to reproduce
- Full traceback with `--log-level debug`

### 3. Feature Requests

Open a feature request issue and describe:

- The problem you're trying to solve, not just the proposed solution
- Alternative approaches you considered
- Whether you'd be willing to implement it

### 4. Code Contributions

1. Open an issue to discuss before large PRs over 200 LOC
2. Follow the existing architecture
3. Use TDD: every PR with code must include tests
4. Make sure all CI checks pass

## Development Conventions

- Formatting: `ruff format`
- Linting: `ruff check`
- Typing: `mypy --strict` on `src/ndl`
- Testing: `pytest`; aim for 80%+ coverage, 90%+ on `core/`, `rules/`, `converters/`
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`)

## License

By contributing, you agree your contributions will be licensed under the MIT License.
