"""Tests for CacheDecorator."""

import sys

sys.path.insert(0, "src")

# Mock structlog before importing modules
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
from datetime import date, datetime, timedelta
from decimal import Decimal

from flight_finder.domain.common.result import Err, Ok, is_ok, unwrap
from flight_finder.domain.entities.flight import Flight
from flight_finder.domain.entities.search_criteria import SearchCriteria
from flight_finder.domain.errors.domain_errors import ProviderError
from flight_finder.domain.value_objects.airport import Airport
from flight_finder.domain.value_objects.cabin_class import CabinClass
from flight_finder.domain.value_objects.passenger_config import PassengerConfig
from flight_finder.domain.value_objects.price import Price
from flight_finder.infrastructure.cache.in_memory_cache import InMemoryCache
from flight_finder.infrastructure.providers.cache_decorator import CacheDecorator


class MockProvider:
    def __init__(self, flights: list[Flight] | None = None, error: ProviderError | None = None):
        self._flights = flights or []
        self._error = error
        self.search_count = 0

    @property
    def provider_name(self) -> str:
        return "mock_provider"

    async def search(self, criteria: SearchCriteria):
        self.search_count += 1
        if self._error:
            return Err(self._error)
        return Ok(self._flights)

    async def is_available(self) -> bool:
        return True


def make_test_flight(flight_id: str = "test-1") -> Flight:
    dep_time = datetime.now() + timedelta(days=30, hours=10)
    arr_time = dep_time + timedelta(hours=5)
    return Flight(
        id=flight_id,
        origin=Airport(code="JFK", name="JFK", city="New York", country="US"),
        destination=Airport(code="LAX", name="LAX", city="Los Angeles", country="US"),
        departure_time=dep_time,
        arrival_time=arr_time,
        price=Price(amount=Decimal("299.00"), currency="USD"),
        cabin_class=CabinClass(),
        stops=0,
        airline="AA",
        airline_name="American Airlines",
    )


def make_test_criteria() -> SearchCriteria:
    return SearchCriteria(
        origin=Airport(code="JFK", name="JFK", city="New York", country="US"),
        destination=Airport(code="LAX", name="LAX", city="Los Angeles", country="US"),
        departure_date=date.today() + timedelta(days=30),
        passengers=PassengerConfig(adults=1),
        cabin_class=CabinClass(),
    )


async def test_cache_decorator_provider_name():
    cache = InMemoryCache()
    provider = MockProvider()
    decorator = CacheDecorator(provider, cache)

    assert decorator.provider_name == "mock_provider_cached"


async def test_cache_decorator_cache_miss_calls_provider():
    flights = [make_test_flight()]
    cache = InMemoryCache()
    provider = MockProvider(flights=flights)
    decorator = CacheDecorator(provider, cache)

    criteria = make_test_criteria()
    result = await decorator.search(criteria)

    assert is_ok(result)
    assert unwrap(result) == flights
    assert provider.search_count == 1


async def test_cache_decorator_cache_hit_skips_provider():
    flights = [make_test_flight()]
    cache = InMemoryCache()
    provider = MockProvider(flights=flights)
    decorator = CacheDecorator(provider, cache)

    criteria = make_test_criteria()

    # First search - cache miss
    result1 = await decorator.search(criteria)
    assert is_ok(result1)
    assert provider.search_count == 1

    # Second search - cache hit
    result2 = await decorator.search(criteria)
    assert is_ok(result2)
    assert unwrap(result2) == flights
    assert provider.search_count == 1  # Should not have called provider again


async def test_cache_decorator_does_not_cache_errors():
    error = ProviderError(provider="mock", message="Test error")
    cache = InMemoryCache()
    provider = MockProvider(error=error)
    decorator = CacheDecorator(provider, cache)

    criteria = make_test_criteria()

    result1 = await decorator.search(criteria)
    assert result1.is_err()

    # Change provider to return flights
    provider._error = None
    provider._flights = [make_test_flight()]

    # Second search should call provider again (error not cached)
    result2 = await decorator.search(criteria)
    assert is_ok(result2)
    assert provider.search_count == 2


async def test_cache_decorator_is_available():
    cache = InMemoryCache()
    provider = MockProvider()
    decorator = CacheDecorator(provider, cache)

    assert await decorator.is_available() is True


def run_tests():
    print("Testing CacheDecorator...")

    asyncio.run(test_cache_decorator_provider_name())
    print("  ✓ test_cache_decorator_provider_name")

    asyncio.run(test_cache_decorator_cache_miss_calls_provider())
    print("  ✓ test_cache_decorator_cache_miss_calls_provider")

    asyncio.run(test_cache_decorator_cache_hit_skips_provider())
    print("  ✓ test_cache_decorator_cache_hit_skips_provider")

    asyncio.run(test_cache_decorator_does_not_cache_errors())
    print("  ✓ test_cache_decorator_does_not_cache_errors")

    asyncio.run(test_cache_decorator_is_available())
    print("  ✓ test_cache_decorator_is_available")

    print("\nAll CacheDecorator tests passed!")


if __name__ == "__main__":
    run_tests()
