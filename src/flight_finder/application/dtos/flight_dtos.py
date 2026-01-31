"""Flight-related DTOs for application layer."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from flight_finder.domain.entities.flight import Flight


class SortOption(str, Enum):
    """Sort options for flight results."""

    PRICE = "price"
    DURATION = "duration"
    DEPARTURE_TIME = "departure_time"
    STOPS = "stops"


class FlightFilters(BaseModel):
    """Filters for post-search refinement."""

    model_config = ConfigDict(frozen=True)

    max_price: Decimal | None = Field(default=None, description="Maximum price")
    min_price: Decimal | None = Field(default=None, description="Minimum price")
    max_stops: int | None = Field(default=None, ge=0, le=5, description="Maximum stops")
    airlines: list[str] | None = Field(default=None, description="Filter by airline codes")
    sort_by: SortOption = Field(default=SortOption.PRICE, description="Sort order")
    sort_descending: bool = Field(default=False, description="Sort in descending order")


class FlightSearchResult(BaseModel):
    """Result of a flight search operation."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    flights: list["Flight"] = Field(..., description="List of flights found")
    total_results: int = Field(..., ge=0, description="Total number of results")
    providers_used: list[str] = Field(default_factory=list, description="Providers queried")
    search_duration_ms: float = Field(default=0.0, ge=0, description="Search duration in ms")
    cache_hit: bool = Field(default=False, description="Whether results came from cache")


class FlightRecommendations(BaseModel):
    """Flight recommendations based on different criteria."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    cheapest: "Flight | None" = Field(default=None, description="Cheapest flight")
    fastest: "Flight | None" = Field(default=None, description="Fastest flight")
    best_value: "Flight | None" = Field(default=None, description="Best value flight")
