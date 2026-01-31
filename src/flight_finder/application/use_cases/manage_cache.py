"""Manage cache use case."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from flight_finder.application.dtos.provider_dtos import CacheStats
from flight_finder.domain.common.result import Err, Ok, Result
from flight_finder.domain.errors.domain_errors import DomainError

if TYPE_CHECKING:
    from flight_finder.infrastructure.cache.in_memory_cache import InMemoryCache

logger = structlog.get_logger()


class CacheManagementError(DomainError):
    """Error during cache management."""

    def __init__(self, message: str, operation: str) -> None:
        super().__init__(message, "CACHE_MANAGEMENT_ERROR", {"operation": operation})
        self.operation = operation


class ManageCacheUseCase:
    """Use case for cache management operations."""

    def __init__(self, cache: InMemoryCache) -> None:
        self._cache = cache
        self._logger = logger.bind(use_case="manage_cache")

    async def get_stats(self) -> Result[CacheStats, CacheManagementError]:
        """Get current cache statistics.

        Returns:
            Result containing CacheStats or CacheManagementError
        """
        try:
            stats = self._cache.get_stats()

            total = stats.hits + stats.misses
            hit_rate = stats.hits / total if total > 0 else 0.0

            return Ok(
                CacheStats(
                    size=stats.size,
                    max_size=stats.max_size,
                    hits=stats.hits,
                    misses=stats.misses,
                    hit_rate=hit_rate,
                )
            )
        except Exception as e:
            self._logger.error("cache_stats_error", error=str(e))
            return Err(
                CacheManagementError(
                    message=f"Failed to get cache stats: {e}",
                    operation="get_stats",
                )
            )

    async def clear(self) -> Result[dict[str, Any], CacheManagementError]:
        """Clear all cached data.

        Returns:
            Result containing clear operation details or CacheManagementError
        """
        try:
            stats_before = self._cache.get_stats()
            entries_before = stats_before.size

            result = await self._cache.clear()

            match result:
                case Ok(cleared_count):
                    self._logger.info(
                        "cache_cleared",
                        entries_cleared=cleared_count,
                    )
                    return Ok({
                        "entries_cleared": cleared_count,
                        "entries_before": entries_before,
                    })
                case Err(error):
                    return Err(
                        CacheManagementError(
                            message=f"Failed to clear cache: {error}",
                            operation="clear",
                        )
                    )
        except Exception as e:
            self._logger.error("cache_clear_error", error=str(e))
            return Err(
                CacheManagementError(
                    message=f"Failed to clear cache: {e}",
                    operation="clear",
                )
            )
