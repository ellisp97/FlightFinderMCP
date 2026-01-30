"""Unit tests for Price value object."""

import pytest
from decimal import Decimal
from flight_finder.domain.value_objects.price import Price


class TestPriceValidation:
    """Test Price validation rules."""

    def test_create_valid_price(self):
        """Test creating a valid price."""
        price = Price(amount=Decimal("123.45"), currency="USD")
        assert price.amount == Decimal("123.45")
        assert price.currency == "USD"

    def test_create_price_from_float(self):
        """Test creating price from float."""
        price = Price(amount=99.99, currency="EUR")
        assert price.amount == Decimal("99.99")
        assert price.currency == "EUR"

    def test_create_price_from_int(self):
        """Test creating price from integer."""
        price = Price(amount=100, currency="GBP")
        assert price.amount == Decimal("100")
        assert price.currency == "GBP"

    def test_default_currency_is_usd(self):
        """Test default currency is USD."""
        price = Price(amount=50)
        assert price.currency == "USD"

    def test_negative_amount_fails(self):
        """Test that negative amounts are rejected."""
        with pytest.raises(ValueError):
            Price(amount=-10, currency="USD")

    def test_invalid_currency_code_fails(self):
        """Test that invalid currency codes are rejected."""
        with pytest.raises(ValueError):
            Price(amount=100, currency="US")  # Too short

        with pytest.raises(ValueError):
            Price(amount=100, currency="USDD")  # Too long

        with pytest.raises(ValueError):
            Price(amount=100, currency="U$D")  # Invalid characters

    def test_lowercase_currency_fails(self):
        """Test that lowercase currency codes are rejected."""
        with pytest.raises(ValueError):
            Price(amount=100, currency="usd")

    def test_too_many_decimal_places_fails(self):
        """Test that more than 2 decimal places are rejected."""
        with pytest.raises(ValueError):
            Price(amount=Decimal("10.123"), currency="USD")

    def test_two_decimal_places_allowed(self):
        """Test that exactly 2 decimal places are allowed."""
        price = Price(amount=Decimal("10.12"), currency="USD")
        assert price.amount == Decimal("10.12")

    def test_immutability(self):
        """Test that Price is immutable."""
        price = Price(amount=100, currency="USD")
        with pytest.raises(Exception):  # Pydantic raises ValidationError or AttributeError
            price.amount = 200


class TestPriceComparison:
    """Test Price comparison operations."""

    def test_price_equality(self):
        """Test price equality comparison."""
        price1 = Price(amount=100, currency="USD")
        price2 = Price(amount=100, currency="USD")
        price3 = Price(amount=200, currency="USD")

        assert price1 == price2
        assert price1 != price3

    def test_price_less_than(self):
        """Test less than comparison."""
        price1 = Price(amount=100, currency="USD")
        price2 = Price(amount=200, currency="USD")

        assert price1 < price2
        assert not price2 < price1

    def test_price_less_than_or_equal(self):
        """Test less than or equal comparison."""
        price1 = Price(amount=100, currency="USD")
        price2 = Price(amount=200, currency="USD")
        price3 = Price(amount=100, currency="USD")

        assert price1 <= price2
        assert price1 <= price3
        assert not price2 <= price1

    def test_price_greater_than(self):
        """Test greater than comparison."""
        price1 = Price(amount=200, currency="USD")
        price2 = Price(amount=100, currency="USD")

        assert price1 > price2
        assert not price2 > price1

    def test_price_greater_than_or_equal(self):
        """Test greater than or equal comparison."""
        price1 = Price(amount=200, currency="USD")
        price2 = Price(amount=100, currency="USD")
        price3 = Price(amount=200, currency="USD")

        assert price1 >= price2
        assert price1 >= price3
        assert not price2 >= price1

    def test_comparison_different_currencies_fails(self):
        """Test that comparing prices in different currencies fails."""
        price_usd = Price(amount=100, currency="USD")
        price_eur = Price(amount=100, currency="EUR")

        with pytest.raises(ValueError, match="different currencies"):
            price_usd < price_eur

        with pytest.raises(ValueError, match="different currencies"):
            price_usd <= price_eur

        with pytest.raises(ValueError, match="different currencies"):
            price_usd > price_eur

        with pytest.raises(ValueError, match="different currencies"):
            price_usd >= price_eur

    def test_equality_different_currencies(self):
        """Test equality with different currencies."""
        price_usd = Price(amount=100, currency="USD")
        price_eur = Price(amount=100, currency="EUR")

        assert price_usd != price_eur


class TestPriceFormatting:
    """Test Price string formatting."""

    def test_str_format(self):
        """Test string formatting."""
        price = Price(amount=Decimal("123.45"), currency="USD")
        assert str(price) == "USD 123.45"

    def test_str_format_rounds_to_two_decimals(self):
        """Test that string formatting shows exactly 2 decimal places."""
        price = Price(amount=100, currency="EUR")
        assert str(price) == "EUR 100.00"


class TestPriceHashing:
    """Test Price hashing for use in sets and dicts."""

    def test_price_hashable(self):
        """Test that Price can be used in sets."""
        price1 = Price(amount=100, currency="USD")
        price2 = Price(amount=200, currency="USD")
        price3 = Price(amount=100, currency="USD")

        price_set = {price1, price2, price3}
        assert len(price_set) == 2  # price1 and price3 are equal

    def test_price_as_dict_key(self):
        """Test that Price can be used as dictionary key."""
        price1 = Price(amount=100, currency="USD")
        price2 = Price(amount=200, currency="USD")

        price_dict = {price1: "cheap", price2: "expensive"}
        assert price_dict[price1] == "cheap"
        assert price_dict[price2] == "expensive"
