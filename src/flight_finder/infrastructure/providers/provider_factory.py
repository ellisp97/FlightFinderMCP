from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from flight_finder.config.settings import get_settings
from flight_finder.infrastructure.cache.in_memory_cache import InMemoryCache
from flight_finder.infrastructure.http.async_http_client import AsyncHTTPClient
from flight_finder.infrastructure.http.rate_limiter import RateLimiter
from flight_finder.infrastructure.providers.cache_decorator import CacheDecorator
from flight_finder.infrastructure.providers.google_flights import GoogleFlightsProvider
from flight_finder.infrastructure.providers.multi_provider_aggregator import (
    MultiProviderAggregator,
)
from flight_finder.infrastructure.providers.provider_registry import ProviderRegistry
from flight_finder.infrastructure.providers.rapidapi_skyscanner import (
    RapidAPISkyscannerProvider,
)
from flight_finder.infrastructure.providers.kiwi import KiwiProvider
from flight_finder.infrastructure.providers.skyscanner import SkyscannerProvider

if TYPE_CHECKING:
    from flight_finder.domain.protocols.flight_provider import IFlightProvider

logger = structlog.get_logger()


class ProviderFactory:
    """Factory for creating and configuring flight providers.

    Handles provider instantiation with dependencies, cache decoration,
    registry management, and multi-provider aggregation.
    """

    def __init__(
        self,
        http_client: AsyncHTTPClient | None = None,
        cache: InMemoryCache | None = None,
    ) -> None:
        self._settings = get_settings()
        self._http_client = http_client or AsyncHTTPClient()
        self._cache = cache or InMemoryCache(
            max_size=self._settings.cache_max_size,
            default_ttl_seconds=self._settings.cache_ttl_seconds,
        )
        self._registry = ProviderRegistry()
        self._logger = logger.bind(component="provider_factory")

    def create_skyscanner_provider(
        self,
        with_cache: bool = True,
    ) -> IFlightProvider | None:
        if not self._settings.has_skyscanner_key:
            self._logger.warning("skyscanner_key_missing")
            return None

        rate_limiter = RateLimiter(rate=1, per=3.0)

        provider: IFlightProvider = SkyscannerProvider(
            api_key=self._settings.skyscanner_api_key,
            http_client=self._http_client,
            rate_limiter=rate_limiter,
        )

        if with_cache:
            provider = CacheDecorator(
                provider=provider,
                cache=self._cache,
                ttl_seconds=self._settings.cache_ttl_seconds,
            )

        self._logger.info("skyscanner_provider_created")
        return provider

    def create_google_flights_provider(
        self,
        with_cache: bool = True,
    ) -> IFlightProvider | None:
        if not self._settings.has_searchapi_key:
            self._logger.warning("searchapi_key_missing")
            return None

        rate_limiter = RateLimiter(rate=1, per=2.0)

        provider: IFlightProvider = GoogleFlightsProvider(
            api_key=self._settings.searchapi_key,
            http_client=self._http_client,
            rate_limiter=rate_limiter,
        )

        if with_cache:
            provider = CacheDecorator(
                provider=provider,
                cache=self._cache,
                ttl_seconds=self._settings.cache_ttl_seconds,
            )

        self._logger.info("google_flights_provider_created")
        return provider

    def create_rapidapi_skyscanner_provider(
        self,
        with_cache: bool = True,
    ) -> IFlightProvider | None:
        if not self._settings.has_rapidapi_key:
            self._logger.warning("rapidapi_key_missing")
            return None

        rate_limiter = RateLimiter(rate=1, per=3.0)

        provider: IFlightProvider = RapidAPISkyscannerProvider(
            api_key=self._settings.rapidapi_key,
            http_client=self._http_client,
            rate_limiter=rate_limiter,
        )

        if with_cache:
            provider = CacheDecorator(
                provider=provider,
                cache=self._cache,
                ttl_seconds=self._settings.cache_ttl_seconds,
            )

        self._logger.info("rapidapi_skyscanner_provider_created")
        return provider

    def create_kiwi_provider(
        self,
        with_cache: bool = True,
    ) -> IFlightProvider | None:
        if not self._settings.has_kiwi_key:
            self._logger.warning("kiwi_key_missing")
            return None

        rate_limiter = RateLimiter(rate=1, per=2.0)

        provider: IFlightProvider = KiwiProvider(
            api_key=self._settings.kiwi_api_key,
            http_client=self._http_client,
            rate_limiter=rate_limiter,
        )

        if with_cache:
            provider = CacheDecorator(
                provider=provider,
                cache=self._cache,
                ttl_seconds=self._settings.cache_ttl_seconds,
            )

        self._logger.info("kiwi_provider_created")
        return provider

    def create_all_providers(
        self,
        with_cache: bool = True,
        register: bool = True,
    ) -> list[IFlightProvider]:
        providers: list[IFlightProvider] = []

        skyscanner = self.create_skyscanner_provider(with_cache=with_cache)
        if skyscanner:
            providers.append(skyscanner)
            if register:
                self._registry.register(skyscanner, priority=90)

        google = self.create_google_flights_provider(with_cache=with_cache)
        if google:
            providers.append(google)
            if register:
                self._registry.register(google, priority=80)

        rapidapi = self.create_rapidapi_skyscanner_provider(with_cache=with_cache)
        if rapidapi:
            providers.append(rapidapi)
            if register:
                self._registry.register(rapidapi, priority=70)

        kiwi = self.create_kiwi_provider(with_cache=with_cache)
        if kiwi:
            providers.append(kiwi)
            if register:
                self._registry.register(kiwi, priority=75)

        self._logger.info(
            "providers_created",
            count=len(providers),
            providers=[p.provider_name for p in providers],
        )

        return providers

    def create_aggregator(
        self,
        providers: list[IFlightProvider] | None = None,
    ) -> MultiProviderAggregator:
        if providers is None:
            providers = self.create_all_providers()

        return MultiProviderAggregator(providers)

    def get_registry(self) -> ProviderRegistry:
        return self._registry

    def get_cache(self) -> InMemoryCache:
        return self._cache

    async def close(self) -> None:
        await self._http_client.close()
