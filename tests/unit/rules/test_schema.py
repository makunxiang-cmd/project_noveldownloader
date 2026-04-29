"""Tests for source rule schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ndl.rules.loader import load_builtin_rules
from ndl.rules.schema import FetcherRule, RateLimitRule, RobotsRule, SourceRule


def test_builtin_example_rule_loads_and_matches_url() -> None:
    rule = next(rule for rule in load_builtin_rules() if rule.id == "example_static")

    assert rule.matches("https://example-novels.test/book/123")
    assert not rule.matches("https://other.test/book/123")
    assert rule.fetcher.rate_limit.min_interval_ms == 800
    assert rule.fetcher.rate_limit.max_concurrency == 2


def test_rate_limit_enforces_ethics_floor() -> None:
    with pytest.raises(ValidationError):
        RateLimitRule(min_interval_ms=499)


def test_rate_limit_enforces_concurrency_ceiling() -> None:
    with pytest.raises(ValidationError):
        RateLimitRule(max_concurrency=4)


def test_robots_ignore_requires_justification() -> None:
    with pytest.raises(ValidationError, match="ignore_justification"):
        RobotsRule(respect=False)


def test_source_rule_rejects_invalid_regex() -> None:
    base = _minimal_rule()
    base["url_patterns"] = [{"pattern": "[", "type": "regex"}]

    with pytest.raises(ValidationError):
        SourceRule.model_validate(base)


def _minimal_rule() -> dict[str, object]:
    return {
        "id": "minimal",
        "name": "Minimal",
        "version": "1.0.0",
        "author": "NDL",
        "url_patterns": [{"pattern": "https://example.test/*", "type": "glob"}],
        "fetcher": FetcherRule().model_dump(),
        "index": {
            "novel": {
                "title": {"selector": "h1"},
                "author": {"selector": ".author"},
            },
            "chapter_list": {
                "container": "#chapters",
                "items": "a",
                "title": {"selector": "self"},
                "url": {"selector": "self", "attr": "href"},
            },
        },
        "chapter": {
            "title": {"selector": "h1"},
            "content": {"selector": "#content", "attr": "html"},
        },
    }
