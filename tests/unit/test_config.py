"""Tests for configuration module."""

import os
from unittest.mock import patch

import pytest

from flight_finder.config.settings import Settings, get_settings


class TestSettings:
    """Tests for Settings class."""

    def test_default_settings(self) -> None:
        """Test that default settings are created correctly with no env vars."""
        # Clear test env vars to test true defaults
        env_overrides = {
            "FLIGHT_FINDER_CACHE_ENABLED": "",
            "FLIGHT_FINDER_LOG_LEVEL": "",
            "FLIGHT_FINDER_DEFAULT_PROVIDER": "",
        }
        with patch.dict(os.environ, env_overrides, clear=False):
            # Remove the keys entirely for this test
            for key in env_overrides:
                os.environ.pop(key, None)
            settings = Settings()
            assert settings.cache_enabled is True
            assert settings.cache_ttl_seconds == 300
            assert settings.log_level == "INFO"
            assert settings.default_currency == "USD"

    def test_settings_from_env(self) -> None:
        """Test that settings can be loaded from environment variables."""
        with patch.dict(
            os.environ,
            {
                "FLIGHT_FINDER_CACHE_ENABLED": "false",
                "FLIGHT_FINDER_LOG_LEVEL": "DEBUG",
                "FLIGHT_FINDER_DEFAULT_CURRENCY": "EUR",
            },
        ):
            settings = Settings()
            assert settings.cache_enabled is False
            assert settings.log_level == "DEBUG"
            assert settings.default_currency == "EUR"

    def test_currency_validation(self) -> None:
        """Test that currency code is validated and uppercased."""
        settings = Settings(default_currency="eur")
        assert settings.default_currency == "EUR"

    def test_currency_validation_invalid_length(self) -> None:
        """Test that invalid currency code length raises error."""
        with pytest.raises(ValueError, match="Currency code must be exactly 3 characters"):
            Settings(default_currency="EURO")

    def test_has_api_keys(self) -> None:
        """Test API key presence checks."""
        settings = Settings(skyscanner_api_key="", google_flights_api_key="")
        assert settings.has_skyscanner_key is False
        assert settings.has_google_flights_key is False

        settings = Settings(skyscanner_api_key="key123", google_flights_api_key="key456")
        assert settings.has_skyscanner_key is True
        assert settings.has_google_flights_key is True

    def test_cache_ttl_bounds(self) -> None:
        """Test that cache TTL is bounded correctly."""
        with pytest.raises(ValueError):
            Settings(cache_ttl_seconds=-1)
        with pytest.raises(ValueError):
            Settings(cache_ttl_seconds=3601)

    def test_http_timeout_bounds(self) -> None:
        """Test that HTTP timeout is bounded correctly."""
        with pytest.raises(ValueError):
            Settings(http_timeout_seconds=1.0)  # Below 5.0
        with pytest.raises(ValueError):
            Settings(http_timeout_seconds=150.0)  # Above 120.0


class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_returns_settings(self) -> None:
        """Test that get_settings returns a Settings instance."""
        get_settings.cache_clear()
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_is_cached(self) -> None:
        """Test that get_settings returns cached instance."""
        get_settings.cache_clear()
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
