"""Tests for cache key generator."""

from datetime import date, timedelta

import pytest

from flight_finder.domain.entities.search_criteria import SearchCriteria
from flight_finder.domain.value_objects.airport import Airport
from flight_finder.domain.value_objects.cabin_class import CabinClass, CabinClassType
from flight_finder.domain.value_objects.passenger_config import PassengerConfig
from flight_finder.infrastructure.cache.cache_key_generator import generate_cache_key


@pytest.fixture
def base_criteria() -> SearchCriteria:
    return SearchCriteria(
        origin=Airport(code="JFK"),
        destination=Airport(code="LAX"),
        departure_date=date.today() + timedelta(days=30),
    )


class TestCacheKeyGenerator:

    def test_same_criteria_produces_same_key(self, base_criteria: SearchCriteria) -> None:
        key1 = generate_cache_key(base_criteria)
        key2 = generate_cache_key(base_criteria)
        assert key1 == key2

    def test_different_origin_produces_different_key(self, base_criteria: SearchCriteria) -> None:
        other = SearchCriteria(
            origin=Airport(code="SFO"),
            destination=base_criteria.destination,
            departure_date=base_criteria.departure_date,
        )

        assert generate_cache_key(base_criteria) != generate_cache_key(other)

    def test_different_provider_produces_different_key(self, base_criteria: SearchCriteria) -> None:
        key1 = generate_cache_key(base_criteria, provider="skyscanner")
        key2 = generate_cache_key(base_criteria, provider="google")
        assert key1 != key2

    def test_different_passengers_produces_different_key(self) -> None:
        departure = date.today() + timedelta(days=30)

        criteria1 = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=departure,
            passengers=PassengerConfig(adults=1),
        )
        criteria2 = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=departure,
            passengers=PassengerConfig(adults=2),
        )

        assert generate_cache_key(criteria1) != generate_cache_key(criteria2)

    def test_different_cabin_class_produces_different_key(self) -> None:
        departure = date.today() + timedelta(days=30)

        criteria1 = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=departure,
            cabin_class=CabinClass(class_type=CabinClassType.ECONOMY),
        )
        criteria2 = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=departure,
            cabin_class=CabinClass(class_type=CabinClassType.BUSINESS),
        )

        assert generate_cache_key(criteria1) != generate_cache_key(criteria2)

    def test_key_is_16_characters(self, base_criteria: SearchCriteria) -> None:
        key = generate_cache_key(base_criteria)
        assert len(key) == 16

    def test_key_is_hexadecimal(self, base_criteria: SearchCriteria) -> None:
        key = generate_cache_key(base_criteria)
        int(key, 16)  # Raises ValueError if not valid hex
