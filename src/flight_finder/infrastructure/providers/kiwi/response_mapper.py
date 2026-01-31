from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog

from flight_finder.domain.entities.flight import Flight
from flight_finder.domain.value_objects.airport import Airport
from flight_finder.domain.value_objects.cabin_class import CabinClass
from flight_finder.domain.value_objects.price import Price

logger = structlog.get_logger()


class KiwiResponseMapper:
    def __init__(self) -> None:
        self._logger = logger.bind(component="kiwi_response_mapper")

    def map_api_response(
        self,
        api_data: dict[str, Any],
        cabin_class: CabinClass,
    ) -> list[Flight]:
        flights: list[Flight] = []

        data = api_data.get("data", {})
        itineraries = data.get("itineraries", [])

        for itinerary in itineraries:
            try:
                flight = self._map_itinerary(itinerary, cabin_class)
                if flight:
                    flights.append(flight)
            except Exception as e:
                itinerary_id = itinerary.get("id", "unknown")
                self._logger.warning(
                    "failed_to_map_itinerary",
                    itinerary_id=itinerary_id,
                    error=str(e),
                )
                continue

        return flights

    def _map_itinerary(
        self,
        itinerary: dict[str, Any],
        cabin_class: CabinClass,
    ) -> Flight | None:
        itinerary_id = itinerary.get("id", "")
        itinerary_type = itinerary.get("__typename", "")

        price_data = itinerary.get("price", {})
        raw_amount = price_data.get("amount")
        if raw_amount is None:
            raise ValueError("No price amount")

        amount = Decimal(str(raw_amount))
        price = Price(amount=amount, currency="USD")

        # Handle both one-way (sector) and round-trip (outbound/inbound) responses
        if itinerary_type == "ItineraryReturn" or "outbound" in itinerary:
            sector_segments = self._get_outbound_segments(itinerary)
        else:
            # One-way: use sector
            sector = itinerary.get("sector", {})
            sector_segments = sector.get("sectorSegments", [])

        if not sector_segments:
            raise ValueError("No sector segments")

        first_segment_data = sector_segments[0].get("segment", {})
        last_segment_data = sector_segments[-1].get("segment", {})

        source = first_segment_data.get("source", {})
        destination = last_segment_data.get("destination", {})

        origin_airport = self._extract_airport(source)
        destination_airport = self._extract_airport(destination)

        departure_time = self._parse_timestamp(source)
        arrival_time = self._parse_timestamp(destination)

        carrier = first_segment_data.get("carrier", {})
        airline_code = carrier.get("code", "XX")
        airline_name = carrier.get("name")
        flight_number = first_segment_data.get("code")

        stops = len(sector_segments) - 1

        booking_url = self._extract_booking_url(itinerary)

        return Flight(
            id=f"kiwi_{itinerary_id}",
            origin=origin_airport,
            destination=destination_airport,
            departure_time=departure_time,
            arrival_time=arrival_time,
            price=price,
            cabin_class=cabin_class,
            stops=stops,
            airline=airline_code if airline_code else "XX",
            airline_name=airline_name,
            flight_number=flight_number,
            booking_url=booking_url,
        )

    def _get_outbound_segments(self, itinerary: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract sector segments from outbound (round-trip response)."""
        outbound = itinerary.get("outbound", {})
        return outbound.get("sectorSegments", [])

    def _extract_airport(self, location_data: dict[str, Any]) -> Airport:
        station = location_data.get("station", {})
        code = station.get("code", "XXX")
        name = station.get("name", "Unknown")

        city_data = station.get("city", {})
        city = city_data.get("name", "Unknown")

        if not code or len(code) != 3 or not code.isalpha():
            code = "XXX"

        return Airport(
            code=code.upper(),
            name=name,
            city=city,
            country=None,
        )

    def _parse_timestamp(self, location_data: dict[str, Any]) -> datetime:
        utc_time = location_data.get("utcTimeIso")
        if utc_time:
            try:
                timestamp_str = utc_time.replace("Z", "+00:00")
                return datetime.fromisoformat(timestamp_str)
            except ValueError:
                pass

        local_time = location_data.get("localTime")
        if local_time:
            try:
                dt = datetime.fromisoformat(local_time)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        return datetime.now(timezone.utc)

    def _extract_booking_url(self, itinerary: dict[str, Any]) -> str | None:
        booking_options = itinerary.get("bookingOptions", {})
        edges = booking_options.get("edges", [])

        if edges:
            first_option = edges[0].get("node", {})
            return first_option.get("bookingUrl")

        return None
