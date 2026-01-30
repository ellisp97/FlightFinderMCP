"""Domain protocols - Interfaces (ports) for infrastructure adapters.

These protocols define the contracts that infrastructure implementations must
fulfill. They follow the Dependency Inversion Principle, allowing the domain
layer to depend on abstractions rather than concrete implementations.
"""

from flight_finder.domain.protocols.cache_strategy import ICacheStrategy
from flight_finder.domain.protocols.flight_provider import IFlightProvider
from flight_finder.domain.protocols.logger import ILogger, LogLevel

__all__ = [
    "IFlightProvider",
    "ICacheStrategy",
    "ILogger",
    "LogLevel",
]
