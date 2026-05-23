"""Pydantic schema for declarative source rules."""

from __future__ import annotations

import fnmatch
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PatternType = Literal["regex", "glob"]
FetcherType = Literal["http", "browser"]
BackoffType = Literal["fixed", "exponential"]
EncodingName = Literal["utf-8", "gbk", "gb18030", "auto"]
BrowserWaitUntil = Literal["commit", "domcontentloaded", "load", "networkidle"]
PaginationType = Literal["none", "next", "index-template"]
ArchiveFormat = Literal["txt"]
ArchiveTriggerType = Literal["url-template", "selector"]
SelectorAttr = Literal["text", "html", "href", "src"]
ResolveMode = Literal["none", "relative"]


class StrictModel(BaseModel):
    """Base model forbidding unknown rule keys."""

    model_config = ConfigDict(extra="forbid")


class UrlPattern(StrictModel):
    """A URL matching pattern."""

    pattern: str = Field(min_length=1)
    type: PatternType

    @field_validator("pattern")
    @classmethod
    def _valid_regex(cls, value: str, info: object) -> str:
        # Pydantic v2 runs field validators before all sibling fields are
        # available, so SourceRule validates regex compilation as a second pass.
        return value

    def matches(self, url: str) -> bool:
        """Return whether this pattern matches `url`."""
        match self.type:
            case "regex":
                return re.search(self.pattern, url) is not None
            case "glob":
                return fnmatch.fnmatch(url, self.pattern)


class RateLimitRule(StrictModel):
    """Per-rule rate-limit constraints."""

    min_interval_ms: int = Field(default=1000, ge=500)
    max_concurrency: int = Field(default=1, ge=1, le=3)


class RetryRule(StrictModel):
    """Retry policy declared by a rule."""

    attempts: int = Field(default=3, ge=1, le=10)
    backoff: BackoffType = "exponential"


class RobotsRule(StrictModel):
    """robots.txt policy declared by a rule."""

    respect: bool = True
    ignore_justification: str | None = None

    @model_validator(mode="after")
    def _requires_justification_when_ignored(self) -> RobotsRule:
        if not self.respect and not self.ignore_justification:
            raise ValueError("ignore_justification is required when robots.respect is false")
        return self


class BrowserViewportRule(StrictModel):
    """Viewport settings for browser-backed rules."""

    width: int = Field(default=1280, ge=320, le=3840)
    height: int = Field(default=900, ge=240, le=2160)


class BrowserRule(StrictModel):
    """Browser runtime controls for browser-backed rules."""

    navigation_timeout_ms: int = Field(default=30000, ge=1000, le=120000)
    wait_until: BrowserWaitUntil = "networkidle"
    wait_for_selector: str | None = Field(default=None, min_length=1)
    extra_wait_ms: int = Field(default=0, ge=0, le=10000)
    viewport: BrowserViewportRule = Field(default_factory=BrowserViewportRule)
    javascript_enabled: bool = True


class FetcherRule(StrictModel):
    """Fetcher configuration for a source rule."""

    type: FetcherType = "http"
    headers: dict[str, str] = Field(default_factory=dict)
    rate_limit: RateLimitRule = Field(default_factory=RateLimitRule)
    retry: RetryRule = Field(default_factory=RetryRule)
    robots: RobotsRule = Field(default_factory=RobotsRule)
    encoding: EncodingName = "auto"
    browser: BrowserRule = Field(default_factory=BrowserRule)


class Selector(StrictModel):
    """Declarative field extraction rule."""

    selector: str = Field(min_length=1)
    attr: str = "text"
    regex: str | None = None
    regex_group: int = Field(default=1, ge=0)
    strip: bool = True
    default: str | None = None
    multiple: bool = False
    map: dict[str, str] = Field(default_factory=dict)
    resolve: ResolveMode = "none"

    @field_validator("regex")
    @classmethod
    def _regex_compiles(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                re.compile(value)
            except re.error as exc:
                raise ValueError(f"invalid regex: {exc}") from exc
        return value


class CleanRule(StrictModel):
    """Content-only cleanup rules."""

    remove_selectors: list[str] = Field(default_factory=list)
    strip_patterns: list[str] = Field(default_factory=list)
    normalize_whitespace: bool = True
    min_paragraph_length: int = Field(default=1, ge=0)

    @field_validator("strip_patterns")
    @classmethod
    def _strip_patterns_compile(cls, values: list[str]) -> list[str]:
        for value in values:
            try:
                re.compile(value)
            except re.error as exc:
                raise ValueError(f"invalid strip pattern: {exc}") from exc
        return values


class ContentSelector(Selector):
    """Selector with cleanup settings for chapter body content."""

    clean: CleanRule = Field(default_factory=CleanRule)


class NovelSelectors(StrictModel):
    """Novel metadata selectors for an index page."""

    title: Selector
    author: Selector
    summary: Selector | None = None
    cover: Selector | None = None
    status: Selector | None = None


class ChapterListRule(StrictModel):
    """Index page chapter list selectors."""

    container: str = Field(min_length=1)
    items: str = Field(min_length=1)
    title: Selector
    url: Selector


class PaginationRule(StrictModel):
    """Pagination configuration."""

    type: PaginationType = "none"
    next: Selector | None = None
    template: str | None = None
    start: int = Field(default=2, ge=1)
    max_pages: int = Field(default=50, ge=1, le=500)
    terminator: str | None = None

    @model_validator(mode="after")
    def _required_fields_match_pagination_type(self) -> PaginationRule:
        if self.type == "next" and self.next is None:
            raise ValueError("pagination.next is required when pagination.type is 'next'")
        if self.type != "next" and self.next is not None:
            raise ValueError("pagination.next is only valid when pagination.type is 'next'")
        if self.type == "index-template" and self.template is None:
            raise ValueError(
                "pagination.template is required when pagination.type is 'index-template'"
            )
        if self.type != "index-template" and self.template is not None:
            raise ValueError(
                "pagination.template is only valid when pagination.type is 'index-template'"
            )
        return self


class IndexRule(StrictModel):
    """Index page parsing rule."""

    url_template: str = "{source_url}"
    novel: NovelSelectors
    chapter_list: ChapterListRule
    pagination: PaginationRule = Field(default_factory=PaginationRule)


class ChapterRule(StrictModel):
    """Chapter page parsing rule."""

    title: Selector
    content: ContentSelector
    pagination: PaginationRule = Field(default_factory=PaginationRule)


class ArchiveDownloadRule(StrictModel):
    """Whole-book archive download configuration."""

    format: ArchiveFormat = "txt"
    trigger: ArchiveTriggerType
    url_template: str | None = None
    selector: str | None = None
    encodings: list[str] = Field(
        default_factory=lambda: ["utf-8-sig", "gb18030", "gbk"],
        min_length=1,
    )
    strip_patterns: list[str] = Field(default_factory=list)

    @field_validator("strip_patterns")
    @classmethod
    def _strip_patterns_compile(cls, values: list[str]) -> list[str]:
        for value in values:
            try:
                re.compile(value)
            except re.error as exc:
                raise ValueError(f"invalid archive strip pattern: {exc}") from exc
        return values

    @model_validator(mode="after")
    def _trigger_field_matches_trigger_type(self) -> ArchiveDownloadRule:
        if self.trigger == "url-template":
            if not self.url_template:
                raise ValueError("download_archive.url_template is required for url-template")
            if self.selector is not None:
                raise ValueError("download_archive.selector is only valid for selector")
        if self.trigger == "selector":
            if not self.selector:
                raise ValueError("download_archive.selector is required for selector")
            if self.url_template is not None:
                raise ValueError("download_archive.url_template is only valid for url-template")
        return self


class SearchFields(StrictModel):
    """Search result field selectors."""

    title: Selector
    author: Selector | None = None
    url: Selector


class SearchRule(StrictModel):
    """Optional search endpoint parsing rule."""

    url_template: str
    results_container: str
    items: str
    fields: SearchFields


class SourceRule(StrictModel):
    """Complete source rule."""

    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    author: str = Field(min_length=1)
    enabled: bool = True
    priority: int = 0
    url_patterns: list[UrlPattern] = Field(min_length=1)
    fetcher: FetcherRule = Field(default_factory=FetcherRule)
    index: IndexRule
    chapter: ChapterRule
    download_archive: ArchiveDownloadRule | None = None
    search: SearchRule | None = None

    @model_validator(mode="after")
    def _validate_cross_rule_constraints(self) -> SourceRule:
        for pattern in self.url_patterns:
            if pattern.type == "regex":
                try:
                    re.compile(pattern.pattern)
                except re.error as exc:
                    raise ValueError(f"invalid URL regex: {exc}") from exc
        if self.download_archive is not None:
            if self.index.pagination.type != "none":
                raise ValueError("download_archive cannot be combined with index.pagination")
            if self.download_archive.trigger == "selector" and self.fetcher.type != "browser":
                raise ValueError(
                    "download_archive selector trigger requires fetcher.type='browser'"
                )
        return self

    def matches(self, url: str) -> bool:
        """Return whether any enabled URL pattern matches `url`."""
        return self.enabled and any(pattern.matches(url) for pattern in self.url_patterns)
