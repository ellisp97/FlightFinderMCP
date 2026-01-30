"""Airport value object with IATA code validation."""

from pydantic import BaseModel, Field, ConfigDict, field_validator


class Airport(BaseModel):
    """Immutable airport value object.

    Represents an airport with IATA code validation.
    IATA codes are 3-letter uppercase codes (e.g., JFK, LAX, LHR).
    """

    model_config = ConfigDict(frozen=True)

    code: str = Field(..., description="IATA airport code")
    name: str | None = Field(default=None, description="Airport name (optional)")
    city: str | None = Field(default=None, description="City name (optional)")
    country: str | None = Field(default=None, description="Country name (optional)")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Ensure IATA code is uppercase and alphabetic."""
        v = v.upper().strip()
        if not v.isalpha():
            raise ValueError(f"IATA code must contain only letters: {v}")
        if len(v) != 3:
            raise ValueError(f"IATA code must be exactly 3 characters: {v}")
        return v

    def __str__(self) -> str:
        """Format as 'JFK (New York)' or just 'JFK'."""
        if self.city:
            return f"{self.code} ({self.city})"
        return self.code

    def __eq__(self, other: object) -> bool:
        """Equality based on IATA code only."""
        if not isinstance(other, Airport):
            return False
        return self.code == other.code

    def __hash__(self) -> int:
        """Hash based on IATA code."""
        return hash(self.code)
