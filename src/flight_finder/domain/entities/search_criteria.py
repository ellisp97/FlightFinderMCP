"""Search criteria entity for flight searches."""

from datetime import date
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic_core.core_schema import ValidationInfo

from flight_finder.domain.value_objects.airport import Airport
from flight_finder.domain.value_objects.passenger_config import PassengerConfig
from flight_finder.domain.value_objects.cabin_class import CabinClass
from flight_finder.domain.value_objects.date_range import DateRange


class SearchCriteria(BaseModel):
    """Immutable search criteria entity for flight searches.

    Encapsulates all parameters needed to search for flights with full validation:
    - Route validation (origin != destination)
    - Passenger limits (1-9 total passengers)
    - Date validation (departure before return for round trips)
    - Flexible date support via DateRange

    Supports both one-way and round-trip searches.
    """

    model_config = ConfigDict(frozen=True)

    origin: Airport = Field(..., description="Departure airport")
    destination: Airport = Field(..., description="Arrival airport")
    departure_date: date = Field(..., description="Departure date")
    return_date: date | None = Field(default=None, description="Return date (None for one-way)")
    passengers: PassengerConfig = Field(
        default_factory=PassengerConfig,
        description="Passenger configuration"
    )
    cabin_class: CabinClass = Field(
        default_factory=CabinClass,
        description="Preferred cabin class"
    )
    max_stops: int | None = Field(
        default=None,
        ge=0,
        le=5,
        description="Maximum number of stops (None = any)"
    )
    non_stop_only: bool = Field(
        default=False,
        description="Search for non-stop flights only"
    )
    flexible_dates: bool = Field(
        default=False,
        description="Allow flexible date searches"
    )
    date_flexibility_days: int = Field(
        default=3,
        ge=1,
        le=7,
        description="Days of flexibility (±N days)"
    )

    @field_validator("departure_date")
    @classmethod
    def validate_departure_not_past(cls, v: date) -> date:
        """Ensure departure date is not in the past."""
        today = date.today()
        if v < today:
            raise ValueError(
                f"Departure date ({v}) cannot be in the past (today: {today})"
            )
        return v

    @field_validator("return_date")
    @classmethod
    def validate_return_after_departure(cls, return_date: date | None, info: ValidationInfo) -> date | None:
        """Ensure return date is after departure date (if provided)."""
        if return_date is not None and "departure_date" in info.data:
            departure = info.data["departure_date"]
            if return_date < departure:
                raise ValueError(
                    f"Return date ({return_date}) cannot be before departure date ({departure})"
                )

            # Sanity check: trip shouldn't be longer than 1 year
            duration_days = (return_date - departure).days
            if duration_days > 365:
                raise ValueError(
                    f"Trip duration ({duration_days} days) exceeds 1 year - "
                    "this is likely an error"
                )

        return return_date

    @field_validator("destination")
    @classmethod
    def validate_different_airports(cls, destination: Airport, info: ValidationInfo) -> Airport:
        """Ensure origin and destination are different."""
        if "origin" in info.data:
            origin = info.data["origin"]
            if destination.code == origin.code:
                raise ValueError(
                    f"Origin and destination cannot be the same: {origin.code}"
                )
        return destination

    @field_validator("non_stop_only")
    @classmethod
    def validate_non_stop_with_max_stops(cls, non_stop_only: bool, info: ValidationInfo) -> bool:
        """Ensure non_stop_only is consistent with max_stops."""
        if non_stop_only and "max_stops" in info.data:
            max_stops = info.data["max_stops"]
            if max_stops is not None and max_stops > 0:
                raise ValueError(
                    "Cannot specify max_stops > 0 when non_stop_only is True"
                )
        return non_stop_only

    @property
    def is_round_trip(self) -> bool:
        """Check if this is a round-trip search."""
        return self.return_date is not None

    @property
    def is_one_way(self) -> bool:
        """Check if this is a one-way search."""
        return self.return_date is None

    @property
    def trip_duration_days(self) -> int | None:
        """Calculate trip duration in days (None for one-way)."""
        if self.return_date is None:
            return None
        return (self.return_date - self.departure_date).days

    @property
    def effective_max_stops(self) -> int | None:
        """Get effective max stops considering non_stop_only flag."""
        if self.non_stop_only:
            return 0
        return self.max_stops

    def get_departure_date_range(self) -> DateRange:
        """Get date range for departure based on flexibility settings."""
        if not self.flexible_dates:
            # Single day range
            return DateRange(start_date=self.departure_date, end_date=self.departure_date)

        # Calculate flexible range
        from datetime import timedelta
        start = self.departure_date - timedelta(days=self.date_flexibility_days)
        end = self.departure_date + timedelta(days=self.date_flexibility_days)

        # Ensure start date is not in the past
        today = date.today()
        if start < today:
            start = today

        return DateRange(start_date=start, end_date=end)

    def get_return_date_range(self) -> DateRange | None:
        """Get date range for return based on flexibility settings (None for one-way)."""
        if self.return_date is None:
            return None

        if not self.flexible_dates:
            # Single day range
            return DateRange(start_date=self.return_date, end_date=self.return_date)

        # Calculate flexible range
        from datetime import timedelta
        start = self.return_date - timedelta(days=self.date_flexibility_days)
        end = self.return_date + timedelta(days=self.date_flexibility_days)

        # Ensure start date is after departure
        if start < self.departure_date:
            start = self.departure_date

        return DateRange(start_date=start, end_date=end)

    def __str__(self) -> str:
        """Format as readable string."""
        trip_type = "Round-trip" if self.is_round_trip else "One-way"
        route = f"{self.origin.code} → {self.destination.code}"
        dates = f"{self.departure_date}"
        if self.return_date:
            dates += f" - {self.return_date}"

        parts = [trip_type, route, dates, str(self.passengers), str(self.cabin_class)]

        if self.non_stop_only:
            parts.append("non-stop only")
        elif self.max_stops is not None:
            parts.append(f"max {self.max_stops} stops")

        return " | ".join(parts)
