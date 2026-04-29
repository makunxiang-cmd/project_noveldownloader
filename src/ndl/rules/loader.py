"""Rule loading from built-in, remote, and user directories."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from ndl.core.errors import RuleLoadError, RuleValidationError
from ndl.rules.schema import SourceRule


@dataclass(frozen=True)
class RuleLoadSource:
    """A directory participating in rule precedence."""

    path: Path
    priority: int


def load_rule_file(path: Path) -> SourceRule:
    """Load and validate one YAML rule file."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuleLoadError(f"Could not read rule file: {path}", detail=str(exc)) from exc
    except yaml.YAMLError as exc:
        raise RuleLoadError(f"Could not parse YAML rule file: {path}", detail=str(exc)) from exc

    if not isinstance(raw, dict):
        raise RuleValidationError(f"Rule file must contain a YAML mapping: {path}")

    try:
        return SourceRule.model_validate(raw)
    except ValidationError as exc:
        raise RuleValidationError(
            f"Rule schema validation failed: {path}", detail=str(exc)
        ) from exc


def load_builtin_rules() -> list[SourceRule]:
    """Load YAML rules bundled inside the package."""
    rules_package = resources.files("ndl.builtin_rules")
    rules = []
    for rule_path in sorted(rules_package.iterdir(), key=lambda item: item.name):
        if rule_path.name.endswith((".yaml", ".yml")):
            with resources.as_file(rule_path) as path:
                rules.append(load_rule_file(path))
    return rules


def load_rules(*sources: RuleLoadSource) -> list[SourceRule]:
    """Load multiple rule directories, with later/higher priority sources overriding IDs."""
    loaded: dict[str, tuple[int, SourceRule]] = {}
    for source in sorted(sources, key=lambda item: item.priority):
        if not source.path.exists():
            continue
        for rule_path in sorted(source.path.glob("*.y*ml")):
            rule = load_rule_file(rule_path)
            current = loaded.get(rule.id)
            if current is None or source.priority >= current[0]:
                loaded[rule.id] = (source.priority, rule)
    return [
        rule
        for _, rule in sorted(loaded.values(), key=lambda item: (-item[1].priority, item[1].id))
    ]


def rule_from_mapping(raw: dict[str, Any]) -> SourceRule:
    """Validate an already-parsed mapping as a SourceRule."""
    try:
        return SourceRule.model_validate(raw)
    except ValidationError as exc:
        raise RuleValidationError("Rule schema validation failed.", detail=str(exc)) from exc
