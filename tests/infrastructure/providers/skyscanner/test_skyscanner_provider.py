from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any


class MockLogger:
    def bind(self, **kwargs):
        return self

    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class MockStructlog:
    @staticmethod
    def get_logger():
        return MockLogger()


sys.modules["structlog"] = MockStructlog()
sys.path.insert(0, "src")

from flight_finder.domain.common.result import is_ok, is_err, unwrap
from flight_finder.domain.entities.search_criteria import SearchCriteria
from flight_finder.domain.value_objects.airport import Airport
from flight_finder.domain.value_objects.cabin_class import CabinClass
from flight_finder.domain.value_objects.passenger_config import PassengerConfig
from flight_finder.infrastructure.providers.skyscanner import SkyscannerProvider


@dataclass
class MockResponse:
    status_code: int = 200
    _json_data: dict = field(default_factory=dict)

    def json(self) -> dict:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import httpx
            request = httpx.Request("GET", "http://test")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("Error", request=request, response=response)


class MockHTTPClient:
    def __init__(self) -> None:
        self.responses: list[MockResponse] = []
        self.calls: list[dict] = []

    async def post(
        self,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> MockResponse:
        self.calls.append({"method": "POST", "url": url, "json": json, "headers": headers})
        if self.responses:
            return self.responses.pop(0)
        return MockResponse()

    async def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> MockResponse:
        self.calls.append({"method": "GET", "url": url, "params": params, "headers": headers})
        if self.responses:
            return self.responses.pop(0)
        return MockResponse()


class MockRateLimiter:
    async def acquire(self) -> None:
        pass

    async def try_acquire(self) -> bool:
        return True


def make_search_criteria() -> SearchCriteria:
    return SearchCriteria(
        origin=Airport(code="JFK", name="JFK", city="New York", country="US"),
        destination=Airport(code="LAX", name="LAX", city="Los Angeles", country="US"),
        departure_date=date.today() + timedelta(days=30),
        passengers=PassengerConfig(adults=1),
        cabin_class=CabinClass(),
    )


def make_api_response() -> dict:
    return {
        "status": "RESULT_STATUS_COMPLETE",
        "content": {
            "results": {
                "itineraries": {
                    "itin_1": {
                        "pricingOptions": [{"price": {"amount": "29900", "unit": "USD"}}],
                        "legIds": ["leg_1"],
                    }
                },
                "legs": {
                    "leg_1": {
                        "originPlaceId": "JFK",
                        "destinationPlaceId": "LAX",
                        "departureDateTime": {"year": 2026, "month": 6, "day": 15, "hour": 8, "minute": 0, "second": 0},
                        "arrivalDateTime": {"year": 2026, "month": 6, "day": 15, "hour": 11, "minute": 30, "second": 0},
                        "stopCount": 0,
                        "segmentIds": ["seg_1"],
                    }
                },
                "segments": {
                    "seg_1": {
                        "marketingCarrierId": "1",
                        "marketingFlightNumber": "123",
                    }
                },
                "places": {
                    "JFK": {"iata": "JFK", "name": "JFK Airport"},
                    "LAX": {"iata": "LAX", "name": "LAX Airport"},
                },
                "carriers": {
                    "1": {"name": "Delta Air Lines", "iata": "DL"},
                },
            }
        },
    }


async def test_provider_search_success():
    http_client = MockHTTPClient()
    http_client.responses.append(
        MockResponse(status_code=200, _json_data={"sessionToken": "test_token", "status": "created"})
    )
    http_client.responses.append(MockResponse(status_code=200, _json_data=make_api_response()))

    rate_limiter = MockRateLimiter()
    provider = SkyscannerProvider(
        api_key="test_key",
        http_client=http_client,
        rate_limiter=rate_limiter,
    )

    criteria = make_search_criteria()
    result = await provider.search(criteria)

    assert is_ok(result)
    flights = unwrap(result)
    assert len(flights) == 1
    assert flights[0].airline == "DL"
    assert flights[0].price.amount == Decimal("299.00")


async def test_provider_name():
    http_client = MockHTTPClient()
    rate_limiter = MockRateLimiter()
    provider = SkyscannerProvider(
        api_key="test_key",
        http_client=http_client,
        rate_limiter=rate_limiter,
    )

    assert provider.provider_name == "skyscanner"


async def test_provider_filters_non_stop():
    api_response = make_api_response()
    api_response["content"]["results"]["itineraries"]["itin_2"] = {
        "pricingOptions": [{"price": {"amount": "20000", "unit": "USD"}}],
        "legIds": ["leg_2"],
    }
    api_response["content"]["results"]["legs"]["leg_2"] = {
        "originPlaceId": "JFK",
        "destinationPlaceId": "LAX",
        "departureDateTime": {"year": 2026, "month": 6, "day": 15, "hour": 10, "minute": 0, "second": 0},
        "arrivalDateTime": {"year": 2026, "month": 6, "day": 15, "hour": 16, "minute": 0, "second": 0},
        "stopCount": 1,
        "segmentIds": ["seg_2"],
    }
    api_response["content"]["results"]["segments"]["seg_2"] = {
        "marketingCarrierId": "1",
        "marketingFlightNumber": "456",
    }

    http_client = MockHTTPClient()
    http_client.responses.append(
        MockResponse(status_code=200, _json_data={"sessionToken": "test_token", "status": "created"})
    )
    http_client.responses.append(MockResponse(status_code=200, _json_data=api_response))

    rate_limiter = MockRateLimiter()
    provider = SkyscannerProvider(
        api_key="test_key",
        http_client=http_client,
        rate_limiter=rate_limiter,
    )

    criteria = SearchCriteria(
        origin=Airport(code="JFK", name="JFK", city="New York", country="US"),
        destination=Airport(code="LAX", name="LAX", city="Los Angeles", country="US"),
        departure_date=date.today() + timedelta(days=30),
        passengers=PassengerConfig(adults=1),
        cabin_class=CabinClass(),
        non_stop_only=True,
    )

    result = await provider.search(criteria)

    assert is_ok(result)
    flights = unwrap(result)
    assert len(flights) == 1
    assert flights[0].is_non_stop


async def test_provider_sorts_by_price():
    api_response = make_api_response()
    api_response["content"]["results"]["itineraries"]["itin_2"] = {
        "pricingOptions": [{"price": {"amount": "15000", "unit": "USD"}}],
        "legIds": ["leg_2"],
    }
    api_response["content"]["results"]["legs"]["leg_2"] = {
        "originPlaceId": "JFK",
        "destinationPlaceId": "LAX",
        "departureDateTime": {"year": 2026, "month": 6, "day": 15, "hour": 10, "minute": 0, "second": 0},
        "arrivalDateTime": {"year": 2026, "month": 6, "day": 15, "hour": 13, "minute": 0, "second": 0},
        "stopCount": 0,
        "segmentIds": ["seg_2"],
    }
    api_response["content"]["results"]["segments"]["seg_2"] = {
        "marketingCarrierId": "1",
        "marketingFlightNumber": "456",
    }

    http_client = MockHTTPClient()
    http_client.responses.append(
        MockResponse(status_code=200, _json_data={"sessionToken": "test_token", "status": "created"})
    )
    http_client.responses.append(MockResponse(status_code=200, _json_data=api_response))

    rate_limiter = MockRateLimiter()
    provider = SkyscannerProvider(
        api_key="test_key",
        http_client=http_client,
        rate_limiter=rate_limiter,
    )

    criteria = make_search_criteria()
    result = await provider.search(criteria)

    assert is_ok(result)
    flights = unwrap(result)
    assert len(flights) == 2
    assert flights[0].price.amount < flights[1].price.amount


async def test_provider_http_error():
    http_client = MockHTTPClient()
    http_client.responses.append(MockResponse(status_code=500, _json_data={}))

    rate_limiter = MockRateLimiter()
    provider = SkyscannerProvider(
        api_key="test_key",
        http_client=http_client,
        rate_limiter=rate_limiter,
    )

    criteria = make_search_criteria()
    result = await provider.search(criteria)

    assert is_err(result)


if __name__ == "__main__":
    asyncio.run(test_provider_search_success())
    print("[PASS] test_provider_search_success")

    asyncio.run(test_provider_name())
    print("[PASS] test_provider_name")

    asyncio.run(test_provider_filters_non_stop())
    print("[PASS] test_provider_filters_non_stop")

    asyncio.run(test_provider_sorts_by_price())
    print("[PASS] test_provider_sorts_by_price")

    asyncio.run(test_provider_http_error())
    print("[PASS] test_provider_http_error")

    print("\nAll provider tests passed!")
