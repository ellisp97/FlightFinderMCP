"""Application use cases."""

from flight_finder.application.use_cases.filter_flights import (
    FilterError,
    FilterFlightsUseCase,
)
from flight_finder.application.use_cases.get_recommendations import (
    GetRecommendationsUseCase,
    RecommendationError,
)
from flight_finder.application.use_cases.manage_cache import (
    CacheManagementError,
    ManageCacheUseCase,
)
from flight_finder.application.use_cases.search_flights import (
    SearchError,
    SearchFlightsUseCase,
)

__all__ = [
    "CacheManagementError",
    "FilterError",
    "FilterFlightsUseCase",
    "GetRecommendationsUseCase",
    "ManageCacheUseCase",
    "RecommendationError",
    "SearchError",
    "SearchFlightsUseCase",
]
