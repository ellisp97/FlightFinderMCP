from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import structlog

from flight_finder.domain.entities.flight import Flight
from flight_finder.domain.value_objects.price import Price
from .time_parser import parse_airport_datetime, parse_flight_time

if TYPE_CHECKING:
    from flight_finder.domain.entities.search_criteria import SearchCriteria

logger = structlog.get_logger()


class SearchAPIResponseMapper:
    def __init__(self) -> None:
        self._logger = logger.bind(component="searchapi_response_mapper")

    def map_response(
        self,
        api_data: dict[str, Any],
        criteria: SearchCriteria,
    ) -> list[Flight]:
        flights: list[Flight] = []

        for flight_data in api_data.get("best_flights", []):
            try:
                flight = self._map_flight(flight_data, criteria)
                flights.append(flight)
            except Exception as e:
                self._logger.warning(
                    "failed_to_map_flight",
                    flight_id=flight_data.get("id"),
                    error=str(e),
                )
                continue

        for flight_data in api_data.get("other_flights", [])[:10]:
            try:
                flight = self._map_flight(flight_data, criteria)
                flights.append(flight)
            except Exception as e:
                self._logger.warning(
                    "failed_to_map_other_flight",
                    flight_id=flight_data.get("id"),
                    error=str(e),
                )
                continue

        return flights

    def _map_flight(
        self,
        flight_data: dict[str, Any],
        criteria: SearchCriteria,
    ) -> Flight:
        flight_segments = flight_data.get("flights", [])
        if not flight_segments:
            raise ValueError("No flight segments in data")

        first_segment = flight_segments[0]
        last_segment = flight_segments[-1]

        # Parse departure from nested airport structure
        departure_airport = first_segment.get("departure_airport", {})
        if departure_airport and "date" in departure_airport:
            departure_time = parse_airport_datetime(departure_airport)
        else:
            departure_time = parse_flight_time(
                first_segment.get("departure_time", "12:00 PM"),
                criteria.departure_date,
            )

        # Parse arrival from nested airport structure
        arrival_airport = last_segment.get("arrival_airport", {})
        if arrival_airport and "date" in arrival_airport:
            arrival_time = parse_airport_datetime(arrival_airport)
        else:
            arrival_time = parse_flight_time(
                last_segment.get("arrival_time", "12:00 PM"),
                criteria.departure_date,
                previous_time=departure_time,
            )

        total_stops = self._calculate_stops(flight_segments)

        price_value = flight_data.get("price", 0)
        price_amount = Decimal(str(price_value))

        airline_name = first_segment.get("airline", "Unknown")
        airline_code = self._extract_airline_code(first_segment, airline_name)

        flight_id = flight_data.get("id", f"gf_{hash(str(flight_data))}")

        booking_url = self._generate_booking_url(flight_data, criteria)

        return Flight(
            id=f"google_{flight_id}",
            origin=criteria.origin,
            destination=criteria.destination,
            departure_time=departure_time,
            arrival_time=arrival_time,
            price=Price(amount=price_amount, currency="USD"),
            cabin_class=criteria.cabin_class,
            stops=total_stops,
            airline=airline_code,
            airline_name=airline_name,
            aircraft_type=first_segment.get("aircraft"),
            flight_number=first_segment.get("flight_number"),
            booking_url=booking_url,
        )

    def _calculate_stops(self, segments: list[dict[str, Any]]) -> int:
        total_stops = 0
        for segment in segments:
            segment_stops = segment.get("stops", 0)
            total_stops += segment_stops

        if len(segments) > 1:
            total_stops += len(segments) - 1

        return total_stops

    def _extract_airline_code(
        self,
        segment: dict[str, Any],
        airline_name: str,
    ) -> str:
        airline_code = segment.get("airline_code", "")
        if airline_code and len(airline_code) >= 2:
            return airline_code[:3].upper()

        flight_number = segment.get("flight_number", "")
        if flight_number and len(flight_number) >= 2:
            code = "".join(c for c in flight_number[:3] if c.isalpha())
            if len(code) >= 2:
                return code.upper()

        if airline_name and len(airline_name) >= 2:
            return airline_name[:2].upper()

        return "XX"

    def _generate_booking_url(
        self,
        flight_data: dict[str, Any],
        criteria: SearchCriteria,
    ) -> str | None:
        """Generate a Google Flights booking/search URL."""
        flight_segments = flight_data.get("flights", [])
        if not flight_segments:
            return None

        first_segment = flight_segments[0]
        departure_airport = first_segment.get("departure_airport", {})
        last_segment = flight_segments[-1]
        arrival_airport = last_segment.get("arrival_airport", {})

        origin = departure_airport.get("id", criteria.origin.code)
        destination = arrival_airport.get("id", criteria.destination.code)
        date_str = criteria.departure_date.strftime("%Y-%m-%d")

        # Build Google Flights URL
        url = f"https://www.google.com/travel/flights?q=flights%20from%20{origin}%20to%20{destination}%20on%20{date_str}"

        return url
