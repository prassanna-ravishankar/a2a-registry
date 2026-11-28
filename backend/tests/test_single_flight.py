import asyncio

import pytest

from app.single_flight import SingleFlightCache


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


async def test_concurrent_callers_share_one_computation():
    cache = SingleFlightCache(60)
    calls = 0
    release = asyncio.Event()

    async def compute():
        nonlocal calls
        calls += 1
        await release.wait()
        return b"body"

    callers = [asyncio.create_task(cache.get(compute)) for _ in range(20)]
    await asyncio.sleep(0)
    release.set()

    assert await asyncio.gather(*callers) == [b"body"] * 20
    assert calls == 1


async def test_value_is_reused_until_the_ttl_then_recomputed():
    clock = Clock()
    cache = SingleFlightCache(60, clock=clock)
    values = iter([b"first", b"second"])

    async def compute():
        return next(values)

    assert await cache.get(compute) == b"first"
    clock.now = 59.9
    assert await cache.get(compute) == b"first"
    clock.now = 60.0
    assert await cache.get(compute) == b"second"


async def test_a_failed_computation_is_not_cached_and_does_not_hold_the_lock():
    cache = SingleFlightCache(60)
    attempts = 0

    async def flaky():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("database down")
        return b"body"

    with pytest.raises(RuntimeError):
        await cache.get(flaky)
    # The next callers are not stuck behind the failed one and get a fresh computation.
    assert await asyncio.wait_for(asyncio.gather(cache.get(flaky), cache.get(flaky)), timeout=1) == [b"body"] * 2
    assert attempts == 2


async def test_waiters_behind_a_failure_retry_instead_of_inheriting_it():
    cache = SingleFlightCache(60)
    attempts = 0
    release = asyncio.Event()

    async def compute():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            await release.wait()
            raise RuntimeError("timeout")
        return b"body"

    first = asyncio.create_task(cache.get(compute))
    waiter = asyncio.create_task(cache.get(compute))
    await asyncio.sleep(0)
    release.set()

    with pytest.raises(RuntimeError):
        await first
    assert await asyncio.wait_for(waiter, timeout=1) == b"body"
    assert attempts == 2
