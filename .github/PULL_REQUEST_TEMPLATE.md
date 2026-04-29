## Summary

<!-- What does this PR do? -->

## Type

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Rule addition/update
- [ ] Documentation
- [ ] Refactor / chore

## Related Issues

<!-- Fixes #123 / Closes #456 / Refs #789 -->

## Checklist

- [ ] Tests added / updated for new behavior
- [ ] `uv run ruff check .` passes
- [ ] `uv run ruff format --check .` passes
- [ ] `uv run mypy src/ndl` passes
- [ ] `uv run pytest` passes
- [ ] CHANGELOG.md updated for user-facing changes
- [ ] Documentation updated if behavior/API changed

## For Rule Contributions

- [ ] Contract fixtures added under `tests/contract/fixtures/<rule_id>/`
- [ ] `rate_limit.min_interval_ms >= 500`
- [ ] `max_concurrency <= 3`
- [ ] User-Agent includes NDL identifier
- [ ] If `ignore_robots: true`, `ignore_justification` is provided
- [ ] Target site is not commercial/paywalled
