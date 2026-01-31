"""Cache management handler for MCP tools."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import structlog

from flight_finder.domain.common.result import Err, Ok
from flight_finder.presentation.utils.error_formatter import format_error_response

if TYPE_CHECKING:
    from flight_finder.application.use_cases.manage_cache import ManageCacheUseCase

logger = structlog.get_logger()


class CacheHandler:
    """Handler for cache management operations."""

    def __init__(self, cache_use_case: ManageCacheUseCase) -> None:
        self._cache_use_case = cache_use_case
        self._logger = logger.bind(handler="cache")

    async def handle_get_stats(self) -> str:
        """Handle get_cache_stats tool invocation.

        Returns:
            JSON string with cache statistics
        """
        try:
            result = await self._cache_use_case.get_stats()

            match result:
                case Ok(stats):
                    return json.dumps(
                        {
                            "success": True,
                            "cache": {
                                "size": stats.size,
                                "max_size": stats.max_size,
                                "hits": stats.hits,
                                "misses": stats.misses,
                                "hit_rate_percent": round(stats.hit_rate * 100, 2),
                            },
                        },
                        indent=2,
                    )

                case Err(error):
                    return format_error_response(error)

        except Exception as e:
            self._logger.exception("cache_stats_error", error=str(e))
            return format_error_response(e)

    async def handle_clear(self) -> str:
        """Handle clear_cache tool invocation.

        Returns:
            JSON string with clear operation result
        """
        try:
            result = await self._cache_use_case.clear()

            match result:
                case Ok(data):
                    return json.dumps(
                        {
                            "success": True,
                            "message": f"Cleared {data['entries_cleared']} cache entries",
                            "details": data,
                        },
                        indent=2,
                    )

                case Err(error):
                    return format_error_response(error)

        except Exception as e:
            self._logger.exception("cache_clear_error", error=str(e))
            return format_error_response(e)
