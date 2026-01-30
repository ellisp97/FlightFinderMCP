from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from flight_finder.domain.common.result import Err, Ok, Result
from flight_finder.domain.errors.domain_errors import ProviderError
from flight_finder.infrastructure.cache.cache_key_generator import generate_cache_key

if TYPE_CHECKING:
    from flight_finder.domain.entities.flight import Flight
    from flight_finder.domain.entities.search_criteria import SearchCriteria
    from flight_finder.domain.protocols.flight_provider import IFlightProvider
    from flight_finder.infrastructure.cache.in_memory_cache import InMemoryCache

logger = structlog.get_logger()


class CacheDecorator:
    """Decorator that adds caching to any flight provider.

    Implements IFlightProvider protocol - can be used anywhere a provider is expected.
    """

    def __init__(
        self,
        provider: IFlightProvider,
        cache: InMemoryCache,
        ttl_seconds: int | None = None,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._ttl_seconds = ttl_seconds
        self._logger = logger.bind(
            component="cache_decorator",
            provider=provider.provider_name,
        )

    @property
    def provider_name(self) -> str:
        return f"{self._provider.provider_name}_cached"

    async def search(
        self,
        criteria: SearchCriteria,
    ) -> Result[list[Flight], ProviderError]:
        cache_key = generate_cache_key(criteria, self._provider.provider_name)

        cached_result = await self._cache.get(cache_key)
        if cached_result.is_ok():
            cached_value = cached_result.value
            if cached_value is not None:
                self._logger.info(
                    "cache_hit",
                    key=cache_key,
                    flight_count=len(cached_value),
                )
                return Ok(cached_value)

        self._logger.debug("cache_miss", key=cache_key)

        result = await self._provider.search(criteria)

        match result:
            case Ok(flights):
                await self._cache.set(
                    cache_key,
                    flights,
                    ttl_seconds=self._ttl_seconds,
                )
                self._logger.info(
                    "cache_stored",
                    key=cache_key,
                    flight_count=len(flights),
                )
            case Err(error):
                self._logger.debug(
                    "cache_skip_error",
                    key=cache_key,
                    error=str(error),
                )

        return result

    async def is_available(self) -> bool:
        return await self._provider.is_available()
