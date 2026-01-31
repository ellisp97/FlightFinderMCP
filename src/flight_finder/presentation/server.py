"""MCP Server entry point for Flight Finder.

This module initializes and runs the FastMCP server with all flight search tools.
Entry point defined in pyproject.toml: flight-finder-mcp = "flight_finder.presentation.server:main"
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog
from mcp.server.fastmcp import FastMCP

from flight_finder.application.use_cases.manage_cache import ManageCacheUseCase
from flight_finder.application.use_cases.search_flights import SearchFlightsUseCase
from flight_finder.config import configure_logging, get_settings
from flight_finder.domain.errors.domain_errors import ConfigurationError
from flight_finder.infrastructure.providers import ProviderFactory
from flight_finder.presentation.handlers.cache_handler import CacheHandler
from flight_finder.presentation.handlers.search_handler import SearchHandler

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


def create_server() -> tuple[FastMCP, ProviderFactory]:
    """Create and configure the MCP server with all dependencies.

    Returns:
        Tuple of (FastMCP server, ProviderFactory for cleanup)

    Raises:
        ConfigurationError: If no API keys are configured
    """
    settings = get_settings()

    configure_logging(level=settings.log_level, log_format=settings.log_format)

    log = logger.bind(component="server")
    log.info(
        "initializing_server",
        server_name=settings.server_name,
        version=settings.server_version,
    )

    if not (
        settings.has_skyscanner_key
        or settings.has_searchapi_key
        or settings.has_rapidapi_key
    ):
        log.error("no_api_keys_configured")
        raise ConfigurationError(
            "At least one provider API key must be configured",
            setting="api_keys",
        )

    factory = ProviderFactory()
    aggregator = factory.create_aggregator()
    cache = factory.get_cache()

    provider_count = len(aggregator._providers) if hasattr(aggregator, "_providers") else 0
    log.info(
        "infrastructure_initialized",
        provider_count=provider_count,
        cache_max_size=settings.cache_max_size,
    )

    search_use_case = SearchFlightsUseCase(provider=aggregator, settings=settings)
    cache_use_case = ManageCacheUseCase(cache=cache)

    search_handler = SearchHandler(search_use_case)
    cache_handler = CacheHandler(cache_use_case)

    mcp = FastMCP(
        name=settings.server_name,
    )

    @mcp.tool()
    async def search_flights(
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
        """Search for flights between airports.

        Args:
            origin: Origin airport IATA code (e.g., 'JFK', 'LAX', 'LHR')
            destination: Destination airport IATA code (e.g., 'JFK', 'LAX', 'LHR')
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Optional return date for round-trip in YYYY-MM-DD format
            adults: Number of adult passengers (1-9, default: 1)
            children: Number of child passengers 2-17 years (0-8, default: 0)
            infants: Number of infant passengers under 2 (0-4, default: 0)
            cabin_class: Cabin class - economy, premium_economy, business, or first
            max_stops: Maximum number of stops (0-5, None for any)
            non_stop_only: If true, only return non-stop flights

        Returns:
            JSON string with flight results including booking_url for each flight
        """
        return await search_handler.handle_search(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            adults=adults,
            children=children,
            infants=infants,
            cabin_class=cabin_class,
            max_stops=max_stops,
            non_stop_only=non_stop_only,
        )

    @mcp.tool()
    async def get_cache_stats() -> str:
        """Get flight search cache statistics.

        Returns cache size, hit/miss counts, and hit rate percentage.

        Returns:
            JSON string with cache statistics
        """
        return await cache_handler.handle_get_stats()

    @mcp.tool()
    async def clear_cache() -> str:
        """Clear all cached flight search results.

        This removes all cached search results, forcing fresh API calls
        for subsequent searches.

        Returns:
            JSON string confirming cache was cleared
        """
        return await cache_handler.handle_clear()

    log.info("server_ready", tool_count=3)

    return mcp, factory


def main() -> None:
    """Main entry point for the MCP server."""
    mcp, factory = create_server()

    async def cleanup() -> None:
        """Cleanup resources on shutdown."""
        await factory.close()

    try:
        mcp.run()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            asyncio.run(cleanup())
        except Exception:
            pass


if __name__ == "__main__":
    main()
