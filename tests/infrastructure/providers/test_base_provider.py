from __future__ import annotations

import sys
sys.path.insert(0, "src")

import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from flight_finder.domain.common.result import Err, Ok, is_err, is_ok
from flight_finder.domain.entities.flight import Flight
from flight_finder.domain.entities.search_criteria import SearchCriteria
from flight_finder.domain.errors.domain_errors import (
    ProviderError,
    RateLimitError,
    TimeoutError as ProviderTimeoutError,
)
from flight_finder.domain.value_objects.airport import Airport
from flight_finder.domain.value_objects.cabin_class import CabinClass
from flight_finder.domain.value_objects.passenger_config import PassengerConfig
from flight_finder.domain.value_objects.price import Price
from flight_finder.infrastructure.http.async_http_client import AsyncHTTPClient
from flight_finder.infrastructure.http.rate_limiter import RateLimiter
from flight_finder.infrastructure.providers.base_provider import BaseFlightProvider

if TYPE_CHECKING:
    from flight_finder.domain.common.result import Result


class MockFlightProvider(BaseFlightProvider):
    def __init__(
        self,
        http_client: AsyncHTTPClient,
        rate_limiter: RateLimiter,
        flights: list[Flight] | None = None,
        error: Exception | None = None,
    ) -> None:
        super().__init__(http_client, rate_limiter)
        self._flights = flights or []
        self._error = error

    @property
    def provider_name(self) -> str:
        return "mock_provider"

    async def _perform_search(self, criteria: SearchCriteria) -> list[Flight]:
        if self._error:
            raise self._error
        return self._flights

    def _map_error(self, error: Exception) -> ProviderError:
        return self._map_http_error(error)


def make_search_criteria() -> SearchCriteria:
    future_date = date.today() + timedelta(days=30)
    return SearchCriteria(
        origin=Airport(code="JFK"),
        destination=Airport(code="LAX"),
        departure_date=future_date,
        passengers=PassengerConfig(adults=1),
        cabin_class=CabinClass(),
    )


def make_flight() -> Flight:
    future_departure = datetime.now(timezone.utc) + timedelta(days=30)
    future_arrival = future_departure + timedelta(hours=5, minutes=30)
    return Flight(
        id="test-flight-001",
        origin=Airport(code="JFK"),
        destination=Airport(code="LAX"),
        departure_time=future_departure,
        arrival_time=future_arrival,
        price=Price(amount=Decimal("299.00"), currency="USD"),
        airline="DL",
    )


class TestBaseFlightProvider:
    @pytest.mark.anyio
    async def test_search_returns_ok_with_flights(self) -> None:
        http_client = AsyncHTTPClient()
        rate_limiter = RateLimiter(rate=10, per=1.0)
        flight = make_flight()
        provider = MockFlightProvider(http_client, rate_limiter, flights=[flight])

        result = await provider.search(make_search_criteria())

        assert is_ok(result)
        assert isinstance(result, Ok)
        assert len(result.value) == 1
        assert result.value[0].id == "test-flight-001"

        await http_client.close()

    @pytest.mark.anyio
    async def test_search_returns_ok_with_empty_list(self) -> None:
        http_client = AsyncHTTPClient()
        rate_limiter = RateLimiter(rate=10, per=1.0)
        provider = MockFlightProvider(http_client, rate_limiter, flights=[])

        result = await provider.search(make_search_criteria())

        assert is_ok(result)
        assert isinstance(result, Ok)
        assert len(result.value) == 0

        await http_client.close()

    @pytest.mark.anyio
    async def test_search_returns_err_on_timeout(self) -> None:
        http_client = AsyncHTTPClient()
        rate_limiter = RateLimiter(rate=10, per=1.0)
        provider = MockFlightProvider(
            http_client,
            rate_limiter,
            error=httpx.TimeoutException("timeout"),
        )

        result = await provider.search(make_search_criteria())

        assert is_err(result)
        assert isinstance(result, Err)
        assert isinstance(result.error, ProviderTimeoutError)

        await http_client.close()

    @pytest.mark.anyio
    async def test_search_returns_err_on_rate_limit(self) -> None:
        http_client = AsyncHTTPClient()
        rate_limiter = RateLimiter(rate=10, per=1.0)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.reason_phrase = "Too Many Requests"
        mock_response.headers = {"Retry-After": "60"}

        http_error = httpx.HTTPStatusError(
            "rate limit",
            request=MagicMock(),
            response=mock_response,
        )

        provider = MockFlightProvider(http_client, rate_limiter, error=http_error)

        result = await provider.search(make_search_criteria())

        assert is_err(result)
        assert isinstance(result, Err)
        assert isinstance(result.error, RateLimitError)
        assert result.error.retry_after == 60.0

        await http_client.close()

    @pytest.mark.anyio
    async def test_search_returns_err_on_http_status_error(self) -> None:
        http_client = AsyncHTTPClient()
        rate_limiter = RateLimiter(rate=10, per=1.0)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"

        http_error = httpx.HTTPStatusError(
            "server error",
            request=MagicMock(),
            response=mock_response,
        )

        provider = MockFlightProvider(http_client, rate_limiter, error=http_error)

        result = await provider.search(make_search_criteria())

        assert is_err(result)
        assert isinstance(result, Err)
        assert isinstance(result.error, ProviderError)
        assert "500" in result.error.message

        await http_client.close()

    @pytest.mark.anyio
    async def test_search_returns_err_on_generic_exception(self) -> None:
        http_client = AsyncHTTPClient()
        rate_limiter = RateLimiter(rate=10, per=1.0)
        provider = MockFlightProvider(
            http_client,
            rate_limiter,
            error=ValueError("something went wrong"),
        )

        result = await provider.search(make_search_criteria())

        assert is_err(result)
        assert isinstance(result, Err)
        assert isinstance(result.error, ProviderError)

        await http_client.close()

    @pytest.mark.anyio
    async def test_provider_name_is_set(self) -> None:
        http_client = AsyncHTTPClient()
        rate_limiter = RateLimiter(rate=10, per=1.0)
        provider = MockFlightProvider(http_client, rate_limiter)

        assert provider.provider_name == "mock_provider"

        await http_client.close()

    @pytest.mark.anyio
    async def test_is_available_delegates_to_rate_limiter(self) -> None:
        http_client = AsyncHTTPClient()
        rate_limiter = RateLimiter(rate=1, per=1.0)
        provider = MockFlightProvider(http_client, rate_limiter)

        assert await provider.is_available() is True
        assert await provider.is_available() is False

        await http_client.close()

    def test_create_provider_error(self) -> None:
        http_client = AsyncHTTPClient()
        rate_limiter = RateLimiter(rate=10, per=1.0)
        provider = MockFlightProvider(http_client, rate_limiter)

        error = provider._create_provider_error("test message")
        assert error.provider == "mock_provider"
        assert "test message" in error.message

    def test_create_rate_limit_error(self) -> None:
        http_client = AsyncHTTPClient()
        rate_limiter = RateLimiter(rate=10, per=1.0)
        provider = MockFlightProvider(http_client, rate_limiter)

        error = provider._create_rate_limit_error(retry_after=30.0)
        assert error.provider == "mock_provider"
        assert error.retry_after == 30.0

    def test_create_timeout_error(self) -> None:
        http_client = AsyncHTTPClient()
        rate_limiter = RateLimiter(rate=10, per=1.0)
        provider = MockFlightProvider(http_client, rate_limiter)

        error = provider._create_timeout_error(timeout_seconds=10.0)
        assert error.provider == "mock_provider"
        assert error.timeout_seconds == 10.0


if __name__ == "__main__":
    async def run_tests() -> None:
        test = TestBaseFlightProvider()

        print("test_search_returns_ok_with_flights...")
        await test.test_search_returns_ok_with_flights()
        print("  PASSED")

        print("test_search_returns_ok_with_empty_list...")
        await test.test_search_returns_ok_with_empty_list()
        print("  PASSED")

        print("test_search_returns_err_on_timeout...")
        await test.test_search_returns_err_on_timeout()
        print("  PASSED")

        print("test_search_returns_err_on_rate_limit...")
        await test.test_search_returns_err_on_rate_limit()
        print("  PASSED")

        print("test_search_returns_err_on_http_status_error...")
        await test.test_search_returns_err_on_http_status_error()
        print("  PASSED")

        print("test_search_returns_err_on_generic_exception...")
        await test.test_search_returns_err_on_generic_exception()
        print("  PASSED")

        print("test_provider_name_is_set...")
        await test.test_provider_name_is_set()
        print("  PASSED")

        print("test_is_available_delegates_to_rate_limiter...")
        await test.test_is_available_delegates_to_rate_limiter()
        print("  PASSED")

        print("test_create_provider_error...")
        test.test_create_provider_error()
        print("  PASSED")

        print("test_create_rate_limit_error...")
        test.test_create_rate_limit_error()
        print("  PASSED")

        print("test_create_timeout_error...")
        test.test_create_timeout_error()
        print("  PASSED")

        print("\nAll tests passed!")

    asyncio.run(run_tests())
