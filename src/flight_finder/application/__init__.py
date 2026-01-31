"""Application layer - Use cases and DTOs."""

from flight_finder.application.dtos import (
    CacheStats,
    FlightFilters,
    FlightRecommendations,
    FlightSearchResult,
    ProviderHealth,
    SortOption,
)
from flight_finder.application.use_cases import (
    CacheManagementError,
    FilterError,
    FilterFlightsUseCase,
    GetRecommendationsUseCase,
    ManageCacheUseCase,
    RecommendationError,
    SearchError,
    SearchFlightsUseCase,
)

__all__ = [
    # DTOs
    "CacheStats",
    "FlightFilters",
    "FlightRecommendations",
    "FlightSearchResult",
    "ProviderHealth",
    "SortOption",
    # Use Cases
    "CacheManagementError",
    "FilterError",
    "FilterFlightsUseCase",
    "GetRecommendationsUseCase",
    "ManageCacheUseCase",
    "RecommendationError",
    "SearchError",
    "SearchFlightsUseCase",
]
