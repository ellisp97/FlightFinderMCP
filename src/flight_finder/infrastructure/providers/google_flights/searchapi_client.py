from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from flight_finder.domain.value_objects.cabin_class import CabinClass
from .constants import CABIN_CLASS_MAPPING, SEARCHAPI_BASE_URL, SEARCHAPI_ENGINE

if TYPE_CHECKING:
    from flight_finder.domain.entities.search_criteria import SearchCriteria
    from flight_finder.infrastructure.http.async_http_client import AsyncHTTPClient

logger = structlog.get_logger()


class SearchAPIClient:
    def __init__(self, api_key: str, http_client: AsyncHTTPClient) -> None:
        self._api_key = api_key
        self._http_client = http_client
        self._logger = logger.bind(component="searchapi_client")

    async def search_flights(self, criteria: SearchCriteria) -> dict[str, Any]:
        """Search flights via SearchAPI.

        Returns API response dict with 'best_flights' and 'other_flights'.
        Raises httpx.HTTPStatusError on HTTP errors.
        """
        params = self._build_params(criteria)

        self._logger.info(
            "searchapi_request",
            origin=criteria.origin.code,
            destination=criteria.destination.code,
        )

        response = await self._http_client.get(SEARCHAPI_BASE_URL, params=params)
        response.raise_for_status()

        data = response.json()

        if "error" in data:
            raise ValueError(f"SearchAPI error: {data['error']}")

        self._logger.info(
            "searchapi_success",
            best_flights_count=len(data.get("best_flights", [])),
            other_flights_count=len(data.get("other_flights", [])),
        )

        return data

    def _build_params(self, criteria: SearchCriteria) -> dict[str, Any]:
        params: dict[str, Any] = {
            "api_key": self._api_key,
            "engine": SEARCHAPI_ENGINE,
            "departure_id": criteria.origin.code,
            "arrival_id": criteria.destination.code,
            "outbound_date": criteria.departure_date.isoformat(),
            "adults": criteria.passengers.adults,
            "children": criteria.passengers.children,
            "infants_in_seat": criteria.passengers.infants,
            "cabin_class": self._map_cabin_class(criteria.cabin_class),
            "currency": "USD",
            "locale": "en_US",
        }

        if criteria.is_round_trip and criteria.return_date:
            params["flight_type"] = "round_trip"
            params["return_date"] = criteria.return_date.isoformat()
        else:
            params["flight_type"] = "one_way"

        return params

    @staticmethod
    def _map_cabin_class(cabin_class: CabinClass) -> str:
        return CABIN_CLASS_MAPPING.get(cabin_class.class_type, "economy")
