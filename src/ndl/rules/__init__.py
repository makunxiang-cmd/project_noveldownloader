"""Rule schema, loading, selection, and selector execution."""

from __future__ import annotations

from ndl.rules.loader import (
    RuleLoadSource,
    load_builtin_rules,
    load_default_rules,
    load_rule_file,
    load_rule_text,
    load_rules,
)
from ndl.rules.resolver import RuleResolver
from ndl.rules.schema import (
    ArchiveDownloadRule,
    BrowserRule,
    BrowserViewportRule,
    ChapterListRule,
    ChapterRule,
    CleanRule,
    ContentSelector,
    FetcherRule,
    IndexRule,
    PaginationRule,
    RateLimitRule,
    RetryRule,
    RobotsRule,
    SearchRule,
    Selector,
    SourceRule,
    UrlPattern,
)
from ndl.rules.selector import clean_html_content, extract_selector

__all__ = [
    "ArchiveDownloadRule",
    "BrowserRule",
    "BrowserViewportRule",
    "ChapterListRule",
    "ChapterRule",
    "CleanRule",
    "ContentSelector",
    "FetcherRule",
    "IndexRule",
    "PaginationRule",
    "RateLimitRule",
    "RetryRule",
    "RobotsRule",
    "RuleLoadSource",
    "RuleResolver",
    "SearchRule",
    "Selector",
    "SourceRule",
    "UrlPattern",
    "clean_html_content",
    "extract_selector",
    "load_builtin_rules",
    "load_default_rules",
    "load_rule_file",
    "load_rule_text",
    "load_rules",
]
