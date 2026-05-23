"""Tests for source rule schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from tests.rule_fixtures import load_example_static_rule

from ndl.rules.schema import (
    ArchiveDownloadRule,
    BrowserRule,
    BrowserSearchRule,
    ChapterListRule,
    FetcherRule,
    PaginationRule,
    RateLimitRule,
    RobotsRule,
    SearchRule,
    Selector,
    SourceRule,
)


def test_example_rule_fixture_loads_and_matches_url() -> None:
    rule = load_example_static_rule()

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


def test_chapter_list_rule_accepts_container_pick_modes() -> None:
    title = Selector(selector="a")
    url = Selector(selector="a", attr="href")

    assert ChapterListRule(container="ul", items="li", title=title, url=url).pick == "first"
    assert (
        ChapterListRule(container="ul", pick="largest", items="li", title=title, url=url).pick
        == "largest"
    )

    with pytest.raises(ValidationError):
        ChapterListRule(container="ul", pick="middle", items="li", title=title, url=url)


def test_archive_download_rule_validates_trigger_modes() -> None:
    url_archive = ArchiveDownloadRule(
        trigger="url-template",
        url_template="{source_url}/download.txt",
        encodings=["utf-8", "gb18030"],
        strip_patterns=[r"^AD.*$"],
    )
    selector_archive = ArchiveDownloadRule(trigger="selector", selector="a.download")

    assert url_archive.format == "txt"
    assert url_archive.url_template == "{source_url}/download.txt"
    assert selector_archive.selector == "a.download"


def test_archive_download_rule_rejects_mismatched_fields() -> None:
    with pytest.raises(ValidationError, match=r"download_archive\.url_template"):
        ArchiveDownloadRule(trigger="url-template")
    with pytest.raises(ValidationError, match=r"download_archive\.selector"):
        ArchiveDownloadRule(trigger="selector")
    with pytest.raises(ValidationError, match=r"download_archive\.selector"):
        ArchiveDownloadRule(
            trigger="url-template",
            url_template="{source_url}/download.txt",
            selector="a.download",
        )
    with pytest.raises(ValidationError, match=r"download_archive\.url_template"):
        ArchiveDownloadRule(
            trigger="selector",
            selector="a.download",
            url_template="{source_url}/download.txt",
        )
    with pytest.raises(ValidationError, match="invalid archive strip pattern"):
        ArchiveDownloadRule(
            trigger="url-template",
            url_template="{source_url}/download.txt",
            strip_patterns=["["],
        )


def test_search_rule_accepts_post_body() -> None:
    rule = SearchRule(
        method="POST",
        url_template="https://example.test/search.html",
        body={"s": "{keyword}"},
        results_container=".results",
        items="li",
        fields={
            "title": {"selector": "a"},
            "url": {"selector": "a", "attr": "href", "resolve": "relative"},
        },
    )

    assert rule.method == "POST"
    assert rule.body == {"s": "{keyword}"}


def test_search_rule_rejects_mismatched_body_modes() -> None:
    fields = {
        "title": {"selector": "a"},
        "url": {"selector": "a", "attr": "href"},
    }

    with pytest.raises(ValidationError, match=r"search\.body"):
        SearchRule(
            method="GET",
            url_template="https://example.test/search?q={keyword}",
            body={"s": "{keyword}"},
            results_container=".results",
            items="li",
            fields=fields,
        )
    with pytest.raises(ValidationError, match=r"search\.body"):
        SearchRule(
            method="POST",
            url_template="https://example.test/search.html",
            results_container=".results",
            items="li",
            fields=fields,
        )


def test_browser_search_rule_requires_wait_condition() -> None:
    rule = BrowserSearchRule(
        navigate_url="https://example.test/",
        input_selector="input[name='searchkey']",
        submit_selector=".btn-tosearch",
        wait_for_url="**/modules/article/search.php**",
    )

    assert rule.wait_for_url == "**/modules/article/search.php**"

    with pytest.raises(ValidationError, match="wait_for_url"):
        BrowserSearchRule(
            navigate_url="https://example.test/",
            input_selector="input[name='searchkey']",
            submit_selector=".btn-tosearch",
        )


def test_source_rule_rejects_browser_search_without_browser_fetcher() -> None:
    base = _minimal_rule()
    base["search"] = _browser_search_block()

    with pytest.raises(ValidationError, match=r"search\.browser"):
        SourceRule.model_validate(base)


def test_source_rule_accepts_qishuxia_style_browser_search() -> None:
    base = _minimal_rule()
    fetcher = base["fetcher"]
    assert isinstance(fetcher, dict)
    fetcher = dict(fetcher)
    fetcher["type"] = "browser"
    base["fetcher"] = fetcher
    base["search"] = _browser_search_block()

    rule = SourceRule.model_validate(base)

    assert rule.search is not None
    assert rule.search.browser is not None
    assert rule.search.browser.input_selector == "input[name='searchkey']"


def test_source_rule_rejects_archive_selector_without_browser_fetcher() -> None:
    base = _minimal_rule()
    base["download_archive"] = {"trigger": "selector", "selector": "a.download"}

    with pytest.raises(ValidationError, match="selector trigger requires"):
        SourceRule.model_validate(base)


def test_source_rule_rejects_archive_with_index_pagination() -> None:
    base = _minimal_rule()
    index = base["index"]
    assert isinstance(index, dict)
    index = dict(index)
    index["pagination"] = {
        "type": "next",
        "next": {"selector": "a.next", "attr": "href", "resolve": "relative"},
    }
    base["index"] = index
    base["download_archive"] = {
        "trigger": "url-template",
        "url_template": "{source_url}/download.txt",
    }

    with pytest.raises(ValidationError, match="cannot be combined"):
        SourceRule.model_validate(base)


def test_source_rule_accepts_qishuxia_style_browser_archive() -> None:
    base = _minimal_rule()
    fetcher = base["fetcher"]
    assert isinstance(fetcher, dict)
    fetcher = dict(fetcher)
    fetcher["type"] = "browser"
    base["fetcher"] = fetcher
    base["download_archive"] = {
        "format": "txt",
        "trigger": "selector",
        "selector": "a[href*='txtarticle.php']",
        "encodings": ["utf-8-sig", "gb18030", "gbk"],
        "strip_patterns": ["^\\u6700\\u65b0\\u7f51\\u5740\\uff1a?.*$"],
    }

    rule = SourceRule.model_validate(base)

    assert rule.download_archive is not None
    assert rule.download_archive.selector == "a[href*='txtarticle.php']"


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


def _browser_search_block() -> dict[str, object]:
    return {
        "url_template": "https://www.qishuxia.com/",
        "browser": {
            "navigate_url": "https://www.qishuxia.com/",
            "input_selector": "input[name='searchkey']",
            "submit_selector": ".btn-tosearch",
            "wait_for_url": "**/modules/article/search.php**",
        },
        "results_container": ".search-list",
        "items": "li",
        "fields": {
            "title": {"selector": "a.book-name"},
            "author": {"selector": ".author"},
            "url": {"selector": "a.book-name", "attr": "href", "resolve": "relative"},
        },
    }
