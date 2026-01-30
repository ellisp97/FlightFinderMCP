"""Cabin class value object."""

from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class CabinClassType(str, Enum):
    """Enumeration of valid cabin classes."""

    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"

    def __str__(self) -> str:
        """Return display name."""
        return self.value.replace("_", " ").title()


class CabinClass(BaseModel):
    """Immutable cabin class value object.

    Represents the class of service for a flight or search.
    """

    model_config = ConfigDict(frozen=True)

    class_type: CabinClassType = Field(
        default=CabinClassType.ECONOMY,
        description="Type of cabin class"
    )

    def __str__(self) -> str:
        """Format as display name."""
        return str(self.class_type)

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if not isinstance(other, CabinClass):
            return False
        return self.class_type == other.class_type

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        return hash(self.class_type)

    @property
    def is_premium(self) -> bool:
        """Check if this is a premium cabin class."""
        return self.class_type in (
            CabinClassType.PREMIUM_ECONOMY,
            CabinClassType.BUSINESS,
            CabinClassType.FIRST
        )
