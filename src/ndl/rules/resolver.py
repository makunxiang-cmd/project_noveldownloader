"""Rule resolution for source URLs."""

from __future__ import annotations

from collections.abc import Iterable

from ndl.core.errors import RuleNotFoundError
from ndl.rules.schema import SourceRule


class RuleResolver:
    """Selects the highest-priority enabled rule matching a URL."""

    def __init__(self, rules: Iterable[SourceRule]) -> None:
        self._rules = sorted(rules, key=lambda rule: (-rule.priority, rule.id))

    def list_rules(self) -> list[SourceRule]:
        """Return rules in resolution order."""
        return list(self._rules)

    def resolve(self, url: str) -> SourceRule:
        """Return the first enabled rule matching `url`."""
        for rule in self._rules:
            if rule.matches(url):
                return rule
        raise RuleNotFoundError(url)
