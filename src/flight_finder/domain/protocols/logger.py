"""Logger protocol (interface).

Defines the contract for logging implementations.
Allows the domain layer to log without depending on a specific logging library.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any, Protocol, runtime_checkable


class LogLevel(IntEnum):
    """Standard log levels."""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@runtime_checkable
class ILogger(Protocol):
    """Protocol for logging implementations.

    This protocol defines the interface that all loggers must implement.
    It provides structured logging with context support.

    Implementations should:
    - Support structured logging with key-value context
    - Be thread-safe and async-safe
    - Include timestamp, level, and message in output
    - Support configurable log levels

    Example implementation:
        class StructLogger:
            @property
            def name(self) -> str:
                return self._name

            def debug(self, message: str, **context: Any) -> None:
                # Implementation here
                ...

            def bind(self, **context: Any) -> ILogger:
                # Return new logger with bound context
                ...

    Usage:
        logger = get_logger("flight_finder.search")
        logger = logger.bind(request_id="abc123")
        logger.info("Search started", criteria=str(criteria))
    """

    @property
    def name(self) -> str:
        """Get the logger name/path.

        Returns:
            The logger name (e.g., "flight_finder.search")
        """
        ...

    def debug(self, message: str, **context: Any) -> None:
        """Log a debug message.

        Args:
            message: The log message
            **context: Additional key-value pairs to include
        """
        ...

    def info(self, message: str, **context: Any) -> None:
        """Log an info message.

        Args:
            message: The log message
            **context: Additional key-value pairs to include
        """
        ...

    def warning(self, message: str, **context: Any) -> None:
        """Log a warning message.

        Args:
            message: The log message
            **context: Additional key-value pairs to include
        """
        ...

    def error(self, message: str, **context: Any) -> None:
        """Log an error message.

        Args:
            message: The log message
            **context: Additional key-value pairs to include
        """
        ...

    def critical(self, message: str, **context: Any) -> None:
        """Log a critical message.

        Args:
            message: The log message
            **context: Additional key-value pairs to include
        """
        ...

    def exception(
        self,
        message: str,
        exc_info: BaseException | None = None,
        **context: Any,
    ) -> None:
        """Log an exception with traceback.

        Args:
            message: The log message
            exc_info: The exception to log (uses current exception if None)
            **context: Additional key-value pairs to include
        """
        ...

    def bind(self, **context: Any) -> ILogger:
        """Create a new logger with additional bound context.

        The returned logger will include the bound context in all log messages.
        This is useful for adding request IDs, user IDs, or other context
        that should be included in all subsequent log messages.

        Args:
            **context: Key-value pairs to bind to the new logger

        Returns:
            A new logger instance with the bound context
        """
        ...

    def with_level(self, level: LogLevel) -> ILogger:
        """Create a new logger with a different log level.

        Args:
            level: The new minimum log level

        Returns:
            A new logger instance with the specified level
        """
        ...
