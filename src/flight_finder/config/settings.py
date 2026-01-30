"""Application settings using pydantic-settings for environment variable validation."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable validation.

    Settings can be configured via environment variables or a .env file.
    All environment variables are prefixed with FLIGHT_FINDER_.
    """

    model_config = SettingsConfigDict(
        env_prefix="FLIGHT_FINDER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys
    skyscanner_api_key: str = Field(
        default="",
        description="Skyscanner RapidAPI key for flight searches",
    )
    google_flights_api_key: str = Field(
        default="",
        description="Google Flights API key (if available)",
    )

    # Cache Settings
    cache_enabled: bool = Field(
        default=True,
        description="Enable/disable caching of flight search results",
    )
    cache_ttl_seconds: int = Field(
        default=300,
        ge=0,
        le=3600,
        description="Cache TTL in seconds (0-3600)",
    )
    cache_max_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Maximum number of cached entries",
    )

    # HTTP Client Settings
    http_timeout_seconds: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
        description="HTTP request timeout in seconds",
    )
    http_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of HTTP request retries",
    )
    http_retry_delay_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Delay between HTTP retries in seconds",
    )

    # Logging Settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    log_format: Literal["json", "console"] = Field(
        default="console",
        description="Log output format (json for production, console for development)",
    )

    # Provider Settings
    default_provider: Literal["skyscanner", "google_flights", "mock"] = Field(
        default="skyscanner",
        description="Default flight data provider",
    )
    enable_fallback_providers: bool = Field(
        default=True,
        description="Enable fallback to other providers on failure",
    )

    # Search Settings
    max_search_results: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Maximum number of flight results to return",
    )
    default_currency: str = Field(
        default="USD",
        description="Default currency for flight prices",
    )
    default_locale: str = Field(
        default="en-US",
        description="Default locale for formatting",
    )

    # MCP Server Settings
    server_name: str = Field(
        default="flight-finder-mcp",
        description="MCP server name",
    )
    server_version: str = Field(
        default="0.1.0",
        description="MCP server version",
    )

    @field_validator("default_currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code is uppercase and 3 characters."""
        v = v.upper()
        if len(v) != 3:
            raise ValueError("Currency code must be exactly 3 characters")
        return v

    @property
    def has_skyscanner_key(self) -> bool:
        """Check if Skyscanner API key is configured."""
        return bool(self.skyscanner_api_key)

    @property
    def has_google_flights_key(self) -> bool:
        """Check if Google Flights API key is configured."""
        return bool(self.google_flights_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Settings: The application settings instance.
    """
    return Settings()
