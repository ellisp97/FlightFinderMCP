"""Error formatting for MCP responses."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from flight_finder.domain.errors.domain_errors import (
    DomainError,
    ProviderError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)


def format_error_response(error: Exception) -> str:
    """Format an error as a JSON response string.

    Args:
        error: The error to format

    Returns:
        JSON string with error details
    """
    response = _build_error_response(error)
    return json.dumps(response, indent=2, default=str)


def _build_error_response(error: Exception) -> dict[str, Any]:
    """Build error response dictionary."""
    if isinstance(error, PydanticValidationError):
        return {
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input parameters",
                "details": _format_pydantic_errors(error),
            },
        }

    if isinstance(error, ValidationError):
        return {
            "success": False,
            "error": {
                "code": error.code,
                "message": error.message,
                "field": error.field,
                "details": error.context,
            },
        }

    if isinstance(error, RateLimitError):
        return {
            "success": False,
            "error": {
                "code": error.code,
                "message": error.message,
                "provider": error.provider,
                "retry_after": error.retry_after,
            },
        }

    if isinstance(error, TimeoutError):
        return {
            "success": False,
            "error": {
                "code": error.code,
                "message": error.message,
                "provider": error.provider,
                "timeout_seconds": error.timeout_seconds,
            },
        }

    if isinstance(error, ProviderError):
        return {
            "success": False,
            "error": {
                "code": error.code,
                "message": error.message,
                "provider": error.provider,
                "details": error.context,
            },
        }

    if isinstance(error, DomainError):
        return {
            "success": False,
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.context,
            },
        }

    return {
        "success": False,
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
        },
    }


def _format_pydantic_errors(error: PydanticValidationError) -> list[dict[str, Any]]:
    """Format Pydantic validation errors."""
    return [
        {
            "field": ".".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in error.errors()
    ]


def format_success_response(data: dict[str, Any], message: str | None = None) -> str:
    """Format a success response as a JSON string.

    Args:
        data: Response data
        message: Optional message

    Returns:
        JSON string with success response
    """
    response: dict[str, Any] = {
        "success": True,
        **data,
    }
    if message:
        response["message"] = message
    return json.dumps(response, indent=2, default=str)
