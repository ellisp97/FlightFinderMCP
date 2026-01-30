from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

from flight_finder.domain.value_objects.cabin_class import CabinClass, CabinClassType
from .constants import (
    API_BASE_URL,
    API_HOST,
    CABIN_CLASS_MAPPING,
    DEFAULT_CURRENCY,
    DEFAULT_LOCALE,
    DEFAULT_MARKET,
    LIVE_SEARCH_CREATE_PATH,
    LIVE_SEARCH_POLL_PATH,
    MAX_POLL_ATTEMPTS,
    POLL_INTERVAL_SECONDS,
    STATUS_COMPLETE,
    STATUS_IN_PROGRESS,
)

if TYPE_CHECKING:
    from flight_finder.domain.entities.search_criteria import SearchCriteria
    from flight_finder.infrastructure.http.async_http_client import AsyncHTTPClient

logger = structlog.get_logger()


@dataclass
class SessionResponse:
    session_token: str
    status: str


class RapidAPISkyscannerClient:
    def __init__(self, api_key: str, http_client: AsyncHTTPClient) -> None:
        self._api_key = api_key
        self._http_client = http_client
        self._logger = logger.bind(component="rapidapi_skyscanner_client")

    def _build_headers(self) -> dict[str, str]:
        return {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": API_HOST,
            "Content-Type": "application/json",
        }

    async def create_session(self, criteria: SearchCriteria) -> SessionResponse:
        url = f"{API_BASE_URL}{LIVE_SEARCH_CREATE_PATH}"
        payload = self._build_session_payload(criteria)
        headers = self._build_headers()

        self._logger.info(
            "creating_session",
            origin=criteria.origin.code,
            destination=criteria.destination.code,
        )

        response = await self._http_client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        return SessionResponse(
            session_token=data.get("sessionToken", ""),
            status=data.get("status", ""),
        )

    async def poll_results(self, session_token: str) -> dict[str, Any]:
        url = f"{API_BASE_URL}{LIVE_SEARCH_POLL_PATH.format(session_token=session_token)}"
        headers = self._build_headers()

        for attempt in range(MAX_POLL_ATTEMPTS):
            if attempt > 0:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)

            self._logger.debug(
                "polling_results",
                attempt=attempt + 1,
                max_attempts=MAX_POLL_ATTEMPTS,
            )

            response = await self._http_client.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            status = data.get("status", "")

            if status == STATUS_COMPLETE:
                self._logger.info("polling_complete", attempt=attempt + 1)
                return data

            if status not in (STATUS_IN_PROGRESS, ""):
                raise ValueError(f"Unexpected status: {status}")

        raise TimeoutError(
            f"Polling timeout: Results not ready after {MAX_POLL_ATTEMPTS} attempts"
        )

    def _build_session_payload(self, criteria: SearchCriteria) -> dict[str, Any]:
        query_legs = [
            {
                "originPlaceId": {"iata": criteria.origin.code},
                "destinationPlaceId": {"iata": criteria.destination.code},
                "date": {
                    "year": criteria.departure_date.year,
                    "month": criteria.departure_date.month,
                    "day": criteria.departure_date.day,
                },
            }
        ]

        if criteria.is_round_trip and criteria.return_date:
            query_legs.append(
                {
                    "originPlaceId": {"iata": criteria.destination.code},
                    "destinationPlaceId": {"iata": criteria.origin.code},
                    "date": {
                        "year": criteria.return_date.year,
                        "month": criteria.return_date.month,
                        "day": criteria.return_date.day,
                    },
                }
            )

        return {
            "query": {
                "market": DEFAULT_MARKET,
                "locale": DEFAULT_LOCALE,
                "currency": DEFAULT_CURRENCY,
                "queryLegs": query_legs,
                "adults": criteria.passengers.adults,
                "childrenAges": [8] * criteria.passengers.children,
                "cabinClass": self._map_cabin_class(criteria.cabin_class),
            }
        }

    @staticmethod
    def _map_cabin_class(cabin_class: CabinClass) -> str:
        mapping = {
            CabinClassType.ECONOMY: CABIN_CLASS_MAPPING["ECONOMY"],
            CabinClassType.PREMIUM_ECONOMY: CABIN_CLASS_MAPPING["PREMIUM_ECONOMY"],
            CabinClassType.BUSINESS: CABIN_CLASS_MAPPING["BUSINESS"],
            CabinClassType.FIRST: CABIN_CLASS_MAPPING["FIRST"],
        }
        return mapping.get(cabin_class.class_type, CABIN_CLASS_MAPPING["ECONOMY"])
