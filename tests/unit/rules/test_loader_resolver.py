"""Tests for rule loading and URL resolution."""

from __future__ import annotations

import textwrap

import pytest

from ndl.core.errors import RuleNotFoundError, RuleValidationError
from ndl.rules.loader import RuleLoadSource, load_rule_file, load_rules
from ndl.rules.resolver import RuleResolver

RULE_YAML = """
id: local_rule
name: Local Rule
version: 1.0.0
author: Tests
priority: 10
url_patterns:
  - pattern: "https://local.test/book/*"
    type: glob
index:
  novel:
    title: { selector: "h1" }
    author: { selector: ".author" }
  chapter_list:
    container: "#chapters"
    items: "a"
    title: { selector: "self" }
    url: { selector: "self", attr: "href" }
chapter:
  title: { selector: "h1" }
  content: { selector: "#content", attr: "html" }
"""


def test_load_rule_file_validates_yaml(tmp_path) -> None:
    path = tmp_path / "local.yaml"
    path.write_text(textwrap.dedent(RULE_YAML), encoding="utf-8")

    rule = load_rule_file(path)

    assert rule.id == "local_rule"
    assert rule.matches("https://local.test/book/abc")


def test_load_rule_file_wraps_schema_errors(tmp_path) -> None:
    path = tmp_path / "broken.yaml"
    path.write_text("id: broken\n", encoding="utf-8")

    with pytest.raises(RuleValidationError):
        load_rule_file(path)


def test_load_rules_higher_source_priority_overrides_same_id(tmp_path) -> None:
    low = tmp_path / "low"
    high = tmp_path / "high"
    low.mkdir()
    high.mkdir()
    (low / "rule.yaml").write_text(textwrap.dedent(RULE_YAML), encoding="utf-8")
    (high / "rule.yaml").write_text(
        textwrap.dedent(RULE_YAML).replace("priority: 10", "priority: 99"),
        encoding="utf-8",
    )

    rules = load_rules(RuleLoadSource(low, 0), RuleLoadSource(high, 10))

    assert len(rules) == 1
    assert rules[0].priority == 99


def test_rule_resolver_uses_highest_rule_priority(tmp_path) -> None:
    path = tmp_path / "local.yaml"
    path.write_text(textwrap.dedent(RULE_YAML), encoding="utf-8")
    resolver = RuleResolver([load_rule_file(path)])

    assert resolver.resolve("https://local.test/book/abc").id == "local_rule"

    with pytest.raises(RuleNotFoundError):
        resolver.resolve("https://missing.test/book/abc")
