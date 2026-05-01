"""Rich-backed progress renderers for CLI commands."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from ndl.core.progress import ProgressCallback, ProgressEvent, ProgressStage

_STAGE_LABELS: dict[ProgressStage, str] = {
    "resolving_rule": "Resolving rule",
    "fetching_index": "Fetching index",
    "fetching_chapters": "Fetching chapters",
    "saving": "Saving",
    "converting": "Converting",
}


@asynccontextmanager
async def cli_progress() -> AsyncIterator[ProgressCallback | None]:
    """Yield a ProgressCallback rendering to stderr; None when non-interactive."""
    console = Console(stderr=True)
    if not console.is_terminal:
        yield None
        return

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )
    tasks: dict[ProgressStage, TaskID] = {}

    async def callback(event: ProgressEvent) -> None:
        if event.stage is None:
            return
        description = _describe(event)
        task_id = tasks.get(event.stage)
        if task_id is None:
            tasks[event.stage] = progress.add_task(
                description,
                total=event.total or 0,
                completed=event.done or 0,
            )
            return
        if event.kind == "done":
            total = event.total or event.done or 0
            progress.update(task_id, description=description, total=total, completed=total)
            return
        progress.update(
            task_id,
            description=description,
            total=event.total if event.total is not None else None,
            completed=event.done if event.done is not None else None,
        )

    with progress:
        yield callback


def _describe(event: ProgressEvent) -> str:
    if event.message:
        return event.message
    assert event.stage is not None
    return _STAGE_LABELS.get(event.stage, event.stage)
