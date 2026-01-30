"""Tests for MultiProviderAggregator."""

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
from flight_finder.infrastructure.providers.multi_provider_aggregator import (
    MultiProviderAggregator,
)


class MockProvider:
    def __init__(
        self, name: str, flights: list[Flight] | None = None, error: ProviderError | None = None
    ):
        self._name = name
        self._flights = flights or []
        self._error = error

    @property
    def provider_name(self) -> str:
        return self._name

    async def search(self, criteria: SearchCriteria):
        if self._error:
            return Err(self._error)
        return Ok(self._flights)


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


async def test_empty_providers_returns_error():
    aggregator = MultiProviderAggregator([])
    criteria = make_test_criteria()

    result = await aggregator.search(criteria)

    assert result.is_err()
    assert "No providers available" in str(result.error)


async def test_single_provider_success():
    flights = [make_test_flight()]
    provider = MockProvider("provider1", flights=flights)
    aggregator = MultiProviderAggregator([provider])
    criteria = make_test_criteria()

    result = await aggregator.search(criteria)

    assert is_ok(result)
    assert len(unwrap(result)) == 1


async def test_multiple_providers_combine_results():
    flights1 = [make_test_flight("flight-1", price=Decimal("299.00"))]
    flights2 = [make_test_flight("flight-2", price=Decimal("399.00"), dep_offset_hours=3)]

    provider1 = MockProvider("provider1", flights=flights1)
    provider2 = MockProvider("provider2", flights=flights2)
    aggregator = MultiProviderAggregator([provider1, provider2])
    criteria = make_test_criteria()

    result = await aggregator.search(criteria)

    assert is_ok(result)
    all_flights = unwrap(result)
    assert len(all_flights) == 2


async def test_partial_failure_returns_successful_results():
    flights = [make_test_flight()]
    provider1 = MockProvider("provider1", flights=flights)
    provider2 = MockProvider(
        "provider2", error=ProviderError(provider="provider2", message="API Error")
    )
    aggregator = MultiProviderAggregator([provider1, provider2])
    criteria = make_test_criteria()

    result = await aggregator.search(criteria)

    # Should succeed with partial results
    assert is_ok(result)
    assert len(unwrap(result)) == 1


async def test_all_providers_fail_returns_error():
    provider1 = MockProvider(
        "provider1", error=ProviderError(provider="provider1", message="Error 1")
    )
    provider2 = MockProvider(
        "provider2", error=ProviderError(provider="provider2", message="Error 2")
    )
    aggregator = MultiProviderAggregator([provider1, provider2])
    criteria = make_test_criteria()

    result = await aggregator.search(criteria)

    assert result.is_err()
    assert "All providers failed" in str(result.error)


async def test_results_sorted_by_price():
    flights1 = [make_test_flight("expensive", price=Decimal("599.00"), dep_offset_hours=1)]
    flights2 = [make_test_flight("cheap", price=Decimal("199.00"), dep_offset_hours=2)]
    flights3 = [make_test_flight("medium", price=Decimal("399.00"), dep_offset_hours=3)]

    provider1 = MockProvider("provider1", flights=flights1)
    provider2 = MockProvider("provider2", flights=flights2)
    provider3 = MockProvider("provider3", flights=flights3)
    aggregator = MultiProviderAggregator([provider1, provider2, provider3])
    criteria = make_test_criteria()

    result = await aggregator.search(criteria)

    assert is_ok(result)
    all_flights = unwrap(result)
    assert len(all_flights) == 3
    assert all_flights[0].price.amount == Decimal("199.00")
    assert all_flights[1].price.amount == Decimal("399.00")
    assert all_flights[2].price.amount == Decimal("599.00")


async def test_deduplication_removes_similar_flights():
    # Create two similar flights (same airline, similar times, similar price)
    base_time = datetime.now() + timedelta(days=30)
    dep_time = base_time + timedelta(hours=10)
    arr_time = dep_time + timedelta(hours=5)

    flight1 = Flight(
        id="flight-provider1",
        origin=Airport(code="JFK", name="JFK", city="New York", country="US"),
        destination=Airport(code="LAX", name="LAX", city="Los Angeles", country="US"),
        departure_time=dep_time,
        arrival_time=arr_time,
        price=Price(amount=Decimal("300.00"), currency="USD"),
        cabin_class=CabinClass(),
        stops=0,
        airline="AA",
    )

    # Similar flight - within 30 min and 5% price
    flight2 = Flight(
        id="flight-provider2",
        origin=Airport(code="JFK", name="JFK", city="New York", country="US"),
        destination=Airport(code="LAX", name="LAX", city="Los Angeles", country="US"),
        departure_time=dep_time + timedelta(minutes=5),  # 5 min later
        arrival_time=arr_time + timedelta(minutes=5),
        price=Price(amount=Decimal("302.00"), currency="USD"),  # ~0.7% diff
        cabin_class=CabinClass(),
        stops=0,
        airline="AA",
    )

    provider1 = MockProvider("provider1", flights=[flight1])
    provider2 = MockProvider("provider2", flights=[flight2])
    aggregator = MultiProviderAggregator([provider1, provider2])
    criteria = make_test_criteria()

    result = await aggregator.search(criteria)

    assert is_ok(result)
    all_flights = unwrap(result)
    # Should deduplicate to 1 flight
    assert len(all_flights) == 1


async def test_different_airlines_not_deduplicated():
    base_time = datetime.now() + timedelta(days=30)
    dep_time = base_time + timedelta(hours=10)
    arr_time = dep_time + timedelta(hours=5)

    flight1 = Flight(
        id="flight-aa",
        origin=Airport(code="JFK", name="JFK", city="New York", country="US"),
        destination=Airport(code="LAX", name="LAX", city="Los Angeles", country="US"),
        departure_time=dep_time,
        arrival_time=arr_time,
        price=Price(amount=Decimal("300.00"), currency="USD"),
        cabin_class=CabinClass(),
        stops=0,
        airline="AA",
    )

    flight2 = Flight(
        id="flight-dl",
        origin=Airport(code="JFK", name="JFK", city="New York", country="US"),
        destination=Airport(code="LAX", name="LAX", city="Los Angeles", country="US"),
        departure_time=dep_time,  # Same time
        arrival_time=arr_time,
        price=Price(amount=Decimal("300.00"), currency="USD"),  # Same price
        cabin_class=CabinClass(),
        stops=0,
        airline="DL",  # Different airline
    )

    provider1 = MockProvider("provider1", flights=[flight1])
    provider2 = MockProvider("provider2", flights=[flight2])
    aggregator = MultiProviderAggregator([provider1, provider2])
    criteria = make_test_criteria()

    result = await aggregator.search(criteria)

    assert is_ok(result)
    all_flights = unwrap(result)
    # Should not deduplicate - different airlines
    assert len(all_flights) == 2


def run_tests():
    print("Testing MultiProviderAggregator...")

    asyncio.run(test_empty_providers_returns_error())
    print("  ✓ test_empty_providers_returns_error")

    asyncio.run(test_single_provider_success())
    print("  ✓ test_single_provider_success")

    asyncio.run(test_multiple_providers_combine_results())
    print("  ✓ test_multiple_providers_combine_results")

    asyncio.run(test_partial_failure_returns_successful_results())
    print("  ✓ test_partial_failure_returns_successful_results")

    asyncio.run(test_all_providers_fail_returns_error())
    print("  ✓ test_all_providers_fail_returns_error")

    asyncio.run(test_results_sorted_by_price())
    print("  ✓ test_results_sorted_by_price")

    asyncio.run(test_deduplication_removes_similar_flights())
    print("  ✓ test_deduplication_removes_similar_flights")

    asyncio.run(test_different_airlines_not_deduplicated())
    print("  ✓ test_different_airlines_not_deduplicated")

    print("\nAll MultiProviderAggregator tests passed!")


if __name__ == "__main__":
    run_tests()
