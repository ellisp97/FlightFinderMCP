from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import httpx
import structlog

from flight_finder.domain.common.result import Err, Ok, Result
from flight_finder.domain.errors.domain_errors import (
    ProviderError,
    RateLimitError,
    TimeoutError as ProviderTimeoutError,
)
from flight_finder.infrastructure.http.async_http_client import AsyncHTTPClient
from flight_finder.infrastructure.http.rate_limiter import RateLimiter

if TYPE_CHECKING:
    from flight_finder.domain.entities.flight import Flight
    from flight_finder.domain.entities.search_criteria import SearchCriteria

logger = structlog.get_logger()


class BaseFlightProvider(ABC):
    def __init__(self, http_client: AsyncHTTPClient, rate_limiter: RateLimiter) -> None:
        self._http_client = http_client
        self._rate_limiter = rate_limiter
        self._logger = logger.bind(provider=self.provider_name)

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def _perform_search(self, criteria: SearchCriteria) -> list[Flight]:
        pass

    @abstractmethod
    def _map_error(self, error: Exception) -> ProviderError:
        pass

    async def search(
        self,
        criteria: SearchCriteria,
    ) -> Result[list[Flight], ProviderError]:
        self._logger.info("search_started", criteria=criteria.model_dump(mode="json"))

        try:
            await self._rate_limiter.acquire()
            flights = await self._perform_search(criteria)
            self._logger.info("search_completed", flight_count=len(flights))
            return Ok(flights)
        except Exception as e:
            self._logger.error("search_failed", error=str(e), error_type=type(e).__name__)
            return Err(self._map_error(e))

    async def is_available(self) -> bool:
        return await self._rate_limiter.try_acquire()

    def _create_provider_error(
        self,
        message: str,
        original: Exception | None = None,
    ) -> ProviderError:
        return ProviderError(
            provider=self.provider_name,
            message=message,
            original=original,
        )

    def _create_rate_limit_error(
        self,
        retry_after: float | None = None,
        original: Exception | None = None,
    ) -> RateLimitError:
        return RateLimitError(
            provider=self.provider_name,
            retry_after=retry_after,
            original=original,
        )

    def _create_timeout_error(
        self,
        timeout_seconds: float | None = None,
        original: Exception | None = None,
    ) -> ProviderTimeoutError:
        return ProviderTimeoutError(
            provider=self.provider_name,
            timeout_seconds=timeout_seconds,
            original=original,
        )

    def _map_http_error(self, error: Exception) -> ProviderError:
        if isinstance(error, httpx.TimeoutException):
            return self._create_timeout_error(original=error)
        if isinstance(error, httpx.HTTPStatusError):
            response = error.response
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                return self._create_rate_limit_error(
                    retry_after=float(retry_after) if retry_after else None,
                    original=error,
                )
            return self._create_provider_error(
                f"HTTP {response.status_code}: {response.reason_phrase}",
                original=error,
            )
        return self._create_provider_error(str(error), original=error)
