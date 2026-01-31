from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from flight_finder.domain.value_objects.cabin_class import CabinClass, CabinClassType

from .constants import (
    API_BASE_URL,
    API_SEARCH_ONEWAY_PATH,
    API_SEARCH_RETURN_PATH,
    CABIN_CLASS_BUSINESS,
    CABIN_CLASS_ECONOMY,
    CABIN_CLASS_FIRST,
    CABIN_CLASS_PREMIUM_ECONOMY,
    DEFAULT_CURRENCY,
    DEFAULT_LIMIT,
    DEFAULT_LOCALE,
    DEFAULT_MARKET,
    RAPIDAPI_HOST,
    SORT_PRICE,
)

if TYPE_CHECKING:
    from flight_finder.domain.entities.search_criteria import SearchCriteria
    from flight_finder.infrastructure.http.async_http_client import AsyncHTTPClient

logger = structlog.get_logger()


class KiwiAPIClient:
    def __init__(self, api_key: str, http_client: AsyncHTTPClient) -> None:
        self._api_key = api_key
        self._http_client = http_client
        self._logger = logger.bind(component="kiwi_api_client")

    async def search_flights(self, criteria: SearchCriteria) -> dict[str, Any]:
        if criteria.is_round_trip:
            return await self._search_return(criteria)
        return await self._search_oneway(criteria)

    async def _search_oneway(self, criteria: SearchCriteria) -> dict[str, Any]:
        url = f"{API_BASE_URL}{API_SEARCH_ONEWAY_PATH}"
        params = self._build_oneway_params(criteria)
        headers = self._get_headers()

        self._logger.info(
            "searching_oneway_flights",
            origin=criteria.origin.code,
            destination=criteria.destination.code,
            departure_date=str(criteria.departure_date),
        )

        response = await self._http_client.get(url, params=params, headers=headers)
        response.raise_for_status()

        data = response.json()

        if not data.get("status"):
            raise ValueError(f"API error: {data.get('message', 'Unknown error')}")

        return data

    async def _search_return(self, criteria: SearchCriteria) -> dict[str, Any]:
        url = f"{API_BASE_URL}{API_SEARCH_RETURN_PATH}"
        params = self._build_return_params(criteria)
        headers = self._get_headers()

        self._logger.info(
            "searching_return_flights",
            origin=criteria.origin.code,
            destination=criteria.destination.code,
            departure_date=str(criteria.departure_date),
            return_date=str(criteria.return_date),
        )

        response = await self._http_client.get(url, params=params, headers=headers)
        response.raise_for_status()

        data = response.json()

        if not data.get("status"):
            raise ValueError(f"API error: {data.get('message', 'Unknown error')}")

        return data

    def _get_headers(self) -> dict[str, str]:
        return {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": RAPIDAPI_HOST,
        }

    def _build_oneway_params(self, criteria: SearchCriteria) -> dict[str, Any]:
        params: dict[str, Any] = {
            "originSkyId": criteria.origin.code,
            "destinationSkyId": criteria.destination.code,
            "departureDate": criteria.departure_date.isoformat(),
            "adults": criteria.passengers.adults,
            "currency": DEFAULT_CURRENCY,
            "locale": DEFAULT_LOCALE,
            "market": DEFAULT_MARKET,
            "limit": DEFAULT_LIMIT,
            "sort": SORT_PRICE,
        }

        if criteria.passengers.children > 0:
            params["children"] = criteria.passengers.children

        if criteria.passengers.infants > 0:
            params["infants"] = criteria.passengers.infants

        cabin_class = self._map_cabin_class(criteria.cabin_class)
        if cabin_class != CABIN_CLASS_ECONOMY:
            params["cabinClass"] = cabin_class

        if criteria.non_stop_only:
            params["stops"] = 0
        elif criteria.max_stops is not None:
            params["stops"] = min(criteria.max_stops, 2)

        return params

    def _build_return_params(self, criteria: SearchCriteria) -> dict[str, Any]:
        params = self._build_oneway_params(criteria)

        if criteria.return_date:
            params["returnDate"] = criteria.return_date.isoformat()

        return params

    @staticmethod
    def _map_cabin_class(cabin_class: CabinClass) -> str:
        mapping = {
            CabinClassType.ECONOMY: CABIN_CLASS_ECONOMY,
            CabinClassType.PREMIUM_ECONOMY: CABIN_CLASS_PREMIUM_ECONOMY,
            CabinClassType.BUSINESS: CABIN_CLASS_BUSINESS,
            CabinClassType.FIRST: CABIN_CLASS_FIRST,
        }
        return mapping.get(cabin_class.class_type, CABIN_CLASS_ECONOMY)
