"""Search flights use case."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog

from flight_finder.application.dtos.flight_dtos import FlightSearchResult
from flight_finder.domain.common.result import Err, Ok, Result
from flight_finder.domain.errors.domain_errors import DomainError, ProviderError

if TYPE_CHECKING:
    from flight_finder.config.settings import Settings
    from flight_finder.domain.entities.flight import Flight
    from flight_finder.domain.entities.search_criteria import SearchCriteria
    from flight_finder.domain.protocols.flight_provider import IFlightProvider

logger = structlog.get_logger()


class SearchError(DomainError):
    """Error during flight search."""

    def __init__(
        self,
        message: str,
        providers_failed: list[str] | None = None,
        original: Exception | None = None,
    ) -> None:
        context = {}
        if providers_failed:
            context["providers_failed"] = providers_failed
        if original:
            context["original_error"] = str(original)
        super().__init__(message, "SEARCH_ERROR", context)
        self.providers_failed = providers_failed or []
        self.original = original


class SearchFlightsUseCase:
    """Use case for searching flights across providers."""

    def __init__(
        self,
        provider: IFlightProvider,
        settings: Settings,
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._logger = logger.bind(use_case="search_flights")

    async def execute(
        self,
        criteria: SearchCriteria,
    ) -> Result[FlightSearchResult, SearchError]:
        """Execute flight search with business logic.

        Args:
            criteria: Search criteria defining the flight search

        Returns:
            Result containing FlightSearchResult or SearchError
        """
        self._logger.info(
            "search_started",
            origin=criteria.origin.code,
            destination=criteria.destination.code,
            departure_date=str(criteria.departure_date),
            return_date=str(criteria.return_date) if criteria.return_date else None,
            passengers=criteria.passengers.total_passengers,
        )

        start_time = time.perf_counter()

        result = await self._provider.search(criteria)

        duration_ms = (time.perf_counter() - start_time) * 1000

        match result:
            case Ok(flights):
                limited_flights = self._apply_limits(flights)

                self._logger.info(
                    "search_completed",
                    duration_ms=round(duration_ms, 2),
                    total_results=len(flights),
                    returned_results=len(limited_flights),
                )

                return Ok(
                    FlightSearchResult(
                        flights=limited_flights,
                        total_results=len(limited_flights),
                        providers_used=self._get_provider_names(),
                        search_duration_ms=duration_ms,
                        cache_hit=False,
                    )
                )

            case Err(error):
                self._logger.error(
                    "search_failed",
                    duration_ms=round(duration_ms, 2),
                    error=str(error),
                )

                providers_failed = []
                if isinstance(error, ProviderError):
                    providers_failed.append(error.provider)

                return Err(
                    SearchError(
                        message=f"Flight search failed: {error.message}",
                        providers_failed=providers_failed,
                        original=error,
                    )
                )

    def _apply_limits(self, flights: list[Flight]) -> list[Flight]:
        """Apply max results limit from settings."""
        max_results = self._settings.max_search_results
        if len(flights) <= max_results:
            return flights
        return flights[:max_results]

    def _get_provider_names(self) -> list[str]:
        """Get list of provider names used in search."""
        return [self._provider.provider_name]
