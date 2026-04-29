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
PaginationType = Literal["none", "next"]
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


class FetcherRule(StrictModel):
    """Fetcher configuration for a source rule."""

    type: FetcherType = "http"
    headers: dict[str, str] = Field(default_factory=dict)
    rate_limit: RateLimitRule = Field(default_factory=RateLimitRule)
    retry: RetryRule = Field(default_factory=RetryRule)
    robots: RobotsRule = Field(default_factory=RobotsRule)
    encoding: EncodingName = "auto"


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
    terminator: str | None = None

    @model_validator(mode="after")
    def _next_required_for_next_pagination(self) -> PaginationRule:
        if self.type == "next" and self.next is None:
            raise ValueError("pagination.next is required when pagination.type is 'next'")
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
    search: SearchRule | None = None

    @model_validator(mode="after")
    def _url_regexes_compile(self) -> SourceRule:
        for pattern in self.url_patterns:
            if pattern.type == "regex":
                try:
                    re.compile(pattern.pattern)
                except re.error as exc:
                    raise ValueError(f"invalid URL regex: {exc}") from exc
        return self

    def matches(self, url: str) -> bool:
        """Return whether any enabled URL pattern matches `url`."""
        return self.enabled and any(pattern.matches(url) for pattern in self.url_patterns)
