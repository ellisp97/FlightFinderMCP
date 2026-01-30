from __future__ import annotations

import sys
sys.path.insert(0, "src")

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from flight_finder.infrastructure.http.async_http_client import (
    AsyncHTTPClient,
    DEFAULT_USER_AGENTS,
)
from flight_finder.infrastructure.http.retry_config import RetryConfig


class TestAsyncHTTPClient:
    @pytest.mark.anyio
    async def test_get_success(self) -> None:
        client = AsyncHTTPClient()
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(client, "_ensure_client") as mock_ensure:
            mock_http_client = AsyncMock()
            mock_http_client.request = AsyncMock(return_value=mock_response)
            mock_ensure.return_value = mock_http_client

            response = await client.get("https://example.com")
            assert response.status_code == 200
            mock_http_client.request.assert_called_once()

        await client.close()

    @pytest.mark.anyio
    async def test_post_success(self) -> None:
        client = AsyncHTTPClient()
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201

        with patch.object(client, "_ensure_client") as mock_ensure:
            mock_http_client = AsyncMock()
            mock_http_client.request = AsyncMock(return_value=mock_response)
            mock_ensure.return_value = mock_http_client

            response = await client.post("https://example.com", json={"key": "value"})
            assert response.status_code == 201

        await client.close()

    @pytest.mark.anyio
    async def test_retry_on_timeout(self) -> None:
        config = RetryConfig(max_retries=2, min_wait_seconds=0.01, max_wait_seconds=0.05)
        client = AsyncHTTPClient(retry_config=config)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("timeout")
            return mock_response

        with patch.object(client, "_ensure_client") as mock_ensure:
            mock_http_client = AsyncMock()
            mock_http_client.request = mock_request
            mock_ensure.return_value = mock_http_client

            response = await client.get("https://example.com")
            assert response.status_code == 200
            assert call_count == 2

        await client.close()

    @pytest.mark.anyio
    async def test_retry_on_network_error(self) -> None:
        config = RetryConfig(max_retries=2, min_wait_seconds=0.01, max_wait_seconds=0.05)
        client = AsyncHTTPClient(retry_config=config)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.NetworkError("network error")
            return mock_response

        with patch.object(client, "_ensure_client") as mock_ensure:
            mock_http_client = AsyncMock()
            mock_http_client.request = mock_request
            mock_ensure.return_value = mock_http_client

            response = await client.get("https://example.com")
            assert response.status_code == 200
            assert call_count == 2

        await client.close()

    @pytest.mark.anyio
    async def test_retry_exhausted_raises(self) -> None:
        config = RetryConfig(max_retries=2, min_wait_seconds=0.01, max_wait_seconds=0.05)
        client = AsyncHTTPClient(retry_config=config)

        async def mock_request(*args, **kwargs):
            raise httpx.TimeoutException("timeout")

        with patch.object(client, "_ensure_client") as mock_ensure:
            mock_http_client = AsyncMock()
            mock_http_client.request = mock_request
            mock_ensure.return_value = mock_http_client

            with pytest.raises(httpx.TimeoutException):
                await client.get("https://example.com")

        await client.close()

    @pytest.mark.anyio
    async def test_retry_on_retryable_status_code(self) -> None:
        config = RetryConfig(
            max_retries=2,
            min_wait_seconds=0.01,
            max_wait_seconds=0.05,
            retryable_status_codes=(500, 502, 503),
        )
        client = AsyncHTTPClient(retry_config=config)

        call_count = 0

        def make_response(status_code: int) -> MagicMock:
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = status_code
            return resp

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return make_response(503)
            return make_response(200)

        with patch.object(client, "_ensure_client") as mock_ensure:
            mock_http_client = AsyncMock()
            mock_http_client.request = mock_request
            mock_ensure.return_value = mock_http_client

            response = await client.get("https://example.com")
            assert response.status_code == 200
            assert call_count == 2

        await client.close()

    def test_user_agent_rotation(self) -> None:
        client = AsyncHTTPClient()
        user_agents = set()
        for _ in range(100):
            user_agents.add(client._get_user_agent())
        assert len(user_agents) > 1
        for ua in user_agents:
            assert ua in DEFAULT_USER_AGENTS

    def test_prepare_headers_includes_user_agent(self) -> None:
        client = AsyncHTTPClient()
        headers = client._prepare_headers(None)
        assert "User-Agent" in headers
        assert headers["User-Agent"] in DEFAULT_USER_AGENTS

    def test_prepare_headers_preserves_custom_headers(self) -> None:
        client = AsyncHTTPClient()
        custom = {"X-Custom": "value", "Authorization": "Bearer token"}
        headers = client._prepare_headers(custom)
        assert headers["X-Custom"] == "value"
        assert headers["Authorization"] == "Bearer token"
        assert "User-Agent" in headers

    @pytest.mark.anyio
    async def test_context_manager(self) -> None:
        async with AsyncHTTPClient() as client:
            assert client._client is not None
            assert not client._client.is_closed
        assert client._client is None

    @pytest.mark.anyio
    async def test_close_is_idempotent(self) -> None:
        client = AsyncHTTPClient()
        await client._ensure_client()
        await client.close()
        await client.close()
        assert client._client is None


class TestRetryConfig:
    def test_get_wait_time_exponential_backoff(self) -> None:
        config = RetryConfig(min_wait_seconds=1.0, max_wait_seconds=10.0, multiplier=1.0)
        assert config.get_wait_time(0) == 1.0
        assert config.get_wait_time(1) == 2.0
        assert config.get_wait_time(2) == 4.0
        assert config.get_wait_time(3) == 8.0
        assert config.get_wait_time(4) == 10.0

    def test_get_wait_time_capped_at_max(self) -> None:
        config = RetryConfig(min_wait_seconds=5.0, max_wait_seconds=8.0)
        assert config.get_wait_time(5) == 8.0

    def test_is_retryable_status(self) -> None:
        config = RetryConfig(retryable_status_codes=(429, 500, 503))
        assert config.is_retryable_status(429) is True
        assert config.is_retryable_status(500) is True
        assert config.is_retryable_status(503) is True
        assert config.is_retryable_status(200) is False
        assert config.is_retryable_status(400) is False
        assert config.is_retryable_status(404) is False


if __name__ == "__main__":
    async def run_tests() -> None:
        test_client = TestAsyncHTTPClient()

        print("test_get_success...")
        await test_client.test_get_success()
        print("  PASSED")

        print("test_post_success...")
        await test_client.test_post_success()
        print("  PASSED")

        print("test_retry_on_timeout...")
        await test_client.test_retry_on_timeout()
        print("  PASSED")

        print("test_retry_on_network_error...")
        await test_client.test_retry_on_network_error()
        print("  PASSED")

        print("test_retry_exhausted_raises...")
        await test_client.test_retry_exhausted_raises()
        print("  PASSED")

        print("test_retry_on_retryable_status_code...")
        await test_client.test_retry_on_retryable_status_code()
        print("  PASSED")

        print("test_user_agent_rotation...")
        test_client.test_user_agent_rotation()
        print("  PASSED")

        print("test_prepare_headers_includes_user_agent...")
        test_client.test_prepare_headers_includes_user_agent()
        print("  PASSED")

        print("test_prepare_headers_preserves_custom_headers...")
        test_client.test_prepare_headers_preserves_custom_headers()
        print("  PASSED")

        print("test_context_manager...")
        await test_client.test_context_manager()
        print("  PASSED")

        print("test_close_is_idempotent...")
        await test_client.test_close_is_idempotent()
        print("  PASSED")

        test_config = TestRetryConfig()

        print("test_get_wait_time_exponential_backoff...")
        test_config.test_get_wait_time_exponential_backoff()
        print("  PASSED")

        print("test_get_wait_time_capped_at_max...")
        test_config.test_get_wait_time_capped_at_max()
        print("  PASSED")

        print("test_is_retryable_status...")
        test_config.test_is_retryable_status()
        print("  PASSED")

        print("\nAll tests passed!")

    asyncio.run(run_tests())
