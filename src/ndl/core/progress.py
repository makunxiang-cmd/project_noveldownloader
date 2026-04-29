"""Progress events shared by CLI and future Web SSE consumers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProgressKind = Literal["stage", "chapter", "done", "error"]
ProgressStage = Literal[
    "resolving_rule",
    "fetching_index",
    "fetching_chapters",
    "saving",
    "converting",
]


class ProgressEvent(BaseModel):
    """A transport-neutral progress notification."""

    model_config = ConfigDict(frozen=True)

    kind: ProgressKind
    stage: ProgressStage | None = None
    total: int | None = Field(default=None, ge=0)
    done: int | None = Field(default=None, ge=0)
    current_title: str | None = None
    message: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


ProgressCallback = Callable[[ProgressEvent], Awaitable[None]]
