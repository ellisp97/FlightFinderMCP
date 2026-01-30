"""Price value object with currency support."""

from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class Price(BaseModel):
    """Immutable price value object.

    Represents a monetary amount with currency validation.
    All price comparisons require matching currencies.
    """

    model_config = ConfigDict(frozen=True)

    amount: Decimal = Field(..., ge=0, description="Price amount (non-negative)")
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$", description="ISO 4217 currency code")

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v):
        """Convert to Decimal and validate precision."""
        if isinstance(v, (int, float, str)):
            decimal_value = Decimal(str(v))
        elif isinstance(v, Decimal):
            decimal_value = v
        else:
            return v

        # Limit to 2 decimal places for currency
        # as_tuple().exponent is negative for decimal places (e.g., -2 for 0.01)
        if decimal_value.as_tuple().exponent < -2:
            raise ValueError("Price amount cannot have more than 2 decimal places")
        return decimal_value

    def __str__(self) -> str:
        """Format as 'USD 123.45'."""
        return f"{self.currency} {self.amount:.2f}"

    def __lt__(self, other: "Price") -> bool:
        """Compare prices (requires same currency)."""
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare prices in different currencies: {self.currency} vs {other.currency}")
        return self.amount < other.amount

    def __le__(self, other: "Price") -> bool:
        """Less than or equal comparison."""
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare prices in different currencies: {self.currency} vs {other.currency}")
        return self.amount <= other.amount

    def __gt__(self, other: "Price") -> bool:
        """Greater than comparison."""
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare prices in different currencies: {self.currency} vs {other.currency}")
        return self.amount > other.amount

    def __ge__(self, other: "Price") -> bool:
        """Greater than or equal comparison."""
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare prices in different currencies: {self.currency} vs {other.currency}")
        return self.amount >= other.amount

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if not isinstance(other, Price):
            return False
        return self.amount == other.amount and self.currency == other.currency

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        return hash((self.amount, self.currency))
