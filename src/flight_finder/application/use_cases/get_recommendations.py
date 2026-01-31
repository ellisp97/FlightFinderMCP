"""Get flight recommendations use case."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from flight_finder.application.dtos.flight_dtos import FlightRecommendations
from flight_finder.domain.common.result import Ok, Result
from flight_finder.domain.errors.domain_errors import DomainError

if TYPE_CHECKING:
    from flight_finder.domain.entities.flight import Flight

logger = structlog.get_logger()


class RecommendationError(DomainError):
    """Error generating recommendations."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "RECOMMENDATION_ERROR")


class GetRecommendationsUseCase:
    """Use case for generating flight recommendations."""

    def __init__(self) -> None:
        self._logger = logger.bind(use_case="get_recommendations")

    async def execute(
        self,
        flights: list[Flight],
    ) -> Result[FlightRecommendations, RecommendationError]:
        """Generate recommendations from flight results.

        Args:
            flights: List of flights to analyze

        Returns:
            Result containing FlightRecommendations or RecommendationError
        """
        if not flights:
            return Ok(
                FlightRecommendations(
                    cheapest=None,
                    fastest=None,
                    best_value=None,
                )
            )

        cheapest = min(flights, key=lambda f: f.price.amount)

        fastest = min(flights, key=lambda f: f.duration_minutes)

        best_value = self._calculate_best_value(flights)

        self._logger.debug(
            "recommendations_generated",
            flight_count=len(flights),
            cheapest_price=str(cheapest.price.amount) if cheapest else None,
            fastest_duration=fastest.duration_minutes if fastest else None,
        )

        return Ok(
            FlightRecommendations(
                cheapest=cheapest,
                fastest=fastest,
                best_value=best_value,
            )
        )

    def _calculate_best_value(self, flights: list[Flight]) -> Flight | None:
        """Calculate best value flight based on price/duration ratio."""
        if not flights:
            return None

        prices = [float(f.price.amount) for f in flights]
        durations = [float(f.duration_minutes) for f in flights]

        max_price = max(prices) or 1.0
        max_duration = max(durations) or 1.0

        def value_score(flight: Flight) -> float:
            normalized_price = float(flight.price.amount) / max_price
            normalized_duration = float(flight.duration_minutes) / max_duration
            return normalized_price * 0.6 + normalized_duration * 0.4

        return min(flights, key=value_score)
