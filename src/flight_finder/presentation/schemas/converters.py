"""Converters between presentation and domain models."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from flight_finder.domain.entities.search_criteria import SearchCriteria
from flight_finder.domain.value_objects.airport import Airport
from flight_finder.domain.value_objects.cabin_class import CabinClass, CabinClassType
from flight_finder.domain.value_objects.passenger_config import PassengerConfig
from flight_finder.presentation.schemas.requests import SearchFlightsRequest
from flight_finder.presentation.schemas.responses import FlightDTO, PriceDTO

if TYPE_CHECKING:
    from flight_finder.domain.entities.flight import Flight


def to_search_criteria(request: SearchFlightsRequest) -> SearchCriteria:
    """Convert SearchFlightsRequest to domain SearchCriteria.

    Args:
        request: Presentation layer request

    Returns:
        Domain SearchCriteria entity
    """
    cabin_class_type = _parse_cabin_class(request.cabin_class)

    return SearchCriteria(
        origin=Airport(code=request.origin),
        destination=Airport(code=request.destination),
        departure_date=request.departure_date,
        return_date=request.return_date,
        passengers=PassengerConfig(
            adults=request.passengers.adults,
            children=request.passengers.children,
            infants=request.passengers.infants,
        ),
        cabin_class=CabinClass(class_type=cabin_class_type),
        max_stops=request.max_stops,
        non_stop_only=request.non_stop_only,
    )


def to_search_criteria_from_params(
    origin: str,
    destination: str,
    departure_date: date,
    return_date: date | None = None,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    cabin_class: str = "economy",
    max_stops: int | None = None,
    non_stop_only: bool = False,
) -> SearchCriteria:
    """Convert raw parameters to domain SearchCriteria.

    Args:
        origin: Origin airport IATA code
        destination: Destination airport IATA code
        departure_date: Departure date
        return_date: Optional return date
        adults: Number of adult passengers
        children: Number of child passengers
        infants: Number of infant passengers
        cabin_class: Cabin class string
        max_stops: Maximum stops
        non_stop_only: Non-stop only flag

    Returns:
        Domain SearchCriteria entity
    """
    cabin_class_type = _parse_cabin_class(cabin_class)

    return SearchCriteria(
        origin=Airport(code=origin.upper()),
        destination=Airport(code=destination.upper()),
        departure_date=departure_date,
        return_date=return_date,
        passengers=PassengerConfig(
            adults=adults,
            children=children,
            infants=infants,
        ),
        cabin_class=CabinClass(class_type=cabin_class_type),
        max_stops=max_stops,
        non_stop_only=non_stop_only,
    )


def flight_to_dto(flight: Flight) -> FlightDTO:
    """Convert domain Flight to FlightDTO.

    Args:
        flight: Domain flight entity

    Returns:
        FlightDTO for JSON serialization
    """
    return FlightDTO(
        id=flight.id,
        origin=flight.origin.code,
        destination=flight.destination.code,
        departure_time=flight.departure_time.isoformat(),
        arrival_time=flight.arrival_time.isoformat(),
        duration_minutes=flight.duration_minutes,
        price=PriceDTO(
            amount=str(flight.price.amount),
            currency=flight.price.currency,
        ),
        airline=flight.airline,
        airline_name=flight.airline_name,
        flight_number=flight.flight_number,
        cabin_class=flight.cabin_class.class_type.value,
        stops=flight.stops,
        is_non_stop=flight.is_non_stop,
        booking_url=flight.booking_url,
    )


def flights_to_dtos(flights: list[Flight]) -> list[FlightDTO]:
    """Convert list of domain Flights to FlightDTOs.

    Args:
        flights: List of domain flight entities

    Returns:
        List of FlightDTOs for JSON serialization
    """
    return [flight_to_dto(f) for f in flights]


def _parse_cabin_class(cabin_class: str) -> CabinClassType:
    """Parse cabin class string to CabinClassType enum."""
    normalized = cabin_class.lower().strip()

    mapping = {
        "economy": CabinClassType.ECONOMY,
        "premium_economy": CabinClassType.PREMIUM_ECONOMY,
        "premium economy": CabinClassType.PREMIUM_ECONOMY,
        "premiumeconomy": CabinClassType.PREMIUM_ECONOMY,
        "business": CabinClassType.BUSINESS,
        "first": CabinClassType.FIRST,
    }

    return mapping.get(normalized, CabinClassType.ECONOMY)
