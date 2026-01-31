"""Presentation layer schemas and converters."""

from flight_finder.presentation.schemas.converters import (
    flight_to_dto,
    to_search_criteria,
)
from flight_finder.presentation.schemas.requests import (
    ClearCacheRequest,
    FilterFlightsRequest,
    GetCacheStatsRequest,
    PassengerCount,
    SearchFlightsRequest,
)
from flight_finder.presentation.schemas.responses import (
    FlightDTO,
    PriceDTO,
)

__all__ = [
    # Requests
    "ClearCacheRequest",
    "FilterFlightsRequest",
    "GetCacheStatsRequest",
    "PassengerCount",
    "SearchFlightsRequest",
    # Responses
    "FlightDTO",
    "PriceDTO",
    # Converters
    "flight_to_dto",
    "to_search_criteria",
]
