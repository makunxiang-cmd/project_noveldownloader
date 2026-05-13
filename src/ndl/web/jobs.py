"""In-memory Web download jobs and progress streams."""

from __future__ import annotations

import asyncio
import json
from collections import OrderedDict
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from uuid import uuid4

from ndl.core.progress import ProgressEvent

JobStatus = Literal["queued", "running", "succeeded", "failed"]
_TERMINAL_STATUSES: frozenset[JobStatus] = frozenset({"succeeded", "failed"})
_DEFAULT_MAX_JOBS = 100


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
    notify: asyncio.Event = field(default_factory=asyncio.Event)


class JobRegistry:
    """Store in-process Web jobs and their progress events."""

    def __init__(self, *, max_jobs: int = _DEFAULT_MAX_JOBS) -> None:
        if max_jobs < 1:
            raise ValueError("max_jobs must be at least 1")
        self._max_jobs = max_jobs
        self._jobs: OrderedDict[str, DownloadJob] = OrderedDict()

    def create(self, *, url: str, target_format: str, save: bool) -> DownloadJob:
        """Create and store a queued job, evicting the oldest terminal job if at capacity."""
        self._evict_if_needed()
        job = DownloadJob(
            id=uuid4().hex,
            url=url,
            target_format=target_format,
            save=save,
        )
        self._jobs[job.id] = job
        return job

    def _evict_if_needed(self) -> None:
        while len(self._jobs) >= self._max_jobs:
            terminal_id = next(
                (job_id for job_id, job in self._jobs.items() if job.status in _TERMINAL_STATUSES),
                None,
            )
            if terminal_id is None:
                return
            del self._jobs[terminal_id]

    def get(self, job_id: str) -> DownloadJob | None:
        """Return a job by id, or None."""
        return self._jobs.get(job_id)

    def list(self) -> list[DownloadJob]:
        """Return jobs in insertion order."""
        return list(self._jobs.values())

    async def record(self, job_id: str, event: ProgressEvent) -> None:
        """Append a progress event to a job and notify any SSE waiter."""
        job = self._jobs[job_id]
        job.events.append(event)
        job.notify.set()

    def mark_running(self, job_id: str) -> None:
        """Mark a job as running."""
        job = self._jobs[job_id]
        job.status = "running"
        job.notify.set()

    def mark_succeeded(self, job_id: str, *, output_path: Path, novel_id: int | None) -> None:
        """Mark a job as succeeded."""
        job = self._jobs[job_id]
        job.status = "succeeded"
        job.output_path = output_path
        job.novel_id = novel_id
        job.notify.set()

    def mark_failed(self, job_id: str, message: str) -> None:
        """Mark a job as failed with a user-visible message."""
        job = self._jobs[job_id]
        job.status = "failed"
        job.error_message = message
        job.notify.set()

    async def stream(self, job_id: str) -> AsyncIterator[dict[str, str]]:
        """Yield Server-Sent Events for a job until it reaches a terminal state."""
        sent = 0
        while True:
            job = self._jobs[job_id]
            while sent < len(job.events):
                event = job.events[sent]
                sent += 1
                yield {"event": "progress", "data": event.model_dump_json()}
            if job.status in _TERMINAL_STATUSES:
                yield {"event": "status", "data": _job_status_data(job)}
                return
            job.notify.clear()
            await job.notify.wait()


def _job_status_data(job: DownloadJob) -> str:
    if job.status == "succeeded":
        output_path = str(job.output_path) if job.output_path is not None else ""
        return json.dumps(
            {"status": "succeeded", "output_path": output_path, "novel_id": job.novel_id}
        )
    return json.dumps({"status": "failed", "error": job.error_message or "Download failed."})
