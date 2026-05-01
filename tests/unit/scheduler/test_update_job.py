"""Unit tests for the recurring update scheduler."""

from __future__ import annotations

from typing import Any

import pytest

from ndl.application.services import UpdateResult
from ndl.core.errors import UserError
from ndl.scheduler import UpdateScheduler


class FakeSchedulerBackend:
    """Capture scheduler interactions without starting a background loop."""

    def __init__(self) -> None:
        self.jobs: list[tuple[Any, str, dict[str, Any]]] = []
        self.started = False
        self.shutdown_wait: bool | None = None

    def add_job(self, func: Any, trigger: str, **kwargs: Any) -> Any:
        self.jobs.append((func, trigger, kwargs))
        return object()

    def start(self) -> None:
        self.started = True

    def shutdown(self, wait: bool = True) -> None:
        self.shutdown_wait = wait


@pytest.mark.asyncio
async def test_update_scheduler_start_shutdown_and_run_once() -> None:
    backend = FakeSchedulerBackend()
    calls = 0
    result = UpdateResult(
        novel_id=1,
        title="Seed",
        status="updated",
        new_chapter_count=2,
        total_chapter_count=4,
    )

    async def update_all() -> list[UpdateResult]:
        nonlocal calls
        calls += 1
        return [result]

    scheduler = UpdateScheduler(update_all=update_all, interval_hours=12, scheduler=backend)

    scheduler.start()
    scheduler.start()
    await scheduler.run_once()
    scheduler.shutdown()

    assert len(backend.jobs) == 1
    assert backend.jobs[0][1] == "interval"
    assert backend.jobs[0][2] == {
        "hours": 12,
        "id": "ndl-update-all",
        "coalesce": True,
        "max_instances": 1,
        "replace_existing": True,
    }
    assert backend.started is True
    assert backend.shutdown_wait is False
    assert scheduler.state.running is False
    assert scheduler.state.last_results == [result]
    assert scheduler.state.last_error is None
    assert scheduler.state.last_run_at is not None
    assert calls == 1


@pytest.mark.asyncio
async def test_update_scheduler_records_user_visible_errors() -> None:
    async def update_all() -> list[UpdateResult]:
        raise UserError("Cannot update.", detail="No matching rule.")

    scheduler = UpdateScheduler(update_all=update_all)

    await scheduler.run_once()

    assert scheduler.state.last_results == []
    assert scheduler.state.last_error == "Cannot update.\n\nNo matching rule."
