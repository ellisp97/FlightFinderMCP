"""Flight entity with business rules and validation."""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic_core.core_schema import ValidationInfo

from flight_finder.domain.value_objects.airport import Airport
from flight_finder.domain.value_objects.price import Price
from flight_finder.domain.value_objects.cabin_class import CabinClass


class Flight(BaseModel):
    """Core flight entity with business rules.

    Represents a single flight segment with full validation of:
    - Temporal constraints (arrival > departure)
    - Logical constraints (stops, duration)
    - Required metadata (airline, airports)

    This is an immutable entity - all validation happens at construction.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unique flight identifier")
    origin: Airport = Field(..., description="Departure airport")
    destination: Airport = Field(..., description="Arrival airport")
    departure_time: datetime = Field(..., description="Scheduled departure time (UTC)")
    arrival_time: datetime = Field(..., description="Scheduled arrival time (UTC)")
    price: Price = Field(..., description="Flight price")
    cabin_class: CabinClass = Field(default_factory=CabinClass, description="Cabin class")
    stops: int = Field(default=0, ge=0, le=5, description="Number of stops (0-5)")
    airline: str = Field(..., min_length=2, max_length=3, description="Airline IATA code")
    airline_name: str | None = Field(default=None, description="Full airline name (optional)")
    aircraft_type: str | None = Field(default=None, description="Aircraft type code (optional)")
    flight_number: str | None = Field(default=None, description="Flight number (optional)")
    booking_url: str | None = Field(default=None, description="URL to book this flight")

    @field_validator("airline")
    @classmethod
    def validate_airline_code(cls, v: str) -> str:
        """Ensure airline code is uppercase and valid format."""
        v = v.upper().strip()
        if not v.isalpha() and not v.isalnum():
            raise ValueError(f"Airline code must be alphanumeric: {v}")
        return v

    @field_validator("arrival_time")
    @classmethod
    def validate_arrival_after_departure(cls, arrival: datetime, info: ValidationInfo) -> datetime:
        """Ensure arrival time is after departure time."""
        if "departure_time" in info.data:
            departure = info.data["departure_time"]
            if arrival <= departure:
                raise ValueError(
                    f"Arrival time ({arrival}) must be after departure time ({departure})"
                )

            # Additional sanity check: flight duration should be reasonable (< 24 hours for single segment)
            duration_hours = (arrival - departure).total_seconds() / 3600
            if duration_hours > 24:
                raise ValueError(
                    f"Flight duration ({duration_hours:.1f} hours) exceeds 24 hours - "
                    "this likely indicates a multi-segment journey that should be split"
                )

        return arrival

    @field_validator("destination")
    @classmethod
    def validate_different_airports(cls, destination: Airport, info: ValidationInfo) -> Airport:
        """Ensure origin and destination are different airports."""
        if "origin" in info.data:
            origin = info.data["origin"]
            if destination.code == origin.code:
                raise ValueError(
                    f"Origin and destination cannot be the same airport: {origin.code}"
                )
        return destination

    @property
    def is_non_stop(self) -> bool:
        """Check if flight is non-stop (direct)."""
        return self.stops == 0

    @property
    def is_direct(self) -> bool:
        """Alias for is_non_stop."""
        return self.is_non_stop

    @property
    def duration_minutes(self) -> int:
        """Calculate total flight duration in minutes."""
        return int((self.arrival_time - self.departure_time).total_seconds() / 60)

    @property
    def duration_hours(self) -> float:
        """Calculate total flight duration in hours."""
        return self.duration_minutes / 60.0

    def __str__(self) -> str:
        """Format as readable string."""
        stops_text = "non-stop" if self.is_non_stop else f"{self.stops} stop{'s' if self.stops > 1 else ''}"
        duration = f"{self.duration_hours:.1f}h"
        return (
            f"{self.airline} {self.flight_number or ''} "
            f"{self.origin.code} → {self.destination.code} "
            f"({duration}, {stops_text}) - {self.price}"
        ).strip()

    def __eq__(self, other: object) -> bool:
        """Equality based on flight ID."""
        if not isinstance(other, Flight):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on flight ID."""
        return hash(self.id)
