"""Domain error hierarchy for Flight Finder.

This module defines a comprehensive error hierarchy for domain-level exceptions.
All domain errors inherit from DomainError, allowing for consistent error handling
and propagation throughout the application.
"""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base domain error.

    All domain-specific exceptions should inherit from this class.
    Provides a consistent interface for error information and context.
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize domain error.

        Args:
            message: Human-readable error message
            code: Optional error code for programmatic handling
            context: Optional additional context about the error
        """
        self.message = message
        self.code = code or self.__class__.__name__
        self.context = context or {}
        super().__init__(message)

    def __str__(self) -> str:
        """Format error as string."""
        if self.context:
            return f"[{self.code}] {self.message} (context: {self.context})"
        return f"[{self.code}] {self.message}"

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"code={self.code!r}, "
            f"context={self.context!r})"
        )

    def with_context(self, **kwargs: Any) -> DomainError:
        """Create a new error with additional context.

        Returns a new error instance with merged context.
        """
        new_context = {**self.context, **kwargs}
        return self.__class__(
            message=self.message,
            code=self.code,
            context=new_context,
        )


class ValidationError(DomainError):
    """Validation error for invalid input data.

    Raised when input fails validation rules (e.g., invalid airport code,
    invalid date range, negative passenger count).
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        code: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Human-readable error message
            field: Name of the field that failed validation
            value: The invalid value (sanitized if sensitive)
            code: Optional error code
            context: Optional additional context
        """
        self.field = field
        self.value = value
        ctx = context or {}
        if field:
            ctx["field"] = field
        if value is not None:
            ctx["value"] = str(value)
        super().__init__(message, code or "VALIDATION_ERROR", ctx)


class ProviderError(DomainError):
    """Provider-specific error.

    Raised when a flight data provider encounters an error during
    search or data retrieval operations.
    """

    def __init__(
        self,
        provider: str,
        message: str,
        original: Exception | None = None,
        code: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize provider error.

        Args:
            provider: Name of the provider that failed
            message: Human-readable error message
            original: The original exception (if wrapping another error)
            code: Optional error code
            context: Optional additional context
        """
        self.provider = provider
        self.original = original
        ctx = context or {}
        ctx["provider"] = provider
        if original:
            ctx["original_error"] = str(original)
            ctx["original_type"] = type(original).__name__
        super().__init__(f"[{provider}] {message}", code or "PROVIDER_ERROR", ctx)


class CacheError(DomainError):
    """Cache operation error.

    Raised when cache operations fail (read, write, invalidate).
    """

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        key: str | None = None,
        original: Exception | None = None,
        code: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize cache error.

        Args:
            message: Human-readable error message
            operation: The cache operation that failed (get, set, delete)
            key: The cache key involved (sanitized if sensitive)
            original: The original exception (if wrapping another error)
            code: Optional error code
            context: Optional additional context
        """
        self.operation = operation
        self.key = key
        self.original = original
        ctx = context or {}
        if operation:
            ctx["operation"] = operation
        if key:
            ctx["key"] = key
        if original:
            ctx["original_error"] = str(original)
        super().__init__(message, code or "CACHE_ERROR", ctx)


class RateLimitError(ProviderError):
    """Rate limit exceeded error.

    Raised when a provider's rate limit has been exceeded.
    """

    def __init__(
        self,
        provider: str,
        message: str | None = None,
        retry_after: float | None = None,
        original: Exception | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize rate limit error.

        Args:
            provider: Name of the provider that rate limited us
            message: Human-readable error message
            retry_after: Seconds to wait before retrying (if known)
            original: The original exception (if wrapping another error)
            context: Optional additional context
        """
        self.retry_after = retry_after
        ctx = context or {}
        if retry_after is not None:
            ctx["retry_after"] = retry_after
        msg = message or "Rate limit exceeded"
        if retry_after is not None:
            msg = f"{msg} (retry after {retry_after:.1f}s)"
        super().__init__(
            provider=provider,
            message=msg,
            original=original,
            code="RATE_LIMIT_ERROR",
            context=ctx,
        )


class TimeoutError(ProviderError):
    """Timeout error for provider operations.

    Raised when a provider operation times out.
    """

    def __init__(
        self,
        provider: str,
        message: str | None = None,
        timeout_seconds: float | None = None,
        original: Exception | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize timeout error.

        Args:
            provider: Name of the provider that timed out
            message: Human-readable error message
            timeout_seconds: The timeout value that was exceeded
            original: The original exception (if wrapping another error)
            context: Optional additional context
        """
        self.timeout_seconds = timeout_seconds
        ctx = context or {}
        if timeout_seconds is not None:
            ctx["timeout_seconds"] = timeout_seconds
        msg = message or "Operation timed out"
        if timeout_seconds is not None:
            msg = f"{msg} (after {timeout_seconds:.1f}s)"
        super().__init__(
            provider=provider,
            message=msg,
            original=original,
            code="TIMEOUT_ERROR",
            context=ctx,
        )


class ConfigurationError(DomainError):
    """Configuration error.

    Raised when there's an issue with application configuration
    (missing API keys, invalid settings, etc.).
    """

    def __init__(
        self,
        message: str,
        setting: str | None = None,
        code: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize configuration error.

        Args:
            message: Human-readable error message
            setting: The configuration setting that's invalid/missing
            code: Optional error code
            context: Optional additional context
        """
        self.setting = setting
        ctx = context or {}
        if setting:
            ctx["setting"] = setting
        super().__init__(message, code or "CONFIGURATION_ERROR", ctx)
