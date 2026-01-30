"""In-memory cache with TTL and LRU eviction."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Generic, TypeVar

from flight_finder.domain.common.result import Err, Ok, Result
from flight_finder.domain.errors.domain_errors import CacheError

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """Single cache entry with value and expiration."""

    value: T
    expires_at: datetime


@dataclass
class CacheStats:
    """Cache statistics for monitoring."""

    hits: int = 0
    misses: int = 0
    size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0


class InMemoryCache:
    """Async in-memory cache with TTL and LRU eviction.

    Implements ICacheStrategy protocol for use with flight search results.
    Uses asyncio.Lock for thread-safety in async context.
    """

    def __init__(self, max_size: int = 1000, default_ttl_seconds: int = 300) -> None:
        self._cache: OrderedDict[str, CacheEntry[Any]] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl_seconds
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    @property
    def cache_name(self) -> str:
        return "in_memory"

    async def get(self, key: str) -> Result[Any | None, CacheError]:
        """Retrieve value from cache, returns None if not found or expired."""
        async with self._lock:
            if key not in self._cache:
                self._misses += 1
                return Ok(None)

            entry = self._cache[key]

            if datetime.now() >= entry.expires_at:
                del self._cache[key]
                self._misses += 1
                return Ok(None)

            self._cache.move_to_end(key)
            self._hits += 1
            return Ok(entry.value)

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> Result[None, CacheError]:
        """Store value in cache with TTL."""
        async with self._lock:
            ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
            expires_at = datetime.now() + timedelta(seconds=ttl)

            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
            self._cache.move_to_end(key)

            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

            return Ok(None)

    async def delete(self, key: str) -> Result[bool, CacheError]:
        """Delete value from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return Ok(True)
            return Ok(False)

    async def exists(self, key: str) -> Result[bool, CacheError]:
        """Check if key exists and is not expired."""
        async with self._lock:
            if key not in self._cache:
                return Ok(False)

            entry = self._cache[key]
            if datetime.now() >= entry.expires_at:
                del self._cache[key]
                return Ok(False)

            return Ok(True)

    async def clear(self) -> Result[int, CacheError]:
        """Clear all entries, returns count of cleared items."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return Ok(count)

    async def is_available(self) -> bool:
        """In-memory cache is always available."""
        return True

    def get_stats(self) -> CacheStats:
        """Get cache statistics (sync, no lock needed for reads)."""
        return CacheStats(
            hits=self._hits,
            misses=self._misses,
            size=len(self._cache),
            max_size=self._max_size,
        )
