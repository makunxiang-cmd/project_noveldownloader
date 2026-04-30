"""Progress event helpers for application services."""

from __future__ import annotations

from ndl.core.progress import ProgressCallback, ProgressEvent, ProgressKind, ProgressStage


async def emit_progress(
    progress: ProgressCallback | None,
    *,
    kind: ProgressKind,
    stage: ProgressStage | None = None,
    total: int | None = None,
    done: int | None = None,
    current_title: str | None = None,
    message: str | None = None,
) -> None:
    """Send a progress event when a callback is configured."""
    if progress is None:
        return
    await progress(
        ProgressEvent(
            kind=kind,
            stage=stage,
            total=total,
            done=done,
            current_title=current_title,
            message=message,
        )
    )
