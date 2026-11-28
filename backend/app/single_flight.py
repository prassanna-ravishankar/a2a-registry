"""One cached value, recomputed at most once per TTL however many callers arrive together."""

import asyncio
import time
from typing import Awaitable, Callable, Generic, Optional, TypeVar

T = TypeVar("T")


class SingleFlightCache(Generic[T]):
    """Callers that find the value expired queue on one lock; the first recomputes and the
    rest get its result. A computation that raises caches nothing and releases the lock, so
    the next caller simply tries again."""

    def __init__(self, ttl_seconds: float, clock: Callable[[], float] = time.monotonic):
        self._ttl = ttl_seconds
        self._clock = clock
        self._lock = asyncio.Lock()
        self._value: Optional[T] = None
        self._expires_at = 0.0

    def _fresh(self) -> bool:
        return self._value is not None and self._clock() < self._expires_at

    async def get(self, compute: Callable[[], Awaitable[T]]) -> T:
        if self._fresh():
            return self._value
        async with self._lock:
            if self._fresh():  # another caller refreshed it while this one waited
                return self._value
            value = await compute()
            self._value, self._expires_at = value, self._clock() + self._ttl
            return value
