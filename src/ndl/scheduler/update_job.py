"""APScheduler wrapper for recurring library updates."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ndl.application.services import UpdateResult
from ndl.core.errors import NDLError

UpdateAllCallback = Callable[[], Awaitable[list[UpdateResult]]]


class SchedulerBackend(Protocol):
    """Subset of APScheduler used by UpdateScheduler."""

    def add_job(self, func: Any, trigger: str, **kwargs: Any) -> Any:
        """Register a scheduled job."""

    def start(self) -> None:
        """Start the scheduler."""

    def shutdown(self, wait: bool = True) -> None:
        """Stop the scheduler."""


@dataclass
class UpdateSchedulerState:
    """Runtime status for the recurring update job."""

    running: bool = False
    last_run_at: datetime | None = None
    last_results: list[UpdateResult] = field(default_factory=list)
    last_error: str | None = None


class UpdateScheduler:
    """Run UpdateService.update_all() on an APScheduler interval."""

    def __init__(
        self,
        *,
        update_all: UpdateAllCallback,
        interval_hours: int = 6,
        scheduler: SchedulerBackend | None = None,
    ) -> None:
        if interval_hours < 1:
            raise ValueError("interval_hours must be at least 1")
        self._update_all = update_all
        self._interval_hours = interval_hours
        self._scheduler = scheduler or AsyncIOScheduler()
        self.state = UpdateSchedulerState()

    def start(self) -> None:
        """Start the recurring update job."""
        if self.state.running:
            return
        self._scheduler.add_job(
            self.run_once,
            "interval",
            hours=self._interval_hours,
            id="ndl-update-all",
            coalesce=True,
            max_instances=1,
            replace_existing=True,
        )
        self._scheduler.start()
        self.state.running = True

    def shutdown(self) -> None:
        """Stop the recurring update job."""
        if not self.state.running:
            return
        self._scheduler.shutdown(wait=False)
        self.state.running = False

    async def run_once(self) -> None:
        """Run one update pass and record the outcome."""
        self.state.last_run_at = datetime.now(timezone.utc)
        try:
            self.state.last_results = await self._update_all()
            self.state.last_error = None
        except NDLError as exc:
            self.state.last_results = []
            self.state.last_error = exc.user_message()
