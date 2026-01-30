"""Unit tests for PassengerConfig value object."""

import pytest
from flight_finder.domain.value_objects.passenger_config import PassengerConfig


class TestPassengerConfigValidation:
    """Test PassengerConfig validation rules."""

    def test_create_default_config(self):
        """Test creating default passenger config (1 adult)."""
        config = PassengerConfig()
        assert config.adults == 1
        assert config.children == 0
        assert config.infants == 0
        assert config.total_passengers == 1

    def test_create_valid_config(self):
        """Test creating valid passenger config."""
        config = PassengerConfig(adults=2, children=1, infants=1)
        assert config.adults == 2
        assert config.children == 1
        assert config.infants == 1
        assert config.total_passengers == 4

    def test_zero_adults_fails(self):
        """Test that zero adults fails."""
        with pytest.raises(ValueError):
            PassengerConfig(adults=0)

    def test_negative_passengers_fail(self):
        """Test that negative passenger counts fail."""
        with pytest.raises(ValueError):
            PassengerConfig(adults=-1)

        with pytest.raises(ValueError):
            PassengerConfig(adults=1, children=-1)

        with pytest.raises(ValueError):
            PassengerConfig(adults=1, infants=-1)

    def test_too_many_adults_fails(self):
        """Test that more than 9 adults fails."""
        with pytest.raises(ValueError):
            PassengerConfig(adults=10)

    def test_too_many_children_fails(self):
        """Test that more than 8 children fails."""
        with pytest.raises(ValueError):
            PassengerConfig(adults=1, children=9)

    def test_too_many_infants_fails(self):
        """Test that more than 4 infants fails."""
        with pytest.raises(ValueError):
            PassengerConfig(adults=5, infants=5)

    def test_total_passengers_exceeds_nine_fails(self):
        """Test that total passengers > 9 fails."""
        with pytest.raises(ValueError, match="Total"):
            PassengerConfig(adults=5, children=5)

        with pytest.raises(ValueError, match="Total"):
            PassengerConfig(adults=6, children=2, infants=2)

    def test_infants_exceed_adults_fails(self):
        """Test that infants cannot exceed adults (lap infant rule)."""
        with pytest.raises(ValueError, match="infants.*cannot exceed.*adults"):
            PassengerConfig(adults=2, infants=3)

        with pytest.raises(ValueError, match="infants.*cannot exceed.*adults"):
            PassengerConfig(adults=1, infants=2)

    def test_max_valid_passengers(self):
        """Test maximum valid passenger configurations."""
        # 9 adults
        config = PassengerConfig(adults=9)
        assert config.total_passengers == 9

        # 5 adults, 4 children
        config = PassengerConfig(adults=5, children=4)
        assert config.total_passengers == 9

        # 4 adults, 4 infants, 1 child
        config = PassengerConfig(adults=4, children=1, infants=4)
        assert config.total_passengers == 9

    def test_immutability(self):
        """Test that PassengerConfig is immutable."""
        config = PassengerConfig(adults=2)
        with pytest.raises(Exception):  # Pydantic raises ValidationError or AttributeError
            config.adults = 3


class TestPassengerConfigProperties:
    """Test PassengerConfig computed properties."""

    def test_total_passengers(self):
        """Test total_passengers calculation."""
        config = PassengerConfig(adults=2, children=1, infants=1)
        assert config.total_passengers == 4

    def test_has_children_or_infants_false(self):
        """Test has_children_or_infants when false."""
        config = PassengerConfig(adults=3)
        assert not config.has_children_or_infants

    def test_has_children_or_infants_with_children(self):
        """Test has_children_or_infants with children."""
        config = PassengerConfig(adults=2, children=2)
        assert config.has_children_or_infants

    def test_has_children_or_infants_with_infants(self):
        """Test has_children_or_infants with infants."""
        config = PassengerConfig(adults=2, infants=1)
        assert config.has_children_or_infants

    def test_has_children_or_infants_with_both(self):
        """Test has_children_or_infants with both."""
        config = PassengerConfig(adults=2, children=1, infants=1)
        assert config.has_children_or_infants


class TestPassengerConfigFormatting:
    """Test PassengerConfig string formatting."""

    def test_str_single_adult(self):
        """Test string format with single adult."""
        config = PassengerConfig(adults=1)
        assert str(config) == "1 adult"

    def test_str_multiple_adults(self):
        """Test string format with multiple adults."""
        config = PassengerConfig(adults=3)
        assert str(config) == "3 adults"

    def test_str_with_children(self):
        """Test string format with children."""
        config = PassengerConfig(adults=2, children=2)
        assert str(config) == "2 adults, 2 children"

    def test_str_with_single_child(self):
        """Test string format with single child."""
        config = PassengerConfig(adults=2, children=1)
        assert str(config) == "2 adults, 1 child"

    def test_str_with_infants(self):
        """Test string format with infants."""
        config = PassengerConfig(adults=2, infants=2)
        assert str(config) == "2 adults, 2 infants"

    def test_str_with_single_infant(self):
        """Test string format with single infant."""
        config = PassengerConfig(adults=1, infants=1)
        assert str(config) == "1 adult, 1 infant"

    def test_str_with_all_types(self):
        """Test string format with all passenger types."""
        config = PassengerConfig(adults=2, children=2, infants=1)
        assert str(config) == "2 adults, 2 children, 1 infant"


class TestPassengerConfigRealWorld:
    """Test real-world passenger configurations."""

    def test_solo_traveler(self):
        """Test solo traveler configuration."""
        config = PassengerConfig(adults=1)
        assert config.total_passengers == 1

    def test_couple(self):
        """Test couple configuration."""
        config = PassengerConfig(adults=2)
        assert config.total_passengers == 2

    def test_family_with_kids(self):
        """Test family with children configuration."""
        config = PassengerConfig(adults=2, children=2)
        assert config.total_passengers == 4

    def test_family_with_infant(self):
        """Test family with infant configuration."""
        config = PassengerConfig(adults=2, children=1, infants=1)
        assert config.total_passengers == 4

    def test_large_group(self):
        """Test large group configuration."""
        config = PassengerConfig(adults=8, children=1)
        assert config.total_passengers == 9
