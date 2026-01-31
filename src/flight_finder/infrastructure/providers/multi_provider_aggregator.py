from __future__ import annotations

import asyncio
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import structlog

from flight_finder.domain.common.result import Err, Ok, Result
from flight_finder.domain.errors.domain_errors import ProviderError

if TYPE_CHECKING:
    from flight_finder.domain.entities.flight import Flight
    from flight_finder.domain.entities.search_criteria import SearchCriteria
    from flight_finder.domain.protocols.flight_provider import IFlightProvider

logger = structlog.get_logger()


class MultiProviderAggregator:
    """Aggregates flight search results from multiple providers.

    Handles parallel execution, partial failures, and deduplication.
    """

    def __init__(self, providers: list[IFlightProvider]) -> None:
        self._providers = providers
        self._logger = logger.bind(component="multi_provider_aggregator")

    @property
    def provider_name(self) -> str:
        """Return aggregator name."""
        return "aggregator"

    def get_provider_names(self) -> list[str]:
        """Get list of all provider names in this aggregator."""
        return [p.provider_name for p in self._providers]

    async def search(
        self,
        criteria: SearchCriteria,
    ) -> Result[list[Flight], ProviderError]:
        if not self._providers:
            return Err(
                ProviderError(
                    provider="aggregator",
                    message="No providers available",
                )
            )

        self._logger.info(
            "multi_search_started",
            provider_count=len(self._providers),
            origin=criteria.origin.code,
            destination=criteria.destination.code,
        )

        search_tasks = [provider.search(criteria) for provider in self._providers]

        results = await asyncio.gather(*search_tasks, return_exceptions=False)

        all_flights: list[Flight] = []
        successful_providers: list[str] = []
        failed_providers: list[str] = []

        for provider, result in zip(self._providers, results):
            match result:
                case Ok(flights):
                    all_flights.extend(flights)
                    successful_providers.append(provider.provider_name)
                    self._logger.info(
                        "provider_success",
                        provider=provider.provider_name,
                        flight_count=len(flights),
                    )
                case Err(error):
                    failed_providers.append(provider.provider_name)
                    self._logger.warning(
                        "provider_failed",
                        provider=provider.provider_name,
                        error=str(error),
                    )

        if not all_flights:
            return Err(
                ProviderError(
                    provider="aggregator",
                    message=f"All providers failed: {', '.join(failed_providers)}",
                )
            )

        unique_flights = self._deduplicate(all_flights)

        unique_flights.sort(key=lambda f: f.price.amount)

        self._logger.info(
            "multi_search_completed",
            total_flights=len(all_flights),
            unique_flights=len(unique_flights),
            successful_providers=len(successful_providers),
            failed_providers=len(failed_providers),
        )

        return Ok(unique_flights)

    def _deduplicate(self, flights: list[Flight]) -> list[Flight]:
        if len(flights) <= 1:
            return flights

        unique: list[Flight] = []
        seen_signatures: set[str] = set()

        for flight in flights:
            signature = self._generate_signature(flight)

            if signature in seen_signatures:
                if self._is_duplicate(flight, unique):
                    self._logger.debug(
                        "duplicate_flight_skipped",
                        flight_id=flight.id,
                        signature=signature,
                    )
                    continue

            unique.append(flight)
            seen_signatures.add(signature)

        removed_count = len(flights) - len(unique)
        if removed_count > 0:
            self._logger.info(
                "deduplication_complete",
                original=len(flights),
                unique=len(unique),
                removed=removed_count,
            )

        return unique

    @staticmethod
    def _generate_signature(flight: Flight) -> str:
        dep_rounded = flight.departure_time.replace(
            minute=(flight.departure_time.minute // 30) * 30,
            second=0,
            microsecond=0,
        )
        arr_rounded = flight.arrival_time.replace(
            minute=(flight.arrival_time.minute // 30) * 30,
            second=0,
            microsecond=0,
        )

        return (
            f"{flight.origin.code}-{flight.destination.code}-"
            f"{flight.airline}-{dep_rounded.isoformat()}-{arr_rounded.isoformat()}"
        )

    def _is_duplicate(self, flight: Flight, existing: list[Flight]) -> bool:
        for existing_flight in existing:
            if self._are_similar(flight, existing_flight):
                return True
        return False

    @staticmethod
    def _are_similar(f1: Flight, f2: Flight) -> bool:
        if f1.origin.code != f2.origin.code:
            return False
        if f1.destination.code != f2.destination.code:
            return False

        if f1.airline != f2.airline:
            return False

        time_threshold = timedelta(minutes=30)
        if abs(f1.departure_time - f2.departure_time) > time_threshold:
            return False
        if abs(f1.arrival_time - f2.arrival_time) > time_threshold:
            return False

        price_diff = abs(f1.price.amount - f2.price.amount)
        avg_price = (f1.price.amount + f2.price.amount) / 2
        price_threshold = avg_price * Decimal("0.05")

        if price_diff > price_threshold:
            return False

        return True
