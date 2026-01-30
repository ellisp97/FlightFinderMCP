from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
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

from flight_finder.domain.entities.search_criteria import SearchCriteria
from flight_finder.domain.value_objects.airport import Airport
from flight_finder.domain.value_objects.cabin_class import CabinClass
from flight_finder.domain.value_objects.passenger_config import PassengerConfig
from flight_finder.infrastructure.providers.skyscanner.api_client import (
    SkyscannerAPIClient,
)


@dataclass
class MockResponse:
    status_code: int = 200
    _json_data: dict = field(default_factory=dict)

    def json(self) -> dict:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class MockHTTPClient:
    def __init__(self) -> None:
        self.post_responses: list[MockResponse] = []
        self.get_responses: list[MockResponse] = []
        self.post_calls: list[dict] = []
        self.get_calls: list[dict] = []

    async def post(
        self,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> MockResponse:
        self.post_calls.append({"url": url, "json": json, "headers": headers})
        if self.post_responses:
            return self.post_responses.pop(0)
        return MockResponse()

    async def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> MockResponse:
        self.get_calls.append({"url": url, "params": params, "headers": headers})
        if self.get_responses:
            return self.get_responses.pop(0)
        return MockResponse()


def make_search_criteria() -> SearchCriteria:
    return SearchCriteria(
        origin=Airport(code="JFK", name="JFK", city="New York", country="US"),
        destination=Airport(code="LAX", name="LAX", city="Los Angeles", country="US"),
        departure_date=date.today() + timedelta(days=30),
        passengers=PassengerConfig(adults=1),
        cabin_class=CabinClass(),
    )


async def test_create_session():
    http_client = MockHTTPClient()
    http_client.post_responses.append(
        MockResponse(
            status_code=200,
            _json_data={"sessionToken": "test_token_123", "status": "created"},
        )
    )

    client = SkyscannerAPIClient(api_key="test_key", http_client=http_client)
    criteria = make_search_criteria()

    session = await client.create_session(criteria)

    assert session.session_token == "test_token_123"
    assert session.status == "created"
    assert len(http_client.post_calls) == 1
    assert "X-API-Key" in http_client.post_calls[0]["headers"]
    assert http_client.post_calls[0]["headers"]["X-API-Key"] == "test_key"


async def test_poll_results_immediate_complete():
    http_client = MockHTTPClient()
    http_client.get_responses.append(
        MockResponse(
            status_code=200,
            _json_data={
                "status": "RESULT_STATUS_COMPLETE",
                "content": {"results": {"itineraries": {}}},
            },
        )
    )

    client = SkyscannerAPIClient(api_key="test_key", http_client=http_client)

    results = await client.poll_results("test_token")

    assert results["status"] == "RESULT_STATUS_COMPLETE"
    assert len(http_client.get_calls) == 1


async def test_poll_results_multiple_attempts():
    http_client = MockHTTPClient()
    http_client.get_responses.append(
        MockResponse(status_code=200, _json_data={"status": "RESULT_STATUS_IN_PROGRESS"})
    )
    http_client.get_responses.append(
        MockResponse(status_code=200, _json_data={"status": "RESULT_STATUS_IN_PROGRESS"})
    )
    http_client.get_responses.append(
        MockResponse(
            status_code=200,
            _json_data={
                "status": "RESULT_STATUS_COMPLETE",
                "content": {"results": {}},
            },
        )
    )

    client = SkyscannerAPIClient(api_key="test_key", http_client=http_client)

    results = await client.poll_results("test_token")

    assert results["status"] == "RESULT_STATUS_COMPLETE"
    assert len(http_client.get_calls) == 3


async def test_build_session_payload_one_way():
    http_client = MockHTTPClient()
    http_client.post_responses.append(
        MockResponse(status_code=200, _json_data={"sessionToken": "token", "status": "ok"})
    )

    client = SkyscannerAPIClient(api_key="test_key", http_client=http_client)
    criteria = make_search_criteria()

    await client.create_session(criteria)

    payload = http_client.post_calls[0]["json"]
    assert "query" in payload
    query = payload["query"]
    assert len(query["queryLegs"]) == 1
    assert query["adults"] == 1
    assert query["cabinClass"] == "CABIN_CLASS_ECONOMY"


async def test_build_session_payload_round_trip():
    http_client = MockHTTPClient()
    http_client.post_responses.append(
        MockResponse(status_code=200, _json_data={"sessionToken": "token", "status": "ok"})
    )

    client = SkyscannerAPIClient(api_key="test_key", http_client=http_client)
    criteria = SearchCriteria(
        origin=Airport(code="JFK", name="JFK", city="New York", country="US"),
        destination=Airport(code="LAX", name="LAX", city="Los Angeles", country="US"),
        departure_date=date.today() + timedelta(days=30),
        return_date=date.today() + timedelta(days=37),
        passengers=PassengerConfig(adults=2, children=1),
        cabin_class=CabinClass(),
    )

    await client.create_session(criteria)

    payload = http_client.post_calls[0]["json"]
    query = payload["query"]
    assert len(query["queryLegs"]) == 2
    assert query["adults"] == 2
    assert len(query["childrenAges"]) == 1


if __name__ == "__main__":
    asyncio.run(test_create_session())
    print("[PASS] test_create_session")

    asyncio.run(test_poll_results_immediate_complete())
    print("[PASS] test_poll_results_immediate_complete")

    asyncio.run(test_poll_results_multiple_attempts())
    print("[PASS] test_poll_results_multiple_attempts")

    asyncio.run(test_build_session_payload_one_way())
    print("[PASS] test_build_session_payload_one_way")

    asyncio.run(test_build_session_payload_round_trip())
    print("[PASS] test_build_session_payload_round_trip")

    print("\nAll API client tests passed!")
