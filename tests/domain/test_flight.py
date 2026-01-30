"""Unit tests for Flight entity."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from flight_finder.domain.entities.flight import Flight
from flight_finder.domain.value_objects.airport import Airport
from flight_finder.domain.value_objects.price import Price
from flight_finder.domain.value_objects.cabin_class import CabinClass, CabinClassType


class TestFlightValidation:
    """Test Flight validation rules."""

    def test_create_valid_flight(self):
        """Test creating a valid flight."""
        departure = datetime(2026, 6, 1, 10, 0)
        arrival = datetime(2026, 6, 1, 14, 30)

        flight = Flight(
            id="AA100-JFK-LAX-20260601",
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_time=departure,
            arrival_time=arrival,
            price=Price(amount=Decimal("299.99"), currency="USD"),
            airline="AA",
            stops=0,
        )

        assert flight.id == "AA100-JFK-LAX-20260601"
        assert flight.origin.code == "JFK"
        assert flight.destination.code == "LAX"
        assert flight.departure_time == departure
        assert flight.arrival_time == arrival
        assert flight.price.amount == Decimal("299.99")
        assert flight.airline == "AA"
        assert flight.stops == 0

    def test_arrival_before_departure_fails(self):
        """Test that arrival before departure fails."""
        departure = datetime(2026, 6, 1, 14, 0)
        arrival = datetime(2026, 6, 1, 10, 0)

        with pytest.raises(ValueError, match="must be after departure"):
            Flight(
                id="TEST-1",
                origin=Airport(code="JFK"),
                destination=Airport(code="LAX"),
                departure_time=departure,
                arrival_time=arrival,
                price=Price(amount=Decimal("299.99")),
                airline="AA",
            )

    def test_arrival_equals_departure_fails(self):
        """Test that arrival equal to departure fails."""
        time = datetime(2026, 6, 1, 10, 0)

        with pytest.raises(ValueError, match="must be after departure"):
            Flight(
                id="TEST-1",
                origin=Airport(code="JFK"),
                destination=Airport(code="LAX"),
                departure_time=time,
                arrival_time=time,
                price=Price(amount=Decimal("299.99")),
                airline="AA",
            )

    def test_same_origin_destination_fails(self):
        """Test that same origin and destination fails."""
        departure = datetime(2026, 6, 1, 10, 0)
        arrival = datetime(2026, 6, 1, 14, 0)

        with pytest.raises(ValueError, match="cannot be the same airport"):
            Flight(
                id="TEST-1",
                origin=Airport(code="JFK"),
                destination=Airport(code="JFK"),  # Same as origin
                departure_time=departure,
                arrival_time=arrival,
                price=Price(amount=Decimal("299.99")),
                airline="AA",
            )

    def test_duration_exceeds_24_hours_fails(self):
        """Test that flight duration > 24 hours fails."""
        departure = datetime(2026, 6, 1, 10, 0)
        arrival = datetime(2026, 6, 3, 11, 0)  # More than 24 hours later

        with pytest.raises(ValueError, match="exceeds 24 hours"):
            Flight(
                id="TEST-1",
                origin=Airport(code="JFK"),
                destination=Airport(code="SYD"),
                departure_time=departure,
                arrival_time=arrival,
                price=Price(amount=Decimal("1299.99")),
                airline="QF",
            )

    def test_invalid_stops_count_fails(self):
        """Test that invalid stops count fails."""
        departure = datetime(2026, 6, 1, 10, 0)
        arrival = datetime(2026, 6, 1, 20, 0)

        # Negative stops
        with pytest.raises(ValueError):
            Flight(
                id="TEST-1",
                origin=Airport(code="JFK"),
                destination=Airport(code="LAX"),
                departure_time=departure,
                arrival_time=arrival,
                price=Price(amount=Decimal("299.99")),
                airline="AA",
                stops=-1,
            )

        # Too many stops
        with pytest.raises(ValueError):
            Flight(
                id="TEST-1",
                origin=Airport(code="JFK"),
                destination=Airport(code="LAX"),
                departure_time=departure,
                arrival_time=arrival,
                price=Price(amount=Decimal("299.99")),
                airline="AA",
                stops=6,
            )

    def test_airline_code_converted_to_uppercase(self):
        """Test that airline code is converted to uppercase."""
        departure = datetime(2026, 6, 1, 10, 0)
        arrival = datetime(2026, 6, 1, 14, 0)

        flight = Flight(
            id="TEST-1",
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_time=departure,
            arrival_time=arrival,
            price=Price(amount=Decimal("299.99")),
            airline="aa",  # lowercase
        )

        assert flight.airline == "AA"

    def test_immutability(self):
        """Test that Flight is immutable."""
        departure = datetime(2026, 6, 1, 10, 0)
        arrival = datetime(2026, 6, 1, 14, 0)

        flight = Flight(
            id="TEST-1",
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_time=departure,
            arrival_time=arrival,
            price=Price(amount=Decimal("299.99")),
            airline="AA",
        )

        with pytest.raises(Exception):  # Pydantic raises ValidationError or AttributeError
            flight.price = Price(amount=Decimal("199.99"))


class TestFlightProperties:
    """Test Flight computed properties."""

    def test_is_non_stop_true(self):
        """Test is_non_stop when flight has no stops."""
        departure = datetime(2026, 6, 1, 10, 0)
        arrival = datetime(2026, 6, 1, 14, 0)

        flight = Flight(
            id="TEST-1",
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_time=departure,
            arrival_time=arrival,
            price=Price(amount=Decimal("299.99")),
            airline="AA",
            stops=0,
        )

        assert flight.is_non_stop
        assert flight.is_direct

    def test_is_non_stop_false(self):
        """Test is_non_stop when flight has stops."""
        departure = datetime(2026, 6, 1, 10, 0)
        arrival = datetime(2026, 6, 1, 20, 0)

        flight = Flight(
            id="TEST-1",
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_time=departure,
            arrival_time=arrival,
            price=Price(amount=Decimal("199.99")),
            airline="AA",
            stops=1,
        )

        assert not flight.is_non_stop
        assert not flight.is_direct

    def test_duration_minutes(self):
        """Test duration_minutes calculation."""
        departure = datetime(2026, 6, 1, 10, 0)
        arrival = datetime(2026, 6, 1, 15, 30)  # 5h 30m

        flight = Flight(
            id="TEST-1",
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_time=departure,
            arrival_time=arrival,
            price=Price(amount=Decimal("299.99")),
            airline="AA",
        )

        assert flight.duration_minutes == 330  # 5.5 hours * 60

    def test_duration_hours(self):
        """Test duration_hours calculation."""
        departure = datetime(2026, 6, 1, 10, 0)
        arrival = datetime(2026, 6, 1, 16, 0)  # 6 hours

        flight = Flight(
            id="TEST-1",
            origin=Airport(code="JFK"),
            destination=Airport(code="SFO"),
            departure_time=departure,
            arrival_time=arrival,
            price=Price(amount=Decimal("349.99")),
            airline="UA",
        )

        assert flight.duration_hours == 6.0


class TestFlightEquality:
    """Test Flight equality and hashing."""

    def test_flights_equal_by_id(self):
        """Test that flights are equal if IDs match."""
        departure = datetime(2026, 6, 1, 10, 0)
        arrival = datetime(2026, 6, 1, 14, 0)

        flight1 = Flight(
            id="AA100",
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_time=departure,
            arrival_time=arrival,
            price=Price(amount=Decimal("299.99")),
            airline="AA",
        )

        # Same ID, different details
        flight2 = Flight(
            id="AA100",
            origin=Airport(code="ORD"),
            destination=Airport(code="SFO"),
            departure_time=departure,
            arrival_time=arrival,
            price=Price(amount=Decimal("399.99")),
            airline="UA",
        )

        assert flight1 == flight2

    def test_flights_not_equal_different_ids(self):
        """Test that flights with different IDs are not equal."""
        departure = datetime(2026, 6, 1, 10, 0)
        arrival = datetime(2026, 6, 1, 14, 0)

        flight1 = Flight(
            id="AA100",
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_time=departure,
            arrival_time=arrival,
            price=Price(amount=Decimal("299.99")),
            airline="AA",
        )

        flight2 = Flight(
            id="AA200",
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_time=departure,
            arrival_time=arrival,
            price=Price(amount=Decimal("299.99")),
            airline="AA",
        )

        assert flight1 != flight2

    def test_flight_hashable(self):
        """Test that flights can be used in sets."""
        departure = datetime(2026, 6, 1, 10, 0)
        arrival = datetime(2026, 6, 1, 14, 0)

        flight1 = Flight(
            id="AA100",
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_time=departure,
            arrival_time=arrival,
            price=Price(amount=Decimal("299.99")),
            airline="AA",
        )

        flight2 = Flight(
            id="AA100",
            origin=Airport(code="ORD"),
            destination=Airport(code="SFO"),
            departure_time=departure,
            arrival_time=arrival,
            price=Price(amount=Decimal("399.99")),
            airline="UA",
        )

        flight3 = Flight(
            id="UA200",
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_time=departure,
            arrival_time=arrival,
            price=Price(amount=Decimal("299.99")),
            airline="UA",
        )

        flight_set = {flight1, flight2, flight3}
        assert len(flight_set) == 2  # flight1 and flight2 have same ID


class TestFlightFormatting:
    """Test Flight string formatting."""

    def test_str_format_complete(self):
        """Test string format with all details."""
        departure = datetime(2026, 6, 1, 10, 0)
        arrival = datetime(2026, 6, 1, 15, 30)

        flight = Flight(
            id="AA100-JFK-LAX",
            origin=Airport(code="JFK", city="New York"),
            destination=Airport(code="LAX", city="Los Angeles"),
            departure_time=departure,
            arrival_time=arrival,
            price=Price(amount=Decimal("299.99")),
            airline="AA",
            flight_number="100",
            stops=0,
        )

        result = str(flight)
        assert "AA" in result
        assert "100" in result
        assert "JFK" in result
        assert "LAX" in result
        assert "non-stop" in result
        assert "USD 299.99" in result

    def test_str_format_with_stops(self):
        """Test string format with stops."""
        departure = datetime(2026, 6, 1, 10, 0)
        arrival = datetime(2026, 6, 1, 20, 0)

        flight = Flight(
            id="AA200",
            origin=Airport(code="JFK"),
            destination=Airport(code="SFO"),
            departure_time=departure,
            arrival_time=arrival,
            price=Price(amount=Decimal("249.99")),
            airline="AA",
            stops=2,
        )

        result = str(flight)
        assert "2 stops" in result
