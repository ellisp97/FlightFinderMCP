"""Tests for ProviderFactory."""

import sys
import os

sys.path.insert(0, "src")

# Mock structlog and httpx before importing modules
class MockLogger:
    def bind(self, **kwargs):
        return self

    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class MockStructlog:
    @staticmethod
    def get_logger():
        return MockLogger()


sys.modules["structlog"] = MockStructlog()

import asyncio
from functools import lru_cache

from flight_finder.config.settings import get_settings
from flight_finder.infrastructure.cache.in_memory_cache import InMemoryCache
from flight_finder.infrastructure.providers.cache_decorator import CacheDecorator
from flight_finder.infrastructure.providers.multi_provider_aggregator import (
    MultiProviderAggregator,
)
from flight_finder.infrastructure.providers.provider_factory import ProviderFactory
from flight_finder.infrastructure.providers.provider_registry import ProviderRegistry


def setup_env():
    """Clear settings cache and setup test environment."""
    get_settings.cache_clear()
    # Clear all api keys first
    os.environ.pop("FLIGHT_FINDER_SKYSCANNER_API_KEY", None)
    os.environ.pop("FLIGHT_FINDER_SEARCHAPI_KEY", None)
    os.environ.pop("FLIGHT_FINDER_RAPIDAPI_KEY", None)


def test_factory_creates_skyscanner_provider():
    setup_env()
    os.environ["FLIGHT_FINDER_SKYSCANNER_API_KEY"] = "test-skyscanner-key"
    get_settings.cache_clear()

    factory = ProviderFactory()
    provider = factory.create_skyscanner_provider(with_cache=False)

    assert provider is not None
    assert provider.provider_name == "skyscanner"


def test_factory_creates_skyscanner_with_cache():
    setup_env()
    os.environ["FLIGHT_FINDER_SKYSCANNER_API_KEY"] = "test-skyscanner-key"
    get_settings.cache_clear()

    factory = ProviderFactory()
    provider = factory.create_skyscanner_provider(with_cache=True)

    assert provider is not None
    assert isinstance(provider, CacheDecorator)
    assert "cached" in provider.provider_name


def test_factory_returns_none_without_api_key():
    setup_env()
    get_settings.cache_clear()

    factory = ProviderFactory()
    provider = factory.create_skyscanner_provider()

    assert provider is None


def test_factory_creates_google_flights_provider():
    setup_env()
    os.environ["FLIGHT_FINDER_SEARCHAPI_KEY"] = "test-searchapi-key"
    get_settings.cache_clear()

    factory = ProviderFactory()
    provider = factory.create_google_flights_provider(with_cache=False)

    assert provider is not None
    assert provider.provider_name == "google_flights"


def test_factory_creates_rapidapi_provider():
    setup_env()
    os.environ["FLIGHT_FINDER_RAPIDAPI_KEY"] = "test-rapidapi-key"
    get_settings.cache_clear()

    factory = ProviderFactory()
    provider = factory.create_rapidapi_skyscanner_provider(with_cache=False)

    assert provider is not None
    assert provider.provider_name == "rapidapi_skyscanner"


def test_factory_creates_all_providers():
    setup_env()
    os.environ["FLIGHT_FINDER_SKYSCANNER_API_KEY"] = "test-key1"
    os.environ["FLIGHT_FINDER_SEARCHAPI_KEY"] = "test-key2"
    os.environ["FLIGHT_FINDER_RAPIDAPI_KEY"] = "test-key3"
    get_settings.cache_clear()

    factory = ProviderFactory()
    providers = factory.create_all_providers()

    assert len(providers) == 3
    provider_names = [p.provider_name for p in providers]
    assert "skyscanner_cached" in provider_names
    assert "google_flights_cached" in provider_names
    assert "rapidapi_skyscanner_cached" in provider_names


def test_factory_creates_only_available_providers():
    setup_env()
    os.environ["FLIGHT_FINDER_SKYSCANNER_API_KEY"] = "test-key1"
    # No other keys
    get_settings.cache_clear()

    factory = ProviderFactory()
    providers = factory.create_all_providers()

    assert len(providers) == 1
    assert providers[0].provider_name == "skyscanner_cached"


def test_factory_registers_providers_in_registry():
    setup_env()
    os.environ["FLIGHT_FINDER_SKYSCANNER_API_KEY"] = "test-key1"
    os.environ["FLIGHT_FINDER_SEARCHAPI_KEY"] = "test-key2"
    get_settings.cache_clear()

    factory = ProviderFactory()
    factory.create_all_providers(register=True)

    registry = factory.get_registry()
    assert registry.count_enabled() == 2


def test_factory_creates_aggregator():
    setup_env()
    os.environ["FLIGHT_FINDER_SKYSCANNER_API_KEY"] = "test-key1"
    get_settings.cache_clear()

    factory = ProviderFactory()
    aggregator = factory.create_aggregator()

    assert isinstance(aggregator, MultiProviderAggregator)


def test_factory_get_cache():
    setup_env()
    get_settings.cache_clear()

    factory = ProviderFactory()
    cache = factory.get_cache()

    assert isinstance(cache, InMemoryCache)


def test_factory_get_registry():
    setup_env()
    get_settings.cache_clear()

    factory = ProviderFactory()
    registry = factory.get_registry()

    assert isinstance(registry, ProviderRegistry)


async def test_factory_close():
    setup_env()
    get_settings.cache_clear()

    factory = ProviderFactory()
    # Should not raise
    await factory.close()


def run_tests():
    print("Testing ProviderFactory...")

    test_factory_creates_skyscanner_provider()
    print("  ✓ test_factory_creates_skyscanner_provider")

    test_factory_creates_skyscanner_with_cache()
    print("  ✓ test_factory_creates_skyscanner_with_cache")

    test_factory_returns_none_without_api_key()
    print("  ✓ test_factory_returns_none_without_api_key")

    test_factory_creates_google_flights_provider()
    print("  ✓ test_factory_creates_google_flights_provider")

    test_factory_creates_rapidapi_provider()
    print("  ✓ test_factory_creates_rapidapi_provider")

    test_factory_creates_all_providers()
    print("  ✓ test_factory_creates_all_providers")

    test_factory_creates_only_available_providers()
    print("  ✓ test_factory_creates_only_available_providers")

    test_factory_registers_providers_in_registry()
    print("  ✓ test_factory_registers_providers_in_registry")

    test_factory_creates_aggregator()
    print("  ✓ test_factory_creates_aggregator")

    test_factory_get_cache()
    print("  ✓ test_factory_get_cache")

    test_factory_get_registry()
    print("  ✓ test_factory_get_registry")

    asyncio.run(test_factory_close())
    print("  ✓ test_factory_close")

    print("\nAll ProviderFactory tests passed!")


if __name__ == "__main__":
    run_tests()
