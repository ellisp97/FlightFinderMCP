"""Domain layer - Core business logic and entities."""

from flight_finder.domain.entities.flight import Flight
from flight_finder.domain.entities.search_criteria import SearchCriteria
from flight_finder.domain.value_objects.price import Price
from flight_finder.domain.value_objects.airport import Airport
from flight_finder.domain.value_objects.cabin_class import CabinClass, CabinClassType
from flight_finder.domain.value_objects.date_range import DateRange
from flight_finder.domain.value_objects.passenger_config import PassengerConfig

__all__ = [
    "Flight",
    "SearchCriteria",
    "Price",
    "Airport",
    "CabinClass",
    "CabinClassType",
    "DateRange",
    "PassengerConfig",
]
