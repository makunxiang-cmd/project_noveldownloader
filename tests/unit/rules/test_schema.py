"""Tests for source rule schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ndl.rules.loader import load_builtin_rules
from ndl.rules.schema import (
    BrowserRule,
    FetcherRule,
    PaginationRule,
    RateLimitRule,
    RobotsRule,
    Selector,
    SourceRule,
)


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


def test_browser_rule_validates_runtime_controls() -> None:
    rule = BrowserRule(
        navigation_timeout_ms=15000,
        wait_until="domcontentloaded",
        wait_for_selector="#ready",
        extra_wait_ms=250,
        viewport={"width": 1024, "height": 768},
        javascript_enabled=False,
    )

    assert rule.navigation_timeout_ms == 15000
    assert rule.wait_until == "domcontentloaded"
    assert rule.wait_for_selector == "#ready"
    assert rule.extra_wait_ms == 250
    assert rule.viewport.width == 1024
    assert rule.javascript_enabled is False


def test_browser_rule_rejects_invalid_runtime_controls() -> None:
    with pytest.raises(ValidationError):
        BrowserRule(wait_until="idle")
    with pytest.raises(ValidationError):
        BrowserRule(navigation_timeout_ms=999)
    with pytest.raises(ValidationError):
        BrowserRule(viewport={"width": 100, "height": 900})


def test_pagination_rule_validates_supported_modes() -> None:
    next_selector = Selector(selector="a.next", attr="href", resolve="relative")

    assert PaginationRule().type == "none"
    assert PaginationRule(type="next", next=next_selector).next == next_selector

    template = PaginationRule(
        type="index-template",
        template="{source_url}index_{page}.html",
        start=2,
        max_pages=20,
    )

    assert template.template == "{source_url}index_{page}.html"
    assert template.start == 2
    assert template.max_pages == 20


def test_pagination_rule_rejects_mismatched_fields() -> None:
    next_selector = Selector(selector="a.next", attr="href")

    with pytest.raises(ValidationError, match=r"pagination\.next"):
        PaginationRule(type="next")
    with pytest.raises(ValidationError, match=r"pagination\.next"):
        PaginationRule(type="none", next=next_selector)
    with pytest.raises(ValidationError, match=r"pagination\.template"):
        PaginationRule(type="index-template")
    with pytest.raises(ValidationError, match=r"pagination\.template"):
        PaginationRule(type="next", next=next_selector, template="index_{page}.html")


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
