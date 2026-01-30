from __future__ import annotations

import sys
sys.path.insert(0, "src")

import asyncio
import time

import pytest

from flight_finder.infrastructure.http.rate_limiter import RateLimiter


class TestRateLimiter:
    @pytest.mark.anyio
    async def test_acquire_within_rate_does_not_block(self) -> None:
        limiter = RateLimiter(rate=10, per=1.0)
        start = time.monotonic()
        for _ in range(5):
            await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1

    @pytest.mark.anyio
    async def test_acquire_exceeding_rate_blocks(self) -> None:
        limiter = RateLimiter(rate=2, per=1.0)
        start = time.monotonic()
        for _ in range(4):
            await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.5

    @pytest.mark.anyio
    async def test_try_acquire_returns_true_when_available(self) -> None:
        limiter = RateLimiter(rate=5, per=1.0)
        result = await limiter.try_acquire()
        assert result is True

    @pytest.mark.anyio
    async def test_try_acquire_returns_false_when_exhausted(self) -> None:
        limiter = RateLimiter(rate=2, per=1.0)
        await limiter.acquire()
        await limiter.acquire()
        result = await limiter.try_acquire()
        assert result is False

    @pytest.mark.anyio
    async def test_tokens_refill_over_time(self) -> None:
        limiter = RateLimiter(rate=2, per=1.0)
        await limiter.acquire()
        await limiter.acquire()
        result_before = await limiter.try_acquire()
        assert result_before is False

        await asyncio.sleep(0.6)
        result_after = await limiter.try_acquire()
        assert result_after is True

    @pytest.mark.anyio
    async def test_reset_refills_all_tokens(self) -> None:
        limiter = RateLimiter(rate=3, per=1.0)
        for _ in range(3):
            await limiter.acquire()
        result_before = await limiter.try_acquire()
        assert result_before is False

        limiter.reset()
        for _ in range(3):
            result = await limiter.try_acquire()
            assert result is True

    @pytest.mark.anyio
    async def test_concurrent_access_is_safe(self) -> None:
        limiter = RateLimiter(rate=5, per=1.0)
        results: list[bool] = []

        async def try_acquire() -> None:
            result = await limiter.try_acquire()
            results.append(result)

        tasks = [asyncio.create_task(try_acquire()) for _ in range(10)]
        await asyncio.gather(*tasks)

        assert len(results) == 10
        assert results.count(True) == 5
        assert results.count(False) == 5


if __name__ == "__main__":
    async def run_tests() -> None:
        test = TestRateLimiter()
        print("test_acquire_within_rate_does_not_block...")
        await test.test_acquire_within_rate_does_not_block()
        print("  PASSED")

        print("test_acquire_exceeding_rate_blocks...")
        await test.test_acquire_exceeding_rate_blocks()
        print("  PASSED")

        print("test_try_acquire_returns_true_when_available...")
        await test.test_try_acquire_returns_true_when_available()
        print("  PASSED")

        print("test_try_acquire_returns_false_when_exhausted...")
        await test.test_try_acquire_returns_false_when_exhausted()
        print("  PASSED")

        print("test_tokens_refill_over_time...")
        await test.test_tokens_refill_over_time()
        print("  PASSED")

        print("test_reset_refills_all_tokens...")
        await test.test_reset_refills_all_tokens()
        print("  PASSED")

        print("test_concurrent_access_is_safe...")
        await test.test_concurrent_access_is_safe()
        print("  PASSED")

        print("\nAll tests passed!")

    asyncio.run(run_tests())
