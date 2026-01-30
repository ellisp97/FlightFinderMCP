"""Unit tests for CabinClass value object."""

import pytest
from flight_finder.domain.value_objects.cabin_class import CabinClass, CabinClassType


class TestCabinClassCreation:
    """Test CabinClass creation."""

    def test_create_default_cabin_class(self):
        """Test creating default cabin class (economy)."""
        cabin_class = CabinClass()
        assert cabin_class.class_type == CabinClassType.ECONOMY

    def test_create_economy(self):
        """Test creating economy cabin class."""
        cabin_class = CabinClass(class_type=CabinClassType.ECONOMY)
        assert cabin_class.class_type == CabinClassType.ECONOMY

    def test_create_premium_economy(self):
        """Test creating premium economy cabin class."""
        cabin_class = CabinClass(class_type=CabinClassType.PREMIUM_ECONOMY)
        assert cabin_class.class_type == CabinClassType.PREMIUM_ECONOMY

    def test_create_business(self):
        """Test creating business cabin class."""
        cabin_class = CabinClass(class_type=CabinClassType.BUSINESS)
        assert cabin_class.class_type == CabinClassType.BUSINESS

    def test_create_first(self):
        """Test creating first class cabin class."""
        cabin_class = CabinClass(class_type=CabinClassType.FIRST)
        assert cabin_class.class_type == CabinClassType.FIRST

    def test_immutability(self):
        """Test that CabinClass is immutable."""
        cabin_class = CabinClass(class_type=CabinClassType.ECONOMY)
        with pytest.raises(Exception):  # Pydantic raises ValidationError or AttributeError
            cabin_class.class_type = CabinClassType.BUSINESS


class TestCabinClassProperties:
    """Test CabinClass computed properties."""

    def test_is_premium_false_for_economy(self):
        """Test is_premium for economy."""
        cabin_class = CabinClass(class_type=CabinClassType.ECONOMY)
        assert not cabin_class.is_premium

    def test_is_premium_true_for_premium_economy(self):
        """Test is_premium for premium economy."""
        cabin_class = CabinClass(class_type=CabinClassType.PREMIUM_ECONOMY)
        assert cabin_class.is_premium

    def test_is_premium_true_for_business(self):
        """Test is_premium for business."""
        cabin_class = CabinClass(class_type=CabinClassType.BUSINESS)
        assert cabin_class.is_premium

    def test_is_premium_true_for_first(self):
        """Test is_premium for first class."""
        cabin_class = CabinClass(class_type=CabinClassType.FIRST)
        assert cabin_class.is_premium


class TestCabinClassEquality:
    """Test CabinClass equality and hashing."""

    def test_equality(self):
        """Test cabin class equality."""
        cabin1 = CabinClass(class_type=CabinClassType.BUSINESS)
        cabin2 = CabinClass(class_type=CabinClassType.BUSINESS)
        cabin3 = CabinClass(class_type=CabinClassType.ECONOMY)

        assert cabin1 == cabin2
        assert cabin1 != cabin3

    def test_hashable(self):
        """Test that cabin class can be used in sets."""
        cabin1 = CabinClass(class_type=CabinClassType.BUSINESS)
        cabin2 = CabinClass(class_type=CabinClassType.BUSINESS)
        cabin3 = CabinClass(class_type=CabinClassType.ECONOMY)

        cabin_set = {cabin1, cabin2, cabin3}
        assert len(cabin_set) == 2  # cabin1 and cabin2 are equal

    def test_as_dict_key(self):
        """Test that cabin class can be used as dictionary key."""
        economy = CabinClass(class_type=CabinClassType.ECONOMY)
        business = CabinClass(class_type=CabinClassType.BUSINESS)

        price_map = {
            economy: 200,
            business: 1000,
        }

        assert price_map[economy] == 200
        assert price_map[business] == 1000


class TestCabinClassFormatting:
    """Test CabinClass string formatting."""

    def test_str_economy(self):
        """Test string format for economy."""
        cabin_class = CabinClass(class_type=CabinClassType.ECONOMY)
        assert str(cabin_class) == "Economy"

    def test_str_premium_economy(self):
        """Test string format for premium economy."""
        cabin_class = CabinClass(class_type=CabinClassType.PREMIUM_ECONOMY)
        assert str(cabin_class) == "Premium Economy"

    def test_str_business(self):
        """Test string format for business."""
        cabin_class = CabinClass(class_type=CabinClassType.BUSINESS)
        assert str(cabin_class) == "Business"

    def test_str_first(self):
        """Test string format for first class."""
        cabin_class = CabinClass(class_type=CabinClassType.FIRST)
        assert str(cabin_class) == "First"


class TestCabinClassTypeEnum:
    """Test CabinClassType enum."""

    def test_enum_values(self):
        """Test enum values."""
        assert CabinClassType.ECONOMY.value == "economy"
        assert CabinClassType.PREMIUM_ECONOMY.value == "premium_economy"
        assert CabinClassType.BUSINESS.value == "business"
        assert CabinClassType.FIRST.value == "first"

    def test_enum_string_representation(self):
        """Test enum string representation."""
        assert str(CabinClassType.ECONOMY) == "Economy"
        assert str(CabinClassType.PREMIUM_ECONOMY) == "Premium Economy"
        assert str(CabinClassType.BUSINESS) == "Business"
        assert str(CabinClassType.FIRST) == "First"

    def test_all_enum_members(self):
        """Test that all enum members are defined."""
        expected_members = {"ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"}
        actual_members = {member.name for member in CabinClassType}
        assert actual_members == expected_members
