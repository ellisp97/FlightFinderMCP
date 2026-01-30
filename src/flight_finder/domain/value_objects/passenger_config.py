"""Passenger configuration value object."""

from pydantic import BaseModel, Field, ConfigDict, field_validator


class PassengerConfig(BaseModel):
    """Immutable passenger configuration value object.

    Represents the number and type of passengers for a flight search.
    Enforces airline-standard passenger limits (1-9 total passengers).
    """

    model_config = ConfigDict(frozen=True)

    adults: int = Field(default=1, ge=1, le=9, description="Number of adult passengers (18+)")
    children: int = Field(default=0, ge=0, le=8, description="Number of children (2-17)")
    infants: int = Field(default=0, ge=0, le=4, description="Number of infants (under 2)")

    @field_validator("children")
    @classmethod
    def validate_total_with_children(cls, children: int, info) -> int:
        """Ensure total passengers doesn't exceed 9."""
        if "adults" in info.data:
            adults = info.data["adults"]
            if adults + children > 9:
                raise ValueError(
                    f"Total adults + children cannot exceed 9 (got {adults + children})"
                )
        return children

    @field_validator("infants")
    @classmethod
    def validate_infants_rules(cls, infants: int, info) -> int:
        """Validate infant-specific rules:
        1. Total passengers (including infants) cannot exceed 9
        2. Infants cannot exceed number of adults (lap infant rule)
        """
        if "adults" in info.data and "children" in info.data:
            adults = info.data["adults"]
            children = info.data["children"]

            # Rule 1: Total passengers limit
            total = adults + children + infants
            if total > 9:
                raise ValueError(
                    f"Total passengers cannot exceed 9 (got {total})"
                )

            # Rule 2: Lap infant rule (1 infant per adult)
            if infants > adults:
                raise ValueError(
                    f"Number of infants ({infants}) cannot exceed number of adults ({adults})"
                )

        return infants

    @property
    def total_passengers(self) -> int:
        """Calculate total number of passengers."""
        return self.adults + self.children + self.infants

    @property
    def has_children_or_infants(self) -> bool:
        """Check if there are any children or infants."""
        return self.children > 0 or self.infants > 0

    def __str__(self) -> str:
        """Format as '2 adults, 1 child, 1 infant' (omitting zero counts)."""
        parts = []
        if self.adults > 0:
            parts.append(f"{self.adults} adult{'s' if self.adults > 1 else ''}")
        if self.children > 0:
            parts.append(f"{self.children} child{'ren' if self.children > 1 else ''}")
        if self.infants > 0:
            parts.append(f"{self.infants} infant{'s' if self.infants > 1 else ''}")
        return ", ".join(parts) if parts else "0 passengers"
