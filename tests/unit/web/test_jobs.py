"""Tests for the in-memory Web job registry."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ndl.web.jobs import JobRegistry


def test_create_evicts_oldest_terminal_job_when_at_capacity() -> None:
    registry = JobRegistry(max_jobs=2)

    first = registry.create(url="u1", target_format="epub", save=False)
    second = registry.create(url="u2", target_format="epub", save=False)
    registry.mark_succeeded(first.id, output_path=Path("/tmp/x"), novel_id=None)
    registry.mark_failed(second.id, "boom")

    registry.create(url="u3", target_format="epub", save=False)

    assert registry.get(first.id) is None
    assert registry.get(second.id) is not None
    assert len(registry.list()) == 2


@pytest.mark.asyncio
async def test_stream_wakes_on_status_change_without_polling() -> None:
    registry = JobRegistry()
    job = registry.create(url="u1", target_format="epub", save=False)
    iterator = registry.stream(job.id)

    async def emit_terminal() -> None:
        await asyncio.sleep(0)
        registry.mark_succeeded(job.id, output_path=Path("/tmp/a"), novel_id=None)

    emitter = asyncio.create_task(emit_terminal())
    status = await asyncio.wait_for(anext(iterator), timeout=1.0)
    await emitter

    assert status["event"] == "status"
    assert '"status": "succeeded"' in status["data"]


def test_create_does_not_evict_active_jobs_even_above_capacity() -> None:
    registry = JobRegistry(max_jobs=2)

    first = registry.create(url="u1", target_format="epub", save=False)
    second = registry.create(url="u2", target_format="epub", save=False)
    registry.mark_running(first.id)
    registry.mark_running(second.id)

    third = registry.create(url="u3", target_format="epub", save=False)

    assert registry.get(first.id) is not None
    assert registry.get(second.id) is not None
    assert registry.get(third.id) is not None
    assert len(registry.list()) == 3
