"""Unit tests for Airport value object."""

import pytest
from flight_finder.domain.value_objects.airport import Airport


class TestAirportValidation:
    """Test Airport validation rules."""

    def test_create_valid_airport_code_only(self):
        """Test creating airport with just code."""
        airport = Airport(code="JFK")
        assert airport.code == "JFK"
        assert airport.name is None
        assert airport.city is None
        assert airport.country is None

    def test_create_valid_airport_full_details(self):
        """Test creating airport with all details."""
        airport = Airport(
            code="LAX",
            name="Los Angeles International Airport",
            city="Los Angeles",
            country="United States"
        )
        assert airport.code == "LAX"
        assert airport.name == "Los Angeles International Airport"
        assert airport.city == "Los Angeles"
        assert airport.country == "United States"

    def test_lowercase_code_converted_to_uppercase(self):
        """Test that lowercase codes are converted to uppercase."""
        airport = Airport(code="lhr")
        assert airport.code == "LHR"

    def test_code_with_whitespace_stripped(self):
        """Test that whitespace is stripped from code."""
        airport = Airport(code=" ORD ")
        assert airport.code == "ORD"

    def test_invalid_code_length_fails(self):
        """Test that codes not exactly 3 characters fail."""
        with pytest.raises(ValueError, match="exactly 3 characters"):
            Airport(code="AB")

        with pytest.raises(ValueError, match="exactly 3 characters"):
            Airport(code="ABCD")

    def test_non_alphabetic_code_fails(self):
        """Test that codes with non-letters fail."""
        with pytest.raises(ValueError, match="must contain only letters"):
            Airport(code="JF1")

        with pytest.raises(ValueError, match="must contain only letters"):
            Airport(code="A-B")

    def test_immutability(self):
        """Test that Airport is immutable."""
        airport = Airport(code="JFK")
        with pytest.raises(Exception):  # Pydantic raises ValidationError or AttributeError
            airport.code = "LAX"


class TestAirportEquality:
    """Test Airport equality and hashing."""

    def test_airports_equal_by_code(self):
        """Test that airports are equal if codes match."""
        airport1 = Airport(code="JFK", name="John F. Kennedy")
        airport2 = Airport(code="JFK", name="Different Name")
        assert airport1 == airport2

    def test_airports_not_equal_different_codes(self):
        """Test that airports with different codes are not equal."""
        airport1 = Airport(code="JFK")
        airport2 = Airport(code="LAX")
        assert airport1 != airport2

    def test_airport_hashable(self):
        """Test that airports can be used in sets."""
        airport1 = Airport(code="JFK", name="Name 1")
        airport2 = Airport(code="JFK", name="Name 2")
        airport3 = Airport(code="LAX")

        airport_set = {airport1, airport2, airport3}
        assert len(airport_set) == 2  # airport1 and airport2 have same code

    def test_airport_as_dict_key(self):
        """Test that airports can be used as dictionary keys."""
        jfk = Airport(code="JFK")
        lax = Airport(code="LAX")

        airport_dict = {jfk: "New York", lax: "Los Angeles"}
        assert airport_dict[jfk] == "New York"
        assert airport_dict[lax] == "Los Angeles"


class TestAirportFormatting:
    """Test Airport string formatting."""

    def test_str_with_city(self):
        """Test string format with city."""
        airport = Airport(code="JFK", city="New York")
        assert str(airport) == "JFK (New York)"

    def test_str_without_city(self):
        """Test string format without city."""
        airport = Airport(code="LAX")
        assert str(airport) == "LAX"

    def test_str_with_all_details(self):
        """Test string format with all details (only code and city shown)."""
        airport = Airport(
            code="LHR",
            name="London Heathrow",
            city="London",
            country="United Kingdom"
        )
        assert str(airport) == "LHR (London)"


class TestAirportRealWorldCodes:
    """Test real-world airport codes."""

    def test_major_us_airports(self):
        """Test major US airport codes."""
        codes = ["JFK", "LAX", "ORD", "ATL", "DFW", "DEN", "SFO", "SEA", "MIA", "LAS"]
        for code in codes:
            airport = Airport(code=code)
            assert airport.code == code

    def test_major_international_airports(self):
        """Test major international airport codes."""
        codes = ["LHR", "CDG", "FRA", "AMS", "DXB", "SIN", "HKG", "NRT", "ICN", "SYD"]
        for code in codes:
            airport = Airport(code=code)
            assert airport.code == code
