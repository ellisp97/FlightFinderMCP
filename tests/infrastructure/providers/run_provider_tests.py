"""Run all provider infrastructure tests."""

from __future__ import annotations

import sys
import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
import os


# Mock structlog and httpx BEFORE any imports
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
    BoundLogger = MockLogger

    @staticmethod
    def get_logger():
        return MockLogger()


sys.modules["structlog"] = MockStructlog()
sys.path.insert(0, "src")

# Now import the modules we need to test
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
from flight_finder.infrastructure.providers.provider_registry import (
    ProviderMetadata,
    ProviderRegistry,
)
from flight_finder.infrastructure.providers.multi_provider_aggregator import (
    MultiProviderAggregator,
)


# ============== Test Helpers ==============

class MockProvider:
    def __init__(
        self,
        name: str,
        flights: list[Flight] | None = None,
        error: ProviderError | None = None
    ):
        self._name = name
        self._flights = flights or []
        self._error = error
        self.search_count = 0

    @property
    def provider_name(self) -> str:
        return self._name

    async def search(self, criteria: SearchCriteria):
        self.search_count += 1
        if self._error:
            return Err(self._error)
        return Ok(self._flights)

    async def is_available(self) -> bool:
        return True


def make_test_flight(
    flight_id: str = "test-1",
    price: Decimal = Decimal("299.00"),
    airline: str = "AA",
    dep_offset_hours: float = 0,
) -> Flight:
    base_time = datetime.now() + timedelta(days=30)
    dep_time = base_time + timedelta(hours=10 + dep_offset_hours)
    arr_time = dep_time + timedelta(hours=5)
    return Flight(
        id=flight_id,
        origin=Airport(code="JFK", name="JFK", city="New York", country="US"),
        destination=Airport(code="LAX", name="LAX", city="Los Angeles", country="US"),
        departure_time=dep_time,
        arrival_time=arr_time,
        price=Price(amount=price, currency="USD"),
        cabin_class=CabinClass(),
        stops=0,
        airline=airline,
        airline_name="Test Airlines",
    )


def make_test_criteria() -> SearchCriteria:
    return SearchCriteria(
        origin=Airport(code="JFK", name="JFK", city="New York", country="US"),
        destination=Airport(code="LAX", name="LAX", city="Los Angeles", country="US"),
        departure_date=date.today() + timedelta(days=30),
        passengers=PassengerConfig(adults=1),
        cabin_class=CabinClass(),
    )


# ============== ProviderRegistry Tests ==============

def test_registry_register_provider():
    registry = ProviderRegistry()
    provider = MockProvider("test_provider")
    registry.register(provider, priority=50)
    assert registry.get("test_provider") is provider
    assert len(registry.get_all()) == 1


def test_registry_get_by_priority():
    registry = ProviderRegistry()
    low = MockProvider("low")
    high = MockProvider("high")
    medium = MockProvider("medium")
    registry.register(low, priority=10)
    registry.register(high, priority=90)
    registry.register(medium, priority=50)
    sorted_providers = registry.get_by_priority()
    assert len(sorted_providers) == 3
    assert sorted_providers[0].provider_name == "high"
    assert sorted_providers[1].provider_name == "medium"
    assert sorted_providers[2].provider_name == "low"


def test_registry_enable_disable():
    registry = ProviderRegistry()
    provider = MockProvider("test")
    registry.register(provider, enabled=True)
    assert registry.is_enabled("test") is True
    registry.disable("test")
    assert registry.is_enabled("test") is False
    registry.enable("test")
    assert registry.is_enabled("test") is True


def test_registry_get_enabled():
    registry = ProviderRegistry()
    p1 = MockProvider("p1")
    p2 = MockProvider("p2")
    registry.register(p1, enabled=True)
    registry.register(p2, enabled=False)
    enabled = registry.get_enabled()
    assert len(enabled) == 1
    assert enabled[0].provider_name == "p1"


def test_registry_get_status():
    registry = ProviderRegistry()
    provider = MockProvider("test")
    registry.register(provider, priority=75, weight=0.8)
    status = registry.get_status()
    assert status["test"]["priority"] == 75
    assert status["test"]["weight"] == 0.8


# ============== CacheDecorator Tests ==============

async def test_cache_decorator_provider_name():
    cache = InMemoryCache()
    provider = MockProvider("mock_provider")
    decorator = CacheDecorator(provider, cache)
    assert decorator.provider_name == "mock_provider_cached"


async def test_cache_decorator_cache_miss_calls_provider():
    flights = [make_test_flight()]
    cache = InMemoryCache()
    provider = MockProvider("mock", flights=flights)
    decorator = CacheDecorator(provider, cache)
    criteria = make_test_criteria()
    result = await decorator.search(criteria)
    assert is_ok(result)
    assert unwrap(result) == flights
    assert provider.search_count == 1


async def test_cache_decorator_cache_hit_skips_provider():
    flights = [make_test_flight()]
    cache = InMemoryCache()
    provider = MockProvider("mock", flights=flights)
    decorator = CacheDecorator(provider, cache)
    criteria = make_test_criteria()
    await decorator.search(criteria)
    assert provider.search_count == 1
    await decorator.search(criteria)
    assert provider.search_count == 1  # Not called again


async def test_cache_decorator_does_not_cache_errors():
    error = ProviderError(provider="mock", message="Test error")
    cache = InMemoryCache()
    provider = MockProvider("mock", error=error)
    decorator = CacheDecorator(provider, cache)
    criteria = make_test_criteria()
    result1 = await decorator.search(criteria)
    assert result1.is_err()
    provider._error = None
    provider._flights = [make_test_flight()]
    result2 = await decorator.search(criteria)
    assert is_ok(result2)
    assert provider.search_count == 2


# ============== MultiProviderAggregator Tests ==============

async def test_aggregator_empty_providers_returns_error():
    aggregator = MultiProviderAggregator([])
    criteria = make_test_criteria()
    result = await aggregator.search(criteria)
    assert result.is_err()
    assert "No providers available" in str(result.error)


async def test_aggregator_single_provider_success():
    flights = [make_test_flight()]
    provider = MockProvider("p1", flights=flights)
    aggregator = MultiProviderAggregator([provider])
    criteria = make_test_criteria()
    result = await aggregator.search(criteria)
    assert is_ok(result)
    assert len(unwrap(result)) == 1


async def test_aggregator_multiple_providers_combine_results():
    f1 = [make_test_flight("f1", price=Decimal("299.00"), dep_offset_hours=0)]
    f2 = [make_test_flight("f2", price=Decimal("399.00"), dep_offset_hours=3)]
    p1 = MockProvider("p1", flights=f1)
    p2 = MockProvider("p2", flights=f2)
    aggregator = MultiProviderAggregator([p1, p2])
    criteria = make_test_criteria()
    result = await aggregator.search(criteria)
    assert is_ok(result)
    assert len(unwrap(result)) == 2


async def test_aggregator_partial_failure_returns_successful_results():
    flights = [make_test_flight()]
    p1 = MockProvider("p1", flights=flights)
    p2 = MockProvider("p2", error=ProviderError(provider="p2", message="Fail"))
    aggregator = MultiProviderAggregator([p1, p2])
    criteria = make_test_criteria()
    result = await aggregator.search(criteria)
    assert is_ok(result)
    assert len(unwrap(result)) == 1


async def test_aggregator_all_fail_returns_error():
    p1 = MockProvider("p1", error=ProviderError(provider="p1", message="E1"))
    p2 = MockProvider("p2", error=ProviderError(provider="p2", message="E2"))
    aggregator = MultiProviderAggregator([p1, p2])
    criteria = make_test_criteria()
    result = await aggregator.search(criteria)
    assert result.is_err()
    assert "All providers failed" in str(result.error)


async def test_aggregator_results_sorted_by_price():
    f1 = [make_test_flight("expensive", price=Decimal("599.00"), dep_offset_hours=1)]
    f2 = [make_test_flight("cheap", price=Decimal("199.00"), dep_offset_hours=2)]
    f3 = [make_test_flight("medium", price=Decimal("399.00"), dep_offset_hours=3)]
    p1 = MockProvider("p1", flights=f1)
    p2 = MockProvider("p2", flights=f2)
    p3 = MockProvider("p3", flights=f3)
    aggregator = MultiProviderAggregator([p1, p2, p3])
    criteria = make_test_criteria()
    result = await aggregator.search(criteria)
    assert is_ok(result)
    flights = unwrap(result)
    assert flights[0].price.amount == Decimal("199.00")
    assert flights[1].price.amount == Decimal("399.00")
    assert flights[2].price.amount == Decimal("599.00")


async def test_aggregator_deduplication():
    base_time = datetime.now() + timedelta(days=30)
    dep_time = base_time + timedelta(hours=10)
    arr_time = dep_time + timedelta(hours=5)

    flight1 = Flight(
        id="f1",
        origin=Airport(code="JFK", name="JFK", city="New York", country="US"),
        destination=Airport(code="LAX", name="LAX", city="Los Angeles", country="US"),
        departure_time=dep_time,
        arrival_time=arr_time,
        price=Price(amount=Decimal("300.00"), currency="USD"),
        cabin_class=CabinClass(),
        stops=0,
        airline="AA",
    )
    # Similar flight (same airline, similar time, similar price)
    flight2 = Flight(
        id="f2",
        origin=Airport(code="JFK", name="JFK", city="New York", country="US"),
        destination=Airport(code="LAX", name="LAX", city="Los Angeles", country="US"),
        departure_time=dep_time + timedelta(minutes=5),
        arrival_time=arr_time + timedelta(minutes=5),
        price=Price(amount=Decimal("302.00"), currency="USD"),
        cabin_class=CabinClass(),
        stops=0,
        airline="AA",
    )
    p1 = MockProvider("p1", flights=[flight1])
    p2 = MockProvider("p2", flights=[flight2])
    aggregator = MultiProviderAggregator([p1, p2])
    criteria = make_test_criteria()
    result = await aggregator.search(criteria)
    assert is_ok(result)
    assert len(unwrap(result)) == 1  # Deduplicated


async def test_aggregator_different_airlines_not_deduplicated():
    base_time = datetime.now() + timedelta(days=30)
    dep_time = base_time + timedelta(hours=10)
    arr_time = dep_time + timedelta(hours=5)

    flight1 = Flight(
        id="f1",
        origin=Airport(code="JFK", name="JFK", city="New York", country="US"),
        destination=Airport(code="LAX", name="LAX", city="Los Angeles", country="US"),
        departure_time=dep_time,
        arrival_time=arr_time,
        price=Price(amount=Decimal("300.00"), currency="USD"),
        cabin_class=CabinClass(),
        stops=0,
        airline="AA",
    )
    # Same time/price but different airline
    flight2 = Flight(
        id="f2",
        origin=Airport(code="JFK", name="JFK", city="New York", country="US"),
        destination=Airport(code="LAX", name="LAX", city="Los Angeles", country="US"),
        departure_time=dep_time,
        arrival_time=arr_time,
        price=Price(amount=Decimal("300.00"), currency="USD"),
        cabin_class=CabinClass(),
        stops=0,
        airline="DL",  # Different airline
    )
    p1 = MockProvider("p1", flights=[flight1])
    p2 = MockProvider("p2", flights=[flight2])
    aggregator = MultiProviderAggregator([p1, p2])
    criteria = make_test_criteria()
    result = await aggregator.search(criteria)
    assert is_ok(result)
    assert len(unwrap(result)) == 2  # Not deduplicated


def run_all_tests():
    print("=" * 50)
    print("Provider Infrastructure Tests")
    print("=" * 50)

    # ProviderRegistry Tests
    print("\n--- ProviderRegistry Tests ---")
    test_registry_register_provider()
    print("  [PASS] test_registry_register_provider")
    test_registry_get_by_priority()
    print("  [PASS] test_registry_get_by_priority")
    test_registry_enable_disable()
    print("  [PASS] test_registry_enable_disable")
    test_registry_get_enabled()
    print("  [PASS] test_registry_get_enabled")
    test_registry_get_status()
    print("  [PASS] test_registry_get_status")

    # CacheDecorator Tests
    print("\n--- CacheDecorator Tests ---")
    asyncio.run(test_cache_decorator_provider_name())
    print("  [PASS] test_cache_decorator_provider_name")
    asyncio.run(test_cache_decorator_cache_miss_calls_provider())
    print("  [PASS] test_cache_decorator_cache_miss_calls_provider")
    asyncio.run(test_cache_decorator_cache_hit_skips_provider())
    print("  [PASS] test_cache_decorator_cache_hit_skips_provider")
    asyncio.run(test_cache_decorator_does_not_cache_errors())
    print("  [PASS] test_cache_decorator_does_not_cache_errors")

    # MultiProviderAggregator Tests
    print("\n--- MultiProviderAggregator Tests ---")
    asyncio.run(test_aggregator_empty_providers_returns_error())
    print("  [PASS] test_aggregator_empty_providers_returns_error")
    asyncio.run(test_aggregator_single_provider_success())
    print("  [PASS] test_aggregator_single_provider_success")
    asyncio.run(test_aggregator_multiple_providers_combine_results())
    print("  [PASS] test_aggregator_multiple_providers_combine_results")
    asyncio.run(test_aggregator_partial_failure_returns_successful_results())
    print("  [PASS] test_aggregator_partial_failure_returns_successful_results")
    asyncio.run(test_aggregator_all_fail_returns_error())
    print("  [PASS] test_aggregator_all_fail_returns_error")
    asyncio.run(test_aggregator_results_sorted_by_price())
    print("  [PASS] test_aggregator_results_sorted_by_price")
    asyncio.run(test_aggregator_deduplication())
    print("  [PASS] test_aggregator_deduplication")
    asyncio.run(test_aggregator_different_airlines_not_deduplicated())
    print("  [PASS] test_aggregator_different_airlines_not_deduplicated")

    print("\n" + "=" * 50)
    print("All provider infrastructure tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    run_all_tests()
