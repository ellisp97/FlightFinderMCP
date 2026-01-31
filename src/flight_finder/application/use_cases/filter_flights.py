"""Filter flights use case."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from flight_finder.application.dtos.flight_dtos import FlightFilters, SortOption
from flight_finder.domain.common.result import Ok, Result
from flight_finder.domain.errors.domain_errors import DomainError

if TYPE_CHECKING:
    from flight_finder.domain.entities.flight import Flight

logger = structlog.get_logger()


class FilterError(DomainError):
    """Error during flight filtering."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "FILTER_ERROR")


class FilterFlightsUseCase:
    """Use case for filtering and sorting flight results."""

    def __init__(self) -> None:
        self._logger = logger.bind(use_case="filter_flights")

    async def execute(
        self,
        flights: list[Flight],
        filters: FlightFilters,
    ) -> Result[list[Flight], FilterError]:
        """Apply filters and sorting to flight results.

        Args:
            flights: List of flights to filter
            filters: Filter criteria to apply

        Returns:
            Result containing filtered flights or FilterError
        """
        self._logger.debug(
            "filtering_started",
            input_count=len(flights),
            filters=filters.model_dump(),
        )

        filtered = list(flights)

        if filters.min_price is not None:
            filtered = [f for f in filtered if f.price.amount >= filters.min_price]

        if filters.max_price is not None:
            filtered = [f for f in filtered if f.price.amount <= filters.max_price]

        if filters.max_stops is not None:
            filtered = [f for f in filtered if f.stops <= filters.max_stops]

        if filters.airlines:
            airline_set = {a.upper() for a in filters.airlines}
            filtered = [f for f in filtered if f.airline.upper() in airline_set]

        filtered = self._sort_flights(filtered, filters.sort_by, filters.sort_descending)

        self._logger.debug(
            "filtering_completed",
            input_count=len(flights),
            output_count=len(filtered),
        )

        return Ok(filtered)

    def _sort_flights(
        self,
        flights: list[Flight],
        sort_by: SortOption,
        descending: bool,
    ) -> list[Flight]:
        """Sort flights by specified criteria."""
        match sort_by:
            case SortOption.PRICE:
                key = lambda f: f.price.amount
            case SortOption.DURATION:
                key = lambda f: f.duration_minutes
            case SortOption.DEPARTURE_TIME:
                key = lambda f: f.departure_time
            case SortOption.STOPS:
                key = lambda f: f.stops
            case _:
                key = lambda f: f.price.amount

        return sorted(flights, key=key, reverse=descending)
