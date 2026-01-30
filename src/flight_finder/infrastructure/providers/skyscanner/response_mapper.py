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


class SkyscannerResponseMapper:
    def __init__(self) -> None:
        self._logger = logger.bind(component="skyscanner_response_mapper")

    def map_api_response(
        self,
        api_data: dict[str, Any],
        cabin_class: CabinClass,
    ) -> list[Flight]:
        flights: list[Flight] = []

        content = api_data.get("content", {})
        results = content.get("results", {})

        itineraries = results.get("itineraries", {})
        legs = results.get("legs", {})
        places = results.get("places", {})
        carriers = results.get("carriers", {})
        segments_map = results.get("segments", {})

        for itinerary_id, itinerary in itineraries.items():
            try:
                flight = self._map_itinerary(
                    itinerary_id,
                    itinerary,
                    legs,
                    places,
                    carriers,
                    segments_map,
                    cabin_class,
                )
                flights.append(flight)
            except Exception as e:
                self._logger.warning(
                    "failed_to_map_itinerary",
                    itinerary_id=itinerary_id,
                    error=str(e),
                )
                continue

        return flights

    def _map_itinerary(
        self,
        itinerary_id: str,
        itinerary: dict[str, Any],
        legs: dict[str, Any],
        places: dict[str, Any],
        carriers: dict[str, Any],
        segments_map: dict[str, Any],
        cabin_class: CabinClass,
    ) -> Flight:
        pricing_options = itinerary.get("pricingOptions", [])
        if not pricing_options:
            raise ValueError("No pricing options")

        price_data = pricing_options[0].get("price", {})
        raw_amount = price_data.get("amount")
        if raw_amount is None:
            raise ValueError("No price amount")

        amount_str = str(raw_amount)
        if "." not in amount_str and len(amount_str) > 2:
            amount = Decimal(amount_str) / 100
        else:
            amount = Decimal(amount_str)

        price = Price(
            amount=amount,
            currency=price_data.get("unit", "USD"),
        )

        leg_ids = itinerary.get("legIds", [])
        if not leg_ids:
            raise ValueError("No legs in itinerary")

        leg_id = leg_ids[0]
        leg = legs.get(leg_id)
        if not leg:
            raise ValueError(f"Leg not found: {leg_id}")

        segment_ids = leg.get("segmentIds", [])
        if not segment_ids:
            raise ValueError("No segments in leg")

        first_segment_id = segment_ids[0]
        first_segment = segments_map.get(first_segment_id, {})

        carrier_id = first_segment.get("marketingCarrierId") or first_segment.get("operatingCarrierId")
        carrier = carriers.get(str(carrier_id), {}) if carrier_id else {}

        origin_id = leg.get("originPlaceId", "")
        destination_id = leg.get("destinationPlaceId", "")

        departure_time = self._parse_timestamp(leg.get("departureDateTime", ""))
        arrival_time = self._parse_timestamp(leg.get("arrivalDateTime", ""))

        airline_code = carrier.get("iata", "")
        if not airline_code and carrier_id:
            airline_code = str(carrier_id)[:2].upper()
        if not airline_code:
            airline_code = "XX"

        return Flight(
            id=f"skyscanner_{itinerary_id}",
            origin=self._resolve_airport(origin_id, places),
            destination=self._resolve_airport(destination_id, places),
            departure_time=departure_time,
            arrival_time=arrival_time,
            price=price,
            cabin_class=cabin_class,
            stops=leg.get("stopCount", 0),
            airline=airline_code,
            airline_name=carrier.get("name"),
            aircraft_type=first_segment.get("marketingFlightNumber"),
            flight_number=first_segment.get("marketingFlightNumber"),
        )

    def _resolve_airport(self, place_id: str, places: dict[str, Any]) -> Airport:
        place = places.get(place_id, {})
        iata = place.get("iata", "")

        if not iata and place_id:
            iata = place_id[:3].upper() if len(place_id) >= 3 else place_id.upper()

        if not iata or len(iata) != 3 or not iata.isalpha():
            iata = "XXX"

        return Airport(
            code=iata,
            name=place.get("name", "Unknown"),
            city=place.get("name", "Unknown"),
            country=place.get("countryName", "US"),
        )

    def _parse_timestamp(self, timestamp_data: Any) -> datetime:
        if isinstance(timestamp_data, str):
            timestamp_str = timestamp_data.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(timestamp_str)
            except ValueError:
                pass

        if isinstance(timestamp_data, dict):
            year = timestamp_data.get("year", 2026)
            month = timestamp_data.get("month", 1)
            day = timestamp_data.get("day", 1)
            hour = timestamp_data.get("hour", 0)
            minute = timestamp_data.get("minute", 0)
            second = timestamp_data.get("second", 0)
            return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)

        return datetime.now(timezone.utc)
