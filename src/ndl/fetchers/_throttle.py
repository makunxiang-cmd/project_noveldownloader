"""Per-host throttle: enforce request spacing and concurrency cap."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import monotonic


class HostThrottle:
    """Async semaphore + spacing lock for a single host."""

    def __init__(self, *, min_interval_ms: int, max_concurrency: int) -> None:
        self._min_interval = min_interval_ms / 1000.0
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._lock = asyncio.Lock()
        self._last_request: float = 0.0

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        """Acquire a request slot, releasing the concurrency seat on exit."""
        await self._semaphore.acquire()
        try:
            async with self._lock:
                wait = self._min_interval - (monotonic() - self._last_request)
                if wait > 0:
                    await asyncio.sleep(wait)
                self._last_request = monotonic()
            yield
        finally:
            self._semaphore.release()
