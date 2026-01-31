"""Request schemas for MCP tools."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PassengerCount(BaseModel):
    """Passenger count for flight search."""

    model_config = ConfigDict(frozen=True)

    adults: int = Field(default=1, ge=1, le=9, description="Number of adults")
    children: int = Field(default=0, ge=0, le=8, description="Number of children")
    infants: int = Field(default=0, ge=0, le=4, description="Number of infants")

    @model_validator(mode="after")
    def validate_total(self) -> "PassengerCount":
        """Ensure total passengers is valid."""
        total = self.adults + self.children + self.infants
        if total > 9:
            raise ValueError(f"Total passengers cannot exceed 9, got {total}")
        if self.infants > self.adults:
            raise ValueError("Infants cannot exceed number of adults")
        return self


class SearchFlightsRequest(BaseModel):
    """Request schema for flight search."""

    model_config = ConfigDict(frozen=True)

    origin: str = Field(..., min_length=3, max_length=3, description="Origin IATA code")
    destination: str = Field(..., min_length=3, max_length=3, description="Destination IATA code")
    departure_date: date = Field(..., description="Departure date")
    return_date: date | None = Field(default=None, description="Return date for round trip")
    passengers: PassengerCount = Field(
        default_factory=PassengerCount, description="Passenger counts"
    )
    cabin_class: str = Field(default="economy", description="Cabin class")
    max_stops: int | None = Field(default=None, ge=0, le=5, description="Maximum stops")
    non_stop_only: bool = Field(default=False, description="Only non-stop flights")

    @field_validator("origin", "destination", mode="before")
    @classmethod
    def uppercase_iata(cls, v: str) -> str:
        """Convert IATA codes to uppercase."""
        if isinstance(v, str):
            return v.upper().strip()
        return v

    @field_validator("cabin_class", mode="before")
    @classmethod
    def normalize_cabin_class(cls, v: str) -> str:
        """Normalize cabin class value."""
        if isinstance(v, str):
            return v.lower().strip()
        return v


class FilterFlightsRequest(BaseModel):
    """Request schema for filtering flights."""

    model_config = ConfigDict(frozen=True)

    max_price: float | None = Field(default=None, ge=0, description="Maximum price")
    min_price: float | None = Field(default=None, ge=0, description="Minimum price")
    max_stops: int | None = Field(default=None, ge=0, le=5, description="Maximum stops")
    airlines: list[str] | None = Field(default=None, description="Filter by airlines")
    sort_by: str = Field(default="price", description="Sort by field")
    sort_descending: bool = Field(default=False, description="Sort in descending order")


class GetCacheStatsRequest(BaseModel):
    """Request schema for cache stats."""

    model_config = ConfigDict(frozen=True)


class ClearCacheRequest(BaseModel):
    """Request schema for clearing cache."""

    model_config = ConfigDict(frozen=True)
