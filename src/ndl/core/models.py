"""Domain models used as NDL's intermediate representation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

NovelStatus = Literal["ongoing", "completed", "unknown"]


class Chapter(BaseModel):
    """A fully fetched chapter in normalized plain text form."""

    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=0, description="Zero-based order within the novel.")
    title: str = Field(min_length=1)
    content: str
    source_url: str | None = None
    word_count: int = Field(default=0, ge=0)
    published_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def _fill_word_count(cls, data: Any) -> Any:
        if isinstance(data, dict):
            existing = data.get("word_count") or 0
            if existing == 0:
                content = data.get("content", "") or ""
                if isinstance(content, str):
                    return {**data, "word_count": len("".join(content.split()))}
        return data

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        return value.strip()


class ChapterStub(BaseModel):
    """A chapter entry discovered on an index page before body fetch."""

    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=0)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)

    @field_validator("title", "url")
    @classmethod
    def _strip_non_empty(cls, value: str) -> str:
        return value.strip()


class Novel(BaseModel):
    """The single in-memory representation shared by download and conversion flows."""

    title: str = Field(min_length=1)
    author: str = Field(min_length=1)
    source_url: str | None = None
    source_rule_id: str = Field(min_length=1)
    summary: str | None = None
    cover_url: str | None = None
    cover_data: bytes | None = None
    tags: list[str] = Field(default_factory=list)
    status: NovelStatus = "unknown"
    chapters: list[Chapter] = Field(default_factory=list)
    fetched_at: datetime
    last_updated: datetime | None = None

    @field_validator("title", "author", "source_rule_id")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("cover_url")
    @classmethod
    def _validate_optional_cover_url(cls, value: str | None) -> str | None:
        if value is not None:
            HttpUrl(value)
        return value

    @model_validator(mode="after")
    def _chapters_are_unique_and_ordered(self) -> Novel:
        indices = [chapter.index for chapter in self.chapters]
        if len(indices) != len(set(indices)):
            raise ValueError("chapter indices must be unique")
        if indices != sorted(indices):
            raise ValueError("chapters must be sorted by index")
        return self
