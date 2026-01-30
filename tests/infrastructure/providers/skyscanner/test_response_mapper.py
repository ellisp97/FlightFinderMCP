from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


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

from flight_finder.domain.value_objects.cabin_class import CabinClass
from flight_finder.infrastructure.providers.skyscanner.response_mapper import (
    SkyscannerResponseMapper,
)


def load_fixture(name: str) -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / name
    with open(fixture_path) as f:
        return json.load(f)


def test_map_api_response_basic():
    mapper = SkyscannerResponseMapper()
    api_data = load_fixture("api_response.json")
    cabin_class = CabinClass()

    flights = mapper.map_api_response(api_data, cabin_class)

    assert len(flights) == 2

    non_stop = [f for f in flights if f.is_non_stop][0]
    assert non_stop.origin.code == "JFK"
    assert non_stop.destination.code == "LAX"
    assert non_stop.airline == "DL"
    assert non_stop.airline_name == "Delta Air Lines"
    assert non_stop.price.amount == Decimal("299.00")
    assert non_stop.stops == 0

    with_stop = [f for f in flights if not f.is_non_stop][0]
    assert with_stop.stops == 1
    assert with_stop.price.amount == Decimal("450.00")


def test_map_api_response_timestamps():
    mapper = SkyscannerResponseMapper()
    api_data = load_fixture("api_response.json")
    cabin_class = CabinClass()

    flights = mapper.map_api_response(api_data, cabin_class)
    flight = flights[0]

    assert flight.departure_time.year == 2026
    assert flight.departure_time.month == 6
    assert flight.departure_time.day == 15
    assert flight.arrival_time > flight.departure_time


def test_map_empty_response():
    mapper = SkyscannerResponseMapper()
    api_data = {"content": {"results": {"itineraries": {}}}}
    cabin_class = CabinClass()

    flights = mapper.map_api_response(api_data, cabin_class)

    assert len(flights) == 0


def test_map_response_with_missing_carrier():
    mapper = SkyscannerResponseMapper()
    api_data = {
        "content": {
            "results": {
                "itineraries": {
                    "itin_1": {
                        "pricingOptions": [{"price": {"amount": "10000", "unit": "USD"}}],
                        "legIds": ["leg_1"],
                    }
                },
                "legs": {
                    "leg_1": {
                        "originPlaceId": "JFK",
                        "destinationPlaceId": "LAX",
                        "departureDateTime": {"year": 2026, "month": 6, "day": 15, "hour": 8, "minute": 0, "second": 0},
                        "arrivalDateTime": {"year": 2026, "month": 6, "day": 15, "hour": 11, "minute": 0, "second": 0},
                        "stopCount": 0,
                        "segmentIds": ["seg_1"],
                    }
                },
                "segments": {
                    "seg_1": {
                        "marketingCarrierId": "unknown_carrier",
                        "marketingFlightNumber": "100",
                    }
                },
                "places": {
                    "JFK": {"iata": "JFK", "name": "JFK Airport"},
                    "LAX": {"iata": "LAX", "name": "LAX Airport"},
                },
                "carriers": {},
            }
        }
    }
    cabin_class = CabinClass()

    flights = mapper.map_api_response(api_data, cabin_class)

    assert len(flights) == 1
    assert len(flights[0].airline) >= 2


if __name__ == "__main__":
    test_map_api_response_basic()
    print("[PASS] test_map_api_response_basic")

    test_map_api_response_timestamps()
    print("[PASS] test_map_api_response_timestamps")

    test_map_empty_response()
    print("[PASS] test_map_empty_response")

    test_map_response_with_missing_carrier()
    print("[PASS] test_map_response_with_missing_carrier")

    print("\nAll response mapper tests passed!")
