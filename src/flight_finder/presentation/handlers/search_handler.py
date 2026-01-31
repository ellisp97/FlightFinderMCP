"""Search flight handler for MCP tools."""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

import structlog

from flight_finder.domain.common.result import Err, Ok
from flight_finder.presentation.schemas.converters import (
    flight_to_dto,
    to_search_criteria_from_params,
)
from flight_finder.presentation.utils.error_formatter import format_error_response

if TYPE_CHECKING:
    from flight_finder.application.use_cases.search_flights import SearchFlightsUseCase

logger = structlog.get_logger()


class SearchHandler:
    """Handler for flight search operations."""

    def __init__(self, search_use_case: SearchFlightsUseCase) -> None:
        self._search_use_case = search_use_case
        self._logger = logger.bind(handler="search")

    async def handle_search(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str | None = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "economy",
        max_stops: int | None = None,
        non_stop_only: bool = False,
    ) -> str:
        """Handle search_flights tool invocation.

        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            departure_date: Departure date (YYYY-MM-DD)
            return_date: Optional return date (YYYY-MM-DD)
            adults: Number of adult passengers
            children: Number of child passengers
            infants: Number of infant passengers
            cabin_class: Cabin class
            max_stops: Maximum stops
            non_stop_only: Only non-stop flights

        Returns:
            JSON string with search results or error
        """
        try:
            parsed_departure = date.fromisoformat(departure_date)
            parsed_return = date.fromisoformat(return_date) if return_date else None

            criteria = to_search_criteria_from_params(
                origin=origin,
                destination=destination,
                departure_date=parsed_departure,
                return_date=parsed_return,
                adults=adults,
                children=children,
                infants=infants,
                cabin_class=cabin_class,
                max_stops=max_stops,
                non_stop_only=non_stop_only,
            )

            result = await self._search_use_case.execute(criteria)

            match result:
                case Ok(search_result):
                    flights_dto = [flight_to_dto(f) for f in search_result.flights]

                    min_price = (
                        min(f.price.amount for f in search_result.flights)
                        if search_result.flights
                        else None
                    )
                    max_price = (
                        max(f.price.amount for f in search_result.flights)
                        if search_result.flights
                        else None
                    )

                    return json.dumps(
                        {
                            "success": True,
                            "summary": {
                                "total_flights": search_result.total_results,
                                "search_duration_ms": round(
                                    search_result.search_duration_ms, 2
                                ),
                                "providers_used": search_result.providers_used,
                                "cache_hit": search_result.cache_hit,
                                "price_range": {
                                    "min": str(min_price) if min_price else None,
                                    "max": str(max_price) if max_price else None,
                                },
                            },
                            "flights": [f.model_dump() for f in flights_dto],
                        },
                        indent=2,
                        default=str,
                    )

                case Err(error):
                    return format_error_response(error)

        except ValueError as e:
            self._logger.warning("validation_error", error=str(e))
            return json.dumps(
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": str(e),
                    },
                },
                indent=2,
            )
        except Exception as e:
            self._logger.exception("search_handler_error", error=str(e))
            return format_error_response(e)
