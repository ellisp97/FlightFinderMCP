"""Tests for InMemoryCache."""

import asyncio
from datetime import datetime, timedelta

import pytest

from flight_finder.domain.common.result import Ok, unwrap
from flight_finder.infrastructure.cache.in_memory_cache import InMemoryCache


class TestBasicOperations:
    """Tests for basic cache get/set/delete."""

    @pytest.mark.anyio
    async def test_set_and_get(self) -> None:
        cache = InMemoryCache()
        await cache.set("key1", {"data": "value"})

        result = await cache.get("key1")
        assert isinstance(result, Ok)
        assert unwrap(result) == {"data": "value"}

    @pytest.mark.anyio
    async def test_get_missing_key_returns_none(self) -> None:
        cache = InMemoryCache()

        result = await cache.get("nonexistent")
        assert isinstance(result, Ok)
        assert unwrap(result) is None

    @pytest.mark.anyio
    async def test_delete_existing_key(self) -> None:
        cache = InMemoryCache()
        await cache.set("key1", "value")

        result = await cache.delete("key1")
        assert unwrap(result) is True

        get_result = await cache.get("key1")
        assert unwrap(get_result) is None

    @pytest.mark.anyio
    async def test_delete_missing_key(self) -> None:
        cache = InMemoryCache()

        result = await cache.delete("nonexistent")
        assert unwrap(result) is False

    @pytest.mark.anyio
    async def test_exists_returns_true_for_valid_key(self) -> None:
        cache = InMemoryCache()
        await cache.set("key1", "value")

        result = await cache.exists("key1")
        assert unwrap(result) is True

    @pytest.mark.anyio
    async def test_exists_returns_false_for_missing_key(self) -> None:
        cache = InMemoryCache()

        result = await cache.exists("nonexistent")
        assert unwrap(result) is False

    @pytest.mark.anyio
    async def test_clear_removes_all_entries(self) -> None:
        cache = InMemoryCache()
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        result = await cache.clear()
        assert unwrap(result) == 2

        assert unwrap(await cache.get("key1")) is None
        assert unwrap(await cache.get("key2")) is None


class TestTTLExpiration:
    """Tests for TTL-based expiration."""

    @pytest.mark.anyio
    async def test_expired_entry_returns_none(self) -> None:
        cache = InMemoryCache(default_ttl_seconds=0)  # Immediate expiry
        await cache.set("key1", "value")

        await asyncio.sleep(0.01)

        result = await cache.get("key1")
        assert unwrap(result) is None

    @pytest.mark.anyio
    async def test_custom_ttl_overrides_default(self) -> None:
        cache = InMemoryCache(default_ttl_seconds=300)
        await cache.set("key1", "value", ttl_seconds=0)

        await asyncio.sleep(0.01)

        result = await cache.get("key1")
        assert unwrap(result) is None

    @pytest.mark.anyio
    async def test_exists_returns_false_for_expired_key(self) -> None:
        cache = InMemoryCache(default_ttl_seconds=0)
        await cache.set("key1", "value")

        await asyncio.sleep(0.01)

        result = await cache.exists("key1")
        assert unwrap(result) is False


class TestLRUEviction:
    """Tests for LRU eviction behavior."""

    @pytest.mark.anyio
    async def test_evicts_oldest_when_max_size_exceeded(self) -> None:
        cache = InMemoryCache(max_size=2)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")  # Should evict key1

        assert unwrap(await cache.get("key1")) is None
        assert unwrap(await cache.get("key2")) == "value2"
        assert unwrap(await cache.get("key3")) == "value3"

    @pytest.mark.anyio
    async def test_accessing_key_moves_it_to_end(self) -> None:
        cache = InMemoryCache(max_size=2)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        await cache.get("key1")  # Access key1, making key2 oldest

        await cache.set("key3", "value3")  # Should evict key2, not key1

        assert unwrap(await cache.get("key1")) == "value1"
        assert unwrap(await cache.get("key2")) is None
        assert unwrap(await cache.get("key3")) == "value3"

    @pytest.mark.anyio
    async def test_setting_existing_key_updates_lru_order(self) -> None:
        cache = InMemoryCache(max_size=2)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key1", "updated")  # Update key1, making key2 oldest

        await cache.set("key3", "value3")  # Should evict key2

        assert unwrap(await cache.get("key1")) == "updated"
        assert unwrap(await cache.get("key2")) is None


class TestStatistics:
    """Tests for cache statistics."""

    @pytest.mark.anyio
    async def test_tracks_hits_and_misses(self) -> None:
        cache = InMemoryCache()
        await cache.set("key1", "value")

        await cache.get("key1")  # Hit
        await cache.get("key1")  # Hit
        await cache.get("missing")  # Miss

        stats = cache.get_stats()
        assert stats.hits == 2
        assert stats.misses == 1

    @pytest.mark.anyio
    async def test_hit_rate_calculation(self) -> None:
        cache = InMemoryCache()
        await cache.set("key1", "value")

        await cache.get("key1")  # Hit
        await cache.get("missing")  # Miss

        stats = cache.get_stats()
        assert stats.hit_rate == 50.0

    def test_hit_rate_zero_when_empty(self) -> None:
        cache = InMemoryCache()
        stats = cache.get_stats()
        assert stats.hit_rate == 0.0


class TestProtocolCompliance:
    """Tests for ICacheStrategy protocol compliance."""

    def test_cache_name_property(self) -> None:
        cache = InMemoryCache()
        assert cache.cache_name == "in_memory"

    @pytest.mark.anyio
    async def test_is_available_returns_true(self) -> None:
        cache = InMemoryCache()
        assert await cache.is_available() is True
