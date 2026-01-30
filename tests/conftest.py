"""Pytest configuration and shared fixtures."""

import os
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic_settings import BaseSettings

# Set test environment variables before importing settings
os.environ.setdefault("FLIGHT_FINDER_LOG_LEVEL", "DEBUG")
os.environ.setdefault("FLIGHT_FINDER_CACHE_ENABLED", "false")
os.environ.setdefault("FLIGHT_FINDER_DEFAULT_PROVIDER", "mock")


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Configure anyio to use asyncio backend."""
    return "asyncio"


@pytest.fixture
def mock_settings() -> Generator[MagicMock, None, None]:
    """Provide mock settings for testing."""
    from flight_finder.config.settings import Settings, get_settings

    # Clear the cached settings
    get_settings.cache_clear()

    mock = MagicMock(spec=Settings)
    mock.log_level = "DEBUG"
    mock.log_format = "console"
    mock.cache_enabled = False
    mock.cache_ttl_seconds = 60
    mock.cache_max_size = 100
    mock.http_timeout_seconds = 10.0
    mock.http_max_retries = 1
    mock.http_retry_delay_seconds = 0.1
    mock.default_provider = "mock"
    mock.enable_fallback_providers = False
    mock.max_search_results = 10
    mock.default_currency = "USD"
    mock.default_locale = "en-US"
    mock.server_name = "flight-finder-mcp-test"
    mock.server_version = "0.1.0-test"
    mock.skyscanner_api_key = "test-key"
    mock.google_flights_api_key = ""
    mock.has_skyscanner_key = True
    mock.has_google_flights_key = False

    yield mock

    # Clear again after test
    get_settings.cache_clear()


@pytest.fixture
def test_settings() -> Generator[BaseSettings, None, None]:
    """Provide real settings instance for testing with test defaults."""
    from flight_finder.config.settings import Settings, get_settings

    # Clear the cached settings
    get_settings.cache_clear()

    # Create settings with test values
    settings = Settings(
        skyscanner_api_key="test-api-key",
        cache_enabled=False,
        log_level="DEBUG",
        default_provider="mock",
    )

    yield settings

    # Clear again after test
    get_settings.cache_clear()


@pytest.fixture
def sample_flight_data() -> dict[str, Any]:
    """Provide sample flight data for testing."""
    return {
        "origin": "JFK",
        "destination": "LAX",
        "departure_date": "2025-06-15",
        "return_date": "2025-06-22",
        "passengers": 1,
        "cabin_class": "economy",
        "flights": [
            {
                "id": "flight-001",
                "airline": "Delta",
                "airline_code": "DL",
                "flight_number": "DL123",
                "origin": "JFK",
                "destination": "LAX",
                "departure_time": "2025-06-15T08:00:00",
                "arrival_time": "2025-06-15T11:30:00",
                "duration_minutes": 330,
                "price": 299.00,
                "currency": "USD",
                "cabin_class": "economy",
                "stops": 0,
                "booking_url": "https://example.com/book/DL123",
            },
            {
                "id": "flight-002",
                "airline": "American Airlines",
                "airline_code": "AA",
                "flight_number": "AA456",
                "origin": "JFK",
                "destination": "LAX",
                "departure_time": "2025-06-15T14:00:00",
                "arrival_time": "2025-06-15T17:15:00",
                "duration_minutes": 315,
                "price": 349.00,
                "currency": "USD",
                "cabin_class": "economy",
                "stops": 0,
                "booking_url": "https://example.com/book/AA456",
            },
        ],
    }


@pytest.fixture
def sample_airport_codes() -> dict[str, str]:
    """Provide sample airport codes for testing."""
    return {
        "JFK": "John F. Kennedy International Airport",
        "LAX": "Los Angeles International Airport",
        "LHR": "London Heathrow Airport",
        "CDG": "Paris Charles de Gaulle Airport",
        "SFO": "San Francisco International Airport",
        "ORD": "O'Hare International Airport",
    }
