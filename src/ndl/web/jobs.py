"""In-memory Web download jobs and progress streams."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from uuid import uuid4

from ndl.core.progress import ProgressEvent

JobStatus = Literal["queued", "running", "succeeded", "failed"]


@dataclass
class DownloadJob:
    """A single in-process Web download job."""

    id: str
    url: str
    target_format: str
    save: bool
    status: JobStatus = "queued"
    output_path: Path | None = None
    novel_id: int | None = None
    error_message: str | None = None
    events: list[ProgressEvent] = field(default_factory=list)


class JobRegistry:
    """Store in-process Web jobs and their progress events."""

    def __init__(self) -> None:
        self._jobs: dict[str, DownloadJob] = {}

    def create(self, *, url: str, target_format: str, save: bool) -> DownloadJob:
        """Create and store a queued job."""
        job = DownloadJob(
            id=uuid4().hex,
            url=url,
            target_format=target_format,
            save=save,
        )
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> DownloadJob | None:
        """Return a job by id, or None."""
        return self._jobs.get(job_id)

    def list(self) -> list[DownloadJob]:
        """Return jobs in insertion order."""
        return list(self._jobs.values())

    async def record(self, job_id: str, event: ProgressEvent) -> None:
        """Append a progress event to a job."""
        job = self._jobs[job_id]
        job.events.append(event)

    def mark_running(self, job_id: str) -> None:
        """Mark a job as running."""
        self._jobs[job_id].status = "running"

    def mark_succeeded(self, job_id: str, *, output_path: Path, novel_id: int | None) -> None:
        """Mark a job as succeeded."""
        job = self._jobs[job_id]
        job.status = "succeeded"
        job.output_path = output_path
        job.novel_id = novel_id

    def mark_failed(self, job_id: str, message: str) -> None:
        """Mark a job as failed with a user-visible message."""
        job = self._jobs[job_id]
        job.status = "failed"
        job.error_message = message

    async def stream(self, job_id: str) -> AsyncIterator[dict[str, str]]:
        """Yield Server-Sent Events for a job until it reaches a terminal state."""
        sent = 0
        while True:
            job = self._jobs[job_id]
            while sent < len(job.events):
                event = job.events[sent]
                sent += 1
                yield {"event": "progress", "data": event.model_dump_json()}
            if job.status in ("succeeded", "failed"):
                yield {"event": "status", "data": _job_status_data(job)}
                return
            await asyncio.sleep(0.1)


def _job_status_data(job: DownloadJob) -> str:
    if job.status == "succeeded":
        output_path = str(job.output_path) if job.output_path is not None else ""
        return json.dumps(
            {"status": "succeeded", "output_path": output_path, "novel_id": job.novel_id}
        )
    return json.dumps({"status": "failed", "error": job.error_message or "Download failed."})
