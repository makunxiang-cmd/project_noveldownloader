"""Unit tests for the per-host throttle."""

from __future__ import annotations

import asyncio
import time

import pytest

from ndl.fetchers._throttle import HostThrottle


@pytest.mark.asyncio
async def test_throttle_enforces_min_interval_between_requests() -> None:
    interval_ms = 200
    throttle = HostThrottle(min_interval_ms=interval_ms, max_concurrency=1)

    start = time.monotonic()
    async with throttle.slot():
        pass
    async with throttle.slot():
        pass
    elapsed = time.monotonic() - start

    # 20ms tolerance: Windows asyncio.sleep granularity is ~15.6ms by default.
    assert elapsed >= (interval_ms - 20) / 1000.0


@pytest.mark.asyncio
async def test_throttle_caps_concurrent_holders() -> None:
    throttle = HostThrottle(min_interval_ms=0, max_concurrency=2)
    in_flight = 0
    peak = 0
    lock = asyncio.Lock()

    async def hold() -> None:
        nonlocal in_flight, peak
        async with throttle.slot():
            async with lock:
                in_flight += 1
                peak = max(peak, in_flight)
            await asyncio.sleep(0.02)
            async with lock:
                in_flight -= 1

    await asyncio.gather(*(hold() for _ in range(6)))

    assert peak == 2
