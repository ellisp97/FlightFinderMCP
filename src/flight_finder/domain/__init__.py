"""Domain layer - Core business logic and entities."""

# Common utilities
from flight_finder.domain.common.result import Err, Ok, Result

# Entities
from flight_finder.domain.entities.flight import Flight
from flight_finder.domain.entities.search_criteria import SearchCriteria

# Errors
from flight_finder.domain.errors.domain_errors import (
    CacheError,
    ConfigurationError,
    DomainError,
    ProviderError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)

# Protocols (Interfaces)
from flight_finder.domain.protocols.cache_strategy import ICacheStrategy
from flight_finder.domain.protocols.flight_provider import IFlightProvider
from flight_finder.domain.protocols.logger import ILogger, LogLevel

# Value Objects
from flight_finder.domain.value_objects.airport import Airport
from flight_finder.domain.value_objects.cabin_class import CabinClass, CabinClassType
from flight_finder.domain.value_objects.date_range import DateRange
from flight_finder.domain.value_objects.passenger_config import PassengerConfig
from flight_finder.domain.value_objects.price import Price

__all__ = [
    # Common
    "Result",
    "Ok",
    "Err",
    # Entities
    "Flight",
    "SearchCriteria",
    # Errors
    "DomainError",
    "ValidationError",
    "ProviderError",
    "CacheError",
    "RateLimitError",
    "TimeoutError",
    "ConfigurationError",
    # Protocols
    "IFlightProvider",
    "ICacheStrategy",
    "ILogger",
    "LogLevel",
    # Value Objects
    "Price",
    "Airport",
    "CabinClass",
    "CabinClassType",
    "DateRange",
    "PassengerConfig",
]
