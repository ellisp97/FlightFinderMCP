"""Unit tests for SearchCriteria entity."""

import pytest
from datetime import date, timedelta

from flight_finder.domain.entities.search_criteria import SearchCriteria
from flight_finder.domain.value_objects.airport import Airport
from flight_finder.domain.value_objects.passenger_config import PassengerConfig
from flight_finder.domain.value_objects.cabin_class import CabinClass, CabinClassType
from flight_finder.domain.value_objects.date_range import DateRange


class TestSearchCriteriaValidation:
    """Test SearchCriteria validation rules."""

    def test_create_valid_one_way_search(self):
        """Test creating valid one-way search."""
        tomorrow = date.today() + timedelta(days=1)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=tomorrow,
        )

        assert criteria.origin.code == "JFK"
        assert criteria.destination.code == "LAX"
        assert criteria.departure_date == tomorrow
        assert criteria.return_date is None
        assert criteria.is_one_way
        assert not criteria.is_round_trip

    def test_create_valid_round_trip_search(self):
        """Test creating valid round-trip search."""
        departure = date.today() + timedelta(days=7)
        return_date = departure + timedelta(days=14)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LHR"),
            departure_date=departure,
            return_date=return_date,
        )

        assert criteria.is_round_trip
        assert not criteria.is_one_way
        assert criteria.return_date == return_date

    def test_departure_in_past_fails(self):
        """Test that departure date in the past fails."""
        yesterday = date.today() - timedelta(days=1)

        with pytest.raises(ValueError, match="cannot be in the past"):
            SearchCriteria(
                origin=Airport(code="JFK"),
                destination=Airport(code="LAX"),
                departure_date=yesterday,
            )

    def test_return_before_departure_fails(self):
        """Test that return before departure fails."""
        departure = date.today() + timedelta(days=7)
        return_date = departure - timedelta(days=1)

        with pytest.raises(ValueError, match="cannot be before departure"):
            SearchCriteria(
                origin=Airport(code="JFK"),
                destination=Airport(code="LAX"),
                departure_date=departure,
                return_date=return_date,
            )

    def test_same_origin_destination_fails(self):
        """Test that same origin and destination fails."""
        tomorrow = date.today() + timedelta(days=1)

        with pytest.raises(ValueError, match="cannot be the same"):
            SearchCriteria(
                origin=Airport(code="JFK"),
                destination=Airport(code="JFK"),
                departure_date=tomorrow,
            )

    def test_trip_duration_exceeds_one_year_fails(self):
        """Test that trip duration > 1 year fails."""
        departure = date.today() + timedelta(days=7)
        return_date = departure + timedelta(days=400)

        with pytest.raises(ValueError, match="exceeds 1 year"):
            SearchCriteria(
                origin=Airport(code="JFK"),
                destination=Airport(code="SYD"),
                departure_date=departure,
                return_date=return_date,
            )

    def test_non_stop_with_max_stops_fails(self):
        """Test that non_stop_only=True with max_stops > 0 fails."""
        tomorrow = date.today() + timedelta(days=1)

        with pytest.raises(ValueError, match="Cannot specify max_stops"):
            SearchCriteria(
                origin=Airport(code="JFK"),
                destination=Airport(code="LAX"),
                departure_date=tomorrow,
                non_stop_only=True,
                max_stops=2,
            )

    def test_immutability(self):
        """Test that SearchCriteria is immutable."""
        tomorrow = date.today() + timedelta(days=1)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=tomorrow,
        )

        with pytest.raises(Exception):  # Pydantic raises ValidationError or AttributeError
            criteria.departure_date = date.today()


class TestSearchCriteriaWithPassengers:
    """Test SearchCriteria with different passenger configurations."""

    def test_default_passenger_config(self):
        """Test default passenger config (1 adult)."""
        tomorrow = date.today() + timedelta(days=1)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=tomorrow,
        )

        assert criteria.passengers.adults == 1
        assert criteria.passengers.children == 0
        assert criteria.passengers.infants == 0

    def test_custom_passenger_config(self):
        """Test custom passenger configuration."""
        tomorrow = date.today() + timedelta(days=1)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=tomorrow,
            passengers=PassengerConfig(adults=2, children=2, infants=1),
        )

        assert criteria.passengers.total_passengers == 5

    def test_invalid_passenger_config_fails(self):
        """Test that invalid passenger config fails."""
        tomorrow = date.today() + timedelta(days=1)

        # Too many passengers
        with pytest.raises(ValueError):
            SearchCriteria(
                origin=Airport(code="JFK"),
                destination=Airport(code="LAX"),
                departure_date=tomorrow,
                passengers=PassengerConfig(adults=5, children=5),
            )


class TestSearchCriteriaCabinClass:
    """Test SearchCriteria with cabin class."""

    def test_default_cabin_class(self):
        """Test default cabin class (economy)."""
        tomorrow = date.today() + timedelta(days=1)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=tomorrow,
        )

        assert criteria.cabin_class.class_type == CabinClassType.ECONOMY

    def test_custom_cabin_class(self):
        """Test custom cabin class."""
        tomorrow = date.today() + timedelta(days=1)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LHR"),
            departure_date=tomorrow,
            cabin_class=CabinClass(class_type=CabinClassType.BUSINESS),
        )

        assert criteria.cabin_class.class_type == CabinClassType.BUSINESS


class TestSearchCriteriaProperties:
    """Test SearchCriteria computed properties."""

    def test_trip_duration_days_one_way(self):
        """Test trip_duration_days for one-way trip."""
        tomorrow = date.today() + timedelta(days=1)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=tomorrow,
        )

        assert criteria.trip_duration_days is None

    def test_trip_duration_days_round_trip(self):
        """Test trip_duration_days for round trip."""
        departure = date.today() + timedelta(days=7)
        return_date = departure + timedelta(days=14)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LHR"),
            departure_date=departure,
            return_date=return_date,
        )

        assert criteria.trip_duration_days == 14

    def test_effective_max_stops_non_stop_only(self):
        """Test effective_max_stops when non_stop_only is True."""
        tomorrow = date.today() + timedelta(days=1)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=tomorrow,
            non_stop_only=True,
        )

        assert criteria.effective_max_stops == 0

    def test_effective_max_stops_with_max_stops(self):
        """Test effective_max_stops with max_stops set."""
        tomorrow = date.today() + timedelta(days=1)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=tomorrow,
            max_stops=2,
        )

        assert criteria.effective_max_stops == 2

    def test_effective_max_stops_none(self):
        """Test effective_max_stops when not specified."""
        tomorrow = date.today() + timedelta(days=1)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=tomorrow,
        )

        assert criteria.effective_max_stops is None


class TestSearchCriteriaFlexibleDates:
    """Test SearchCriteria flexible date functionality."""

    def test_get_departure_date_range_not_flexible(self):
        """Test departure date range when not flexible."""
        departure = date.today() + timedelta(days=7)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=departure,
            flexible_dates=False,
        )

        date_range = criteria.get_departure_date_range()
        assert date_range.start_date == departure
        assert date_range.end_date == departure
        assert date_range.is_single_day()

    def test_get_departure_date_range_flexible(self):
        """Test departure date range when flexible."""
        departure = date.today() + timedelta(days=10)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=departure,
            flexible_dates=True,
            date_flexibility_days=3,
        )

        date_range = criteria.get_departure_date_range()
        expected_start = departure - timedelta(days=3)
        expected_end = departure + timedelta(days=3)

        assert date_range.start_date == expected_start
        assert date_range.end_date == expected_end
        assert date_range.duration_days == 7

    def test_get_departure_date_range_flexible_near_today(self):
        """Test flexible departure date range doesn't go into past."""
        tomorrow = date.today() + timedelta(days=1)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=tomorrow,
            flexible_dates=True,
            date_flexibility_days=3,
        )

        date_range = criteria.get_departure_date_range()
        assert date_range.start_date >= date.today()

    def test_get_return_date_range_one_way(self):
        """Test return date range for one-way trip."""
        tomorrow = date.today() + timedelta(days=1)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=tomorrow,
        )

        assert criteria.get_return_date_range() is None

    def test_get_return_date_range_not_flexible(self):
        """Test return date range when not flexible."""
        departure = date.today() + timedelta(days=7)
        return_date = departure + timedelta(days=14)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LHR"),
            departure_date=departure,
            return_date=return_date,
            flexible_dates=False,
        )

        date_range = criteria.get_return_date_range()
        assert date_range is not None
        assert date_range.start_date == return_date
        assert date_range.end_date == return_date

    def test_get_return_date_range_flexible(self):
        """Test return date range when flexible."""
        departure = date.today() + timedelta(days=7)
        return_date = departure + timedelta(days=14)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LHR"),
            departure_date=departure,
            return_date=return_date,
            flexible_dates=True,
            date_flexibility_days=2,
        )

        date_range = criteria.get_return_date_range()
        assert date_range is not None
        expected_start = return_date - timedelta(days=2)
        expected_end = return_date + timedelta(days=2)

        assert date_range.start_date == expected_start
        assert date_range.end_date == expected_end


class TestSearchCriteriaFormatting:
    """Test SearchCriteria string formatting."""

    def test_str_one_way(self):
        """Test string format for one-way trip."""
        tomorrow = date.today() + timedelta(days=1)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=tomorrow,
        )

        result = str(criteria)
        assert "One-way" in result
        assert "JFK" in result
        assert "LAX" in result

    def test_str_round_trip(self):
        """Test string format for round trip."""
        departure = date.today() + timedelta(days=7)
        return_date = departure + timedelta(days=14)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LHR"),
            departure_date=departure,
            return_date=return_date,
        )

        result = str(criteria)
        assert "Round-trip" in result
        assert "JFK" in result
        assert "LHR" in result

    def test_str_with_non_stop_only(self):
        """Test string format with non-stop only."""
        tomorrow = date.today() + timedelta(days=1)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="LAX"),
            departure_date=tomorrow,
            non_stop_only=True,
        )

        result = str(criteria)
        assert "non-stop only" in result

    def test_str_with_max_stops(self):
        """Test string format with max stops."""
        tomorrow = date.today() + timedelta(days=1)

        criteria = SearchCriteria(
            origin=Airport(code="JFK"),
            destination=Airport(code="SFO"),
            departure_date=tomorrow,
            max_stops=1,
        )

        result = str(criteria)
        assert "max 1 stops" in result
