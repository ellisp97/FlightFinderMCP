"""Flight provider protocol (interface).

Defines the contract for flight data providers using the Strategy pattern.
Implementations can include Amadeus API, Google Flights scraper, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from flight_finder.domain.common.result import Result
    from flight_finder.domain.entities.flight import Flight
    from flight_finder.domain.entities.search_criteria import SearchCriteria
    from flight_finder.domain.errors.domain_errors import ProviderError


@runtime_checkable
class IFlightProvider(Protocol):
    """Protocol for flight data providers (Strategy pattern).

    This protocol defines the interface that all flight providers must implement.
    Providers are responsible for searching flight data from their respective
    sources (APIs, web scraping, etc.).

    Implementations should:
    - Return Results instead of raising exceptions for expected failures
    - Be async to support concurrent searches
    - Include proper rate limiting and retry logic
    - Cache responses where appropriate

    Example implementation:
        class AmadeusProvider:
            @property
            def provider_name(self) -> str:
                return "amadeus"

            async def search(
                self,
                criteria: SearchCriteria
            ) -> Result[list[Flight], ProviderError]:
                # Implementation here
                ...

            async def is_available(self) -> bool:
                # Check API health
                ...
    """

    @property
    def provider_name(self) -> str:
        """Get the unique provider name for logging/metrics.

        Returns:
            A lowercase identifier (e.g., "amadeus", "google_flights")
        """
        ...

    async def search(
        self,
        criteria: SearchCriteria,
    ) -> Result[list[Flight], ProviderError]:
        """Search for flights matching the given criteria.

        Args:
            criteria: The search criteria specifying route, dates, passengers, etc.

        Returns:
            Result containing either:
            - Ok[list[Flight]]: List of matching flights (may be empty)
            - Err[ProviderError]: Error details if search failed
        """
        ...

    async def is_available(self) -> bool:
        """Check if the provider is currently available.

        This can be used for health checks and to skip unavailable providers
        when searching multiple providers in parallel.

        Returns:
            True if the provider is available and ready to serve requests
        """
        ...
