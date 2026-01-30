from __future__ import annotations

from typing import TYPE_CHECKING

from flight_finder.domain.entities.flight import Flight
from flight_finder.domain.errors.domain_errors import ProviderError
from flight_finder.infrastructure.providers.base_provider import BaseFlightProvider
from .api_client import SkyscannerAPIClient
from .response_mapper import SkyscannerResponseMapper

if TYPE_CHECKING:
    from flight_finder.domain.entities.search_criteria import SearchCriteria
    from flight_finder.infrastructure.http.async_http_client import AsyncHTTPClient
    from flight_finder.infrastructure.http.rate_limiter import RateLimiter


class SkyscannerProvider(BaseFlightProvider):
    def __init__(
        self,
        api_key: str,
        http_client: AsyncHTTPClient,
        rate_limiter: RateLimiter,
    ) -> None:
        super().__init__(http_client, rate_limiter)
        self._api_client = SkyscannerAPIClient(api_key, http_client)
        self._mapper = SkyscannerResponseMapper()

    @property
    def provider_name(self) -> str:
        return "skyscanner"

    async def _perform_search(self, criteria: SearchCriteria) -> list[Flight]:
        session = await self._api_client.create_session(criteria)
        results = await self._api_client.poll_results(session.session_token)
        flights = self._mapper.map_api_response(results, criteria.cabin_class)
        flights = self._apply_filters(flights, criteria)
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
