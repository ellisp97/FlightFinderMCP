from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx
import structlog

from flight_finder.infrastructure.http.retry_config import DEFAULT_RETRY_CONFIG, RetryConfig

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = structlog.get_logger()

DEFAULT_USER_AGENTS: tuple[str, ...] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)


@dataclass
class AsyncHTTPClient:
    timeout: float = 30.0
    retry_config: RetryConfig = field(default_factory=lambda: DEFAULT_RETRY_CONFIG)
    user_agents: tuple[str, ...] = DEFAULT_USER_AGENTS
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)
    _logger: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = logger.bind(component="async_http_client")

    def _get_user_agent(self) -> str:
        return random.choice(self.user_agents)

    def _prepare_headers(self, headers: dict[str, str] | None) -> dict[str, str]:
        result = {"User-Agent": self._get_user_agent()}
        if headers:
            result.update(headers)
        return result

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        client = await self._ensure_client()
        prepared_headers = self._prepare_headers(headers)
        last_exception: Exception | None = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                self._logger.debug(
                    "http_request_attempt",
                    method=method,
                    url=url,
                    attempt=attempt + 1,
                    max_attempts=self.retry_config.max_retries + 1,
                )

                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    data=data,
                    headers=prepared_headers,
                )

                if self.retry_config.is_retryable_status(response.status_code):
                    if attempt < self.retry_config.max_retries:
                        wait_time = self.retry_config.get_wait_time(attempt)
                        self._logger.warning(
                            "http_retryable_status",
                            status_code=response.status_code,
                            attempt=attempt + 1,
                            wait_time=wait_time,
                        )
                        await asyncio.sleep(wait_time)
                        continue

                self._logger.debug(
                    "http_request_completed",
                    method=method,
                    url=url,
                    status_code=response.status_code,
                )
                return response

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                if attempt < self.retry_config.max_retries:
                    wait_time = self.retry_config.get_wait_time(attempt)
                    self._logger.warning(
                        "http_request_retry",
                        method=method,
                        url=url,
                        error=str(e),
                        error_type=type(e).__name__,
                        attempt=attempt + 1,
                        wait_time=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self._logger.error(
                        "http_request_failed",
                        method=method,
                        url=url,
                        error=str(e),
                        error_type=type(e).__name__,
                        attempts=attempt + 1,
                    )
                    raise

        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected retry loop exit")

    async def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        return await self._request_with_retry("GET", url, params=params, headers=headers)

    async def post(
        self,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        return await self._request_with_retry("POST", url, json=json, data=data, headers=headers)

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> AsyncHTTPClient:
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
