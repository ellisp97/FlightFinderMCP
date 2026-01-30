"""Cache strategy protocol (interface).

Defines the contract for caching implementations using the Strategy pattern.
Implementations can include in-memory cache, Redis, file-based cache, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from flight_finder.domain.common.result import Result
    from flight_finder.domain.errors.domain_errors import CacheError

T = TypeVar("T")


@runtime_checkable
class ICacheStrategy(Protocol):
    """Protocol for cache implementations (Strategy pattern).

    This protocol defines the interface that all cache strategies must implement.
    Cache implementations are responsible for storing and retrieving data with
    TTL (time-to-live) support.

    Implementations should:
    - Be async to support distributed caches (Redis, etc.)
    - Handle serialization/deserialization transparently
    - Return Results instead of raising exceptions for expected failures
    - Support optional TTL overrides per operation

    Example implementation:
        class InMemoryCache:
            @property
            def cache_name(self) -> str:
                return "in_memory"

            async def get(self, key: str) -> Result[T | None, CacheError]:
                # Implementation here
                ...

            async def set(
                self,
                key: str,
                value: T,
                ttl_seconds: int | None = None
            ) -> Result[None, CacheError]:
                # Implementation here
                ...
    """

    @property
    def cache_name(self) -> str:
        """Get the cache implementation name for logging/metrics.

        Returns:
            A lowercase identifier (e.g., "in_memory", "redis", "file")
        """
        ...

    async def get(self, key: str) -> Result[T | None, CacheError]:
        """Retrieve a value from the cache.

        Args:
            key: The cache key to retrieve

        Returns:
            Result containing either:
            - Ok[T | None]: The cached value, or None if not found/expired
            - Err[CacheError]: Error details if retrieval failed
        """
        ...

    async def set(
        self,
        key: str,
        value: T,
        ttl_seconds: int | None = None,
    ) -> Result[None, CacheError]:
        """Store a value in the cache.

        Args:
            key: The cache key to store under
            value: The value to cache
            ttl_seconds: Optional TTL override (None uses default TTL)

        Returns:
            Result containing either:
            - Ok[None]: Value was successfully cached
            - Err[CacheError]: Error details if storage failed
        """
        ...

    async def delete(self, key: str) -> Result[bool, CacheError]:
        """Delete a value from the cache.

        Args:
            key: The cache key to delete

        Returns:
            Result containing either:
            - Ok[bool]: True if key was deleted, False if key didn't exist
            - Err[CacheError]: Error details if deletion failed
        """
        ...

    async def exists(self, key: str) -> Result[bool, CacheError]:
        """Check if a key exists in the cache.

        Args:
            key: The cache key to check

        Returns:
            Result containing either:
            - Ok[bool]: True if key exists and hasn't expired
            - Err[CacheError]: Error details if check failed
        """
        ...

    async def clear(self) -> Result[int, CacheError]:
        """Clear all entries from the cache.

        Returns:
            Result containing either:
            - Ok[int]: Number of entries cleared
            - Err[CacheError]: Error details if clear failed
        """
        ...

    async def is_available(self) -> bool:
        """Check if the cache backend is available.

        This can be used for health checks and to fall back to
        other caching strategies.

        Returns:
            True if the cache backend is available and operational
        """
        ...
