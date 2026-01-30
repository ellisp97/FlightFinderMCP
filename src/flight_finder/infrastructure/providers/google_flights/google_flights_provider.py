from __future__ import annotations

from typing import TYPE_CHECKING

from flight_finder.domain.entities.flight import Flight
from flight_finder.domain.errors.domain_errors import ProviderError
from flight_finder.infrastructure.providers.base_provider import BaseFlightProvider
from .searchapi_client import SearchAPIClient
from .response_mapper import SearchAPIResponseMapper

if TYPE_CHECKING:
    from flight_finder.domain.entities.search_criteria import SearchCriteria
    from flight_finder.infrastructure.http.async_http_client import AsyncHTTPClient
    from flight_finder.infrastructure.http.rate_limiter import RateLimiter


class GoogleFlightsProvider(BaseFlightProvider):
    """Google Flights provider using SearchAPI.io integration.

    Flow:
    1. Make single HTTP request to SearchAPI
    2. Parse response (best_flights + other_flights)
    3. Map to Flight entities
    4. Apply filters
    5. Return flights
    """

    def __init__(
        self,
        api_key: str,
        http_client: AsyncHTTPClient,
        rate_limiter: RateLimiter,
    ) -> None:
        super().__init__(http_client, rate_limiter)
        self._api_client = SearchAPIClient(api_key, http_client)
        self._mapper = SearchAPIResponseMapper()

    @property
    def provider_name(self) -> str:
        return "google_flights"

    async def _perform_search(self, criteria: SearchCriteria) -> list[Flight]:
        self._logger.info(
            "search_started",
            origin=criteria.origin.code,
            destination=criteria.destination.code,
        )

        api_response = await self._api_client.search_flights(criteria)
        flights = self._mapper.map_response(api_response, criteria)
        flights = self._apply_filters(flights, criteria)

        self._logger.info("search_completed", flight_count=len(flights))

        return flights

    def _map_error(self, error: Exception) -> ProviderError:
        return self._map_http_error(error)

    def _apply_filters(
        self,
        flights: list[Flight],
        criteria: SearchCriteria,
    ) -> list[Flight]:
        filtered = flights

        if criteria.non_stop_only:
            filtered = [f for f in filtered if f.is_non_stop]
        elif criteria.max_stops is not None:
            filtered = [f for f in filtered if f.stops <= criteria.max_stops]

        filtered.sort(key=lambda f: f.price.amount)

        return filtered
